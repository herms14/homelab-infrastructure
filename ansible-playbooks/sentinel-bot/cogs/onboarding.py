"""
Sentinel Bot - Onboarding Cog
Service onboarding verification.
"""

import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import TYPE_CHECKING, Dict, List, Optional

from core.progress import make_progress_bar, ProgressEmbed

if TYPE_CHECKING:
    from core import SentinelBot

logger = logging.getLogger('sentinel.cogs.onboarding')


# Known services that should be onboarded
EXPECTED_SERVICES = [
    'grafana', 'prometheus', 'uptime-kuma', 'n8n', 'glance',
    'jellyfin', 'radarr', 'sonarr', 'prowlarr', 'bazarr',
    'jellyseerr', 'tdarr', 'deluge', 'sabnzbd', 'autobrr',
    'gitlab', 'authentik', 'traefik', 'immich',
    'lagident', 'karakeep', 'wizarr', 'tracearr',
    'speedtest', 'jaeger', 'paperless',
]


class OnboardingCog(commands.Cog, name="Onboarding"):
    """Service onboarding verification."""

    def __init__(self, bot: 'SentinelBot'):
        self.bot = bot

    @property
    def config(self):
        return self.bot.config

    @property
    def ssh(self):
        return self.bot.ssh

    # ==================== Check Methods ====================

    async def _check_dns(self, service: str) -> bool:
        """Check if DNS record exists for service."""
        domain = f"{service}.{self.config.domain}"
        # Check via SSH to a host that can resolve
        result = await self.ssh.run(
            self.config.ssh.docker_utilities_ip,
            f"nslookup {domain} 192.168.91.30 2>/dev/null | grep -q 'Address:' && echo 'ok'"
        )
        return 'ok' in result.output

    async def _check_traefik(self, service: str) -> bool:
        """Check if Traefik route exists for service."""
        result = await self.ssh.run(
            self.config.ssh.traefik_ip,
            f"grep -r '{service}' /opt/traefik/config/dynamic/ 2>/dev/null | head -1"
        )
        return bool(result.output.strip())

    async def _check_ssl(self, service: str) -> bool:
        """Check if SSL certificate is valid for service."""
        domain = f"{service}.{self.config.domain}"
        result = await self.ssh.run(
            self.config.ssh.docker_utilities_ip,
            f"timeout 5 openssl s_client -connect {domain}:443 -servername {domain} </dev/null 2>/dev/null | grep -q 'Verify return code: 0' && echo 'ok'"
        )
        return 'ok' in result.output

    async def _check_authentik(self, service: str) -> Optional[bool]:
        """Check if Authentik provider exists for service (optional)."""
        # Query Authentik API for providers
        url = f"{self.config.api.authentik_url}/api/v3/providers/all/"
        providers = await self.bot.api_get(url, 'authentik')

        if not providers:
            return None  # Can't determine

        # Check if any provider matches service
        for provider in providers.get('results', []):
            if service.lower() in provider.get('name', '').lower():
                return True
        return False

    async def _check_docs(self, service: str) -> bool:
        """Check if service has documentation."""
        result = await self.ssh.run(
            self.config.ssh.ansible_ip,
            f"grep -r -i '{service}' ~/ansible/docs/ 2>/dev/null | head -1"
        )
        return bool(result.output.strip())

    async def check_service(self, service: str) -> Dict[str, Optional[bool]]:
        """Run all onboarding checks for a service."""
        checks = {
            'dns': await self._check_dns(service),
            'traefik': await self._check_traefik(service),
            'ssl': await self._check_ssl(service),
            'authentik': await self._check_authentik(service),
            'docs': await self._check_docs(service),
        }
        return checks

    # ==================== Commands ====================

    @app_commands.command(name="onboard", description="Check onboarding status for a service")
    @app_commands.describe(service="Service name to check")
    async def onboard_check(self, interaction: discord.Interaction, service: str):
        """Check onboarding status for a single service."""
        await interaction.response.defer()

        # 5 checks: dns, traefik, ssl, authentik, docs
        progress = ProgressEmbed(f":clipboard: Onboarding: {service}", 5)
        status_msg = await interaction.followup.send(embed=progress.embed)

        # Run checks with progress updates
        checks = {}

        progress.update(0, ":hourglass: Checking DNS...")
        await status_msg.edit(embed=progress.embed)
        checks['dns'] = await self._check_dns(service)

        progress.update(1, ":hourglass: Checking Traefik...")
        await status_msg.edit(embed=progress.embed)
        checks['traefik'] = await self._check_traefik(service)

        progress.update(2, ":hourglass: Checking SSL...")
        await status_msg.edit(embed=progress.embed)
        checks['ssl'] = await self._check_ssl(service)

        progress.update(3, ":hourglass: Checking Authentik...")
        await status_msg.edit(embed=progress.embed)
        checks['authentik'] = await self._check_authentik(service)

        progress.update(4, ":hourglass: Checking Docs...")
        await status_msg.edit(embed=progress.embed)
        checks['docs'] = await self._check_docs(service)

        # Determine overall status
        required_checks = ['dns', 'traefik', 'ssl']
        all_required_passed = all(checks.get(c) for c in required_checks)

        # Format results
        check_lines = []
        for check_name, passed in checks.items():
            if passed is None:
                emoji = ":grey_question:"
                status = "N/A"
            elif passed:
                emoji = ":white_check_mark:"
                status = "OK"
            else:
                emoji = ":x:"
                status = "Missing"

            optional = " (optional)" if check_name in ['authentik', 'docs'] else ""
            check_lines.append(f"{emoji} **{check_name.title()}**: {status}{optional}")

        # Build final embed
        color = discord.Color.green() if all_required_passed else discord.Color.yellow()
        title = f":white_check_mark: {service}" if all_required_passed else f":warning: {service}"
        embed = progress.complete(title, "All required checks passed!" if all_required_passed else "Some checks need attention", color)
        embed.clear_fields()
        embed.add_field(name="Checks", value="\n".join(check_lines), inline=False)
        embed.add_field(name="URL", value=f"https://{service}.{self.config.domain}", inline=True)

        await status_msg.edit(embed=embed)

    @app_commands.command(name="onboard-all", description="Check onboarding status for all services")
    async def onboard_all(self, interaction: discord.Interaction):
        """Check onboarding status for all known services."""
        await interaction.response.defer()

        # Service categories (same as /onboard-services)
        categories = {
            "Monitoring": ['grafana', 'prometheus', 'uptime-kuma', 'jaeger', 'speedtest'],
            "Media": ['jellyfin', 'radarr', 'sonarr', 'prowlarr', 'bazarr', 'jellyseerr', 'tdarr', 'deluge', 'sabnzbd', 'autobrr'],
            "Infrastructure": ['traefik', 'authentik', 'gitlab'],
            "Utilities": ['glance', 'n8n', 'immich', 'paperless'],
            "New Services": ['lagident', 'karakeep', 'wizarr', 'tracearr'],
        }

        total_services = len(EXPECTED_SERVICES)
        progress = ProgressEmbed(":clipboard: Checking All Services...", total_services)
        status_msg = await interaction.followup.send(embed=progress.embed)

        # Store results by service
        service_results = {}
        checked = 0
        fully_onboarded = 0

        for service in EXPECTED_SERVICES:
            progress.update(checked, f":hourglass: Checking **{service}**...")
            await status_msg.edit(embed=progress.embed)

            checks = await self.check_service(service)
            required = ['dns', 'traefik', 'ssl']
            passed = sum(1 for c in required if checks.get(c))
            total = len(required)

            if passed == total:
                status = ":white_check_mark:"
                fully_onboarded += 1
            elif passed > 0:
                status = ":yellow_circle:"
            else:
                status = ":red_circle:"

            service_results[service] = f"{status} {service}"
            checked += 1

        # Build categorized embed
        color = discord.Color.green() if fully_onboarded == total_services else discord.Color.yellow()
        embed = progress.complete(":clipboard: Service Onboarding Status", f"Checked {total_services} services", color)
        embed.clear_fields()

        for category, services in categories.items():
            matching = [service_results[s] for s in services if s in service_results]
            if matching:
                embed.add_field(
                    name=category,
                    value=", ".join(matching),
                    inline=False
                )

        embed.set_footer(text=f"Fully Onboarded: {fully_onboarded}/{len(EXPECTED_SERVICES)}")

        await status_msg.edit(embed=embed)

    @app_commands.command(name="onboard-services", description="List known services for onboarding")
    async def list_services(self, interaction: discord.Interaction):
        """List all known services that should be onboarded."""
        await interaction.response.defer()

        embed = discord.Embed(
            title=":package: Known Services",
            description="Services tracked for onboarding verification",
            color=discord.Color.blue()
        )

        # Categorize services
        categories = {
            "Monitoring": ['grafana', 'prometheus', 'uptime-kuma', 'jaeger', 'speedtest'],
            "Media": ['jellyfin', 'radarr', 'sonarr', 'prowlarr', 'bazarr', 'jellyseerr', 'tdarr', 'deluge', 'sabnzbd', 'autobrr'],
            "Infrastructure": ['traefik', 'authentik', 'gitlab'],
            "Utilities": ['glance', 'n8n', 'immich', 'paperless'],
            "New Services": ['lagident', 'karakeep', 'wizarr', 'tracearr'],
        }

        for category, services in categories.items():
            matching = [s for s in services if s in EXPECTED_SERVICES]
            if matching:
                embed.add_field(
                    name=category,
                    value=", ".join(matching),
                    inline=False
                )

        embed.set_footer(text=f"Total: {len(EXPECTED_SERVICES)} services")
        await interaction.followup.send(embed=embed)


async def setup(bot: 'SentinelBot'):
    """Load the Onboarding cog."""
    await bot.add_cog(OnboardingCog(bot))
