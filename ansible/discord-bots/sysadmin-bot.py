#!/usr/bin/env python3
"""
Homelab SysAdmin Discord Bot - Argus
Comprehensive infrastructure management via Discord slash commands.
Uses SSH for all operations (no API tokens required).
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiohttp
import paramiko

# Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SYSADMIN_CHANNEL_ID = int(os.getenv("SYSADMIN_CHANNEL_ID", "0"))
ALERTS_CHANNEL_ID = int(os.getenv("ALERTS_CHANNEL_ID", "0"))

# SSH Configuration
SSH_KEY_PATH = os.getenv("SSH_KEY_PATH", "/app/ssh/homelab_ed25519")
SSH_USER = os.getenv("SSH_USER", "hermes-admin")

# Docker Hosts
DOCKER_HOSTS = {
    "utilities": "192.168.40.10",
    "media": "192.168.40.11",
}

# Proxmox Nodes (SSH as root)
PROXMOX_NODES = {
    "node01": "192.168.20.20",
    "node02": "192.168.20.21",
    "node03": "192.168.20.22",
}

# VM Mapping (name -> node, vmid)
VM_MAPPING = {
    "ansible": ("node02", 201),
    "docker-utilities": ("node02", 210),
    "docker-media": ("node02", 211),
    "traefik": ("node02", 220),
    "authentik": ("node02", 221),
    "immich": ("node02", 222),
    "gitlab": ("node02", 223),
    "gitlab-runner": ("node02", 224),
    "n8n": ("node02", 225),
    "k8s-controller01": ("node03", 301),
    "k8s-controller02": ("node03", 302),
    "k8s-controller03": ("node03", 303),
    "k8s-worker01": ("node03", 311),
    "k8s-worker02": ("node03", 312),
    "k8s-worker03": ("node03", 313),
    "k8s-worker04": ("node03", 314),
    "k8s-worker05": ("node03", 315),
    "k8s-worker06": ("node03", 316),
}

# Radarr/Sonarr Configuration
RADARR_URL = os.getenv("RADARR_URL", "http://192.168.40.11:7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "")
SONARR_URL = os.getenv("SONARR_URL", "http://192.168.40.11:8989")
SONARR_API_KEY = os.getenv("SONARR_API_KEY", "")

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Track previous states for alerts
previous_states = {}


def ssh_execute(host: str, command: str, user: str = None, timeout: int = 30) -> tuple:
    """Execute command via SSH."""
    if user is None:
        user = SSH_USER

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        key = paramiko.Ed25519Key.from_private_key_file(SSH_KEY_PATH)
        ssh.connect(host, username=user, pkey=key, timeout=10)
        stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0 and error:
            return None, error
        return output, error
    except Exception as e:
        logger.error(f"SSH error to {host}: {e}")
        return None, str(e)
    finally:
        ssh.close()


def create_embed(title: str, description: str = None, color: int = 0x00ff00, fields: list = None):
    """Create a Discord embed."""
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
    embed.set_footer(text="Argus - Homelab Guardian")
    if fields:
        for field in fields:
            embed.add_field(name=field["name"], value=field["value"], inline=field.get("inline", True))
    return embed


# ============== INFRASTRUCTURE COMMANDS ==============

@bot.tree.command(name="status", description="Get cluster and infrastructure status")
async def status(interaction: discord.Interaction):
    """Get overall infrastructure status."""
    await interaction.response.defer()

    try:
        node_status = []
        running_vms = 0
        total_vms = 0

        # Check each Proxmox node via SSH
        for node, ip in PROXMOX_NODES.items():
            output, error = ssh_execute(ip, "uptime -p", user="root")
            if output:
                # Get VM count on this node
                vm_output, _ = ssh_execute(ip, "qm list 2>/dev/null | tail -n +2 | wc -l", user="root")
                running_output, _ = ssh_execute(ip, "qm list 2>/dev/null | grep running | wc -l", user="root")

                vm_count = int(vm_output) if vm_output and vm_output.isdigit() else 0
                running_count = int(running_output) if running_output and running_output.isdigit() else 0

                total_vms += vm_count
                running_vms += running_count
                node_status.append(f"🟢 **{node}**: {output} ({running_count}/{vm_count} VMs)")
            else:
                node_status.append(f"🔴 **{node}**: Unreachable")

        # Docker containers
        container_count = 0
        for host_name, host_ip in DOCKER_HOSTS.items():
            output, _ = ssh_execute(host_ip, "docker ps -q | wc -l")
            if output and output.isdigit():
                container_count += int(output)

        embed = create_embed(
            "🖥️ Infrastructure Status",
            "Current state of your homelab",
            color=0x00ff00
        )

        embed.add_field(name="Proxmox Cluster", value=f"{len([n for n in node_status if '🟢' in n])}/{len(PROXMOX_NODES)} nodes online", inline=True)
        embed.add_field(name="Virtual Machines", value=f"{running_vms}/{total_vms} running", inline=True)
        embed.add_field(name="Docker Containers", value=f"{container_count} running", inline=True)
        embed.add_field(name="Node Details", value="\n".join(node_status), inline=False)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Status command error: {e}")
        await interaction.followup.send(embed=create_embed("❌ Error", str(e), color=0xff0000))


@bot.tree.command(name="shutdown", description="Shutdown a Proxmox node")
@app_commands.describe(node="Node to shutdown (node01, node02, node03)")
@app_commands.choices(node=[
    app_commands.Choice(name="node01", value="node01"),
    app_commands.Choice(name="node02", value="node02"),
    app_commands.Choice(name="node03", value="node03"),
])
async def shutdown(interaction: discord.Interaction, node: str):
    """Shutdown a Proxmox node with confirmation."""

    class ConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            self.value = None

        @discord.ui.button(label="Confirm Shutdown", style=discord.ButtonStyle.danger)
        async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            self.value = True
            self.stop()
            await button_interaction.response.defer()

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
        async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            self.value = False
            self.stop()
            await button_interaction.response.defer()

    view = ConfirmView()
    embed = create_embed(
        "⚠️ Confirm Node Shutdown",
        f"Are you sure you want to shutdown **{node}**?\n\nThis will stop all VMs on this node!",
        color=0xff9900
    )

    await interaction.response.send_message(embed=embed, view=view)
    await view.wait()

    if view.value is None:
        await interaction.edit_original_response(
            embed=create_embed("⏱️ Timeout", "Shutdown cancelled - no response", color=0x808080),
            view=None
        )
    elif view.value:
        try:
            node_ip = PROXMOX_NODES.get(node)
            output, error = ssh_execute(node_ip, "shutdown -h +1 'Shutdown initiated by Argus'", user="root")

            await interaction.edit_original_response(
                embed=create_embed("✅ Shutdown Initiated", f"**{node}** will shutdown in 1 minute...", color=0x00ff00),
                view=None
            )
        except Exception as e:
            await interaction.edit_original_response(
                embed=create_embed("❌ Shutdown Failed", str(e), color=0xff0000),
                view=None
            )
    else:
        await interaction.edit_original_response(
            embed=create_embed("❌ Cancelled", "Shutdown cancelled by user", color=0x808080),
            view=None
        )


@bot.tree.command(name="reboot", description="Reboot a VM or Proxmox node")
@app_commands.describe(target="VM name or node (e.g., docker-utilities, node01)")
async def reboot(interaction: discord.Interaction, target: str):
    """Reboot a VM or node."""
    await interaction.response.defer()

    try:
        # Check if it's a node
        if target in PROXMOX_NODES:
            node_ip = PROXMOX_NODES[target]
            output, error = ssh_execute(node_ip, "reboot", user="root")
            await interaction.followup.send(
                embed=create_embed("🔄 Reboot Initiated", f"**{target}** is rebooting...", color=0x00ff00)
            )
            return

        # Check if it's a VM
        if target in VM_MAPPING:
            node, vmid = VM_MAPPING[target]
            node_ip = PROXMOX_NODES[node]
            output, error = ssh_execute(node_ip, f"qm reboot {vmid}", user="root")

            if error and "error" in error.lower():
                await interaction.followup.send(embed=create_embed("❌ Error", error, color=0xff0000))
            else:
                await interaction.followup.send(
                    embed=create_embed("🔄 Reboot Initiated", f"VM **{target}** (ID: {vmid}) is rebooting...", color=0x00ff00)
                )
            return

        # List valid targets
        valid_targets = list(PROXMOX_NODES.keys()) + list(VM_MAPPING.keys())
        await interaction.followup.send(
            embed=create_embed(
                "❌ Not Found",
                f"Unknown target: `{target}`\n\n**Valid targets:**\n• Nodes: {', '.join(PROXMOX_NODES.keys())}\n• VMs: {', '.join(VM_MAPPING.keys())}",
                color=0xff0000
            )
        )

    except Exception as e:
        logger.error(f"Reboot command error: {e}")
        await interaction.followup.send(embed=create_embed("❌ Error", str(e), color=0xff0000))


@bot.tree.command(name="start", description="Start a VM")
@app_commands.describe(vm="VM name to start")
async def start_vm(interaction: discord.Interaction, vm: str):
    """Start a VM."""
    await interaction.response.defer()

    try:
        if vm not in VM_MAPPING:
            await interaction.followup.send(
                embed=create_embed("❌ Not Found", f"Unknown VM: `{vm}`\n\n**Valid VMs:** {', '.join(VM_MAPPING.keys())}", color=0xff0000)
            )
            return

        node, vmid = VM_MAPPING[vm]
        node_ip = PROXMOX_NODES[node]
        output, error = ssh_execute(node_ip, f"qm start {vmid}", user="root")

        if error and "already running" in error.lower():
            await interaction.followup.send(
                embed=create_embed("ℹ️ Already Running", f"VM **{vm}** is already running", color=0x0099ff)
            )
        elif error and "error" in error.lower():
            await interaction.followup.send(embed=create_embed("❌ Error", error, color=0xff0000))
        else:
            await interaction.followup.send(
                embed=create_embed("✅ VM Started", f"**{vm}** (ID: {vmid}) is starting...", color=0x00ff00)
            )

    except Exception as e:
        logger.error(f"Start command error: {e}")
        await interaction.followup.send(embed=create_embed("❌ Error", str(e), color=0xff0000))


@bot.tree.command(name="stop", description="Stop a VM")
@app_commands.describe(vm="VM name to stop")
async def stop_vm(interaction: discord.Interaction, vm: str):
    """Stop a VM."""
    await interaction.response.defer()

    try:
        if vm not in VM_MAPPING:
            await interaction.followup.send(
                embed=create_embed("❌ Not Found", f"Unknown VM: `{vm}`\n\n**Valid VMs:** {', '.join(VM_MAPPING.keys())}", color=0xff0000)
            )
            return

        node, vmid = VM_MAPPING[vm]
        node_ip = PROXMOX_NODES[node]
        output, error = ssh_execute(node_ip, f"qm shutdown {vmid}", user="root")

        if error and "not running" in error.lower():
            await interaction.followup.send(
                embed=create_embed("ℹ️ Already Stopped", f"VM **{vm}** is not running", color=0x0099ff)
            )
        elif error and "error" in error.lower():
            await interaction.followup.send(embed=create_embed("❌ Error", error, color=0xff0000))
        else:
            await interaction.followup.send(
                embed=create_embed("✅ VM Stopping", f"**{vm}** (ID: {vmid}) is shutting down...", color=0x00ff00)
            )

    except Exception as e:
        logger.error(f"Stop command error: {e}")
        await interaction.followup.send(embed=create_embed("❌ Error", str(e), color=0xff0000))


@bot.tree.command(name="vms", description="List all VMs and their status")
async def list_vms(interaction: discord.Interaction):
    """List all VMs."""
    await interaction.response.defer()

    try:
        embed = create_embed("🖥️ Virtual Machines", color=0x0099ff)

        for node, node_ip in PROXMOX_NODES.items():
            output, error = ssh_execute(node_ip, "qm list 2>/dev/null | tail -n +2", user="root")

            if output:
                lines = output.strip().split('\n')
                vm_list = []
                for line in lines[:10]:  # Limit to 10 VMs per node
                    parts = line.split()
                    if len(parts) >= 3:
                        vmid = parts[0]
                        name = parts[1]
                        status = parts[2]
                        icon = "🟢" if status == "running" else "🔴"
                        vm_list.append(f"{icon} {name} ({vmid})")

                if len(lines) > 10:
                    vm_list.append(f"... and {len(lines) - 10} more")

                embed.add_field(name=f"📦 {node}", value="\n".join(vm_list) if vm_list else "No VMs", inline=False)
            else:
                embed.add_field(name=f"📦 {node}", value="Unable to fetch VMs", inline=False)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"VMs command error: {e}")
        await interaction.followup.send(embed=create_embed("❌ Error", str(e), color=0xff0000))


# ============== CONTAINER COMMANDS ==============

@bot.tree.command(name="restart", description="Restart a Docker container")
@app_commands.describe(container="Container name", host="Docker host (utilities or media)")
@app_commands.choices(host=[
    app_commands.Choice(name="utilities", value="utilities"),
    app_commands.Choice(name="media", value="media"),
])
async def restart_container(interaction: discord.Interaction, container: str, host: str = "utilities"):
    """Restart a Docker container."""
    await interaction.response.defer()

    try:
        host_ip = DOCKER_HOSTS.get(host)
        if not host_ip:
            await interaction.followup.send(embed=create_embed("❌ Error", f"Unknown host: {host}", color=0xff0000))
            return

        output, error = ssh_execute(host_ip, f"docker restart {container}")

        if error and ("No such container" in error or "Error" in error):
            await interaction.followup.send(embed=create_embed("❌ Error", error, color=0xff0000))
        else:
            await interaction.followup.send(
                embed=create_embed("🔄 Container Restarted", f"**{container}** on {host} has been restarted", color=0x00ff00)
            )

    except Exception as e:
        logger.error(f"Restart command error: {e}")
        await interaction.followup.send(embed=create_embed("❌ Error", str(e), color=0xff0000))


@bot.tree.command(name="logs", description="Get recent container logs")
@app_commands.describe(container="Container name", host="Docker host", lines="Number of lines (default 20)")
@app_commands.choices(host=[
    app_commands.Choice(name="utilities", value="utilities"),
    app_commands.Choice(name="media", value="media"),
])
async def logs(interaction: discord.Interaction, container: str, host: str = "utilities", lines: int = 20):
    """Get container logs."""
    await interaction.response.defer()

    try:
        host_ip = DOCKER_HOSTS.get(host)
        output, error = ssh_execute(host_ip, f"docker logs --tail {min(lines, 50)} {container} 2>&1")

        if not output:
            output = error if error else "No logs available"

        # Truncate if too long
        if len(output) > 1800:
            output = "..." + output[-1800:]

        embed = create_embed(f"📋 Logs: {container}", f"```\n{output}\n```", color=0x0099ff)
        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Logs command error: {e}")
        await interaction.followup.send(embed=create_embed("❌ Error", str(e), color=0xff0000))


@bot.tree.command(name="containers", description="List running containers")
@app_commands.describe(host="Docker host (utilities, media, or all)")
@app_commands.choices(host=[
    app_commands.Choice(name="all", value="all"),
    app_commands.Choice(name="utilities", value="utilities"),
    app_commands.Choice(name="media", value="media"),
])
async def containers(interaction: discord.Interaction, host: str = "all"):
    """List running containers."""
    await interaction.response.defer()

    try:
        hosts_to_check = DOCKER_HOSTS if host == "all" else {host: DOCKER_HOSTS[host]}

        embed = create_embed("🐳 Running Containers", color=0x0099ff)

        for host_name, host_ip in hosts_to_check.items():
            output, _ = ssh_execute(host_ip, "docker ps --format '{{.Names}}: {{.Status}}'")

            if output:
                lines = output.split("\n")
                if len(lines) > 15:
                    output = "\n".join(lines[:15]) + f"\n... and {len(lines) - 15} more"
                embed.add_field(name=f"📦 {host_name}", value=f"```\n{output}\n```", inline=False)
            else:
                embed.add_field(name=f"📦 {host_name}", value="No containers or unreachable", inline=False)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Containers command error: {e}")
        await interaction.followup.send(embed=create_embed("❌ Error", str(e), color=0xff0000))


@bot.tree.command(name="deploy", description="Run an Ansible playbook")
@app_commands.describe(playbook="Playbook name")
@app_commands.choices(playbook=[
    app_commands.Choice(name="traefik", value="traefik/deploy-traefik.yml"),
    app_commands.Choice(name="authentik", value="authentik/deploy-authentik.yml"),
    app_commands.Choice(name="immich", value="immich/deploy-immich.yml"),
    app_commands.Choice(name="monitoring", value="monitoring/deploy-monitoring-stack.yml"),
    app_commands.Choice(name="glance", value="glance/deploy-glance-dashboard.yml"),
    app_commands.Choice(name="arr-stack", value="media/deploy-arr-stack.yml"),
])
async def deploy(interaction: discord.Interaction, playbook: str):
    """Run an Ansible playbook."""
    await interaction.response.defer()

    try:
        ansible_ip = "192.168.20.30"

        await interaction.followup.send(
            embed=create_embed("🚀 Deployment Started", f"Running playbook: `{playbook}`\n\nThis may take a few minutes...", color=0x0099ff)
        )

        output, error = ssh_execute(
            ansible_ip,
            f"cd ~/ansible && ansible-playbook {playbook} 2>&1 | tail -30",
            timeout=300
        )

        result = output if output else error
        if result and ("failed=0" in result or "ok=" in result):
            result_embed = create_embed("✅ Deployment Complete", f"Playbook `{playbook}` finished successfully", color=0x00ff00)
        else:
            result_embed = create_embed("⚠️ Deployment Result", f"```\n{result[-1500:] if result else 'No output'}\n```", color=0xff9900)

        await interaction.channel.send(embed=result_embed)

    except Exception as e:
        logger.error(f"Deploy command error: {e}")
        await interaction.channel.send(embed=create_embed("❌ Deployment Error", str(e), color=0xff0000))


# ============== MONITORING COMMANDS ==============

@bot.tree.command(name="health", description="Quick infrastructure health check")
async def health(interaction: discord.Interaction):
    """Quick health check of all services."""
    await interaction.response.defer()

    try:
        checks = []

        # Check Proxmox nodes
        for node, ip in PROXMOX_NODES.items():
            output, _ = ssh_execute(ip, "uptime -p", user="root")
            if output:
                checks.append(f"🟢 **{node}**: {output}")
            else:
                checks.append(f"🔴 **{node}**: Unreachable")

        # Check Docker hosts
        for host, ip in DOCKER_HOSTS.items():
            output, _ = ssh_execute(ip, "docker ps -q | wc -l")
            if output:
                checks.append(f"🟢 **docker-{host}**: {output} containers")
            else:
                checks.append(f"🔴 **docker-{host}**: Unreachable")

        # Check key services via HTTP
        services = [
            ("Traefik", "http://192.168.40.20:80"),
            ("Grafana", "http://192.168.40.10:3030"),
            ("Prometheus", "http://192.168.40.10:9090"),
        ]

        async with aiohttp.ClientSession() as session:
            for name, url in services:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        checks.append(f"🟢 **{name}**: Online")
                except:
                    checks.append(f"🔴 **{name}**: Offline")

        embed = create_embed("🏥 Health Check", "\n".join(checks), color=0x00ff00)
        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Health command error: {e}")
        await interaction.followup.send(embed=create_embed("❌ Error", str(e), color=0xff0000))


@bot.tree.command(name="disk", description="Check disk usage across hosts")
async def disk(interaction: discord.Interaction):
    """Check disk usage."""
    await interaction.response.defer()

    try:
        embed = create_embed("💾 Disk Usage", color=0x0099ff)

        # Check Proxmox nodes
        for name, ip in PROXMOX_NODES.items():
            output, _ = ssh_execute(ip, "df -h / | tail -1 | awk '{print $3 \"/\" $2 \" (\" $5 \")\"}'", user="root")
            if output:
                usage_str = output.split("(")[1].replace("%)", "") if "%" in output else "0"
                usage = int(usage_str) if usage_str.isdigit() else 0
                icon = "🟢" if usage < 70 else "🟡" if usage < 85 else "🔴"
                embed.add_field(name=f"{icon} {name}", value=output, inline=True)
            else:
                embed.add_field(name=f"🔴 {name}", value="Unreachable", inline=True)

        # Check Docker hosts
        for name, ip in DOCKER_HOSTS.items():
            output, _ = ssh_execute(ip, "df -h / | tail -1 | awk '{print $3 \"/\" $2 \" (\" $5 \")\"}'")
            if output:
                usage_str = output.split("(")[1].replace("%)", "") if "%" in output else "0"
                usage = int(usage_str) if usage_str.isdigit() else 0
                icon = "🟢" if usage < 70 else "🟡" if usage < 85 else "🔴"
                embed.add_field(name=f"{icon} docker-{name}", value=output, inline=True)
            else:
                embed.add_field(name=f"🔴 docker-{name}", value="Unreachable", inline=True)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Disk command error: {e}")
        await interaction.followup.send(embed=create_embed("❌ Error", str(e), color=0xff0000))


@bot.tree.command(name="top", description="Show top resource consumers")
async def top_resources(interaction: discord.Interaction):
    """Show top resource consuming containers."""
    await interaction.response.defer()

    try:
        embed = create_embed("📊 Top Resource Consumers", color=0x0099ff)

        for host_name, host_ip in DOCKER_HOSTS.items():
            output, _ = ssh_execute(
                host_ip,
                "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' | head -8"
            )

            if output:
                embed.add_field(name=f"📦 {host_name}", value=f"```\n{output}\n```", inline=False)
            else:
                embed.add_field(name=f"📦 {host_name}", value="Unable to fetch stats", inline=False)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Top command error: {e}")
        await interaction.followup.send(embed=create_embed("❌ Error", str(e), color=0xff0000))


@bot.tree.command(name="uptime", description="Show uptime for all hosts")
async def uptime_cmd(interaction: discord.Interaction):
    """Show uptime for all hosts."""
    await interaction.response.defer()

    try:
        embed = create_embed("⏱️ System Uptime", color=0x0099ff)

        # Proxmox nodes
        for name, ip in PROXMOX_NODES.items():
            output, _ = ssh_execute(ip, "uptime -p", user="root")
            embed.add_field(name=f"🖥️ {name}", value=output if output else "Unreachable", inline=True)

        # Docker hosts
        for name, ip in DOCKER_HOSTS.items():
            output, _ = ssh_execute(ip, "uptime -p")
            embed.add_field(name=f"🐳 docker-{name}", value=output if output else "Unreachable", inline=True)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Uptime command error: {e}")
        await interaction.followup.send(embed=create_embed("❌ Error", str(e), color=0xff0000))


# ============== MEDIA COMMANDS ==============

@bot.tree.command(name="request", description="Request a movie or TV show")
@app_commands.describe(title="Movie or show title", media_type="Movie or TV Show")
@app_commands.choices(media_type=[
    app_commands.Choice(name="Movie", value="movie"),
    app_commands.Choice(name="TV Show", value="tv"),
])
async def request_media(interaction: discord.Interaction, title: str, media_type: str = "movie"):
    """Request a movie or TV show."""
    await interaction.response.defer()

    try:
        if media_type == "movie":
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{RADARR_URL}/api/v3/movie/lookup",
                    params={"term": title},
                    headers={"X-Api-Key": RADARR_API_KEY}
                ) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(
                            embed=create_embed("❌ Error", f"Radarr API error: {resp.status}", color=0xff0000)
                        )
                        return
                    results = await resp.json()

            if not results:
                await interaction.followup.send(
                    embed=create_embed("🔍 Not Found", f"No movies found matching: {title}", color=0xff9900)
                )
                return

            movie = results[0]
            embed = create_embed(
                f"🎬 {movie['title']} ({movie.get('year', 'N/A')})",
                movie.get('overview', 'No description available')[:500],
                color=0x0099ff
            )

            if movie.get('remotePoster'):
                embed.set_thumbnail(url=movie['remotePoster'])

            class AddView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=60)

                @discord.ui.button(label="Add to Radarr", style=discord.ButtonStyle.success)
                async def add_movie(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                    try:
                        add_data = {
                            "title": movie['title'],
                            "tmdbId": movie['tmdbId'],
                            "qualityProfileId": 1,
                            "rootFolderPath": "/data/media/movies",
                            "monitored": True,
                            "addOptions": {"searchForMovie": True}
                        }

                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                f"{RADARR_URL}/api/v3/movie",
                                json=add_data,
                                headers={"X-Api-Key": RADARR_API_KEY}
                            ) as resp:
                                if resp.status in [200, 201]:
                                    await button_interaction.response.send_message(
                                        embed=create_embed("✅ Added", f"**{movie['title']}** added to Radarr!", color=0x00ff00)
                                    )
                                else:
                                    text = await resp.text()
                                    await button_interaction.response.send_message(
                                        embed=create_embed("❌ Error", text[:500], color=0xff0000)
                                    )
                    except Exception as e:
                        await button_interaction.response.send_message(
                            embed=create_embed("❌ Error", str(e), color=0xff0000)
                        )

            await interaction.followup.send(embed=embed, view=AddView())

        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{SONARR_URL}/api/v3/series/lookup",
                    params={"term": title},
                    headers={"X-Api-Key": SONARR_API_KEY}
                ) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(
                            embed=create_embed("❌ Error", f"Sonarr API error: {resp.status}", color=0xff0000)
                        )
                        return
                    results = await resp.json()

            if not results:
                await interaction.followup.send(
                    embed=create_embed("🔍 Not Found", f"No TV shows found matching: {title}", color=0xff9900)
                )
                return

            show = results[0]
            embed = create_embed(
                f"📺 {show['title']} ({show.get('year', 'N/A')})",
                show.get('overview', 'No description available')[:500],
                color=0x0099ff
            )

            embed.add_field(name="Seasons", value=str(show.get('seasonCount', 'N/A')), inline=True)
            embed.add_field(name="Status", value=show.get('status', 'N/A'), inline=True)

            await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Request command error: {e}")
        await interaction.followup.send(embed=create_embed("❌ Error", str(e), color=0xff0000))


@bot.tree.command(name="media", description="Get media library statistics")
async def media_stats(interaction: discord.Interaction):
    """Get media library stats."""
    await interaction.response.defer()

    try:
        embed = create_embed("🎬 Media Library", color=0x0099ff)

        async with aiohttp.ClientSession() as session:
            # Radarr movies
            try:
                async with session.get(
                    f"{RADARR_URL}/api/v3/movie",
                    headers={"X-Api-Key": RADARR_API_KEY}
                ) as resp:
                    movies = await resp.json()
                    downloaded = sum(1 for m in movies if m.get('hasFile'))
                    embed.add_field(name="🎬 Movies", value=f"{downloaded}/{len(movies)} downloaded", inline=True)
            except Exception as e:
                embed.add_field(name="🎬 Movies", value="Unavailable", inline=True)

            # Sonarr series
            try:
                async with session.get(
                    f"{SONARR_URL}/api/v3/series",
                    headers={"X-Api-Key": SONARR_API_KEY}
                ) as resp:
                    series = await resp.json()
                    embed.add_field(name="📺 TV Shows", value=f"{len(series)} series", inline=True)
            except Exception as e:
                embed.add_field(name="📺 TV Shows", value="Unavailable", inline=True)

        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Media command error: {e}")
        await interaction.followup.send(embed=create_embed("❌ Error", str(e), color=0xff0000))


# ============== ALERTS TASK ==============

@tasks.loop(minutes=5)
async def check_services():
    """Background task to check services and send alerts."""
    global previous_states

    if not ALERTS_CHANNEL_ID:
        return

    channel = bot.get_channel(ALERTS_CHANNEL_ID)
    if not channel:
        return

    try:
        for host_name, host_ip in DOCKER_HOSTS.items():
            output, _ = ssh_execute(host_ip, "docker ps --format '{{.Names}}:{{.Status}}'")
            if not output:
                continue

            for line in output.split("\n"):
                if ":" not in line:
                    continue
                name, status = line.split(":", 1)
                key = f"{host_name}:{name}"

                is_healthy = "Up" in status and "unhealthy" not in status.lower()
                prev_healthy = previous_states.get(key, True)

                if not is_healthy and prev_healthy:
                    await channel.send(
                        embed=create_embed(
                            "🔴 Container Down",
                            f"**{name}** on {host_name} is unhealthy\n\nStatus: {status}",
                            color=0xff0000
                        )
                    )
                elif is_healthy and not prev_healthy:
                    await channel.send(
                        embed=create_embed(
                            "🟢 Container Recovered",
                            f"**{name}** on {host_name} is back online",
                            color=0x00ff00
                        )
                    )

                previous_states[key] = is_healthy

    except Exception as e:
        logger.error(f"Alert check error: {e}")


# ============== BOT EVENTS ==============

@bot.event
async def on_ready():
    """Called when bot is ready."""
    logger.info(f"Logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} commands")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

    if not check_services.is_running():
        check_services.start()

    if SYSADMIN_CHANNEL_ID:
        channel = bot.get_channel(SYSADMIN_CHANNEL_ID)
        if channel:
            await channel.send(
                embed=create_embed(
                    "🛡️ Argus Online",
                    "Hey Master Hermes, I'm ready to guard your homelab!\n\n"
                    "Type `/` to see available commands.",
                    color=0x00ff00
                )
            )


@bot.tree.command(name="help", description="Show available commands")
async def help_command(interaction: discord.Interaction):
    """Show help message."""
    embed = create_embed("🛡️ Argus Commands", "Your homelab guardian", color=0x0099ff)

    embed.add_field(
        name="🖥️ Infrastructure",
        value="`/status` - Cluster overview\n`/shutdown` - Shutdown node\n`/reboot` - Reboot VM/node\n`/start` - Start VM\n`/stop` - Stop VM\n`/vms` - List all VMs",
        inline=False
    )

    embed.add_field(
        name="🐳 Containers",
        value="`/restart` - Restart container\n`/logs` - View logs\n`/containers` - List containers\n`/deploy` - Run playbook",
        inline=False
    )

    embed.add_field(
        name="📊 Monitoring",
        value="`/health` - Health check\n`/disk` - Disk usage\n`/top` - Resource usage\n`/uptime` - System uptime",
        inline=False
    )

    embed.add_field(
        name="🎬 Media",
        value="`/request` - Request movie/show\n`/media` - Library stats",
        inline=False
    )

    await interaction.response.send_message(embed=embed)


def main():
    """Main entry point."""
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not set!")
        return

    logger.info("Starting Argus - Homelab Guardian...")
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
