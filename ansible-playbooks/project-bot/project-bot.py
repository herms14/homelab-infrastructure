#!/usr/bin/env python3
"""
Project Bot - Discord-GitLab Kanban Integration
Manages homelab tasks via Discord slash commands with GitLab board sync.

Commands:
  /todo <task>     - Create task in "To Do" column
  /idea <task>     - Create task in "Backlog" column
  /doing <task>    - Create task in "In Progress" column
  /done <id>       - Mark task as done (close issue)
  /move <id> <col> - Move task between columns
  /list [column]   - List tasks (optionally by column)
  /board           - Show board summary
  /search <query>  - Search tasks

Task Syntax:
  [high/medium/low] - Priority label
  [infra/media/k8s/monitoring/automation/docs] - Category label
  @tomorrow/@friday/@monday/etc - Due date

Example: /todo [high] [infra] Fix DNS issue @friday
"""

import os
import re
import logging
import asyncio
import threading
import hmac
import hashlib
from datetime import datetime, timedelta, time
from typing import Optional, List, Dict, Any

import discord
from discord import app_commands
from discord.ext import commands, tasks
import gitlab
from flask import Flask, request, jsonify

# === Logging Configuration ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('project-bot')

# === Environment Configuration ===
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', '0'))
GITLAB_URL = os.getenv('GITLAB_URL', 'https://gitlab.hrmsmrflrii.xyz')
GITLAB_TOKEN = os.getenv('GITLAB_TOKEN')
GITLAB_PROJECT_ID = os.getenv('GITLAB_PROJECT_ID')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '5055'))
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')
DAILY_DIGEST_HOUR = int(os.getenv('DAILY_DIGEST_HOUR', '9'))
TZ = os.getenv('TZ', 'Asia/Manila')

# === Label Configuration ===
COLUMN_LABELS = {
    'backlog': 'Backlog',
    'todo': 'To Do',
    'doing': 'In Progress',
    'review': 'In Review',
    'testing': 'Testing',
    'blocked': 'Blocked',
    'done': 'Done'
}

PRIORITY_LABELS = {
    'critical': 'priority::critical',
    'high': 'priority::high',
    'medium': 'priority::medium',
    'low': 'priority::low'
}

CATEGORY_LABELS = {
    'infra': 'infra',
    'media': 'media',
    'k8s': 'k8s',
    'monitoring': 'monitoring',
    'automation': 'automation',
    'docs': 'docs'
}

# Priority colors for embeds
PRIORITY_COLORS = {
    'critical': 0x721c24,  # Dark Red
    'high': 0xdc3545,      # Red
    'medium': 0xfd7e14,    # Orange
    'low': 0x28a745,       # Green
    'default': 0x007bff    # Blue
}

# Column colors for embeds
COLUMN_COLORS = {
    'Backlog': 0x6c757d,      # Gray
    'To Do': 0x007bff,        # Blue
    'In Progress': 0xfd7e14,  # Orange
    'In Review': 0x6f42c1,    # Purple
    'Testing': 0x17a2b8,      # Cyan
    'Blocked': 0xdc3545,      # Red
    'Done': 0x28a745          # Green
}

# Due date parsing patterns
DUE_DATE_PATTERNS = {
    '@today': 0,
    '@tomorrow': 1,
    '@monday': None,  # Calculated dynamically
    '@tuesday': None,
    '@wednesday': None,
    '@thursday': None,
    '@friday': None,
    '@saturday': None,
    '@sunday': None,
    '@nextweek': 7
}

# === GitLab Client ===
gl: Optional[gitlab.Gitlab] = None
project: Optional[Any] = None

def init_gitlab():
    """Initialize GitLab client and project."""
    global gl, project
    try:
        gl = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_TOKEN)
        gl.auth()
        project = gl.projects.get(GITLAB_PROJECT_ID)
        logger.info(f"Connected to GitLab project: {project.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to GitLab: {e}")
        return False

# === Task Parsing ===
def parse_task_input(text: str) -> Dict[str, Any]:
    """
    Parse task input for priority, category, due date, and title.

    Example: "[high] [infra] Fix DNS issue @friday"
    Returns: {
        'title': 'Fix DNS issue',
        'priority': 'high',
        'category': 'infra',
        'due_date': '2024-01-05'
    }
    """
    result = {
        'title': text,
        'priority': None,
        'category': None,
        'due_date': None,
        'labels': []
    }

    # Extract priority [high], [medium], [low]
    priority_match = re.search(r'\[(high|medium|low)\]', text, re.IGNORECASE)
    if priority_match:
        result['priority'] = priority_match.group(1).lower()
        result['labels'].append(PRIORITY_LABELS[result['priority']])
        text = text.replace(priority_match.group(0), '').strip()

    # Extract category [infra], [media], etc.
    for cat in CATEGORY_LABELS:
        cat_match = re.search(rf'\[{cat}\]', text, re.IGNORECASE)
        if cat_match:
            result['category'] = cat
            result['labels'].append(CATEGORY_LABELS[cat])
            text = text.replace(cat_match.group(0), '').strip()
            break

    # Extract due date @tomorrow, @friday, etc.
    due_match = re.search(r'@(\w+)', text)
    if due_match:
        due_key = f"@{due_match.group(1).lower()}"
        if due_key in DUE_DATE_PATTERNS:
            result['due_date'] = calculate_due_date(due_key)
            text = text.replace(due_match.group(0), '').strip()

    # Clean up title
    result['title'] = ' '.join(text.split())  # Normalize whitespace

    return result

def calculate_due_date(due_key: str) -> str:
    """Calculate actual date from due key like @friday."""
    today = datetime.now()

    if due_key == '@today':
        target = today
    elif due_key == '@tomorrow':
        target = today + timedelta(days=1)
    elif due_key == '@nextweek':
        target = today + timedelta(days=7)
    else:
        # Day of week
        day_names = ['@monday', '@tuesday', '@wednesday', '@thursday', '@friday', '@saturday', '@sunday']
        if due_key in day_names:
            target_weekday = day_names.index(due_key)
            current_weekday = today.weekday()
            days_ahead = target_weekday - current_weekday
            if days_ahead <= 0:
                days_ahead += 7
            target = today + timedelta(days=days_ahead)
        else:
            target = today + timedelta(days=1)  # Default to tomorrow

    return target.strftime('%Y-%m-%d')

# === GitLab API Helpers ===
def create_issue(title: str, column: str, labels: List[str] = None, due_date: str = None) -> Optional[Any]:
    """Create a new issue in GitLab with specified labels."""
    if not project:
        return None

    try:
        issue_labels = [COLUMN_LABELS.get(column, 'To Do')]
        if labels:
            issue_labels.extend(labels)

        issue_data = {
            'title': title,
            'labels': issue_labels
        }

        if due_date:
            issue_data['due_date'] = due_date

        issue = project.issues.create(issue_data)
        logger.info(f"Created issue #{issue.iid}: {title}")
        return issue
    except Exception as e:
        logger.error(f"Failed to create issue: {e}")
        return None

def get_issue(issue_iid: int) -> Optional[Any]:
    """Get an issue by its IID (internal ID)."""
    if not project:
        return None
    try:
        return project.issues.get(issue_iid)
    except Exception as e:
        logger.error(f"Failed to get issue #{issue_iid}: {e}")
        return None

def update_issue_column(issue_iid: int, new_column: str) -> bool:
    """Move an issue to a different column by updating labels."""
    if not project:
        return False

    try:
        issue = project.issues.get(issue_iid)
        current_labels = issue.labels

        # Remove existing column labels
        new_labels = [l for l in current_labels if l not in COLUMN_LABELS.values()]

        # Add new column label
        new_labels.append(COLUMN_LABELS.get(new_column, 'To Do'))

        issue.labels = new_labels
        issue.save()
        logger.info(f"Moved issue #{issue_iid} to {new_column}")
        return True
    except Exception as e:
        logger.error(f"Failed to move issue #{issue_iid}: {e}")
        return False

def close_issue(issue_iid: int) -> bool:
    """Close an issue and add Done label."""
    if not project:
        return False

    try:
        issue = project.issues.get(issue_iid)

        # Update labels - remove other columns, add Done
        current_labels = issue.labels
        new_labels = [l for l in current_labels if l not in COLUMN_LABELS.values()]
        new_labels.append('Done')

        issue.labels = new_labels
        issue.state_event = 'close'
        issue.save()
        logger.info(f"Closed issue #{issue_iid}")
        return True
    except Exception as e:
        logger.error(f"Failed to close issue #{issue_iid}: {e}")
        return False

def get_issues_by_column(column: str = None) -> List[Any]:
    """Get issues filtered by column label."""
    if not project:
        return []

    try:
        params = {'state': 'opened'}
        if column and column in COLUMN_LABELS:
            params['labels'] = [COLUMN_LABELS[column]]

        issues = project.issues.list(**params, all=True)
        return list(issues)
    except Exception as e:
        logger.error(f"Failed to get issues: {e}")
        return []

def get_board_summary() -> Dict[str, int]:
    """Get count of issues per column."""
    if not project:
        return {}

    summary = {}
    try:
        for key, label in COLUMN_LABELS.items():
            if key == 'done':
                # Count closed issues with Done label
                issues = project.issues.list(state='closed', labels=[label], all=True)
            else:
                issues = project.issues.list(state='opened', labels=[label], all=True)
            summary[label] = len(list(issues))
        return summary
    except Exception as e:
        logger.error(f"Failed to get board summary: {e}")
        return {}

def search_issues(query: str) -> List[Any]:
    """Search issues by title or description."""
    if not project:
        return []

    try:
        issues = project.issues.list(search=query, all=True)
        return list(issues)
    except Exception as e:
        logger.error(f"Failed to search issues: {e}")
        return []

# === Discord Bot Setup ===
intents = discord.Intents.default()
# Note: message_content intent not needed for slash commands
# If you want to enable prefix commands, enable "Message Content Intent"
# in Discord Developer Portal and uncomment the line below:
# intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Track bot-initiated changes to prevent webhook loops
bot_initiated_changes = set()

# === Discord Slash Commands ===
@bot.tree.command(name="todo", description="Create a new task in the To Do column")
@app_commands.describe(task="Task description (supports [priority], [category], @due)")
async def todo_command(interaction: discord.Interaction, task: str):
    """Create a task in To Do column."""
    await create_task_command(interaction, task, 'todo')

@bot.tree.command(name="idea", description="Create a new idea in the Backlog column")
@app_commands.describe(task="Idea description (supports [priority], [category], @due)")
async def idea_command(interaction: discord.Interaction, task: str):
    """Create a task in Backlog column."""
    await create_task_command(interaction, task, 'backlog')

@bot.tree.command(name="doing", description="Create a task and start working on it")
@app_commands.describe(task="Task description (supports [priority], [category], @due)")
async def doing_command(interaction: discord.Interaction, task: str):
    """Create a task in In Progress column."""
    await create_task_command(interaction, task, 'doing')


@bot.tree.command(name="review", description="Move a task to In Review")
@app_commands.describe(issue_id="Issue number (e.g., 5 or #5)")
async def review_command(interaction: discord.Interaction, issue_id: str):
    """Move an issue to In Review column."""
    await interaction.response.defer()
    iid = int(re.sub(r'[#\s]', '', issue_id))
    issue = get_issue(iid)
    if not issue:
        await interaction.followup.send(f"Issue #{iid} not found.", ephemeral=True)
        return
    if update_issue_column(iid, 'review'):
        bot_initiated_changes.add(iid)
        embed = discord.Embed(
            title=f"#{iid} {issue.title}",
            url=issue.web_url,
            color=COLUMN_COLORS['In Review']
        )
        embed.add_field(name="Status", value="In Review", inline=True)
        embed.set_footer(text="Ready for review")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Failed to move issue #{iid}.", ephemeral=True)


@bot.tree.command(name="testing", description="Move a task to Testing")
@app_commands.describe(issue_id="Issue number (e.g., 5 or #5)")
async def testing_command(interaction: discord.Interaction, issue_id: str):
    """Move an issue to Testing column."""
    await interaction.response.defer()
    iid = int(re.sub(r'[#\s]', '', issue_id))
    issue = get_issue(iid)
    if not issue:
        await interaction.followup.send(f"Issue #{iid} not found.", ephemeral=True)
        return
    if update_issue_column(iid, 'testing'):
        bot_initiated_changes.add(iid)
        embed = discord.Embed(
            title=f"#{iid} {issue.title}",
            url=issue.web_url,
            color=COLUMN_COLORS['Testing']
        )
        embed.add_field(name="Status", value="Testing", inline=True)
        embed.set_footer(text="In QA/Testing")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Failed to move issue #{iid}.", ephemeral=True)


@bot.tree.command(name="block", description="Mark a task as blocked")
@app_commands.describe(issue_id="Issue number (e.g., 5 or #5)", reason="Reason for blocking (optional)")
async def block_command(interaction: discord.Interaction, issue_id: str, reason: str = None):
    """Move an issue to Blocked column."""
    await interaction.response.defer()
    iid = int(re.sub(r'[#\s]', '', issue_id))
    issue = get_issue(iid)
    if not issue:
        await interaction.followup.send(f"Issue #{iid} not found.", ephemeral=True)
        return
    if update_issue_column(iid, 'blocked'):
        bot_initiated_changes.add(iid)
        embed = discord.Embed(
            title=f"#{iid} {issue.title}",
            url=issue.web_url,
            color=COLUMN_COLORS['Blocked']
        )
        embed.add_field(name="Status", value="BLOCKED", inline=True)
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text="Task is blocked")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Failed to move issue #{iid}.", ephemeral=True)


@bot.tree.command(name="unblock", description="Unblock a task and move it back to In Progress")
@app_commands.describe(issue_id="Issue number (e.g., 5 or #5)")
async def unblock_command(interaction: discord.Interaction, issue_id: str):
    """Move a blocked issue back to In Progress."""
    await interaction.response.defer()
    iid = int(re.sub(r'[#\s]', '', issue_id))
    issue = get_issue(iid)
    if not issue:
        await interaction.followup.send(f"Issue #{iid} not found.", ephemeral=True)
        return
    if update_issue_column(iid, 'doing'):
        bot_initiated_changes.add(iid)
        embed = discord.Embed(
            title=f"#{iid} {issue.title}",
            url=issue.web_url,
            color=COLUMN_COLORS['In Progress']
        )
        embed.add_field(name="Status", value="Unblocked - In Progress", inline=True)
        embed.set_footer(text="Task unblocked")
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Failed to unblock issue #{iid}.", ephemeral=True)

async def create_task_command(interaction: discord.Interaction, task: str, column: str):
    """Common handler for creating tasks."""
    await interaction.response.defer()

    # Parse task input
    parsed = parse_task_input(task)

    if not parsed['title']:
        await interaction.followup.send("Please provide a task description.", ephemeral=True)
        return

    # Create issue in GitLab
    issue = create_issue(
        title=parsed['title'],
        column=column,
        labels=parsed['labels'],
        due_date=parsed['due_date']
    )

    if issue:
        # Track this change to prevent webhook loop
        bot_initiated_changes.add(issue.iid)

        # Build embed
        color = PRIORITY_COLORS.get(parsed['priority'], PRIORITY_COLORS['default'])
        embed = discord.Embed(
            title=f"#{issue.iid} {parsed['title']}",
            url=issue.web_url,
            color=color
        )
        embed.add_field(name="Column", value=COLUMN_LABELS[column], inline=True)

        if parsed['priority']:
            embed.add_field(name="Priority", value=parsed['priority'].title(), inline=True)
        if parsed['category']:
            embed.add_field(name="Category", value=parsed['category'], inline=True)
        if parsed['due_date']:
            embed.add_field(name="Due", value=parsed['due_date'], inline=True)

        embed.set_footer(text="Created via Discord")
        embed.timestamp = datetime.utcnow()

        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("Failed to create task. Check GitLab connection.", ephemeral=True)

@bot.tree.command(name="done", description="Mark a task as done")
@app_commands.describe(issue_id="Issue number (e.g., 5 or #5)")
async def done_command(interaction: discord.Interaction, issue_id: str):
    """Close an issue and mark it as done."""
    await interaction.response.defer()

    # Parse issue ID
    iid = int(re.sub(r'[#\s]', '', issue_id))

    issue = get_issue(iid)
    if not issue:
        await interaction.followup.send(f"Issue #{iid} not found.", ephemeral=True)
        return

    if close_issue(iid):
        bot_initiated_changes.add(iid)

        embed = discord.Embed(
            title=f"#{iid} {issue.title}",
            url=issue.web_url,
            color=COLUMN_COLORS['Done']
        )
        embed.add_field(name="Status", value="Done", inline=True)
        embed.set_footer(text="Closed via Discord")
        embed.timestamp = datetime.utcnow()

        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Failed to close issue #{iid}.", ephemeral=True)

@bot.tree.command(name="move", description="Move a task to a different column")
@app_commands.describe(
    issue_id="Issue number (e.g., 5 or #5)",
    column="Target column"
)
@app_commands.choices(column=[
    app_commands.Choice(name="Backlog", value="backlog"),
    app_commands.Choice(name="To Do", value="todo"),
    app_commands.Choice(name="In Progress", value="doing"),
    app_commands.Choice(name="In Review", value="review"),
    app_commands.Choice(name="Testing", value="testing"),
    app_commands.Choice(name="Blocked", value="blocked"),
    app_commands.Choice(name="Done", value="done")
])
async def move_command(interaction: discord.Interaction, issue_id: str, column: app_commands.Choice[str]):
    """Move an issue to a different column."""
    await interaction.response.defer()

    iid = int(re.sub(r'[#\s]', '', issue_id))

    issue = get_issue(iid)
    if not issue:
        await interaction.followup.send(f"Issue #{iid} not found.", ephemeral=True)
        return

    if column.value == 'done':
        success = close_issue(iid)
    else:
        success = update_issue_column(iid, column.value)

    if success:
        bot_initiated_changes.add(iid)

        embed = discord.Embed(
            title=f"#{iid} {issue.title}",
            url=issue.web_url,
            color=COLUMN_COLORS.get(COLUMN_LABELS[column.value], 0x007bff)
        )
        embed.add_field(name="Moved to", value=column.name, inline=True)
        embed.set_footer(text="Updated via Discord")
        embed.timestamp = datetime.utcnow()

        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Failed to move issue #{iid}.", ephemeral=True)

@bot.tree.command(name="list", description="List tasks (optionally by column)")
@app_commands.describe(column="Filter by column (optional)")
@app_commands.choices(column=[
    app_commands.Choice(name="All", value="all"),
    app_commands.Choice(name="Backlog", value="backlog"),
    app_commands.Choice(name="To Do", value="todo"),
    app_commands.Choice(name="In Progress", value="doing"),
    app_commands.Choice(name="In Review", value="review"),
    app_commands.Choice(name="Testing", value="testing"),
    app_commands.Choice(name="Blocked", value="blocked")
])
async def list_command(interaction: discord.Interaction, column: app_commands.Choice[str] = None):
    """List issues, optionally filtered by column."""
    await interaction.response.defer()

    col_value = column.value if column and column.value != 'all' else None
    issues = get_issues_by_column(col_value)

    if not issues:
        msg = "No open tasks found."
        if col_value:
            msg = f"No tasks in {COLUMN_LABELS.get(col_value, col_value)}."
        await interaction.followup.send(msg)
        return

    # Group by column
    grouped = {}
    for issue in issues:
        col = 'Other'
        for label in issue.labels:
            if label in COLUMN_LABELS.values():
                col = label
                break
        if col not in grouped:
            grouped[col] = []
        grouped[col].append(issue)

    # Build embed
    embed = discord.Embed(
        title="Homelab Tasks",
        color=0x007bff
    )

    for col_name in ['Backlog', 'To Do', 'In Progress', 'In Review', 'Testing', 'Blocked']:
        if col_name in grouped:
            task_list = []
            for issue in grouped[col_name][:10]:  # Limit to 10 per column
                priority = ''
                for label in issue.labels:
                    if 'priority::' in label:
                        p = label.replace('priority::', '')
                        priority = f" [{p}]"
                        break
                due = f" (due {issue.due_date})" if issue.due_date else ""
                task_list.append(f"• #{issue.iid} {issue.title}{priority}{due}")

            if len(grouped[col_name]) > 10:
                task_list.append(f"... and {len(grouped[col_name]) - 10} more")

            embed.add_field(
                name=f"{col_name} ({len(grouped[col_name])})",
                value='\n'.join(task_list) or "None",
                inline=False
            )

    embed.set_footer(text=f"Total: {len(issues)} open tasks")
    embed.timestamp = datetime.utcnow()

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="board", description="Show board summary")
async def board_command(interaction: discord.Interaction):
    """Show summary of issues per column."""
    await interaction.response.defer()

    summary = get_board_summary()

    if not summary:
        await interaction.followup.send("Failed to get board summary.", ephemeral=True)
        return

    embed = discord.Embed(
        title="Homelab Tasks Board",
        color=0x007bff
    )

    total = 0
    for col_name in ['Backlog', 'To Do', 'In Progress', 'Done']:
        count = summary.get(col_name, 0)
        total += count
        emoji = {'Backlog': '', 'To Do': '', 'In Progress': '', 'Done': ''}
        embed.add_field(
            name=f"{emoji.get(col_name, '')} {col_name}",
            value=str(count),
            inline=True
        )

    embed.set_footer(text=f"Total: {total} tasks")
    embed.timestamp = datetime.utcnow()

    # Add link to GitLab board
    if project:
        embed.url = f"{GITLAB_URL}/{project.path_with_namespace}/-/boards"

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="search", description="Search for tasks")
@app_commands.describe(query="Search query")
async def search_command(interaction: discord.Interaction, query: str):
    """Search issues by title or description."""
    await interaction.response.defer()

    issues = search_issues(query)

    if not issues:
        await interaction.followup.send(f"No tasks found matching '{query}'.")
        return

    embed = discord.Embed(
        title=f"Search Results: {query}",
        color=0x007bff
    )

    for issue in issues[:15]:  # Limit to 15 results
        status = "Done" if issue.state == 'closed' else "Open"
        col = "Unknown"
        for label in issue.labels:
            if label in COLUMN_LABELS.values():
                col = label
                break

        embed.add_field(
            name=f"#{issue.iid} {issue.title}",
            value=f"Status: {status} | Column: {col}",
            inline=False
        )

    if len(issues) > 15:
        embed.set_footer(text=f"Showing 15 of {len(issues)} results")
    else:
        embed.set_footer(text=f"Found {len(issues)} task(s)")

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="details", description="Show detailed information about a task")
@app_commands.describe(issue_id="Issue number (e.g., 5 or #5)")
async def details_command(interaction: discord.Interaction, issue_id: str):
    """Show detailed task info including activity log."""
    await interaction.response.defer()

    iid = int(re.sub(r'[#\s]', '', issue_id))

    issue = get_issue(iid)
    if not issue:
        await interaction.followup.send(f"Issue #{iid} not found.", ephemeral=True)
        return

    # Determine priority and column
    priority = None
    column = "Unknown"
    category = None
    for label in issue.labels:
        if 'priority::' in label:
            priority = label.replace('priority::', '').title()
        elif label in COLUMN_LABELS.values():
            column = label
        elif label in CATEGORY_LABELS.values():
            category = label

    # Get priority color
    color = PRIORITY_COLORS.get(priority.lower() if priority else 'default', PRIORITY_COLORS['default'])

    embed = discord.Embed(
        title=f"#{issue.iid} {issue.title}",
        url=issue.web_url,
        color=color
    )

    # Status and column
    status = "Closed" if issue.state == 'closed' else "Open"
    embed.add_field(name="Status", value=status, inline=True)
    embed.add_field(name="Column", value=column, inline=True)

    if priority:
        embed.add_field(name="Priority", value=priority, inline=True)
    if category:
        embed.add_field(name="Category", value=category, inline=True)

    # Due date
    if issue.due_date:
        today = datetime.now().strftime('%Y-%m-%d')
        if issue.due_date < today:
            due_status = f"{issue.due_date} (OVERDUE)"
        elif issue.due_date == today:
            due_status = f"{issue.due_date} (TODAY)"
        else:
            days_until = (datetime.strptime(issue.due_date, '%Y-%m-%d') - datetime.now()).days + 1
            due_status = f"{issue.due_date} ({days_until} days)"
        embed.add_field(name="Due Date", value=due_status, inline=True)

    # Dates
    created_at = datetime.fromisoformat(issue.created_at.replace('Z', '+00:00'))
    updated_at = datetime.fromisoformat(issue.updated_at.replace('Z', '+00:00'))
    embed.add_field(name="Created", value=created_at.strftime('%Y-%m-%d %H:%M'), inline=True)
    embed.add_field(name="Last Updated", value=updated_at.strftime('%Y-%m-%d %H:%M'), inline=True)

    # Days since last activity
    days_inactive = (datetime.now() - updated_at.replace(tzinfo=None)).days
    if days_inactive > 0:
        embed.add_field(name="Inactive", value=f"{days_inactive} days", inline=True)

    # Description (truncated)
    if issue.description:
        desc = issue.description[:500] + "..." if len(issue.description) > 500 else issue.description
        embed.add_field(name="Description", value=desc, inline=False)

    # Get recent activity (notes/comments)
    try:
        notes = issue.notes.list(per_page=5, order_by='created_at', sort='desc')
        if notes:
            activity = []
            for note in notes[:5]:
                if note.system:  # System notes (label changes, etc.)
                    note_date = datetime.fromisoformat(note.created_at.replace('Z', '+00:00'))
                    activity.append(f"• {note_date.strftime('%m/%d')}: {note.body[:80]}")
            if activity:
                embed.add_field(name="Recent Activity", value='\n'.join(activity[:5]), inline=False)
    except Exception as e:
        logger.debug(f"Could not fetch notes for #{iid}: {e}")

    # All labels
    if issue.labels:
        embed.add_field(name="Labels", value=", ".join(issue.labels), inline=False)

    embed.set_footer(text="Task Details")
    embed.timestamp = datetime.utcnow()

    await interaction.followup.send(embed=embed)

# === Due Date Reminders ===
REMINDER_DAYS_BEFORE = int(os.getenv('REMINDER_DAYS_BEFORE', '2'))
STALE_DAYS_THRESHOLD = int(os.getenv('STALE_DAYS_THRESHOLD', '7'))

@tasks.loop(hours=6)
async def due_date_reminders():
    """Check for tasks approaching their due date and send reminders."""
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if not channel:
        logger.warning("Could not find channel for due date reminders")
        return

    issues = get_issues_by_column()
    if not issues:
        return

    today = datetime.now().date()
    reminder_date = (today + timedelta(days=REMINDER_DAYS_BEFORE)).strftime('%Y-%m-%d')

    # Find tasks due in REMINDER_DAYS_BEFORE days
    upcoming = [i for i in issues if i.due_date == reminder_date]

    if not upcoming:
        logger.debug(f"No tasks due in {REMINDER_DAYS_BEFORE} days")
        return

    embed = discord.Embed(
        title=f"Tasks Due in {REMINDER_DAYS_BEFORE} Days",
        description=f"The following tasks are due on **{reminder_date}**:",
        color=0xfd7e14  # Orange warning color
    )

    for issue in upcoming[:10]:
        priority = ""
        column = "Unknown"
        for label in issue.labels:
            if 'priority::' in label:
                priority = f" [{label.replace('priority::', '').title()}]"
            if label in COLUMN_LABELS.values():
                column = label

        embed.add_field(
            name=f"#{issue.iid} {issue.title}{priority}",
            value=f"Column: {column} | [View in GitLab]({issue.web_url})",
            inline=False
        )

    embed.set_footer(text=f"Due date reminder - {REMINDER_DAYS_BEFORE} days notice")
    embed.timestamp = datetime.utcnow()

    await channel.send(embed=embed)
    logger.info(f"Sent due date reminder for {len(upcoming)} task(s)")

@due_date_reminders.before_loop
async def before_due_date_reminders():
    await bot.wait_until_ready()


# === Stale Critical Task Monitoring ===
@tasks.loop(hours=12)
async def stale_task_monitor():
    """Alert when high-priority tasks haven't been updated for STALE_DAYS_THRESHOLD days."""
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if not channel:
        logger.warning("Could not find channel for stale task monitor")
        return

    if not project:
        return

    try:
        # Get all high-priority open issues
        issues = project.issues.list(
            state='opened',
            labels=['priority::high'],
            all=True
        )

        stale_threshold = datetime.now() - timedelta(days=STALE_DAYS_THRESHOLD)
        stale_tasks = []

        for issue in issues:
            # Check last activity date
            updated_at = datetime.fromisoformat(issue.updated_at.replace('Z', '+00:00'))
            updated_at = updated_at.replace(tzinfo=None)  # Make naive for comparison

            if updated_at < stale_threshold:
                days_stale = (datetime.now() - updated_at).days
                stale_tasks.append((issue, days_stale))

        if not stale_tasks:
            logger.debug("No stale high-priority tasks found")
            return

        embed = discord.Embed(
            title="Stale High-Priority Tasks",
            description=f"The following **critical tasks** haven't been updated in {STALE_DAYS_THRESHOLD}+ days:",
            color=0xdc3545  # Red alert color
        )

        for issue, days in sorted(stale_tasks, key=lambda x: -x[1])[:10]:
            column = "Unknown"
            for label in issue.labels:
                if label in COLUMN_LABELS.values():
                    column = label
                    break

            embed.add_field(
                name=f"#{issue.iid} {issue.title}",
                value=f"Column: {column} | Stale for **{days} days**\n[View in GitLab]({issue.web_url})",
                inline=False
            )

        embed.set_footer(text=f"Stale task alert - Tasks inactive for {STALE_DAYS_THRESHOLD}+ days")
        embed.timestamp = datetime.utcnow()

        await channel.send(embed=embed)
        logger.info(f"Sent stale task alert for {len(stale_tasks)} task(s)")

    except Exception as e:
        logger.error(f"Error in stale task monitor: {e}")

@stale_task_monitor.before_loop
async def before_stale_task_monitor():
    await bot.wait_until_ready()


# === Daily Digest ===
@tasks.loop(time=time(hour=DAILY_DIGEST_HOUR, minute=0))
async def daily_digest():
    """Send daily summary of tasks."""
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if not channel:
        logger.warning("Could not find channel for daily digest")
        return

    summary = get_board_summary()
    issues = get_issues_by_column()

    embed = discord.Embed(
        title="Daily Task Digest",
        description="Good morning! Here's your task summary:",
        color=0x007bff
    )

    # Summary counts
    for col_name in ['To Do', 'In Progress', 'Backlog']:
        count = summary.get(col_name, 0)
        embed.add_field(name=col_name, value=str(count), inline=True)

    # High priority tasks
    high_priority = [i for i in issues if 'priority::high' in i.labels]
    if high_priority:
        hp_list = [f"• #{i.iid} {i.title}" for i in high_priority[:5]]
        embed.add_field(
            name="High Priority Tasks",
            value='\n'.join(hp_list),
            inline=False
        )

    # Overdue tasks
    today = datetime.now().strftime('%Y-%m-%d')
    overdue = [i for i in issues if i.due_date and i.due_date < today]
    if overdue:
        od_list = [f"• #{i.iid} {i.title} (due {i.due_date})" for i in overdue[:5]]
        embed.add_field(
            name="Overdue Tasks",
            value='\n'.join(od_list),
            inline=False
        )

    # Due today
    due_today = [i for i in issues if i.due_date == today]
    if due_today:
        dt_list = [f"• #{i.iid} {i.title}" for i in due_today[:5]]
        embed.add_field(
            name="Due Today",
            value='\n'.join(dt_list),
            inline=False
        )

    embed.timestamp = datetime.utcnow()
    embed.set_footer(text="Daily digest")

    await channel.send(embed=embed)
    logger.info("Sent daily digest")

# === Flask Webhook Server ===
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'project-bot',
        'gitlab_connected': project is not None
    })

@app.route('/webhook', methods=['POST'])
def gitlab_webhook():
    """Handle GitLab webhook events."""
    # Verify webhook secret
    if WEBHOOK_SECRET:
        token = request.headers.get('X-Gitlab-Token', '')
        if not hmac.compare_digest(token, WEBHOOK_SECRET):
            logger.warning("Invalid webhook token")
            return jsonify({'error': 'Invalid token'}), 401

    data = request.json
    if not data:
        return jsonify({'error': 'No data'}), 400

    # Only handle issue events
    if data.get('object_kind') != 'issue':
        return jsonify({'status': 'ignored'})

    obj = data.get('object_attributes', {})
    issue_iid = obj.get('iid')
    action = obj.get('action')
    title = obj.get('title')
    url = obj.get('url')
    state = obj.get('state')

    # Skip if this was a bot-initiated change
    if issue_iid in bot_initiated_changes:
        bot_initiated_changes.discard(issue_iid)
        logger.info(f"Skipping webhook for bot-initiated change #{issue_iid}")
        return jsonify({'status': 'skipped'})

    # Get labels
    labels = [l.get('title') for l in data.get('labels', [])]

    # Determine column
    column = 'Unknown'
    for label in labels:
        if label in COLUMN_LABELS.values():
            column = label
            break

    # Build notification
    if action == 'open':
        color = COLUMN_COLORS.get(column, 0x007bff)
        embed_title = f"New Task: #{issue_iid} {title}"
        description = f"Created in **{column}**"
    elif action == 'close':
        color = COLUMN_COLORS['Done']
        embed_title = f"Task Completed: #{issue_iid} {title}"
        description = "Marked as **Done**"
    elif action == 'update':
        color = COLUMN_COLORS.get(column, 0x007bff)
        embed_title = f"Task Updated: #{issue_iid} {title}"
        description = f"Now in **{column}**"
    elif action == 'reopen':
        color = COLUMN_COLORS.get(column, 0x007bff)
        embed_title = f"Task Reopened: #{issue_iid} {title}"
        description = f"Moved to **{column}**"
    else:
        return jsonify({'status': 'ignored'})

    # Send to Discord asynchronously
    asyncio.run_coroutine_threadsafe(
        send_webhook_notification(embed_title, description, url, color),
        bot.loop
    )

    return jsonify({'status': 'processed'})

async def send_webhook_notification(title: str, description: str, url: str, color: int):
    """Send webhook notification to Discord channel."""
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if not channel:
        logger.warning("Could not find channel for webhook notification")
        return

    embed = discord.Embed(
        title=title,
        description=description,
        url=url,
        color=color
    )
    embed.set_footer(text="Updated via GitLab")
    embed.timestamp = datetime.utcnow()

    await channel.send(embed=embed)
    logger.info(f"Sent webhook notification: {title}")

def run_flask():
    """Run Flask server in separate thread."""
    app.run(host='0.0.0.0', port=WEBHOOK_PORT, threaded=True)

# === Bot Events ===
@bot.event
async def on_ready():
    """Called when bot is ready."""
    logger.info(f'Logged in as {bot.user}')

    # Initialize GitLab connection
    if not init_gitlab():
        logger.error("GitLab initialization failed!")

    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash commands")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

    # Start scheduled tasks
    if not daily_digest.is_running():
        daily_digest.start()
        logger.info(f"Started daily digest (runs at {DAILY_DIGEST_HOUR}:00)")

    if not due_date_reminders.is_running():
        due_date_reminders.start()
        logger.info(f"Started due date reminders ({REMINDER_DAYS_BEFORE} days notice, every 6h)")

    if not stale_task_monitor.is_running():
        stale_task_monitor.start()
        logger.info(f"Started stale task monitor ({STALE_DAYS_THRESHOLD} days threshold, every 12h)")

    # Send startup message
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="Project Bot Online",
            description="Ready to manage your homelab tasks!",
            color=0x28a745
        )
        embed.add_field(
            name="Create Tasks",
            value="`/todo` `/idea` `/doing`",
            inline=True
        )
        embed.add_field(
            name="Workflow",
            value="`/review` `/testing` `/done`",
            inline=True
        )
        embed.add_field(
            name="Manage",
            value="`/move` `/block` `/unblock`",
            inline=True
        )
        embed.add_field(
            name="View",
            value="`/list` `/board` `/search` `/details`",
            inline=False
        )
        embed.add_field(
            name="Notifications",
            value=f"• Due date reminder: {REMINDER_DAYS_BEFORE} days before\n• Stale task alert: {STALE_DAYS_THRESHOLD}+ days inactive\n• Daily digest: {DAILY_DIGEST_HOUR}:00",
            inline=False
        )
        if project:
            embed.add_field(name="GitLab Project", value=project.name, inline=True)
        await channel.send(embed=embed)

# === Main Entry Point ===
def main():
    """Main entry point."""
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not set!")
        return

    if not GITLAB_TOKEN or not GITLAB_PROJECT_ID:
        logger.error("GITLAB_TOKEN or GITLAB_PROJECT_ID not set!")
        return

    # Start Flask webhook server in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"Webhook server started on port {WEBHOOK_PORT}")

    # Run Discord bot
    bot.run(DISCORD_TOKEN)

if __name__ == '__main__':
    main()
