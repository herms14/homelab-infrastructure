"""
Sentinel Bot Progress Bar Utilities
Shared progress bar helpers for Discord embeds.
"""

import discord
from typing import Optional


def make_progress_bar(current: int, total: int, width: int = 20) -> str:
    """
    Create a text progress bar.

    Args:
        current: Current progress value
        total: Total value
        width: Bar width in characters

    Returns:
        Formatted progress bar string like `[████████░░░░]` 66%
    """
    if total == 0:
        return "`[" + "░" * width + "]` 0%"

    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    percent = int(100 * current / total)
    return f"`[{bar}]` {percent}%"


def make_step_progress(current_step: int, total_steps: int, step_name: str) -> str:
    """
    Create a step-based progress indicator.

    Args:
        current_step: Current step number (1-based)
        total_steps: Total number of steps
        step_name: Name of current step

    Returns:
        Formatted string like "Step 2/4: Pulling image..."
    """
    return f"Step {current_step}/{total_steps}: {step_name}"


class ProgressEmbed:
    """Helper class for managing progress updates in Discord embeds."""

    def __init__(
        self,
        title: str,
        total: int,
        color: discord.Color = discord.Color.blue()
    ):
        self.title = title
        self.total = total
        self.current = 0
        self.color = color
        self.embed = discord.Embed(
            title=title,
            description=make_progress_bar(0, total),
            color=color
        )
        self.embed.add_field(name="Status", value="Starting...", inline=False)

    def update(self, current: int, status: str) -> discord.Embed:
        """Update progress and return the embed."""
        self.current = current
        self.embed.description = make_progress_bar(current, self.total)
        self.embed.set_field_at(0, name="Status", value=status, inline=False)
        return self.embed

    def complete(
        self,
        title: str,
        status: str,
        color: discord.Color = discord.Color.green()
    ) -> discord.Embed:
        """Mark as complete and return the embed."""
        self.embed.title = title
        self.embed.description = make_progress_bar(self.total, self.total)
        self.embed.color = color
        self.embed.set_field_at(0, name="Status", value=status, inline=False)
        return self.embed

    def error(self, title: str, error_msg: str) -> discord.Embed:
        """Mark as error and return the embed."""
        self.embed.title = title
        self.embed.color = discord.Color.red()
        self.embed.set_field_at(0, name="Error", value=error_msg, inline=False)
        return self.embed
