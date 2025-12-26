#!/usr/bin/env python3
"""
Chronos - Project Management Bot (GitLab Integration)
Location: /opt/chronos-bot/chronos-bot.py

Features:
- GitLab Boards integration for task management
- Create issues with /todo command
- List and manage tasks via slash commands
- Channel-restricted to project-management

Commands:
- /todo <task> - Create a new task/issue
- /tasks - List all open tasks
- /done - List completed tasks
- /board - Show board overview
- /assign <issue_id> - Self-assign an issue
- /close <issue_id> - Close an issue
- /chronos - Show help and bot info
"""

import os
import asyncio
from datetime import datetime
import discord
from discord import app_commands, ui
from discord.ext import commands
import aiohttp
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN', '')
GITLAB_URL = os.environ.get('GITLAB_URL', 'https://gitlab.hrmsmrflrii.xyz')
GITLAB_TOKEN = os.environ.get('GITLAB_TOKEN', '')
GITLAB_PROJECT_ID = os.environ.get('GITLAB_PROJECT_ID', '')  # e.g., "homelab/tasks"
ALLOWED_CHANNELS = os.environ.get('ALLOWED_CHANNELS', 'project-management')

# Parse allowed channels
def parse_allowed_channels(channels_str: str) -> list:
    channels = []
    for ch in channels_str.split(","):
        ch = ch.strip()
        if ch.isdigit():
            channels.append(int(ch))
        else:
            channels.append(ch.lower())
    return channels

ALLOWED_CHANNEL_LIST = parse_allowed_channels(ALLOWED_CHANNELS)

# Discord bot setup
intents = discord.Intents.default()


class ChronosBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.session = None

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        await self.tree.sync()
        logger.info("Slash commands synced")

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()


bot = ChronosBot()


# ============================================================================
# Channel Restriction
# ============================================================================

def is_allowed_channel():
    """Decorator to restrict commands to allowed channels."""
    async def predicate(interaction: discord.Interaction) -> bool:
        channel = interaction.channel
        channel_name = getattr(channel, 'name', '').lower()
        channel_id = getattr(channel, 'id', 0)

        # Debug logging
        logger.info(f"Channel check - name: '{channel_name}', id: {channel_id}, allowed: {ALLOWED_CHANNEL_LIST}")

        # Check by ID first
        if channel_id in ALLOWED_CHANNEL_LIST:
            return True
        # Check by name (case-insensitive)
        if channel_name in ALLOWED_CHANNEL_LIST:
            return True
        # Check if name contains the allowed channel (for threads)
        for allowed in ALLOWED_CHANNEL_LIST:
            if isinstance(allowed, str) and allowed in channel_name:
                return True

        await interaction.response.send_message(
            f"This command can only be used in: **#{', #'.join(str(c) for c in ALLOWED_CHANNEL_LIST)}**",
            ephemeral=True
        )
        return False
    return app_commands.check(predicate)


# ============================================================================
# GitLab API Helpers
# ============================================================================

async def gitlab_request(method: str, endpoint: str, data: dict = None) -> dict:
    """Make a GitLab API request."""
    headers = {
        'PRIVATE-TOKEN': GITLAB_TOKEN,
        'Content-Type': 'application/json'
    }

    url = f"{GITLAB_URL}/api/v4{endpoint}"

    async with bot.session.request(method, url, headers=headers, json=data, ssl=False) as resp:
        if resp.status in [200, 201]:
            return await resp.json()
        else:
            text = await resp.text()
            logger.error(f"GitLab API error: {resp.status} - {text}")
            return None


async def get_project_issues(state: str = 'opened', labels: str = None) -> list:
    """Get issues from the project."""
    endpoint = f"/projects/{GITLAB_PROJECT_ID}/issues?state={state}"
    if labels:
        endpoint += f"&labels={labels}"
    endpoint += "&per_page=50"

    result = await gitlab_request('GET', endpoint)
    return result if result else []


async def create_issue(title: str, description: str = None, labels: list = None) -> dict:
    """Create a new issue."""
    data = {
        'title': title,
        'description': description or '',
        'labels': ','.join(labels) if labels else 'todo'
    }

    result = await gitlab_request('POST', f"/projects/{GITLAB_PROJECT_ID}/issues", data)
    return result


async def update_issue(issue_iid: int, state_event: str = None, labels: list = None) -> dict:
    """Update an issue."""
    data = {}
    if state_event:
        data['state_event'] = state_event
    if labels:
        data['labels'] = ','.join(labels)

    result = await gitlab_request('PUT', f"/projects/{GITLAB_PROJECT_ID}/issues/{issue_iid}", data)
    return result


async def get_boards() -> list:
    """Get project boards."""
    result = await gitlab_request('GET', f"/projects/{GITLAB_PROJECT_ID}/boards")
    return result if result else []


async def get_board_lists(board_id: int) -> list:
    """Get lists in a board."""
    result = await gitlab_request('GET', f"/projects/{GITLAB_PROJECT_ID}/boards/{board_id}/lists")
    return result if result else []


# ============================================================================
# UI Components
# ============================================================================

class TaskSelect(ui.Select):
    """Dropdown for selecting tasks to act on."""

    def __init__(self, issues: list, action: str):
        self.action = action
        options = []
        for issue in issues[:25]:  # Discord limit
            options.append(
                discord.SelectOption(
                    label=f"#{issue['iid']}: {issue['title'][:80]}",
                    value=str(issue['iid']),
                    description=issue.get('labels', [''])[0] if issue.get('labels') else None
                )
            )

        super().__init__(
            placeholder=f"Select a task to {action}...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        issue_iid = int(self.values[0])

        if self.action == 'close':
            result = await update_issue(issue_iid, state_event='close')
            if result:
                await interaction.response.send_message(
                    f" Task #{issue_iid} closed: **{result['title']}**"
                )
            else:
                await interaction.response.send_message(
                    f" Failed to close task #{issue_iid}",
                    ephemeral=True
                )


class TaskSelectView(ui.View):
    def __init__(self, issues: list, action: str):
        super().__init__(timeout=120)
        self.add_item(TaskSelect(issues, action))


# ============================================================================
# Slash Commands
# ============================================================================

@bot.tree.command(name="chronos", description="Show Chronos help and available commands")
@is_allowed_channel()
async def chronos_help(interaction: discord.Interaction):
    """Show help information."""
    embed = discord.Embed(
        title=" Chronos - Project Management",
        description="I help you manage tasks and projects via GitLab integration.",
        color=0x8b5cf6
    )

    embed.add_field(
        name=" Task Management",
        value=(
            "`/todo <task>` - Create a new task\n"
            "`/tasks` - List all open tasks\n"
            "`/done` - List completed tasks\n"
            "`/close` - Close a task"
        ),
        inline=False
    )

    embed.add_field(
        name=" Board & Overview",
        value=(
            "`/board` - Show board overview\n"
            "`/chronos` - Show this help message"
        ),
        inline=False
    )

    embed.add_field(
        name=" GitLab Integration",
        value=f"Connected to: `{GITLAB_URL}`\nProject: `{GITLAB_PROJECT_ID}`",
        inline=False
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="todo", description="Create a new task")
@app_commands.describe(
    task="The task description",
    priority="Task priority (optional)"
)
@app_commands.choices(priority=[
    app_commands.Choice(name="High", value="priority::high"),
    app_commands.Choice(name="Medium", value="priority::medium"),
    app_commands.Choice(name="Low", value="priority::low"),
])
@is_allowed_channel()
async def create_todo(
    interaction: discord.Interaction,
    task: str,
    priority: app_commands.Choice[str] = None
):
    """Create a new task/issue."""
    await interaction.response.defer()

    labels = ['todo']
    if priority:
        labels.append(priority.value)

    # Add creator info to description
    description = f"Created by {interaction.user.name} via Discord\n\n---\n"

    result = await create_issue(task, description, labels)

    if result:
        embed = discord.Embed(
            title=" Task Created",
            color=0x22c55e
        )
        embed.add_field(name="Issue", value=f"#{result['iid']}", inline=True)
        embed.add_field(name="Title", value=result['title'], inline=True)
        if priority:
            embed.add_field(name="Priority", value=priority.name, inline=True)
        embed.add_field(
            name="Link",
            value=f"[View in GitLab]({result['web_url']})",
            inline=False
        )
        embed.set_footer(text=f"Created by {interaction.user.name}")

        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(
            " Failed to create task. Check GitLab connection.",
            ephemeral=True
        )


@bot.tree.command(name="tasks", description="List all open tasks")
@app_commands.describe(label="Filter by label (optional)")
@is_allowed_channel()
async def list_tasks(interaction: discord.Interaction, label: str = None):
    """List all open tasks."""
    await interaction.response.defer()

    issues = await get_project_issues('opened', label)

    if not issues:
        await interaction.followup.send(
            " No open tasks found!" if not label else f" No tasks with label `{label}`"
        )
        return

    embed = discord.Embed(
        title=" Open Tasks",
        description=f"Found **{len(issues)}** open tasks",
        color=0x3b82f6
    )

    # Group by priority
    high = []
    medium = []
    low = []
    other = []

    for issue in issues:
        labels = issue.get('labels', [])
        title = f"#{issue['iid']}: {issue['title'][:50]}"

        if 'priority::high' in labels:
            high.append(title)
        elif 'priority::medium' in labels:
            medium.append(title)
        elif 'priority::low' in labels:
            low.append(title)
        else:
            other.append(title)

    if high:
        embed.add_field(
            name=f" High Priority ({len(high)})",
            value="\n".join(high[:5]) + (f"\n*+{len(high)-5} more*" if len(high) > 5 else ""),
            inline=False
        )

    if medium:
        embed.add_field(
            name=f" Medium Priority ({len(medium)})",
            value="\n".join(medium[:5]) + (f"\n*+{len(medium)-5} more*" if len(medium) > 5 else ""),
            inline=False
        )

    if low:
        embed.add_field(
            name=f" Low Priority ({len(low)})",
            value="\n".join(low[:5]) + (f"\n*+{len(low)-5} more*" if len(low) > 5 else ""),
            inline=False
        )

    if other:
        embed.add_field(
            name=f" Other ({len(other)})",
            value="\n".join(other[:5]) + (f"\n*+{len(other)-5} more*" if len(other) > 5 else ""),
            inline=False
        )

    embed.set_footer(text=f"Use /close to complete a task | GitLab: {GITLAB_PROJECT_ID}")

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="done", description="List completed tasks")
@is_allowed_channel()
async def list_done(interaction: discord.Interaction):
    """List completed tasks."""
    await interaction.response.defer()

    issues = await get_project_issues('closed')

    if not issues:
        await interaction.followup.send(" No completed tasks found!")
        return

    # Get recent 10
    recent = issues[:10]

    embed = discord.Embed(
        title=" Completed Tasks",
        description=f"**{len(issues)}** tasks completed (showing recent 10)",
        color=0x22c55e
    )

    task_list = []
    for issue in recent:
        closed_at = issue.get('closed_at', '')[:10] if issue.get('closed_at') else 'Unknown'
        task_list.append(f" #{issue['iid']}: {issue['title'][:40]} *({closed_at})*")

    embed.add_field(
        name="Recent Completions",
        value="\n".join(task_list),
        inline=False
    )

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="close", description="Close a task")
@is_allowed_channel()
async def close_task(interaction: discord.Interaction):
    """Close a task with dropdown selection."""
    issues = await get_project_issues('opened')

    if not issues:
        await interaction.response.send_message(
            " No open tasks to close!",
            ephemeral=True
        )
        return

    view = TaskSelectView(issues, 'close')

    embed = discord.Embed(
        title=" Close Task",
        description="Select a task to mark as completed:",
        color=0xf59e0b
    )

    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="board", description="Show board overview")
@is_allowed_channel()
async def show_board(interaction: discord.Interaction):
    """Show board overview."""
    await interaction.response.defer()

    boards = await get_boards()

    if not boards:
        await interaction.followup.send(
            " No boards found. Create one in GitLab first.",
            ephemeral=True
        )
        return

    board = boards[0]  # Use first board
    board_lists = await get_board_lists(board['id'])

    embed = discord.Embed(
        title=f" {board.get('name', 'Project Board')}",
        color=0x8b5cf6
    )

    # Get issue counts per list
    for lst in board_lists:
        label = lst.get('label', {})
        label_name = label.get('name', 'Backlog') if label else 'Open'

        # Get issues with this label
        if label:
            issues = await get_project_issues('opened', label_name)
            count = len(issues) if issues else 0
        else:
            issues = await get_project_issues('opened')
            count = len(issues) if issues else 0

        emoji = ""
        if 'done' in label_name.lower() or 'closed' in label_name.lower():
            emoji = ""
        elif 'progress' in label_name.lower() or 'doing' in label_name.lower():
            emoji = ""
        elif 'review' in label_name.lower():
            emoji = ""

        embed.add_field(
            name=f"{emoji} {label_name}",
            value=f"**{count}** issues",
            inline=True
        )

    embed.add_field(
        name=" View Board",
        value=f"[Open in GitLab]({GITLAB_URL}/{GITLAB_PROJECT_ID}/-/boards)",
        inline=False
    )

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="quick", description="Quick add multiple tasks")
@app_commands.describe(tasks="Tasks separated by semicolons (;)")
@is_allowed_channel()
async def quick_add(interaction: discord.Interaction, tasks: str):
    """Quick add multiple tasks at once."""
    await interaction.response.defer()

    task_list = [t.strip() for t in tasks.split(';') if t.strip()]

    if not task_list:
        await interaction.followup.send(
            " No tasks provided. Separate tasks with semicolons (;)",
            ephemeral=True
        )
        return

    created = []
    failed = []

    for task in task_list[:10]:  # Limit to 10
        result = await create_issue(task, f"Quick add by {interaction.user.name}", ['todo'])
        if result:
            created.append(f"#{result['iid']}: {task[:30]}")
        else:
            failed.append(task[:30])

    embed = discord.Embed(
        title=" Quick Add Results",
        color=0x22c55e if not failed else 0xf59e0b
    )

    if created:
        embed.add_field(
            name=f" Created ({len(created)})",
            value="\n".join(created),
            inline=False
        )

    if failed:
        embed.add_field(
            name=f" Failed ({len(failed)})",
            value="\n".join(failed),
            inline=False
        )

    await interaction.followup.send(embed=embed)


# ============================================================================
# Events
# ============================================================================

@bot.event
async def on_ready():
    logger.info(f'Chronos logged in as {bot.user}')

    # Send welcome message
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.name.lower() in ALLOWED_CHANNEL_LIST or channel.id in ALLOWED_CHANNEL_LIST:
                embed = discord.Embed(
                    title=" Chronos Online",
                    description="Project Management Bot connected to GitLab.",
                    color=0x8b5cf6
                )
                embed.add_field(
                    name=" Commands",
                    value="`/todo` `/tasks` `/done` `/close` `/board` `/quick` `/chronos`",
                    inline=False
                )
                embed.add_field(
                    name=" GitLab",
                    value=f"Connected to: `{GITLAB_PROJECT_ID}`",
                    inline=False
                )

                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    logger.error(f"Could not send welcome: {e}")
                break


def main():
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN required")
        return

    if not GITLAB_TOKEN:
        logger.error("GITLAB_TOKEN required")
        return

    if not GITLAB_PROJECT_ID:
        logger.error("GITLAB_PROJECT_ID required (e.g., 'homelab/tasks' or numeric ID)")
        return

    bot.run(DISCORD_TOKEN)


if __name__ == '__main__':
    main()
