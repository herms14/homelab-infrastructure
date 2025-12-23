#!/usr/bin/env python3
"""
Update Manager Discord Bot with Service Onboarding Checker
Location: /opt/update-manager/update_manager.py

Features:
- Watchtower update notifications with interactive approval
- Service onboarding status checks via slash commands
- Daily 9am onboarding report
- CI/CD webhook integration
"""

import os
import re
import json
import asyncio
import subprocess
from datetime import datetime, time
from flask import Flask, request, jsonify
import discord
from discord import app_commands
from discord.ext import commands, tasks
import threading
import logging
import yaml
import requests
import urllib3

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN', '')
DISCORD_CHANNEL_ID = int(os.environ.get('DISCORD_CHANNEL_ID', '0'))
ONBOARD_CHANNEL_ID = int(os.environ.get('ONBOARD_CHANNEL_ID', '0'))
SSH_KEY_PATH = os.environ.get('SSH_KEY_PATH', '/root/.ssh/homelab_ed25519')
WEBHOOK_PORT = int(os.environ.get('WEBHOOK_PORT', '5000'))

# API credentials for onboarding checks
OPNSENSE_API_KEY = os.environ.get('OPNSENSE_API_KEY', '')
OPNSENSE_API_SECRET = os.environ.get('OPNSENSE_API_SECRET', '')
AUTHENTIK_TOKEN = os.environ.get('AUTHENTIK_TOKEN', '')

# Infrastructure hosts
TRAEFIK_HOST = '192.168.40.20'
ANSIBLE_HOST = '192.168.20.30'
GITLAB_RUNNER_HOST = '192.168.40.24'
OPNSENSE_URL = 'https://192.168.91.30'
AUTHENTIK_URL = 'http://192.168.40.21:9000'
DOMAIN = 'hrmsmrflrii.xyz'

# Container to host mapping
CONTAINER_HOSTS = {
    "uptime-kuma": "192.168.40.10",
    "prometheus": "192.168.40.10",
    "grafana": "192.168.40.10",
    "glance": "192.168.40.10",
    "n8n": "192.168.40.10",
    "paperless-ngx": "192.168.40.10",
    "openspeedtest": "192.168.40.10",
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

# Traefik config cache
traefik_config_cache = None

# Flask app for webhook
app = Flask(__name__)

# Discord bot with slash commands
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True


class UpdateManagerBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # Sync slash commands
        await self.tree.sync()
        logger.info("Slash commands synced")

        # Start daily report task
        if not daily_onboard_report.is_running():
            daily_onboard_report.start()


bot = UpdateManagerBot()


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
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return ""
    except Exception as e:
        logger.error(f"SSH error to {host}: {e}")
        return ""


def get_host_for_container(container_name):
    return CONTAINER_HOSTS.get(container_name, None)


def get_container_info(host_ip, container_name):
    """Get current image info for a container"""
    try:
        cmd = f"ssh -i {SSH_KEY_PATH} -o StrictHostKeyChecking=no -o ConnectTimeout=5 hermes-admin@{host_ip} " \
              f"\"docker inspect {container_name} --format '{{{{.Config.Image}}}}|{{{{.Image}}}}' 2>/dev/null\""
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split('|')
            return {
                'image': parts[0] if parts else 'unknown',
                'digest': parts[1][:19] if len(parts) > 1 else 'unknown'
            }
    except Exception as e:
        logger.error(f"Error getting info for {container_name}: {e}")
    return None


def check_for_updates_on_host(host_ip):
    """Run watchtower check on a specific host and return updates"""
    try:
        cmd = f"ssh -i {SSH_KEY_PATH} -o StrictHostKeyChecking=no -o ConnectTimeout=10 hermes-admin@{host_ip} " \
              f"\"docker exec watchtower /watchtower --run-once 2>&1\" 2>/dev/null"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        return result.stdout
    except Exception as e:
        logger.error(f"Error checking updates on {host_ip}: {e}")
    return ""


def update_container(host_ip, container_name):
    try:
        cmd_dir = f"ssh -i {SSH_KEY_PATH} -o StrictHostKeyChecking=no hermes-admin@{host_ip} " \
                  f"\"docker inspect {container_name} --format '{{{{index .Config.Labels \\\"com.docker.compose.project.working_dir\\\"}}}}'\""

        result = subprocess.run(cmd_dir, shell=True, capture_output=True, text=True, timeout=30)
        compose_dir = result.stdout.strip()

        if not compose_dir:
            return None, "Could not find compose directory"

        cmd_update = f"ssh -i {SSH_KEY_PATH} -o StrictHostKeyChecking=no hermes-admin@{host_ip} " \
                     f"\"cd {compose_dir} && sudo docker compose pull {container_name} && sudo docker compose up -d {container_name}\""

        result = subprocess.run(cmd_update, shell=True, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            return None, result.stderr

        cmd_version = f"ssh -i {SSH_KEY_PATH} -o StrictHostKeyChecking=no hermes-admin@{host_ip} " \
                      f"\"docker inspect {container_name} --format '{{{{.Config.Image}}}}'\""

        result = subprocess.run(cmd_version, shell=True, capture_output=True, text=True, timeout=30)
        new_version = result.stdout.strip()

        return new_version, None
    except Exception as e:
        return None, str(e)


# ============================================================================
# Onboarding Checker Functions
# ============================================================================

def get_traefik_config():
    """Fetch and parse Traefik services.yml."""
    global traefik_config_cache
    if traefik_config_cache:
        return traefik_config_cache

    output = ssh_command(TRAEFIK_HOST, "cat /opt/traefik/config/dynamic/services.yml")
    if output:
        try:
            traefik_config_cache = yaml.safe_load(output)
            return traefik_config_cache
        except yaml.YAMLError:
            return None
    return None


def get_all_services():
    """Get all service names from Traefik config."""
    config = get_traefik_config()
    if not config:
        return []

    services = set()
    routers = config.get('http', {}).get('routers', {})

    skip_patterns = [
        'api@internal', 'authentik-outpost', 'proxmox-node',
        'traefik-dashboard', 'proxmox'
    ]

    for router_name, router_config in routers.items():
        if any(skip in router_name for skip in skip_patterns):
            continue

        rule = router_config.get('rule', '')
        match = re.search(r"Host\(`([^.]+)\.", rule)
        if match:
            service_name = match.group(1)
            if service_name not in ['auth', 'node01', 'node02', 'node03']:
                services.add(service_name)

    return sorted(list(services))


def check_terraform(service_name: str) -> bool:
    """Check if service has Terraform VM configuration."""
    output = ssh_command(
        ANSIBLE_HOST,
        f"grep -qi '{service_name}' ~/tf-proxmox/main.tf && echo 'found'"
    )
    return 'found' in output if output else False


def check_ansible(service_name: str) -> bool:
    """Check if service has Ansible playbook."""
    output = ssh_command(
        ANSIBLE_HOST,
        f"ls -d ~/ansible-playbooks/{service_name}/ 2>/dev/null || "
        f"ls ~/ansible-playbooks/*/{service_name}*.yml 2>/dev/null || "
        f"ls ~/ansible-playbooks/{service_name}*.yml 2>/dev/null"
    )
    return bool(output)


def check_dns(service_name: str) -> bool:
    """Check if service has DNS record in OPNsense."""
    if not OPNSENSE_API_KEY or not OPNSENSE_API_SECRET:
        # Fallback to DNS lookup
        try:
            import socket
            socket.gethostbyname(f"{service_name}.{DOMAIN}")
            return True
        except socket.gaierror:
            return False

    try:
        response = requests.get(
            f"{OPNSENSE_URL}/api/unbound/settings/searchHostOverride",
            auth=(OPNSENSE_API_KEY, OPNSENSE_API_SECRET),
            verify=False,
            timeout=10
        )
        if response.status_code == 200:
            for row in response.json().get('rows', []):
                if row.get('hostname') == service_name and row.get('domain') == DOMAIN:
                    return True
    except Exception:
        pass
    return False


def check_traefik(service_name: str) -> bool:
    """Check if service has Traefik router configuration."""
    config = get_traefik_config()
    if not config:
        return False

    routers = config.get('http', {}).get('routers', {})

    for router_name, router_config in routers.items():
        if service_name.lower() in router_name.lower():
            return True
        rule = router_config.get('rule', '')
        if f"`{service_name}." in rule:
            return True

    return False


def check_ssl(service_name: str) -> bool:
    """Check if service has SSL/TLS configured."""
    config = get_traefik_config()
    if not config:
        return False

    routers = config.get('http', {}).get('routers', {})

    for router_name, router_config in routers.items():
        if service_name.lower() in router_name.lower():
            tls = router_config.get('tls', {})
            if tls and tls.get('certResolver'):
                return True
        rule = router_config.get('rule', '')
        if f"`{service_name}." in rule:
            tls = router_config.get('tls', {})
            if tls and tls.get('certResolver'):
                return True

    return False


def check_authentik(service_name: str) -> bool:
    """Check if service has Authentik SSO application."""
    if not AUTHENTIK_TOKEN:
        return False

    try:
        headers = {
            'Authorization': f'Bearer {AUTHENTIK_TOKEN}',
            'Content-Type': 'application/json'
        }
        response = requests.get(
            f"{AUTHENTIK_URL}/api/v3/core/applications/",
            headers=headers,
            params={'slug': service_name},
            timeout=10
        )
        if response.status_code == 200:
            results = response.json().get('results', [])
            return len(results) > 0
    except Exception:
        pass
    return False


def check_documentation(service_name: str) -> bool:
    """Check if service is documented in docs/SERVICES.md."""
    output = ssh_command(
        ANSIBLE_HOST,
        f"grep -qi '{service_name}' ~/tf-proxmox/docs/SERVICES.md && echo 'found'"
    )
    return 'found' in output if output else False


def check_service(service_name: str) -> dict:
    """Run all checks for a single service."""
    return {
        'terraform': check_terraform(service_name),
        'ansible': check_ansible(service_name),
        'dns': check_dns(service_name),
        'traefik': check_traefik(service_name),
        'ssl': check_ssl(service_name),
        'authentik': check_authentik(service_name),
        'documentation': check_documentation(service_name),
    }


def generate_report(services=None) -> str:
    """Generate a formatted report table for services."""
    if services is None:
        services = get_all_services()

    if not services:
        return "No services found in Traefik configuration."

    header = (
        "```\n"
        f"{'Service':<15} | {'TF':<3} | {'Ans':<3} | {'DNS':<3} | "
        f"{'Traf':<4} | {'SSL':<3} | {'Auth':<4} | {'Docs':<4}\n"
        f"{'-'*15}-+-{'-'*3}-+-{'-'*3}-+-{'-'*3}-+-"
        f"{'-'*4}-+-{'-'*3}-+-{'-'*4}-+-{'-'*4}\n"
    )

    rows = []
    summary = {'complete': 0, 'incomplete': 0}

    for service in services:
        checks = check_service(service)

        required_checks = ['dns', 'traefik', 'ssl']
        core_complete = all(checks[c] for c in required_checks)

        if core_complete:
            summary['complete'] += 1
        else:
            summary['incomplete'] += 1

        row = (
            f"{service[:15]:<15} | "
            f"{'Y' if checks['terraform'] else 'N':^3} | "
            f"{'Y' if checks['ansible'] else 'N':^3} | "
            f"{'Y' if checks['dns'] else 'N':^3} | "
            f"{'Y' if checks['traefik'] else 'N':^4} | "
            f"{'Y' if checks['ssl'] else 'N':^3} | "
            f"{'Y' if checks['authentik'] else '-':^4} | "
            f"{'Y' if checks['documentation'] else 'N':^4}"
        )
        rows.append(row)

    table = header + "\n".join(rows) + "\n```"

    summary_text = (
        f"\n**Summary:** {summary['complete']} fully onboarded, "
        f"{summary['incomplete']} need attention\n"
        f"*Legend: TF=Terraform, Ans=Ansible, Traf=Traefik, Auth=Authentik, Docs=Documentation*"
    )

    return table + summary_text


def generate_single_report(service_name: str) -> str:
    """Generate detailed report for a single service."""
    checks = check_service(service_name)

    report = f"**Onboarding Status: {service_name}**\n\n"

    icons = {True: ':white_check_mark:', False: ':x:'}

    report += f"{icons[checks['terraform']]} **Terraform Config**\n"
    report += f"{icons[checks['ansible']]} **Ansible Playbook**\n"
    report += f"{icons[checks['dns']]} **DNS Record** ({service_name}.{DOMAIN})\n"
    report += f"{icons[checks['traefik']]} **Traefik Router**\n"
    report += f"{icons[checks['ssl']]} **SSL/TLS Certificate**\n"
    report += f"{icons[checks['authentik']]} **Authentik SSO** (optional)\n"
    report += f"{icons[checks['documentation']]} **Documentation**\n"

    required = ['dns', 'traefik', 'ssl']
    if all(checks[c] for c in required):
        report += "\n:tada: **Core onboarding complete!**"
    else:
        missing = [c for c in required if not checks[c]]
        report += f"\n:warning: **Missing core requirements:** {', '.join(missing)}"

    return report


# ============================================================================
# Slash Commands
# ============================================================================

@bot.tree.command(name="onboard", description="Check onboarding status for a specific service")
@app_commands.describe(service_name="The name of the service to check")
async def onboard_command(interaction: discord.Interaction, service_name: str):
    """Check onboarding status for a specific service."""
    await interaction.response.defer()

    # Clear cache to get fresh data
    global traefik_config_cache
    traefik_config_cache = None

    report = await asyncio.get_event_loop().run_in_executor(
        None, generate_single_report, service_name
    )

    await interaction.followup.send(report)


@bot.tree.command(name="onboard-all", description="Check onboarding status for all services")
async def onboard_all_command(interaction: discord.Interaction):
    """Check onboarding status for all services."""
    await interaction.response.defer()

    # Clear cache to get fresh data
    global traefik_config_cache
    traefik_config_cache = None

    report = await asyncio.get_event_loop().run_in_executor(
        None, generate_report
    )

    # Split if too long
    if len(report) > 1900:
        parts = report.split("```")
        for i, part in enumerate(parts):
            if part.strip():
                if i % 2 == 1:  # Code block
                    await interaction.followup.send(f"```{part}```")
                else:
                    await interaction.followup.send(part)
    else:
        await interaction.followup.send(report)


@bot.tree.command(name="onboard-services", description="List all discovered services")
async def onboard_services_command(interaction: discord.Interaction):
    """List all services discovered from Traefik config."""
    await interaction.response.defer()

    global traefik_config_cache
    traefik_config_cache = None

    services = await asyncio.get_event_loop().run_in_executor(
        None, get_all_services
    )

    if services:
        response = f"**Discovered Services ({len(services)}):**\n"
        response += "\n".join([f"- {s}" for s in services])
    else:
        response = "No services found in Traefik configuration."

    await interaction.followup.send(response)


# ============================================================================
# Scheduled Tasks
# ============================================================================

@tasks.loop(time=time(hour=14, minute=0))  # 9am EST = 14:00 UTC
async def daily_onboard_report():
    """Send daily onboarding report at 9am."""
    if ONBOARD_CHANNEL_ID == 0:
        return

    channel = bot.get_channel(ONBOARD_CHANNEL_ID)
    if not channel:
        logger.error(f"Could not find onboard channel {ONBOARD_CHANNEL_ID}")
        return

    # Clear cache
    global traefik_config_cache
    traefik_config_cache = None

    report = await asyncio.get_event_loop().run_in_executor(
        None, generate_report
    )

    await channel.send(
        f":sunrise: **Daily Onboarding Report** - {datetime.now().strftime('%B %d, %Y')}\n\n{report}"
    )
    logger.info("Daily onboarding report sent")


@daily_onboard_report.before_loop
async def before_daily_report():
    await bot.wait_until_ready()


# ============================================================================
# Discord Events (Legacy Commands)
# ============================================================================

@bot.event
async def on_ready():
    logger.info(f'Discord bot logged in as {bot.user}')
    logger.info(f'Update channel: {DISCORD_CHANNEL_ID}')
    logger.info(f'Onboard channel: {ONBOARD_CHANNEL_ID}')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.channel.id != DISCORD_CHANNEL_ID:
        return

    content = message.content.lower().strip()

    if content in ['check versions', 'check version', 'check updates', 'status']:
        await handle_check_versions(message)
        return

    if content in ['help', 'commands', '?']:
        await handle_help(message)
        return

    if content == 'update all':
        await handle_update_all(message)
        return

    if content.startswith('update '):
        service_name = content[7:].strip()
        if service_name and service_name != 'all':
            await handle_update_single(message, service_name)
            return


async def handle_help(message):
    """Show available commands"""
    help_text = """**Available Commands, Master Hermes:**

**Container Updates:**
`check versions` - Check all services for available updates
`update all` - Update all services that have pending updates
`update <service>` - Update a specific service (e.g., `update sonarr`)

**Service Onboarding (Slash Commands):**
`/onboard <service>` - Check onboarding status for a service
`/onboard-all` - Check all services onboarding status
`/onboard-services` - List all discovered services

**Reactions:**
React with :thumbsup: to approve an update
React with :thumbsdown: to skip an update
"""
    await message.channel.send(help_text)


async def handle_update_single(message, service_name):
    """Update a specific container by name"""
    matched_service = None
    matched_host = None

    for container, host_ip in CONTAINER_HOSTS.items():
        if container.lower() == service_name.lower():
            matched_service = container
            matched_host = host_ip
            break
        elif service_name.lower() in container.lower():
            matched_service = container
            matched_host = host_ip

    if not matched_service:
        await message.channel.send(
            f":x: Service **{service_name}** not found, Master Hermes.\n"
            f"Available services: {', '.join(sorted(CONTAINER_HOSTS.keys()))}"
        )
        return

    await message.channel.send(f":arrows_counterclockwise: Updating **{matched_service}**... Please wait, Master Hermes!")

    new_version, error = await asyncio.get_event_loop().run_in_executor(
        None, update_container, matched_host, matched_service
    )

    if error:
        await message.channel.send(f":x: Update failed for **{matched_service}**: {error}")
    else:
        await message.channel.send(
            f":white_check_mark: **{matched_service}** has been updated to **{new_version}**, Master Hermes! :tada:"
        )


async def handle_check_versions(message):
    """Check all containers for their current versions and available updates"""
    global available_updates
    available_updates = {}

    await message.channel.send(":mag: Checking all services for updates, Master Hermes... This may take a minute.")

    hosts = {}
    for container, host_ip in CONTAINER_HOSTS.items():
        if host_ip not in hosts:
            hosts[host_ip] = []
        hosts[host_ip].append(container)

    results = []
    updates_found = []

    for host_ip, containers in hosts.items():
        for container in containers:
            info = await asyncio.get_event_loop().run_in_executor(
                None, get_container_info, host_ip, container
            )
            if info:
                results.append({
                    'name': container,
                    'host': host_ip,
                    'image': info['image'],
                    'digest': info['digest'],
                    'has_update': False,
                    'new_version': '-'
                })

        output = await asyncio.get_event_loop().run_in_executor(
            None, check_for_updates_on_host, host_ip
        )

        found_updates = re.findall(r'Found new (.+?) image', output)
        for image_name in found_updates:
            container_name = image_name.split('/')[-1].split(':')[0]
            for result in results:
                if container_name.lower() in result['name'].lower() or result['name'].lower() in container_name.lower():
                    result['has_update'] = True
                    result['new_version'] = 'Available'
                    updates_found.append(result['name'])
                    available_updates[result['name']] = host_ip

    results.sort(key=lambda x: x['name'])

    table_header = "```\n"
    table_header += f"{'Service':<20} {'Current Image':<30} {'Status':<15}\n"
    table_header += f"{'-'*20} {'-'*30} {'-'*15}\n"

    table_rows = []
    for r in results:
        image_short = r['image'][-28:] if len(r['image']) > 28 else r['image']
        status = "UPDATE AVAILABLE" if r['has_update'] else "Up to date"
        table_rows.append(f"{r['name']:<20} {image_short:<30} {status:<15}")

    table_content = table_header + "\n".join(table_rows) + "\n```"

    if len(table_content) > 1900:
        await message.channel.send(table_header + "\n".join(table_rows[:len(table_rows)//2]) + "\n```")
        await message.channel.send("```\n" + "\n".join(table_rows[len(table_rows)//2:]) + "\n```")
    else:
        await message.channel.send(table_content)

    if updates_found:
        await message.channel.send(
            f"\n:package: **{len(updates_found)} updates available:** {', '.join(updates_found)}\n"
            f"Type `update all` to update all, or wait for individual notifications."
        )
    else:
        await message.channel.send("\n:white_check_mark: **All services are up to date, Master Hermes!**")


async def handle_update_all(message):
    """Update all containers that have pending updates"""
    global available_updates

    if not available_updates:
        await message.channel.send(":information_source: No pending updates. Run `check versions` first to scan for updates.")
        return

    await message.channel.send(f":arrows_counterclockwise: Updating {len(available_updates)} services... Please wait, Master Hermes!")

    success = []
    failed = []

    for container_name, host_ip in available_updates.items():
        await message.channel.send(f":arrows_counterclockwise: Updating **{container_name}**...")

        new_version, error = await asyncio.get_event_loop().run_in_executor(
            None, update_container, host_ip, container_name
        )

        if error:
            failed.append(f"{container_name}: {error}")
            await message.channel.send(f":x: Failed to update **{container_name}**")
        else:
            success.append(container_name)
            await message.channel.send(f":white_check_mark: **{container_name}** updated to `{new_version}`")

    available_updates = {}

    summary = f"\n**Update Summary:**\n"
    summary += f":white_check_mark: Success: {len(success)}\n"
    if failed:
        summary += f":x: Failed: {len(failed)}\n"
        for f in failed:
            summary += f"  - {f}\n"

    await message.channel.send(summary + "\nAll done, Master Hermes! :tada:")


@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    message_id = reaction.message.id

    if message_id not in pending_updates:
        return

    update_info = pending_updates[message_id]
    container_name = update_info['container']
    host_ip = update_info['host_ip']

    if str(reaction.emoji) == '\U0001f44d':
        logger.info(f"Update approved for {container_name}")

        channel = bot.get_channel(DISCORD_CHANNEL_ID)
        await channel.send(f":arrows_counterclockwise: Updating **{container_name}**... Please wait, Master Hermes!")

        new_version, error = await asyncio.get_event_loop().run_in_executor(
            None, update_container, host_ip, container_name
        )

        if error:
            await channel.send(f":x: Update failed for **{container_name}**: {error}")
        else:
            await channel.send(
                f":white_check_mark: **{container_name}** has been updated to **{new_version}**, Master Hermes! :tada:"
            )

        del pending_updates[message_id]

    elif str(reaction.emoji) == '\U0001f44e':
        logger.info(f"Update rejected for {container_name}")

        channel = bot.get_channel(DISCORD_CHANNEL_ID)
        await channel.send(f":fast_forward: Skipping update for **{container_name}** as requested, Master Hermes.")

        del pending_updates[message_id]


async def send_update_notification(container_name, old_image, new_image):
    host_ip = get_host_for_container(container_name)

    if not host_ip:
        for name, ip in CONTAINER_HOSTS.items():
            if container_name.lower() in name.lower():
                host_ip = ip
                break

    if not host_ip:
        logger.error(f"Could not find host for container: {container_name}")
        return

    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if not channel:
        logger.error(f"Could not find channel {DISCORD_CHANNEL_ID}")
        return

    message = await channel.send(
        f":wave: Hey Hermes!\n\n"
        f":new: There is a new update available for **{container_name}**\n"
        f":package: Current: `{old_image}`\n"
        f":rocket: New: `{new_image}`\n\n"
        f"React with :thumbsup: to update or :thumbsdown: to skip!"
    )

    await message.add_reaction('\U0001f44d')
    await message.add_reaction('\U0001f44e')

    pending_updates[message.id] = {
        'container': container_name,
        'old_image': old_image,
        'new_image': new_image,
        'host_ip': host_ip,
        'timestamp': datetime.now().isoformat()
    }

    logger.info(f"Sent update notification for {container_name}")


def parse_watchtower_message(message):
    """Parse Watchtower notification message to extract update info"""
    updates = []

    pattern1 = re.findall(r'Updating (\S+) \((.+?) to (.+?)\)', message)
    for match in pattern1:
        updates.append({
            'container': match[0],
            'old_image': match[1],
            'new_image': match[2]
        })

    pattern2 = re.findall(r'Found new (.+?) image \((.+?)\)', message)
    for match in pattern2:
        image_name = match[0]
        new_digest = match[1]
        container = image_name.split('/')[-1].split(':')[0]
        updates.append({
            'container': container,
            'old_image': 'current',
            'new_image': f"{image_name} ({new_digest[:12]}...)"
        })

    pattern3 = re.findall(r'(\S+) would be updated', message, re.IGNORECASE)
    for container in pattern3:
        if not any(u['container'] == container for u in updates):
            updates.append({
                'container': container,
                'old_image': 'current',
                'new_image': 'latest'
            })

    return updates


# ============================================================================
# Flask Webhook Endpoints
# ============================================================================

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_data(as_text=True)
        logger.info(f"Received webhook data: {data[:500]}...")

        updates = parse_watchtower_message(data)

        if updates:
            logger.info(f"Found {len(updates)} updates to process")
            for update in updates:
                asyncio.run_coroutine_threadsafe(
                    send_update_notification(
                        update['container'],
                        update['old_image'],
                        update['new_image']
                    ),
                    bot.loop
                )
        else:
            logger.info("No updates found in message")

        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/onboard-check', methods=['POST'])
def onboard_check():
    """Webhook endpoint for CI/CD to trigger onboarding check."""
    try:
        data = request.get_json() or {}
        service_name = data.get('service_name')

        if not service_name:
            return jsonify({'status': 'error', 'message': 'service_name required'}), 400

        if ONBOARD_CHANNEL_ID == 0:
            return jsonify({'status': 'error', 'message': 'ONBOARD_CHANNEL_ID not configured'}), 500

        # Clear cache
        global traefik_config_cache
        traefik_config_cache = None

        report = generate_single_report(service_name)

        asyncio.run_coroutine_threadsafe(
            send_onboard_notification(service_name, report),
            bot.loop
        )

        return jsonify({'status': 'ok', 'service': service_name})
    except Exception as e:
        logger.error(f"Onboard check error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


async def send_onboard_notification(service_name: str, report: str):
    """Send onboarding status to Discord channel."""
    channel = bot.get_channel(ONBOARD_CHANNEL_ID)
    if not channel:
        logger.error(f"Could not find onboard channel {ONBOARD_CHANNEL_ID}")
        return

    await channel.send(
        f":rocket: **New Service Deployed: {service_name}**\n\n{report}"
    )
    logger.info(f"Sent onboarding notification for {service_name}")


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'pending_updates': len(pending_updates),
        'onboard_channel': ONBOARD_CHANNEL_ID
    })


@app.route('/test', methods=['GET'])
def test():
    asyncio.run_coroutine_threadsafe(
        send_update_notification('test-container', 'test:old', 'test:new'),
        bot.loop
    )
    return jsonify({'status': 'test notification sent'})


@app.route('/test-onboard', methods=['GET'])
def test_onboard():
    """Test the onboarding check."""
    service = request.args.get('service', 'jellyfin')
    report = generate_single_report(service)

    asyncio.run_coroutine_threadsafe(
        send_onboard_notification(service, report),
        bot.loop
    )

    return jsonify({'status': 'test onboard notification sent', 'service': service})


def run_flask():
    app.run(host='0.0.0.0', port=WEBHOOK_PORT, threaded=True)


def main():
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN environment variable is required")
        return

    if DISCORD_CHANNEL_ID == 0:
        logger.error("DISCORD_CHANNEL_ID environment variable is required")
        return

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"Webhook server started on port {WEBHOOK_PORT}")

    bot.run(DISCORD_TOKEN)


if __name__ == '__main__':
    main()
