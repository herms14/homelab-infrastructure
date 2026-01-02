"""
Sentinel Bot - GitLab Cog
GitLab issue and todo management.
Ported from Chronos bot.
"""

import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import TYPE_CHECKING, List, Optional

from core.progress import make_progress_bar, ProgressEmbed

if TYPE_CHECKING:
    from core import SentinelBot

logger = logging.getLogger('sentinel.cogs.gitlab')


class GitLabCog(commands.Cog, name="GitLab"):
    """GitLab issue and todo management."""

    def __init__(self, bot: 'SentinelBot'):
        self.bot = bot

    @property
    def config(self):
        return self.bot.config

    @property
    def gitlab_url(self):
        return self.config.api.gitlab_url

    @property
    def project_id(self):
        return self.config.api.gitlab_project_id

    # ==================== Issue Commands ====================

    @app_commands.command(name="todo", description="Create a new GitLab issue")
    @app_commands.describe(
        description="Issue description",
        priority="Priority level"
    )
    @app_commands.choices(priority=[
        app_commands.Choice(name="High", value="high"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Low", value="low"),
    ])
    async def create_todo(
        self,
        interaction: discord.Interaction,
        description: str,
        priority: str = "medium"
    ):
        """Create a new GitLab issue."""
        await interaction.response.defer()

        # Map priority to labels
        labels = f"priority::{priority}"

        url = f"{self.gitlab_url}/api/v4/projects/{self.project_id}/issues"
        data = {
            "title": description[:100],
            "description": description,
            "labels": labels,
        }

        result = await self.bot.api_post(url, 'gitlab', data=data)

        if result:
            issue_url = result.get('web_url', '')
            issue_id = result.get('iid', 'Unknown')

            embed = discord.Embed(
                title=f":white_check_mark: Issue #{issue_id} Created",
                description=description[:200],
                color=discord.Color.green(),
                url=issue_url
            )
            embed.add_field(name="Priority", value=priority.title(), inline=True)
            embed.set_footer(text=f"Created by {interaction.user.display_name}")

            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(":x: Failed to create issue")

    @app_commands.command(name="issues", description="List open GitLab issues")
    @app_commands.describe(limit="Number of issues to show")
    async def list_issues(self, interaction: discord.Interaction, limit: int = 10):
        """List open GitLab issues."""
        await interaction.response.defer()

        url = f"{self.gitlab_url}/api/v4/projects/{self.project_id}/issues?state=opened&per_page={limit}"
        issues = await self.bot.api_get(url, 'gitlab')

        if not issues:
            await interaction.followup.send(":information_source: No open issues found")
            return

        embed = discord.Embed(
            title=":clipboard: Open Issues",
            color=discord.Color.blue()
        )

        for issue in issues[:limit]:
            labels = ", ".join(issue.get('labels', [])) or "No labels"
            embed.add_field(
                name=f"#{issue.get('iid')} - {issue.get('title', 'Untitled')[:50]}",
                value=f"Labels: {labels}",
                inline=False
            )

        embed.set_footer(text=f"Showing {len(issues)} issues")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="close", description="Close a GitLab issue")
    @app_commands.describe(issue_id="Issue number to close")
    async def close_issue(self, interaction: discord.Interaction, issue_id: int):
        """Close a GitLab issue."""
        await interaction.response.defer()

        url = f"{self.gitlab_url}/api/v4/projects/{self.project_id}/issues/{issue_id}"
        data = {"state_event": "close"}

        # Use PUT for updating
        if not self.bot.http_session:
            await interaction.followup.send(":x: HTTP session not available")
            return

        headers = self.bot.get_api_headers('gitlab')
        try:
            async with self.bot.http_session.put(url, headers=headers, json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    embed = discord.Embed(
                        title=f":white_check_mark: Issue #{issue_id} Closed",
                        description=result.get('title', 'Unknown'),
                        color=discord.Color.green()
                    )
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(f":x: Failed to close issue: {resp.status}")
        except Exception as e:
            await interaction.followup.send(f":x: Error: {e}")

    @app_commands.command(name="quick", description="Create multiple issues quickly")
    @app_commands.describe(tasks="Semicolon-separated list of tasks")
    async def quick_create(self, interaction: discord.Interaction, tasks: str):
        """Create multiple issues from semicolon-separated list."""
        await interaction.response.defer()

        task_list = [t.strip() for t in tasks.split(';') if t.strip()]

        if not task_list:
            await interaction.followup.send(":x: No tasks provided")
            return

        progress = ProgressEmbed(":clipboard: Creating Issues...", len(task_list))
        status_msg = await interaction.followup.send(embed=progress.embed)

        created = []
        failed = []
        processed = 0

        for task in task_list:
            progress.update(processed, f":hourglass: Creating issue: **{task[:30]}**...")
            await status_msg.edit(embed=progress.embed)

            url = f"{self.gitlab_url}/api/v4/projects/{self.project_id}/issues"
            data = {"title": task[:100], "description": task}

            result = await self.bot.api_post(url, 'gitlab', data=data)
            if result:
                created.append(f"#{result.get('iid')} - {task[:30]}")
            else:
                failed.append(task[:30])
            processed += 1

        # Build final embed
        color = discord.Color.green() if not failed else discord.Color.yellow()
        embed = progress.complete(":clipboard: Quick Create Results", f"Created {len(created)} of {len(task_list)} issues", color)
        embed.clear_fields()

        if created:
            embed.add_field(
                name=f":white_check_mark: Created ({len(created)})",
                value="\n".join(created) or "None",
                inline=False
            )

        if failed:
            embed.add_field(
                name=f":x: Failed ({len(failed)})",
                value="\n".join(failed) or "None",
                inline=False
            )

        await status_msg.edit(embed=embed)

    # ==================== Project Info ====================

    @app_commands.command(name="project", description="Show GitLab project info")
    async def project_info(self, interaction: discord.Interaction):
        """Show GitLab project information."""
        await interaction.response.defer()

        url = f"{self.gitlab_url}/api/v4/projects/{self.project_id}"
        project = await self.bot.api_get(url, 'gitlab')

        if not project:
            await interaction.followup.send(":x: Failed to get project info")
            return

        embed = discord.Embed(
            title=f":gitlab: {project.get('name', 'Unknown')}",
            description=project.get('description', 'No description'),
            color=discord.Color.orange(),
            url=project.get('web_url', '')
        )

        # Get issue stats
        open_issues = project.get('open_issues_count', 0)
        embed.add_field(name="Open Issues", value=str(open_issues), inline=True)
        embed.add_field(name="Visibility", value=project.get('visibility', 'Unknown').title(), inline=True)
        embed.add_field(name="Default Branch", value=project.get('default_branch', 'main'), inline=True)

        await interaction.followup.send(embed=embed)


async def setup(bot: 'SentinelBot'):
    """Load the GitLab cog."""
    await bot.add_cog(GitLabCog(bot))
