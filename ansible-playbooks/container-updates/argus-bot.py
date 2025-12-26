#!/usr/bin/env python3
"""
Argus - Container Update Guardian Bot
Location: /opt/argus-bot/argus-bot.py

Features:
- Watchtower webhook integration for update notifications
- Button-based approval for container updates
- Slash commands for checking and managing updates
- Container status monitoring
- Channel-restricted to container-updates

Commands:
- /check - Check all containers for available updates
- /update <container> - Update a specific container
- /updateall - Update all containers with pending updates
- /containers - List all monitored containers
- /status - Show container running status
- /argus - Show help and bot info
"""

import os
import re
import asyncio
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify
import discord
from discord import app_commands, ui
from discord.ext import commands, tasks
import threading
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN', '')
WEBHOOK_PORT = int(os.environ.get('WEBHOOK_PORT', '5000'))
SSH_KEY_PATH = os.environ.get('SSH_KEY_PATH', '/root/.ssh/homelab_ed25519')
ALLOWED_CHANNELS = os.environ.get('ALLOWED_CHANNELS', 'container-updates')

# Container to host mapping
CONTAINER_HOSTS = {
    # docker-vm-utilities01 (192.168.40.10)
    "uptime-kuma": "192.168.40.10",
    "prometheus": "192.168.40.10",
    "grafana": "192.168.40.10",
    "glance": "192.168.40.10",
    "n8n": "192.168.40.10",
    "paperless-ngx": "192.168.40.10",
    "speedtest-tracker": "192.168.40.10",
    "jaeger": "192.168.40.10",
    "omada-exporter": "192.168.40.10",
    "nba-stats-api": "192.168.40.10",
    "media-stats-api": "192.168.40.10",

    # docker-vm-media01 (192.168.40.11)
    "jellyfin": "192.168.40.11",
    "radarr": "192.168.40.11",
    "sonarr": "192.168.40.11",
    "lidarr": "192.168.40.11",
    "prowlarr": "192.168.40.11",
    "bazarr": "192.168.40.11",
    "overseerr": "192.168.40.11",
    "jellyseerr": "192.168.40.11",
    "tdarr": "192.168.40.11",
    "autobrr": "192.168.40.11",
    "deluge": "192.168.40.11",
    "sabnzbd": "192.168.40.11",

    # Dedicated VMs
    "traefik": "192.168.40.20",
    "authentik-server": "192.168.40.21",
    "authentik-worker": "192.168.40.21",
    "immich-server": "192.168.40.22",
    "immich-ml": "192.168.40.22",
    "gitlab": "192.168.40.23",
}

# Pending updates storage
pending_updates = {}
available_updates = {}

# Flask app for webhook
app = Flask(__name__)

# Parse allowed channels
def parse_allowed_channels(channels_str: str) -> list:
    """Parse allowed channels from comma-separated string."""
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
intents.message_content = True

class ArgusBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.notification_channel_id = None

    async def setup_hook(self):
        await self.tree.sync()
        logger.info("Slash commands synced")

bot = ArgusBot()


# ============================================================================
# Channel Restriction Decorator
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
        # Check if name contains the allowed channel (for threads like "container-updates-thread")
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
# Button Views for Update Approval
# ============================================================================

class UpdateApprovalView(ui.View):
    """Button view for approving/rejecting container updates."""

    def __init__(self, container_name: str, host_ip: str, old_image: str, new_image: str):
        super().__init__(timeout=86400)  # 24 hour timeout
        self.container_name = container_name
        self.host_ip = host_ip
        self.old_image = old_image
        self.new_image = new_image
        self.responded = False

    @ui.button(label="Update", style=discord.ButtonStyle.success, emoji="")
    async def approve_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.responded:
            await interaction.response.send_message("This update has already been processed.", ephemeral=True)
            return

        self.responded = True
        self.disable_all_items()
        await interaction.response.edit_message(view=self)

        # Send updating message
        await interaction.followup.send(
            f" Updating **{self.container_name}**... Please wait!"
        )

        # Perform update
        new_version, error = await asyncio.get_event_loop().run_in_executor(
            None, update_container, self.host_ip, self.container_name
        )

        if error:
            await interaction.followup.send(
                f" Update failed for **{self.container_name}**\n"
                f"```{error}```"
            )
        else:
            await interaction.followup.send(
                f" **{self.container_name}** has been updated!\n"
                f" New version: `{new_version}`"
            )

    @ui.button(label="Skip", style=discord.ButtonStyle.danger, emoji="")
    async def reject_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.responded:
            await interaction.response.send_message("This update has already been processed.", ephemeral=True)
            return

        self.responded = True
        self.disable_all_items()
        await interaction.response.edit_message(view=self)

        await interaction.followup.send(
            f" Skipped update for **{self.container_name}**"
        )

    def disable_all_items(self):
        for item in self.children:
            item.disabled = True


class UpdateAllView(ui.View):
    """Button view for confirming update all."""

    def __init__(self, updates: dict):
        super().__init__(timeout=300)  # 5 minute timeout
        self.updates = updates
        self.responded = False

    @ui.button(label="Update All", style=discord.ButtonStyle.success, emoji="")
    async def confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.responded:
            return

        self.responded = True
        self.disable_all_items()
        await interaction.response.edit_message(view=self)

        await interaction.followup.send(
            f" Updating {len(self.updates)} containers..."
        )

        success = []
        failed = []

        for container_name, host_ip in self.updates.items():
            new_version, error = await asyncio.get_event_loop().run_in_executor(
                None, update_container, host_ip, container_name
            )

            if error:
                failed.append(f"{container_name}: {error[:50]}")
            else:
                success.append(container_name)

        summary = f"**Update Complete**\n\n"
        summary += f" Success: {len(success)}\n"
        if success:
            summary += f"```{', '.join(success)}```\n"
        if failed:
            summary += f" Failed: {len(failed)}\n"
            summary += f"```{chr(10).join(failed)}```"

        await interaction.followup.send(summary)

    @ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="")
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.responded:
            return

        self.responded = True
        self.disable_all_items()
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(" Update cancelled.")

    def disable_all_items(self):
        for item in self.children:
            item.disabled = True


# ============================================================================
# SSH Helper Functions
# ============================================================================

def ssh_command(host: str, command: str, timeout: int = 30) -> str:
    """Execute SSH command and return output."""
    try:
        cmd = (
            f"ssh -i {SSH_KEY_PATH} -o StrictHostKeyChecking=no "
            f"-o ConnectTimeout=10 hermes-admin@{host} \"{command}\""
        )
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception as e:
        logger.error(f"SSH error to {host}: {e}")
        return ""


def get_container_info(host_ip: str, container_name: str) -> dict:
    """Get container status and image info."""
    try:
        cmd = (
            f"ssh -i {SSH_KEY_PATH} -o StrictHostKeyChecking=no -o ConnectTimeout=5 "
            f"hermes-admin@{host_ip} "
            f"\"docker inspect {container_name} --format "
            f"'{{{{.State.Status}}}}|{{{{.Config.Image}}}}|{{{{.State.StartedAt}}}}' 2>/dev/null\""
        )
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split('|')
            return {
                'status': parts[0] if parts else 'unknown',
                'image': parts[1] if len(parts) > 1 else 'unknown',
                'started_at': parts[2] if len(parts) > 2 else 'unknown'
            }
    except Exception as e:
        logger.error(f"Error getting info for {container_name}: {e}")
    return None


def check_for_updates_on_host(host_ip: str) -> str:
    """Run watchtower check on a specific host."""
    try:
        cmd = (
            f"ssh -i {SSH_KEY_PATH} -o StrictHostKeyChecking=no -o ConnectTimeout=10 "
            f"hermes-admin@{host_ip} "
            f"\"docker exec watchtower /watchtower --run-once 2>&1\" 2>/dev/null"
        )
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        return result.stdout
    except Exception as e:
        logger.error(f"Error checking updates on {host_ip}: {e}")
    return ""


def update_container(host_ip: str, container_name: str) -> tuple:
    """Update a container and return (new_version, error)."""
    try:
        # Get compose directory
        cmd_dir = (
            f"ssh -i {SSH_KEY_PATH} -o StrictHostKeyChecking=no hermes-admin@{host_ip} "
            f"\"docker inspect {container_name} --format "
            f"'{{{{index .Config.Labels \\\"com.docker.compose.project.working_dir\\\"}}}}'\""
        )
        result = subprocess.run(cmd_dir, shell=True, capture_output=True, text=True, timeout=30)
        compose_dir = result.stdout.strip()

        if not compose_dir:
            return None, "Could not find compose directory"

        # Pull and recreate
        cmd_update = (
            f"ssh -i {SSH_KEY_PATH} -o StrictHostKeyChecking=no hermes-admin@{host_ip} "
            f"\"cd {compose_dir} && sudo docker compose pull {container_name} && "
            f"sudo docker compose up -d {container_name}\""
        )
        result = subprocess.run(cmd_update, shell=True, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            return None, result.stderr

        # Get new version
        cmd_version = (
            f"ssh -i {SSH_KEY_PATH} -o StrictHostKeyChecking=no hermes-admin@{host_ip} "
            f"\"docker inspect {container_name} --format '{{{{.Config.Image}}}}'\""
        )
        result = subprocess.run(cmd_version, shell=True, capture_output=True, text=True, timeout=30)

        return result.stdout.strip(), None
    except Exception as e:
        return None, str(e)


# ============================================================================
# Slash Commands
# ============================================================================

@bot.tree.command(name="argus", description="Show Argus help and available commands")
@is_allowed_channel()
async def argus_help(interaction: discord.Interaction):
    """Show help information."""
    embed = discord.Embed(
        title=" Argus - Container Update Guardian",
        description="I monitor your containers and notify you when updates are available.",
        color=0x00ff00
    )

    embed.add_field(
        name=" Check & Update",
        value=(
            "`/check` - Scan all containers for updates\n"
            "`/update <name>` - Update a specific container\n"
            "`/updateall` - Update all pending containers"
        ),
        inline=False
    )

    embed.add_field(
        name=" Status & Info",
        value=(
            "`/containers` - List all monitored containers\n"
            "`/status` - Show container running status\n"
            "`/argus` - Show this help message"
        ),
        inline=False
    )

    embed.add_field(
        name=" Automatic Updates",
        value="When Watchtower detects updates, I'll send a notification with approve/skip buttons.",
        inline=False
    )

    embed.set_footer(text=f"Monitoring {len(CONTAINER_HOSTS)} containers across 6 hosts")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="check", description="Check all containers for available updates")
@is_allowed_channel()
async def check_updates(interaction: discord.Interaction):
    """Check all containers for updates."""
    global available_updates
    available_updates = {}

    await interaction.response.defer()

    # Group containers by host
    hosts = {}
    for container, host_ip in CONTAINER_HOSTS.items():
        if host_ip not in hosts:
            hosts[host_ip] = []
        hosts[host_ip].append(container)

    results = []
    updates_found = []

    # Check each host
    for host_ip, containers in hosts.items():
        for container in containers:
            info = await asyncio.get_event_loop().run_in_executor(
                None, get_container_info, host_ip, container
            )
            if info:
                results.append({
                    'name': container,
                    'host': host_ip,
                    'status': info['status'],
                    'image': info['image'],
                    'has_update': False
                })

        # Run watchtower check
        output = await asyncio.get_event_loop().run_in_executor(
            None, check_for_updates_on_host, host_ip
        )

        # Parse update notifications
        found = re.findall(r'Found new (.+?) image', output)
        for image_name in found:
            container_name = image_name.split('/')[-1].split(':')[0]
            for result in results:
                if container_name.lower() in result['name'].lower():
                    result['has_update'] = True
                    updates_found.append(result['name'])
                    available_updates[result['name']] = host_ip

    # Build response
    embed = discord.Embed(
        title=" Container Update Check",
        color=0xf59e0b if updates_found else 0x22c55e
    )

    if updates_found:
        embed.description = f"**{len(updates_found)} updates available**"
        embed.add_field(
            name=" Updates Available",
            value="\n".join([f" {c}" for c in updates_found]),
            inline=False
        )
        embed.add_field(
            name=" Actions",
            value="Use `/update <name>` or `/updateall` to update",
            inline=False
        )
    else:
        embed.description = " All containers are up to date!"

    embed.set_footer(text=f"Checked {len(results)} containers")

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="update", description="Update a specific container")
@app_commands.describe(container="The container name to update")
@is_allowed_channel()
async def update_single(interaction: discord.Interaction, container: str):
    """Update a specific container."""
    # Find container
    matched = None
    host_ip = None

    for name, ip in CONTAINER_HOSTS.items():
        if name.lower() == container.lower():
            matched = name
            host_ip = ip
            break
        elif container.lower() in name.lower():
            matched = name
            host_ip = ip

    if not matched:
        containers_list = ", ".join(sorted(CONTAINER_HOSTS.keys())[:20])
        await interaction.response.send_message(
            f" Container **{container}** not found.\n"
            f"Available: `{containers_list}...`",
            ephemeral=True
        )
        return

    await interaction.response.defer()

    await interaction.followup.send(f" Updating **{matched}**...")

    new_version, error = await asyncio.get_event_loop().run_in_executor(
        None, update_container, host_ip, matched
    )

    if error:
        await interaction.followup.send(
            f" Update failed for **{matched}**\n```{error[:500]}```"
        )
    else:
        await interaction.followup.send(
            f" **{matched}** updated successfully!\n"
            f" New version: `{new_version}`"
        )


@bot.tree.command(name="updateall", description="Update all containers with pending updates")
@is_allowed_channel()
async def update_all(interaction: discord.Interaction):
    """Update all pending containers."""
    global available_updates

    if not available_updates:
        await interaction.response.send_message(
            " No pending updates. Run `/check` first to scan for updates.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=" Confirm Update All",
        description=f"**{len(available_updates)} containers** will be updated:",
        color=0xf59e0b
    )

    embed.add_field(
        name="Containers",
        value="\n".join([f" {c}" for c in available_updates.keys()]),
        inline=False
    )

    view = UpdateAllView(available_updates.copy())
    available_updates = {}

    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="containers", description="List all monitored containers")
@is_allowed_channel()
async def list_containers(interaction: discord.Interaction):
    """List all monitored containers."""
    # Group by host
    hosts = {}
    for container, host_ip in CONTAINER_HOSTS.items():
        if host_ip not in hosts:
            hosts[host_ip] = []
        hosts[host_ip].append(container)

    embed = discord.Embed(
        title=" Monitored Containers",
        description=f"Total: **{len(CONTAINER_HOSTS)}** containers across **{len(hosts)}** hosts",
        color=0x3b82f6
    )

    host_names = {
        "192.168.40.10": " Utilities",
        "192.168.40.11": " Media",
        "192.168.40.20": " Traefik",
        "192.168.40.21": " Authentik",
        "192.168.40.22": " Immich",
        "192.168.40.23": " GitLab",
    }

    for host_ip, containers in sorted(hosts.items()):
        host_label = host_names.get(host_ip, f" {host_ip}")
        embed.add_field(
            name=f"{host_label} ({len(containers)})",
            value="`" + "`, `".join(sorted(containers)[:10]) + "`" + (f" +{len(containers)-10} more" if len(containers) > 10 else ""),
            inline=False
        )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="status", description="Show container running status")
@is_allowed_channel()
async def container_status(interaction: discord.Interaction):
    """Show status of all containers."""
    await interaction.response.defer()

    running = []
    stopped = []
    unknown = []

    # Group by host for efficiency
    hosts = {}
    for container, host_ip in CONTAINER_HOSTS.items():
        if host_ip not in hosts:
            hosts[host_ip] = []
        hosts[host_ip].append(container)

    for host_ip, containers in hosts.items():
        for container in containers:
            info = await asyncio.get_event_loop().run_in_executor(
                None, get_container_info, host_ip, container
            )
            if info:
                if info['status'] == 'running':
                    running.append(container)
                elif info['status'] in ['exited', 'stopped']:
                    stopped.append(container)
                else:
                    unknown.append(f"{container} ({info['status']})")
            else:
                unknown.append(f"{container} (unreachable)")

    embed = discord.Embed(
        title=" Container Status",
        color=0x22c55e if not stopped else 0xef4444
    )

    embed.add_field(
        name=f" Running ({len(running)})",
        value="`" + "`, `".join(running[:15]) + "`" if running else "None",
        inline=False
    )

    if stopped:
        embed.add_field(
            name=f" Stopped ({len(stopped)})",
            value="`" + "`, `".join(stopped) + "`",
            inline=False
        )

    if unknown:
        embed.add_field(
            name=f" Unknown ({len(unknown)})",
            value="\n".join(unknown[:5]),
            inline=False
        )

    embed.set_footer(text=f"Total: {len(CONTAINER_HOSTS)} containers")

    await interaction.followup.send(embed=embed)


# ============================================================================
# Events
# ============================================================================

@bot.event
async def on_ready():
    logger.info(f'Argus logged in as {bot.user}')

    # Find and save notification channel
    for guild in bot.guilds:
        for channel in guild.channels:
            if channel.name.lower() in ALLOWED_CHANNEL_LIST or channel.id in ALLOWED_CHANNEL_LIST:
                bot.notification_channel_id = channel.id
                logger.info(f'Notification channel: {channel.name} ({channel.id})')

                # Send welcome message
                embed = discord.Embed(
                    title=" Argus Online",
                    description="Container Update Guardian is now watching your infrastructure.",
                    color=0x22c55e
                )
                embed.add_field(
                    name=" Commands",
                    value="`/check` `/update` `/updateall` `/containers` `/status` `/argus`",
                    inline=False
                )
                embed.set_footer(text=f"Monitoring {len(CONTAINER_HOSTS)} containers")

                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    logger.error(f"Could not send welcome message: {e}")
                break


async def send_update_notification(container_name: str, old_image: str, new_image: str):
    """Send update notification with buttons."""
    if not bot.notification_channel_id:
        logger.error("No notification channel configured")
        return

    channel = bot.get_channel(bot.notification_channel_id)
    if not channel:
        logger.error(f"Could not find channel {bot.notification_channel_id}")
        return

    host_ip = CONTAINER_HOSTS.get(container_name)
    if not host_ip:
        # Try partial match
        for name, ip in CONTAINER_HOSTS.items():
            if container_name.lower() in name.lower():
                host_ip = ip
                container_name = name
                break

    if not host_ip:
        logger.error(f"Unknown container: {container_name}")
        return

    embed = discord.Embed(
        title=" Update Available",
        description=f"A new version is available for **{container_name}**",
        color=0xf59e0b
    )

    embed.add_field(name=" Current", value=f"`{old_image}`", inline=True)
    embed.add_field(name=" New", value=f"`{new_image}`", inline=True)
    embed.set_footer(text=f"Host: {host_ip}")

    view = UpdateApprovalView(container_name, host_ip, old_image, new_image)

    await channel.send(embed=embed, view=view)
    logger.info(f"Sent update notification for {container_name}")


# ============================================================================
# Webhook Endpoints
# ============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle Watchtower webhooks."""
    try:
        data = request.get_data(as_text=True)
        logger.info(f"Received webhook: {data[:200]}...")

        # Parse watchtower message
        updates = []

        # Pattern: Found new <image> image (sha256:xxx)
        pattern = re.findall(r'Found new (.+?) image \((.+?)\)', data)
        for match in pattern:
            image_name = match[0]
            new_digest = match[1]
            container = image_name.split('/')[-1].split(':')[0]
            updates.append({
                'container': container,
                'old_image': 'current',
                'new_image': f"{image_name} ({new_digest[:12]}...)"
            })

        if updates:
            for update in updates:
                asyncio.run_coroutine_threadsafe(
                    send_update_notification(
                        update['container'],
                        update['old_image'],
                        update['new_image']
                    ),
                    bot.loop
                )

        return jsonify({'status': 'ok', 'updates': len(updates)})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'bot': str(bot.user) if bot.user else 'not connected',
        'containers': len(CONTAINER_HOSTS)
    })


@app.route('/test', methods=['GET'])
def test():
    """Send test notification."""
    asyncio.run_coroutine_threadsafe(
        send_update_notification('test-container', 'test:old', 'test:new'),
        bot.loop
    )
    return jsonify({'status': 'test sent'})


def run_flask():
    app.run(host='0.0.0.0', port=WEBHOOK_PORT, threaded=True)


def main():
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN required")
        return

    # Start webhook server
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"Webhook server on port {WEBHOOK_PORT}")

    # Run bot
    bot.run(DISCORD_TOKEN)


if __name__ == '__main__':
    main()
