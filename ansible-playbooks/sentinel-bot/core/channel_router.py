"""
Sentinel Bot Channel Router
Routes notifications to appropriate Discord channels.
"""

import logging
import discord
from typing import Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .bot import SentinelBot

logger = logging.getLogger('sentinel.router')


class ChannelRouter:
    """Routes messages to appropriate Discord channels."""

    # Channel name to config attribute mapping
    CHANNEL_MAPPING = {
        'updates': 'channel_container_updates',
        'container-updates': 'channel_container_updates',
        'media': 'channel_media_downloads',
        'media-downloads': 'channel_media_downloads',
        'downloads': 'channel_media_downloads',
        'onboarding': 'channel_onboarding',
        'argus': 'channel_argus',
        'homelab': 'channel_argus',
        'gitlab': 'channel_project_management',
        'project-management': 'channel_project_management',
        'tasks': 'channel_claude_tasks',
        'claude-tasks': 'channel_claude_tasks',
        'announcements': 'channel_announcements',
    }

    def __init__(self, bot: 'SentinelBot', discord_config):
        self.bot = bot
        self.config = discord_config
        self._channel_cache: Dict[str, discord.TextChannel] = {}

    async def cache_channels(self) -> None:
        """Cache all configured channels for fast access."""
        if not self.bot.guilds:
            logger.warning("No guilds connected, cannot cache channels")
            return

        guild = self.bot.guilds[0]  # Primary guild

        # Log all available channels for debugging
        logger.info(f"Guild: {guild.name} (ID: {guild.id})")
        logger.info(f"Available text channels: {[c.name for c in guild.text_channels]}")

        # Get all channel names from config
        channel_names = {
            'container_updates': self.config.channel_container_updates,
            'media_downloads': self.config.channel_media_downloads,
            'onboarding': self.config.channel_onboarding,
            'argus': self.config.channel_argus,
            'project_management': self.config.channel_project_management,
            'claude_tasks': self.config.channel_claude_tasks,
            'announcements': self.config.channel_announcements,
        }

        for key, name in channel_names.items():
            channel = discord.utils.get(guild.text_channels, name=name)
            if channel:
                self._channel_cache[key] = channel
                logger.debug(f"Cached channel {key}: #{name}")
            else:
                logger.warning(f"Channel not found: {name}")

        logger.info(f"Cached {len(self._channel_cache)} channels")

    def get_channel(self, channel_type: str) -> Optional[discord.TextChannel]:
        """
        Get a cached channel by type.

        Args:
            channel_type: Channel identifier (e.g., 'updates', 'media', 'homelab')

        Returns:
            The Discord TextChannel or None if not found
        """
        # Normalize the channel type
        normalized = channel_type.lower().replace('-', '_').replace(' ', '_')

        # Direct cache lookup
        if normalized in self._channel_cache:
            return self._channel_cache[normalized]

        # Check mapping
        if channel_type in self.CHANNEL_MAPPING:
            config_attr = self.CHANNEL_MAPPING[channel_type]
            # Convert config attr to cache key
            cache_key = config_attr.replace('channel_', '')
            return self._channel_cache.get(cache_key)

        logger.warning(f"Unknown channel type: {channel_type}")
        return None

    async def send(
        self,
        channel_type: str,
        content: str = None,
        embed: discord.Embed = None,
        view: discord.ui.View = None,
        **kwargs
    ) -> Optional[discord.Message]:
        """
        Send a message to a specific channel type.

        Args:
            channel_type: Channel identifier
            content: Text content
            embed: Discord embed
            view: Discord UI view
            **kwargs: Additional send parameters

        Returns:
            The sent message or None if failed
        """
        channel = self.get_channel(channel_type)
        if not channel:
            logger.error(f"Cannot send to channel type: {channel_type}")
            return None

        try:
            return await channel.send(content=content, embed=embed, view=view, **kwargs)
        except discord.Forbidden:
            logger.error(f"No permission to send to #{channel.name}")
            return None
        except discord.HTTPException as e:
            logger.error(f"Failed to send to #{channel.name}: {e}")
            return None

    async def send_update_notification(
        self,
        container_name: str,
        host_ip: str,
        status: str,
        details: str = None
    ) -> Optional[discord.Message]:
        """Send a container update notification."""
        color = {
            'pending': discord.Color.blue(),
            'in_progress': discord.Color.yellow(),
            'success': discord.Color.green(),
            'failed': discord.Color.red(),
        }.get(status, discord.Color.greyple())

        embed = discord.Embed(
            title=f"Container Update: {container_name}",
            description=details or f"Status: {status}",
            color=color
        )
        embed.add_field(name="Host", value=host_ip, inline=True)
        embed.add_field(name="Status", value=status.upper(), inline=True)

        return await self.send('updates', embed=embed)

    async def send_media_notification(
        self,
        title: str,
        media_type: str,
        event: str,
        poster_url: str = None,
        details: Dict = None
    ) -> Optional[discord.Message]:
        """Send a media download/add notification."""
        emoji = {
            'movie': ':movie_camera:',
            'series': ':tv:',
            'episode': ':clapper:',
            'music': ':musical_note:',
        }.get(media_type.lower(), ':film_frames:')

        color = {
            'requested': discord.Color.blue(),
            'downloading': discord.Color.yellow(),
            'grabbed': discord.Color.orange(),
            'completed': discord.Color.green(),
            'failed': discord.Color.red(),
        }.get(event.lower(), discord.Color.greyple())

        embed = discord.Embed(
            title=f"{emoji} {title}",
            description=f"**{event.upper()}** - {media_type.title()}",
            color=color
        )

        if poster_url:
            embed.set_thumbnail(url=poster_url)

        if details:
            for key, value in details.items():
                embed.add_field(name=key, value=str(value), inline=True)

        return await self.send('media', embed=embed)

    async def send_task_notification(
        self,
        task_id: int,
        description: str,
        event: str,
        instance_name: str = None
    ) -> Optional[discord.Message]:
        """Send a Claude task notification."""
        color = {
            'created': discord.Color.blue(),
            'claimed': discord.Color.yellow(),
            'completed': discord.Color.green(),
            'cancelled': discord.Color.red(),
        }.get(event.lower(), discord.Color.greyple())

        embed = discord.Embed(
            title=f"Task #{task_id}",
            description=description,
            color=color
        )
        embed.add_field(name="Event", value=event.upper(), inline=True)

        if instance_name:
            embed.add_field(name="Instance", value=instance_name, inline=True)

        return await self.send('tasks', embed=embed)

    async def send_homelab_alert(
        self,
        title: str,
        message: str,
        severity: str = 'info'
    ) -> Optional[discord.Message]:
        """Send a homelab infrastructure alert."""
        color = {
            'info': discord.Color.blue(),
            'warning': discord.Color.yellow(),
            'error': discord.Color.red(),
            'success': discord.Color.green(),
        }.get(severity.lower(), discord.Color.greyple())

        embed = discord.Embed(
            title=f":house: {title}",
            description=message,
            color=color
        )

        return await self.send('homelab', embed=embed)

    async def send_onboarding_status(
        self,
        service_name: str,
        checks: Dict[str, bool],
        details: str = None
    ) -> Optional[discord.Message]:
        """Send a service onboarding status notification."""
        all_passed = all(checks.values())
        color = discord.Color.green() if all_passed else discord.Color.yellow()

        embed = discord.Embed(
            title=f"Onboarding: {service_name}",
            description=details or ("All checks passed!" if all_passed else "Some checks pending"),
            color=color
        )

        status_text = []
        for check_name, passed in checks.items():
            emoji = ":white_check_mark:" if passed else ":x:"
            status_text.append(f"{emoji} {check_name}")

        embed.add_field(name="Checks", value="\n".join(status_text), inline=False)

        return await self.send('onboarding', embed=embed)
