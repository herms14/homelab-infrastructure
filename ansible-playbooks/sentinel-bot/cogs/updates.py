"""
Sentinel Bot - Updates Cog
Container update management with reaction-based approval.
Ported from Argus bot.
"""

import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import TYPE_CHECKING, Dict, List

from config import CONTAINER_HOSTS, VM_HOSTS
from core.progress import make_progress_bar, ProgressEmbed

if TYPE_CHECKING:
    from core import SentinelBot

logger = logging.getLogger('sentinel.cogs.updates')

# Reaction emojis for approval
APPROVE_ALL_EMOJI = "\U0001F44D"  # :thumbsup:
NUMBER_EMOJIS = ["1\ufe0f\u20e3", "2\ufe0f\u20e3", "3\ufe0f\u20e3", "4\ufe0f\u20e3",
                 "5\ufe0f\u20e3", "6\ufe0f\u20e3", "7\ufe0f\u20e3", "8\ufe0f\u20e3",
                 "9\ufe0f\u20e3", "\U0001F51F"]  # 1️⃣ through 🔟


class UpdatesCog(commands.Cog, name="Updates"):
    """Container update management with reaction-based approval."""

    def __init__(self, bot: 'SentinelBot'):
        self.bot = bot
        self._pending_updates: Dict[int, Dict] = {}  # message_id -> update info

    @property
    def ssh(self):
        return self.bot.ssh

    @property
    def db(self):
        return self.bot.db

    # ==================== Commands ====================

    @app_commands.command(name="check", description="Check all containers for available updates")
    async def check_updates(self, interaction: discord.Interaction):
        """Scan all containers for available image updates."""
        await interaction.response.defer()

        # Group containers by host
        hosts = {}
        for container, host_ip in CONTAINER_HOSTS.items():
            if host_ip not in hosts:
                hosts[host_ip] = []
            hosts[host_ip].append(container)

        total_hosts = len(hosts)
        progress = ProgressEmbed(":mag: Checking for Container Updates...", total_hosts)
        status_msg = await interaction.followup.send(embed=progress.embed)

        updates_available = []
        errors = []
        checked = 0

        for host_ip, containers in hosts.items():
            progress.update(checked, f":hourglass: Checking **{host_ip}** ({len(containers)} containers)...")
            await status_msg.edit(embed=progress.embed)

            result = await self.ssh.docker_ps_all(host_ip)
            if not result.success:
                errors.append(f"**{host_ip}**: Connection failed")
            checked += 1

        # Final result
        if updates_available:
            embed = progress.complete(
                ":arrow_up: Updates Available",
                "\n".join([f"• {u['container']} on {u['host']}" for u in updates_available]),
                discord.Color.yellow()
            )
            embed.set_footer(text=f"React with {APPROVE_ALL_EMOJI} to update all")
        else:
            embed = progress.complete(
                ":white_check_mark: Update Check Complete",
                f"All containers are up to date!\nChecked {total_hosts} hosts."
            )

        if errors:
            embed.add_field(name=":warning: Errors", value="\n".join(errors), inline=False)

        await status_msg.edit(embed=embed)

    @app_commands.command(name="update", description="Update a specific container")
    @app_commands.describe(container="Container name to update")
    async def update_container(self, interaction: discord.Interaction, container: str):
        """Update a specific container."""
        await interaction.response.defer()

        if container not in CONTAINER_HOSTS:
            await interaction.followup.send(f":x: Unknown container: {container}")
            return

        host_ip = CONTAINER_HOSTS[container]

        # 3 steps: pull, restart, verify
        progress = ProgressEmbed(f":arrows_counterclockwise: Updating {container}", 3)
        progress.embed.add_field(name="Host", value=host_ip, inline=True)
        status_msg = await interaction.followup.send(embed=progress.embed)

        # Step 1: Pull new image
        progress.update(0, ":hourglass: Pulling latest image...")
        await status_msg.edit(embed=progress.embed)

        result = await self.ssh.docker_pull(host_ip, container)
        if not result.success:
            embed = progress.error(f":x: Update Failed: {container}", f"Failed to pull image: {result.stderr}")
            await status_msg.edit(embed=embed)
            return

        # Step 2: Restart container
        progress.update(1, ":hourglass: Restarting container...")
        await status_msg.edit(embed=progress.embed)

        result = await self.ssh.docker_restart(host_ip, container)
        if not result.success:
            embed = progress.error(f":x: Update Failed: {container}", f"Restart failed: {result.stderr}")
            if self.db:
                await self.db.record_update(container, host_ip, 'failed', str(interaction.user))
            await status_msg.edit(embed=embed)
            return

        # Step 3: Verify
        progress.update(2, ":hourglass: Verifying...")
        await status_msg.edit(embed=progress.embed)

        # Record success
        if self.db:
            await self.db.record_update(container, host_ip, 'success', str(interaction.user))

        embed = progress.complete(
            f":white_check_mark: {container} Updated",
            "Container updated and restarted successfully"
        )
        await status_msg.edit(embed=embed)

    @app_commands.command(name="containers", description="List all monitored containers")
    async def list_containers(self, interaction: discord.Interaction):
        """List all containers being monitored."""
        await interaction.response.defer()

        # Group by host
        hosts = {}
        for container, host_ip in CONTAINER_HOSTS.items():
            if host_ip not in hosts:
                hosts[host_ip] = []
            hosts[host_ip].append(container)

        embed = discord.Embed(
            title=":package: Monitored Containers",
            color=discord.Color.blue()
        )

        for host_ip, containers in sorted(hosts.items()):
            embed.add_field(
                name=f":computer: {host_ip}",
                value="\n".join([f"• {c}" for c in sorted(containers)]),
                inline=True
            )

        embed.set_footer(text=f"Total: {len(CONTAINER_HOSTS)} containers")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="restart", description="Restart a container")
    @app_commands.describe(container="Container name to restart")
    async def restart_container(self, interaction: discord.Interaction, container: str):
        """Restart a specific container."""
        await interaction.response.defer()

        if container not in CONTAINER_HOSTS:
            await interaction.followup.send(f":x: Unknown container: {container}")
            return

        host_ip = CONTAINER_HOSTS[container]

        progress = ProgressEmbed(f":arrows_counterclockwise: Restarting {container}", 2)
        progress.embed.add_field(name="Host", value=host_ip, inline=True)
        status_msg = await interaction.followup.send(embed=progress.embed)

        # Step 1: Stop
        progress.update(0, ":hourglass: Restarting container...")
        await status_msg.edit(embed=progress.embed)

        result = await self.ssh.docker_restart(host_ip, container)

        if result.success:
            progress.update(1, ":hourglass: Verifying...")
            await status_msg.edit(embed=progress.embed)

            embed = progress.complete(
                f":white_check_mark: {container} Restarted",
                "Container restarted successfully"
            )
        else:
            embed = progress.error(
                f":x: Restart Failed: {container}",
                result.stderr
            )

        await status_msg.edit(embed=embed)

    @app_commands.command(name="logs", description="Get container logs")
    @app_commands.describe(container="Container name", lines="Number of lines (default 50)")
    async def container_logs(
        self,
        interaction: discord.Interaction,
        container: str,
        lines: int = 50
    ):
        """Get recent logs from a container."""
        await interaction.response.defer()

        if container not in CONTAINER_HOSTS:
            await interaction.followup.send(f":x: Unknown container: {container}")
            return

        host_ip = CONTAINER_HOSTS[container]

        embed = discord.Embed(
            title=f":scroll: Fetching logs for {container}...",
            description=make_progress_bar(0, 1),
            color=discord.Color.blue()
        )
        status_msg = await interaction.followup.send(embed=embed)

        result = await self.ssh.docker_logs(host_ip, container, tail=min(lines, 100))

        if result.success:
            # Truncate if too long
            output = result.output[:1900] if len(result.output) > 1900 else result.output
            await status_msg.edit(content=f"**Logs for {container}:**\n```\n{output}\n```", embed=None)
        else:
            embed.title = f":x: Failed to get logs"
            embed.description = result.stderr
            embed.color = discord.Color.red()
            await status_msg.edit(embed=embed)

    @app_commands.command(name="vmcheck", description="Check VMs for apt updates")
    async def vm_check(self, interaction: discord.Interaction):
        """Check all VMs for available apt updates."""
        await interaction.response.defer()

        total_vms = len(VM_HOSTS)
        progress = ProgressEmbed(":mag: Checking VMs for Updates...", total_vms)
        status_msg = await interaction.followup.send(embed=progress.embed)

        updates_found = []
        errors = []
        checked = 0

        for name, host_ip in VM_HOSTS.items():
            progress.update(checked, f":hourglass: Checking **{name}** ({host_ip})...")
            await status_msg.edit(embed=progress.embed)

            # Run apt update
            update_result = await self.ssh.apt_update(host_ip)
            if not update_result.success:
                errors.append(f"**{name}**: Connection failed")
                checked += 1
                continue

            # Check for upgradable packages
            result = await self.ssh.apt_upgradable(host_ip)
            if result.success and result.output.strip():
                count = len(result.output.strip().split('\n'))
                updates_found.append(f"**{name}** ({host_ip}): {count} packages")

            checked += 1

        # Final result
        if updates_found:
            embed = progress.complete(
                ":arrow_up: Updates Available",
                "\n".join(updates_found),
                discord.Color.yellow()
            )
        else:
            embed = progress.complete(
                ":white_check_mark: All VMs Up to Date",
                "All VMs are up to date!"
            )

        if errors:
            embed.add_field(name=":warning: Errors", value="\n".join(errors), inline=False)

        embed.set_footer(text=f"Checked {total_vms} VMs")
        await status_msg.edit(embed=embed)

    # ==================== Reaction Handler ====================

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle reactions for update approval."""
        if payload.user_id == self.bot.user.id:
            return

        if payload.message_id not in self._pending_updates:
            return

        update_info = self._pending_updates[payload.message_id]
        emoji = str(payload.emoji)

        if emoji == APPROVE_ALL_EMOJI:
            # Approve all updates
            logger.info(f"User {payload.user_id} approved all updates")
            # Process all pending updates
            for container, host_ip in update_info.get('containers', []):
                await self._perform_update(container, host_ip, update_info.get('channel_id'))

            del self._pending_updates[payload.message_id]

        elif emoji in NUMBER_EMOJIS:
            # Approve single update
            index = NUMBER_EMOJIS.index(emoji)
            containers = update_info.get('containers', [])
            if index < len(containers):
                container, host_ip = containers[index]
                await self._perform_update(container, host_ip, update_info.get('channel_id'))

    async def _perform_update(self, container: str, host_ip: str, channel_id: int):
        """Perform a container update."""
        logger.info(f"Updating {container} on {host_ip}")

        # Pull and restart
        await self.ssh.docker_pull(host_ip, container)
        result = await self.ssh.docker_restart(host_ip, container)

        # Record result
        if self.db:
            status = 'success' if result.success else 'failed'
            await self.db.record_update(container, host_ip, status, 'reaction')

        # Send notification
        if self.bot.channel_router:
            await self.bot.channel_router.send_update_notification(
                container_name=container,
                host_ip=host_ip,
                status='success' if result.success else 'failed'
            )


async def setup(bot: 'SentinelBot'):
    """Load the Updates cog."""
    await bot.add_cog(UpdatesCog(bot))
