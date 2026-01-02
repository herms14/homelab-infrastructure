"""
Sentinel Bot - Main Bot Class
Consolidated Discord bot for homelab management.
"""

import logging
import discord
from discord.ext import commands
from typing import Optional, Dict, Any
import aiohttp

from config import Config

logger = logging.getLogger('sentinel')


class SentinelBot(commands.Bot):
    """
    Sentinel - Consolidated homelab Discord bot.

    Combines functionality from:
    - Argus (container updates)
    - Mnemosyne (media downloads)
    - Chronos (GitLab integration)
    - Athena (Claude task queue)

    Plus new features:
    - Homelab management (Proxmox)
    - Service onboarding verification
    """

    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.reactions = True
        intents.guild_messages = True
        intents.guilds = True

        super().__init__(
            command_prefix='!',  # Fallback, primarily using slash commands
            intents=intents,
            help_command=None,
        )

        self.config = config
        self.http_session: Optional[aiohttp.ClientSession] = None
        self._channel_cache: Dict[str, discord.TextChannel] = {}

        # Database and SSH manager will be initialized in setup_hook
        self.db = None
        self.ssh = None
        self.channel_router = None

    async def setup_hook(self) -> None:
        """Called when the bot is starting up."""
        logger.info("Sentinel Bot starting up...")

        # Create shared HTTP session
        self.http_session = aiohttp.ClientSession()

        # Initialize database
        from .database import Database
        self.db = Database(self.config.database.path)
        await self.db.initialize()

        # Initialize SSH manager
        from .ssh_manager import SSHManager
        self.ssh = SSHManager(self.config.ssh)

        # Initialize channel router
        from .channel_router import ChannelRouter
        self.channel_router = ChannelRouter(self, self.config.discord)

        # Load cogs
        await self._load_cogs()

        # Clear ALL existing commands first (removes old Chronos/Argus/etc commands)
        if self.config.discord.guild_id:
            guild = discord.Object(id=self.config.discord.guild_id)
            # Clear guild commands
            self.tree.clear_commands(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Cleared old guild commands")

            # Now copy and sync our commands
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Commands synced to guild {self.config.discord.guild_id}")
        else:
            # Clear global commands first
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
            logger.info("Cleared old global commands")

            # Load cogs again after clearing to re-register commands
            for cog_name in list(self.cogs.keys()):
                cog = self.get_cog(cog_name)
                if cog:
                    for cmd in cog.walk_app_commands():
                        self.tree.add_command(cmd)

            await self.tree.sync()
            logger.info("Commands synced globally")

    async def _load_cogs(self) -> None:
        """Load all cogs."""
        cogs = [
            'cogs.homelab',
            'cogs.updates',
            'cogs.media',
            'cogs.gitlab',
            'cogs.tasks',
            'cogs.onboarding',
            'cogs.scheduler',
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")

    async def on_ready(self) -> None:
        """Called when the bot is fully ready."""
        logger.info(f"Sentinel Bot online as {self.user}")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")

        # Cache channels
        await self.channel_router.cache_channels()

        # Send startup message to announcements channel
        channel = self.channel_router.get_channel('announcements')
        if channel:
            embed = discord.Embed(
                title="Sentinel Bot Online",
                description="All systems operational. Monitoring homelab infrastructure.",
                color=discord.Color.green()
            )
            embed.add_field(name="Modules", value="Homelab | Updates | Media | GitLab | Tasks | Onboarding", inline=False)
            await channel.send(embed=embed)

    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """Global error handler for prefix commands."""
        logger.error(f"Command error: {error}")

    async def close(self) -> None:
        """Clean up resources when shutting down."""
        logger.info("Sentinel Bot shutting down...")

        if self.http_session:
            await self.http_session.close()

        if self.db:
            await self.db.close()

        await super().close()

    def get_api_headers(self, service: str) -> Dict[str, str]:
        """Get API headers for a specific service."""
        headers = {'Content-Type': 'application/json'}

        if service == 'radarr':
            headers['X-Api-Key'] = self.config.api.radarr_api_key
        elif service == 'sonarr':
            headers['X-Api-Key'] = self.config.api.sonarr_api_key
        elif service == 'jellyseerr':
            headers['X-Api-Key'] = self.config.api.jellyseerr_api_key
        elif service == 'jellyfin':
            headers['X-Emby-Token'] = self.config.api.jellyfin_api_key
        elif service == 'gitlab':
            headers['PRIVATE-TOKEN'] = self.config.api.gitlab_token
        elif service == 'authentik':
            headers['Authorization'] = f'Bearer {self.config.api.authentik_token}'

        return headers

    async def api_get(self, url: str, service: str, **kwargs) -> Optional[Any]:
        """Make an authenticated GET request to a service API."""
        if not self.http_session:
            return None

        headers = self.get_api_headers(service)
        try:
            async with self.http_session.get(url, headers=headers, **kwargs) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"API GET {url} failed: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"API GET {url} error: {e}")
            return None

    async def api_post(self, url: str, service: str, data: Any = None, **kwargs) -> Optional[Any]:
        """Make an authenticated POST request to a service API."""
        if not self.http_session:
            return None

        headers = self.get_api_headers(service)
        try:
            async with self.http_session.post(url, headers=headers, json=data, **kwargs) as resp:
                if resp.status in (200, 201):
                    return await resp.json()
                else:
                    logger.error(f"API POST {url} failed: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"API POST {url} error: {e}")
            return None
