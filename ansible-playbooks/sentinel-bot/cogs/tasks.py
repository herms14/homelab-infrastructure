"""
Sentinel Bot - Tasks Cog
Claude task queue management.
Ported from Athena bot.
"""

import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import TYPE_CHECKING, List

from core.progress import make_progress_bar, ProgressEmbed

if TYPE_CHECKING:
    from core import SentinelBot

logger = logging.getLogger('sentinel.cogs.tasks')


class TasksCog(commands.Cog, name="Tasks"):
    """Claude task queue management."""

    def __init__(self, bot: 'SentinelBot'):
        self.bot = bot

    @property
    def db(self):
        return self.bot.db

    # ==================== Task Commands ====================

    @app_commands.command(name="task", description="Submit a new task for Claude")
    @app_commands.describe(
        description="Task description",
        priority="Task priority"
    )
    @app_commands.choices(priority=[
        app_commands.Choice(name="High", value="high"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Low", value="low"),
    ])
    async def create_task(
        self,
        interaction: discord.Interaction,
        description: str,
        priority: str = "medium"
    ):
        """Submit a new task to the queue."""
        await interaction.response.defer()

        if not self.db:
            await interaction.followup.send(":x: Database not available")
            return

        task_id = await self.db.create_task(
            description=description,
            priority=priority,
            submitted_by=str(interaction.user)
        )

        embed = discord.Embed(
            title=f":white_check_mark: Task #{task_id} Created",
            description=description[:500],
            color=discord.Color.green()
        )
        embed.add_field(name="Priority", value=priority.title(), inline=True)
        embed.add_field(name="Status", value="Pending", inline=True)
        embed.set_footer(text=f"Submitted by {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)

        # Also notify in tasks channel
        if self.bot.channel_router:
            await self.bot.channel_router.send_task_notification(
                task_id=task_id,
                description=description,
                event='created'
            )

    @app_commands.command(name="queue", description="View pending tasks")
    @app_commands.describe(limit="Number of tasks to show")
    async def view_queue(self, interaction: discord.Interaction, limit: int = 10):
        """View the pending task queue."""
        await interaction.response.defer()

        if not self.db:
            await interaction.followup.send(":x: Database not available")
            return

        tasks = await self.db.get_pending_tasks(limit=limit)

        if not tasks:
            await interaction.followup.send(":information_source: No pending tasks")
            return

        embed = discord.Embed(
            title=":inbox_tray: Pending Tasks",
            color=discord.Color.blue()
        )

        for task in tasks:
            priority_emoji = {
                'high': ':red_circle:',
                'medium': ':yellow_circle:',
                'low': ':green_circle:',
            }.get(task.get('priority', 'medium'), ':white_circle:')

            embed.add_field(
                name=f"{priority_emoji} #{task['id']}",
                value=task['description'][:100],
                inline=False
            )

        # Get stats
        stats = await self.db.get_task_stats()
        embed.set_footer(
            text=f"Total: {sum(stats.values())} | Pending: {stats.get('pending', 0)} | Completed: {stats.get('completed', 0)}"
        )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="status", description="View Claude instance status")
    async def instance_status(self, interaction: discord.Interaction):
        """View active Claude instances."""
        await interaction.response.defer()

        if not self.db:
            await interaction.followup.send(":x: Database not available")
            return

        instances = await self.db.get_active_instances(minutes=10)

        embed = discord.Embed(
            title=":robot: Claude Instances",
            color=discord.Color.purple()
        )

        if not instances:
            embed.description = "No active instances in the last 10 minutes"
        else:
            for instance in instances:
                status_emoji = {
                    'idle': ':green_circle:',
                    'working': ':yellow_circle:',
                    'busy': ':orange_circle:',
                }.get(instance.get('status', 'idle'), ':white_circle:')

                embed.add_field(
                    name=f"{status_emoji} {instance.get('name', 'Unknown')}",
                    value=f"Status: {instance.get('status', 'Unknown')}\nLast seen: {instance.get('last_seen', 'Unknown')}",
                    inline=True
                )

        # Add stats
        stats = await self.db.get_task_stats()
        embed.add_field(
            name=":bar_chart: Queue Stats",
            value=f"Pending: {stats.get('pending', 0)}\nIn Progress: {stats.get('in_progress', 0)}\nCompleted: {stats.get('completed', 0)}",
            inline=False
        )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="done", description="View completed tasks")
    @app_commands.describe(limit="Number of tasks to show")
    async def completed_tasks(self, interaction: discord.Interaction, limit: int = 10):
        """View recently completed tasks."""
        await interaction.response.defer()

        if not self.db:
            await interaction.followup.send(":x: Database not available")
            return

        tasks = await self.db.get_completed_tasks(limit=limit)

        if not tasks:
            await interaction.followup.send(":information_source: No completed tasks")
            return

        embed = discord.Embed(
            title=":white_check_mark: Completed Tasks",
            color=discord.Color.green()
        )

        for task in tasks:
            completed = task.get('completed_at', 'Unknown')
            instance = task.get('instance_name', 'Unknown')

            embed.add_field(
                name=f"#{task['id']} - {task['description'][:30]}...",
                value=f"By: {instance}\nCompleted: {completed}",
                inline=False
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="cancel", description="Cancel a pending task")
    @app_commands.describe(task_id="Task ID to cancel")
    async def cancel_task(self, interaction: discord.Interaction, task_id: int):
        """Cancel a pending task."""
        await interaction.response.defer()

        if not self.db:
            await interaction.followup.send(":x: Database not available")
            return

        success = await self.db.cancel_task(task_id)

        if success:
            embed = discord.Embed(
                title=f":x: Task #{task_id} Cancelled",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

            # Notify in tasks channel
            if self.bot.channel_router:
                await self.bot.channel_router.send_task_notification(
                    task_id=task_id,
                    description="Task cancelled by user",
                    event='cancelled'
                )
        else:
            await interaction.followup.send(f":x: Could not cancel task #{task_id} (may not exist or not pending)")

    @app_commands.command(name="taskstats", description="View task queue statistics")
    async def task_stats(self, interaction: discord.Interaction):
        """View task queue statistics."""
        await interaction.response.defer()

        if not self.db:
            await interaction.followup.send(":x: Database not available")
            return

        # 2 steps: get stats, get instances
        progress = ProgressEmbed(":bar_chart: Loading Task Statistics...", 2)
        status_msg = await interaction.followup.send(embed=progress.embed)

        progress.update(0, ":hourglass: Fetching task statistics...")
        await status_msg.edit(embed=progress.embed)
        stats = await self.db.get_task_stats()

        progress.update(1, ":hourglass: Fetching active instances...")
        await status_msg.edit(embed=progress.embed)
        instances = await self.db.get_active_instances(minutes=60)

        # Build final embed
        embed = progress.complete(":bar_chart: Task Queue Statistics", "Statistics loaded")
        embed.clear_fields()

        # Task counts
        embed.add_field(
            name=":inbox_tray: Pending",
            value=str(stats.get('pending', 0)),
            inline=True
        )
        embed.add_field(
            name=":arrows_counterclockwise: In Progress",
            value=str(stats.get('in_progress', 0)),
            inline=True
        )
        embed.add_field(
            name=":white_check_mark: Completed",
            value=str(stats.get('completed', 0)),
            inline=True
        )

        # Instance info
        embed.add_field(
            name=":robot: Active Instances",
            value=str(len(instances)),
            inline=True
        )

        cancelled = stats.get('cancelled', 0)
        if cancelled:
            embed.add_field(
                name=":x: Cancelled",
                value=str(cancelled),
                inline=True
            )

        await status_msg.edit(embed=embed)


async def setup(bot: 'SentinelBot'):
    """Load the Tasks cog."""
    await bot.add_cog(TasksCog(bot))
