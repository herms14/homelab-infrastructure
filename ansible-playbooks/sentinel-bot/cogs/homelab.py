"""
Sentinel Bot - Homelab Cog
Commands for Proxmox cluster and infrastructure management.
"""

import logging
import json
import discord
from discord import app_commands
from discord.ext import commands
from typing import TYPE_CHECKING

from core.progress import make_progress_bar, ProgressEmbed

if TYPE_CHECKING:
    from core import SentinelBot

logger = logging.getLogger('sentinel.cogs.homelab')


class HomelabCog(commands.Cog, name="Homelab"):
    """Proxmox cluster and infrastructure management."""

    def __init__(self, bot: 'SentinelBot'):
        self.bot = bot

    @property
    def ssh(self):
        return self.bot.ssh

    @property
    def config(self):
        return self.bot.config

    # ==================== Homelab Commands ====================

    homelab_group = app_commands.Group(name="homelab", description="Homelab infrastructure commands")

    @homelab_group.command(name="status", description="Show cluster overview")
    async def homelab_status(self, interaction: discord.Interaction):
        """Get Proxmox cluster status overview."""
        await interaction.response.defer()

        nodes = [
            ('node01', self.config.ssh.node01_ip),
            ('node02', self.config.ssh.node02_ip)
        ]

        progress = ProgressEmbed(":house: Checking Cluster Status...", len(nodes))
        status_msg = await interaction.followup.send(embed=progress.embed)

        node_results = []
        checked = 0

        # Get node statuses
        for node_name, node_ip in nodes:
            progress.update(checked, f":hourglass: Checking **{node_name}**...")
            await status_msg.edit(embed=progress.embed)

            result = await self.ssh.pve_node_status(node_ip)
            if result.success:
                try:
                    data = json.loads(result.stdout)
                    cpu = data.get('cpu', 0) * 100
                    mem_used = data.get('memory', {}).get('used', 0) / (1024**3)
                    mem_total = data.get('memory', {}).get('total', 0) / (1024**3)
                    uptime_days = data.get('uptime', 0) / 86400

                    node_results.append((
                        f":green_circle: {node_name}",
                        f"CPU: {cpu:.1f}%\nMemory: {mem_used:.1f}/{mem_total:.1f} GB\nUptime: {uptime_days:.1f} days"
                    ))
                except json.JSONDecodeError:
                    node_results.append((f":yellow_circle: {node_name}", "Parse error"))
            else:
                node_results.append((f":red_circle: {node_name}", "Unreachable"))
            checked += 1

        # Build final embed
        all_healthy = all(":green_circle:" in r[0] for r in node_results)
        color = discord.Color.green() if all_healthy else discord.Color.yellow()
        embed = progress.complete(":house: MorpheusCluster Status", "Cluster check complete", color)
        embed.clear_fields()

        for name, value in node_results:
            embed.add_field(name=name, value=value, inline=True)

        await status_msg.edit(embed=embed)

    @homelab_group.command(name="uptime", description="Show uptime for all nodes")
    async def homelab_uptime(self, interaction: discord.Interaction):
        """Get uptime for all infrastructure components."""
        await interaction.response.defer()

        # All hosts to check
        proxmox_nodes = [
            ('node01', self.config.ssh.node01_ip),
            ('node02', self.config.ssh.node02_ip)
        ]
        docker_hosts_list = [
            ('utilities', self.config.ssh.docker_utilities_ip),
            ('media', self.config.ssh.docker_media_ip),
            ('glance', self.config.ssh.docker_glance_ip),
        ]

        total_hosts = len(proxmox_nodes) + len(docker_hosts_list)
        progress = ProgressEmbed(":clock: Checking Infrastructure Uptime...", total_hosts)
        status_msg = await interaction.followup.send(embed=progress.embed)

        checked = 0

        # Proxmox nodes (use root user)
        nodes = []
        for node_name, node_ip in proxmox_nodes:
            progress.update(checked, f":hourglass: Checking **{node_name}**...")
            await status_msg.edit(embed=progress.embed)

            # Use run_proxmox for Proxmox nodes (requires root)
            result = await self.ssh.run_proxmox(node_ip, 'uptime -p')
            if result.success:
                nodes.append(f"**{node_name}**: {result.output}")
            else:
                nodes.append(f"**{node_name}**: :x: Unreachable")
            checked += 1

        # Docker hosts
        docker_hosts = []
        for name, ip in docker_hosts_list:
            progress.update(checked, f":hourglass: Checking **{name}**...")
            await status_msg.edit(embed=progress.embed)

            result = await self.ssh.system_uptime(ip)
            if result.success:
                docker_hosts.append(f"**{name}**: {result.output}")
            else:
                docker_hosts.append(f"**{name}**: :x: Unreachable")
            checked += 1

        # Build final embed
        embed = progress.complete(":clock: Infrastructure Uptime", "Uptime check complete")
        embed.clear_fields()
        embed.add_field(name="Proxmox Nodes", value="\n".join(nodes), inline=False)
        embed.add_field(name="Docker Hosts", value="\n".join(docker_hosts), inline=False)

        await status_msg.edit(embed=embed)

    # ==================== Node Commands ====================

    @app_commands.command(name="node", description="Manage Proxmox nodes")
    @app_commands.describe(
        name="Node name (node01 or node02)",
        action="Action to perform"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="status", value="status"),
        app_commands.Choice(name="vms", value="vms"),
        app_commands.Choice(name="lxc", value="lxc"),
        app_commands.Choice(name="restart", value="restart"),
    ])
    async def node_command(
        self,
        interaction: discord.Interaction,
        name: str,
        action: str
    ):
        """Manage Proxmox nodes."""
        await interaction.response.defer()

        node_ips = {
            'node01': self.config.ssh.node01_ip,
            'node02': self.config.ssh.node02_ip,
        }

        if name.lower() not in node_ips:
            await interaction.followup.send(f":x: Unknown node: {name}")
            return

        node_ip = node_ips[name.lower()]

        if action == "restart":
            # Confirm before restarting a node
            embed = discord.Embed(
                title=f":warning: Confirm Node Restart",
                description=f"Are you sure you want to restart **{name}**?\n\nThis will affect all VMs and containers on this node!",
                color=discord.Color.orange()
            )
            embed.set_footer(text="React with ✅ to confirm or ❌ to cancel")
            msg = await interaction.followup.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            def check(reaction, user):
                return user == interaction.user and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                if str(reaction.emoji) == "✅":
                    result = await self.ssh.run_proxmox(node_ip, 'reboot')
                    if result.success or "Connection reset" in result.stderr:
                        embed = discord.Embed(
                            title=f":arrows_counterclockwise: Restarting {name}",
                            description="Node restart initiated. It may take a few minutes to come back online.",
                            color=discord.Color.green()
                        )
                    else:
                        embed = discord.Embed(
                            title=f":x: Restart Failed",
                            description=f"Error: {result.stderr}",
                            color=discord.Color.red()
                        )
                else:
                    embed = discord.Embed(
                        title=":x: Restart Cancelled",
                        description=f"Node {name} restart was cancelled.",
                        color=discord.Color.grey()
                    )
                await msg.edit(embed=embed)
                await msg.clear_reactions()
            except Exception:
                embed = discord.Embed(
                    title=":x: Restart Cancelled",
                    description="Timed out waiting for confirmation.",
                    color=discord.Color.grey()
                )
                await msg.edit(embed=embed)
                await msg.clear_reactions()
            return

        elif action == "status":
            result = await self.ssh.pve_node_status(node_ip)
            if result.success:
                try:
                    data = json.loads(result.stdout)
                    embed = discord.Embed(
                        title=f":computer: {name} Status",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="CPU", value=f"{data.get('cpu', 0) * 100:.1f}%", inline=True)
                    mem = data.get('memory', {})
                    embed.add_field(
                        name="Memory",
                        value=f"{mem.get('used', 0) / (1024**3):.1f} / {mem.get('total', 0) / (1024**3):.1f} GB",
                        inline=True
                    )
                    embed.add_field(name="Uptime", value=f"{data.get('uptime', 0) / 86400:.1f} days", inline=True)
                    await interaction.followup.send(embed=embed)
                except json.JSONDecodeError:
                    await interaction.followup.send(f":warning: Could not parse status for {name}")
            else:
                await interaction.followup.send(f":x: Failed to get status: {result.stderr}")

        elif action == "vms":
            result = await self.ssh.pve_list_vms(node_ip)
            if result.success:
                try:
                    vms = json.loads(result.stdout)
                    if not vms:
                        await interaction.followup.send(f":information_source: No VMs on {name}")
                        return

                    lines = []
                    for vm in vms:
                        status_emoji = ":green_circle:" if vm.get('status') == 'running' else ":red_circle:"
                        lines.append(f"{status_emoji} **{vm.get('name')}** (VMID: {vm.get('vmid')})")

                    embed = discord.Embed(
                        title=f":desktop: VMs on {name}",
                        description="\n".join(lines),
                        color=discord.Color.blue()
                    )
                    await interaction.followup.send(embed=embed)
                except json.JSONDecodeError:
                    await interaction.followup.send(f":warning: Could not parse VM list")
            else:
                await interaction.followup.send(f":x: Failed to list VMs: {result.stderr}")

        elif action == "lxc":
            result = await self.ssh.pve_list_lxc(node_ip)
            if result.success:
                try:
                    containers = json.loads(result.stdout)
                    if not containers:
                        await interaction.followup.send(f":information_source: No LXC containers on {name}")
                        return

                    lines = []
                    for ct in containers:
                        status_emoji = ":green_circle:" if ct.get('status') == 'running' else ":red_circle:"
                        lines.append(f"{status_emoji} **{ct.get('name')}** (CTID: {ct.get('vmid')})")

                    embed = discord.Embed(
                        title=f":package: LXC Containers on {name}",
                        description="\n".join(lines),
                        color=discord.Color.blue()
                    )
                    await interaction.followup.send(embed=embed)
                except json.JSONDecodeError:
                    await interaction.followup.send(f":warning: Could not parse LXC list")
            else:
                await interaction.followup.send(f":x: Failed to list LXC: {result.stderr}")

    # ==================== VM Commands ====================

    @app_commands.command(name="vm", description="Manage VMs")
    @app_commands.describe(
        vmid="VM ID",
        action="Action to perform"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="status", value="status"),
        app_commands.Choice(name="start", value="start"),
        app_commands.Choice(name="stop", value="stop"),
        app_commands.Choice(name="restart", value="restart"),
    ])
    async def vm_command(
        self,
        interaction: discord.Interaction,
        vmid: int,
        action: str
    ):
        """Manage VMs by VMID."""
        await interaction.response.defer()

        # Try both nodes
        node_ip = None
        for ip in [self.config.ssh.node01_ip, self.config.ssh.node02_ip]:
            result = await self.ssh.pve_vm_status(ip, vmid)
            if result.success:
                node_ip = ip
                break

        if not node_ip:
            await interaction.followup.send(f":x: VM {vmid} not found on any node")
            return

        if action == "status":
            result = await self.ssh.pve_vm_status(node_ip, vmid)
            if result.success:
                data = json.loads(result.stdout)
                status_emoji = ":green_circle:" if data.get('status') == 'running' else ":red_circle:"
                embed = discord.Embed(
                    title=f"{status_emoji} VM {vmid} - {data.get('name', 'Unknown')}",
                    color=discord.Color.green() if data.get('status') == 'running' else discord.Color.red()
                )
                embed.add_field(name="Status", value=data.get('status', 'unknown'), inline=True)
                embed.add_field(name="CPU", value=f"{data.get('cpu', 0) * 100:.1f}%", inline=True)
                await interaction.followup.send(embed=embed)

        elif action in ["start", "stop", "restart"]:
            action_func = {
                "start": self.ssh.pve_start_vm,
                "stop": self.ssh.pve_stop_vm,
                "restart": self.ssh.pve_restart_vm,
            }[action]

            result = await action_func(node_ip, vmid)
            if result.success:
                await interaction.followup.send(f":white_check_mark: VM {vmid} {action} command sent")
            else:
                await interaction.followup.send(f":x: Failed to {action} VM {vmid}: {result.stderr}")


    # ==================== LXC Commands ====================

    @app_commands.command(name="lxc", description="Manage LXC containers")
    @app_commands.describe(
        ctid="Container ID",
        action="Action to perform"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="status", value="status"),
        app_commands.Choice(name="start", value="start"),
        app_commands.Choice(name="stop", value="stop"),
        app_commands.Choice(name="restart", value="restart"),
    ])
    async def lxc_command(
        self,
        interaction: discord.Interaction,
        ctid: int,
        action: str
    ):
        """Manage LXC containers by CTID."""
        await interaction.response.defer()

        # Try both nodes to find the container
        node_ip = None
        container_name = None
        for ip in [self.config.ssh.node01_ip, self.config.ssh.node02_ip]:
            result = await self.ssh.pve_lxc_status(ip, ctid)
            if result.success:
                node_ip = ip
                try:
                    data = json.loads(result.stdout)
                    container_name = data.get('name', f'CT{ctid}')
                except:
                    container_name = f'CT{ctid}'
                break

        if not node_ip:
            await interaction.followup.send(f":x: LXC container {ctid} not found on any node")
            return

        if action == "status":
            result = await self.ssh.pve_lxc_status(node_ip, ctid)
            if result.success:
                data = json.loads(result.stdout)
                status_emoji = ":green_circle:" if data.get('status') == 'running' else ":red_circle:"
                embed = discord.Embed(
                    title=f"{status_emoji} LXC {ctid} - {data.get('name', 'Unknown')}",
                    color=discord.Color.green() if data.get('status') == 'running' else discord.Color.red()
                )
                embed.add_field(name="Status", value=data.get('status', 'unknown'), inline=True)
                embed.add_field(name="CPU", value=f"{data.get('cpu', 0) * 100:.1f}%", inline=True)
                mem = data.get('mem', 0) / (1024**3)
                maxmem = data.get('maxmem', 0) / (1024**3)
                embed.add_field(name="Memory", value=f"{mem:.1f} / {maxmem:.1f} GB", inline=True)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f":x: Failed to get status: {result.stderr}")

        elif action in ["start", "stop", "restart"]:
            action_func = {
                "start": self.ssh.pve_start_lxc,
                "stop": self.ssh.pve_stop_lxc,
                "restart": self.ssh.pve_restart_lxc,
            }[action]

            result = await action_func(node_ip, ctid)
            if result.success:
                emoji = ":arrow_forward:" if action == "start" else ":stop_button:" if action == "stop" else ":arrows_counterclockwise:"
                await interaction.followup.send(f"{emoji} LXC **{container_name}** ({ctid}) {action} command sent")
            else:
                await interaction.followup.send(f":x: Failed to {action} LXC {ctid}: {result.stderr}")


async def setup(bot: 'SentinelBot'):
    """Load the Homelab cog."""
    await bot.add_cog(HomelabCog(bot))
