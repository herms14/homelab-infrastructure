"""
Sentinel Bot - Scheduler Cog
Scheduled tasks and background jobs.
"""

import logging
import asyncio
from datetime import datetime, time
import discord
from discord.ext import commands, tasks
from typing import TYPE_CHECKING, List, Dict

from config import CONTAINER_HOSTS

if TYPE_CHECKING:
    from core import SentinelBot

logger = logging.getLogger('sentinel.cogs.scheduler')


class SchedulerCog(commands.Cog, name="Scheduler"):
    """Scheduled tasks and background jobs."""

    def __init__(self, bot: 'SentinelBot'):
        self.bot = bot
        self._download_cache: Dict[str, Dict] = {}
        self._notified_failures: set = set()  # Track notified failed downloads
        self._failed_download_messages: Dict[int, Dict] = {}  # msg_id -> {queue_id, service}

    async def cog_load(self):
        """Called when cog is loaded. Start scheduled tasks."""
        self.daily_update_report.start()
        self.download_progress_check.start()
        self.failed_download_check.start()
        self.stale_task_cleanup.start()
        self.daily_onboarding_report.start()
        logger.info("Scheduler tasks started")

    async def cog_unload(self):
        """Called when cog is unloaded. Stop scheduled tasks."""
        self.daily_update_report.cancel()
        self.download_progress_check.cancel()
        self.failed_download_check.cancel()
        self.stale_task_cleanup.cancel()
        self.daily_onboarding_report.cancel()
        logger.info("Scheduler tasks stopped")

    # ==================== Daily Update Report (7 PM) ====================

    @tasks.loop(time=time(hour=19, minute=0))  # 7:00 PM
    async def daily_update_report(self):
        """Send daily container update availability report at 7 PM."""
        logger.info("Running daily update report")

        try:
            updates_available = await self._check_all_updates()

            if not updates_available:
                logger.info("No updates available")
                return

            # Build embed
            embed = discord.Embed(
                title=":arrow_up: Daily Update Report",
                description=f"Found {len(updates_available)} container(s) with available updates",
                color=discord.Color.blue()
            )

            # Group by host
            by_host: Dict[str, List[str]] = {}
            for update in updates_available:
                host = update['host']
                if host not in by_host:
                    by_host[host] = []
                by_host[host].append(update['container'])

            for host, containers in by_host.items():
                embed.add_field(
                    name=f":computer: {host}",
                    value="\n".join([f"• {c}" for c in containers]),
                    inline=True
                )

            embed.set_footer(text="React with :thumbsup: to approve all updates")

            # Send to updates channel
            if self.bot.channel_router:
                msg = await self.bot.channel_router.send('updates', embed=embed)
                if msg:
                    # Add approval reactions
                    await msg.add_reaction("\U0001F44D")  # thumbsup
                    for i, _ in enumerate(updates_available[:10]):
                        await msg.add_reaction(f"{i+1}\ufe0f\u20e3")

        except Exception as e:
            logger.error(f"Daily update report failed: {e}")

    @daily_update_report.before_loop
    async def before_daily_update_report(self):
        """Wait for bot to be ready before starting daily report."""
        await self.bot.wait_until_ready()

    async def _check_all_updates(self) -> List[Dict]:
        """Check all containers for available updates."""
        updates = []

        # Group containers by host
        hosts: Dict[str, List[str]] = {}
        for container, host_ip in CONTAINER_HOSTS.items():
            if host_ip not in hosts:
                hosts[host_ip] = []
            hosts[host_ip].append(container)

        for host_ip, containers in hosts.items():
            for container in containers:
                # Check for updates (simplified - real impl would check digests)
                # This would compare local image digest with remote
                has_update = await self._check_container_update(host_ip, container)
                if has_update:
                    updates.append({
                        'container': container,
                        'host': host_ip,
                    })

        return updates

    async def _check_container_update(self, host: str, container: str) -> bool:
        """Check if a container has an available update."""
        # Simplified check - real implementation would:
        # 1. Get current image digest
        # 2. Check remote registry for newer digest
        # 3. Compare and return True if different
        return False  # Placeholder

    # ==================== Download Progress Check (Every 60s) ====================

    @tasks.loop(seconds=60)
    async def download_progress_check(self):
        """Check download progress and send milestone notifications."""
        try:
            await self._check_radarr_progress()
            await self._check_sonarr_progress()
        except Exception as e:
            logger.error(f"Download progress check failed: {e}")

    @download_progress_check.before_loop
    async def before_download_progress_check(self):
        """Wait for bot to be ready."""
        await self.bot.wait_until_ready()
        # Wait a bit for other systems to initialize
        await asyncio.sleep(30)

    async def _check_radarr_progress(self):
        """Check Radarr download progress."""
        url = f"{self.bot.config.api.radarr_url}/api/v3/queue"
        data = await self.bot.api_get(url, 'radarr')

        if not data:
            return

        for item in data.get('records', []):
            download_id = str(item.get('id'))
            title = item.get('title', 'Unknown')
            progress = item.get('sizeleft', 0)
            size = item.get('size', 1)

            if size > 0:
                percent_complete = ((size - progress) / size) * 100
            else:
                percent_complete = 0

            await self._notify_progress(download_id, title, 'movie', percent_complete)

    async def _check_sonarr_progress(self):
        """Check Sonarr download progress."""
        url = f"{self.bot.config.api.sonarr_url}/api/v3/queue"
        data = await self.bot.api_get(url, 'sonarr')

        if not data:
            return

        for item in data.get('records', []):
            download_id = str(item.get('id'))
            title = item.get('title', 'Unknown')
            progress = item.get('sizeleft', 0)
            size = item.get('size', 1)

            if size > 0:
                percent_complete = ((size - progress) / size) * 100
            else:
                percent_complete = 0

            await self._notify_progress(download_id, title, 'episode', percent_complete)

    async def _notify_progress(self, download_id: str, title: str, media_type: str, percent: float):
        """Send progress notification at milestones."""
        milestones = [50, 80, 100]

        if not self.bot.db:
            return

        # Ensure download is being tracked (creates record if not exists)
        await self.bot.db.start_download_tracking(download_id, media_type, title)

        # Get already notified milestones
        notified = await self.bot.db.get_download_milestones(download_id)

        for milestone in milestones:
            if percent >= milestone and milestone not in notified:
                # Record milestone
                await self.bot.db.add_download_milestone(download_id, milestone)

                # Send notification
                if self.bot.channel_router:
                    emoji = ":clapper:" if media_type == 'movie' else ":tv:"
                    if milestone == 100:
                        msg = f"{emoji} **{title}** download complete!"
                        await self.bot.db.complete_download(download_id)
                    else:
                        msg = f"{emoji} **{title}** - {milestone}% complete"

                    await self.bot.channel_router.send('media', content=msg)
                break

    # ==================== Failed Download Check (Every 5 min) ====================

    @tasks.loop(minutes=5)
    async def failed_download_check(self):
        """Check for failed downloads and notify with removal option."""
        try:
            await self._check_radarr_failures()
            await self._check_sonarr_failures()
        except Exception as e:
            logger.error(f"Failed download check error: {e}")

    @failed_download_check.before_loop
    async def before_failed_download_check(self):
        """Wait for bot to be ready."""
        await self.bot.wait_until_ready()
        await asyncio.sleep(60)  # Wait a bit after startup

    async def _check_radarr_failures(self):
        """Check Radarr queue for failed downloads."""
        url = f"{self.bot.config.api.radarr_url}/api/v3/queue"
        data = await self.bot.api_get(url, 'radarr')

        if not data:
            return

        for item in data.get('records', []):
            status = item.get('status', '').lower()
            if status in ['failed', 'warning']:
                queue_id = item.get('id')
                failure_key = f"radarr_{queue_id}"

                if failure_key not in self._notified_failures:
                    await self._notify_failed_download(item, 'radarr')
                    self._notified_failures.add(failure_key)

    async def _check_sonarr_failures(self):
        """Check Sonarr queue for failed downloads."""
        url = f"{self.bot.config.api.sonarr_url}/api/v3/queue"
        data = await self.bot.api_get(url, 'sonarr')

        if not data:
            return

        for item in data.get('records', []):
            status = item.get('status', '').lower()
            if status in ['failed', 'warning']:
                queue_id = item.get('id')
                failure_key = f"sonarr_{queue_id}"

                if failure_key not in self._notified_failures:
                    await self._notify_failed_download(item, 'sonarr')
                    self._notified_failures.add(failure_key)

    async def _notify_failed_download(self, item: Dict, service: str):
        """Send notification for failed download with removal option."""
        queue_id = item.get('id')
        title = item.get('title', 'Unknown')
        status = item.get('status', 'failed')
        error_msg = ''

        # Get error message if available
        status_messages = item.get('statusMessages', [])
        if status_messages:
            messages = []
            for sm in status_messages[:2]:  # Limit to first 2 messages
                msgs = sm.get('messages', [])
                messages.extend(msgs[:2])
            error_msg = '\n'.join(messages[:3]) if messages else ''

        emoji = ":movie_camera:" if service == 'radarr' else ":tv:"
        service_name = "Radarr" if service == 'radarr' else "Sonarr"

        embed = discord.Embed(
            title=f":x: {service_name} Download Failed",
            description=f"{emoji} **{title}**",
            color=discord.Color.red()
        )

        embed.add_field(name="Status", value=status.title(), inline=True)
        embed.add_field(name="Queue ID", value=str(queue_id), inline=True)

        if error_msg:
            embed.add_field(name="Error", value=error_msg[:500], inline=False)

        embed.set_footer(text="React with :wastebasket: to remove from queue")

        if self.bot.channel_router:
            msg = await self.bot.channel_router.send('media', embed=embed)
            if msg:
                await msg.add_reaction("\U0001F5D1")  # wastebasket emoji
                # Store message mapping for reaction handler
                self._failed_download_messages[msg.id] = {
                    'queue_id': queue_id,
                    'service': service,
                    'title': title
                }
                logger.info(f"Notified failed download: {title} ({service})")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle reactions on failed download notifications."""
        # Ignore bot's own reactions
        if payload.user_id == self.bot.user.id:
            return

        # Check if this is a failed download message
        if payload.message_id not in self._failed_download_messages:
            return

        # Check for wastebasket emoji
        if str(payload.emoji) != "\U0001F5D1":
            return

        info = self._failed_download_messages[payload.message_id]
        queue_id = info['queue_id']
        service = info['service']
        title = info['title']

        # Remove from queue via API
        success = await self._remove_from_queue(queue_id, service)

        # Update the message
        channel = self.bot.get_channel(payload.channel_id)
        if channel:
            try:
                message = await channel.fetch_message(payload.message_id)

                if success:
                    embed = discord.Embed(
                        title=":white_check_mark: Download Removed",
                        description=f"**{title}** removed from {service.title()} queue",
                        color=discord.Color.green()
                    )
                    # Clean up tracking
                    failure_key = f"{service}_{queue_id}"
                    self._notified_failures.discard(failure_key)
                    del self._failed_download_messages[payload.message_id]
                else:
                    embed = discord.Embed(
                        title=":warning: Removal Failed",
                        description=f"Failed to remove **{title}** from queue",
                        color=discord.Color.orange()
                    )

                await message.edit(embed=embed)
                await message.clear_reactions()

            except Exception as e:
                logger.error(f"Failed to update message: {e}")

    async def _remove_from_queue(self, queue_id: int, service: str) -> bool:
        """Remove an item from Radarr/Sonarr queue."""
        if service == 'radarr':
            base_url = self.bot.config.api.radarr_url
            api_key = self.bot.config.api.radarr_api_key
        else:
            base_url = self.bot.config.api.sonarr_url
            api_key = self.bot.config.api.sonarr_api_key

        url = f"{base_url}/api/v3/queue/{queue_id}?removeFromClient=true&blocklist=false&apikey={api_key}"

        try:
            if not self.bot.http_session:
                return False

            async with self.bot.http_session.delete(url) as resp:
                if resp.status in [200, 204]:
                    logger.info(f"Removed queue item {queue_id} from {service}")
                    return True
                else:
                    logger.error(f"Failed to remove queue item: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Error removing queue item: {e}")
            return False

    # ==================== Stale Task Cleanup (Every 30 min) ====================

    @tasks.loop(minutes=30)
    async def stale_task_cleanup(self):
        """Reset tasks stuck in progress for too long."""
        try:
            if not self.bot.db:
                return

            count = await self.bot.db.reset_stale_tasks(hours=2)
            if count > 0:
                logger.info(f"Reset {count} stale tasks")

            # Also cleanup old completed downloads
            removed = await self.bot.db.cleanup_old_downloads(hours=24)
            if removed > 0:
                logger.debug(f"Cleaned up {removed} old download records")

        except Exception as e:
            logger.error(f"Stale task cleanup failed: {e}")

    @stale_task_cleanup.before_loop
    async def before_stale_task_cleanup(self):
        """Wait for bot to be ready."""
        await self.bot.wait_until_ready()

    # ==================== Daily Onboarding Report (9 AM) ====================

    @tasks.loop(time=time(hour=9, minute=0))  # 9:00 AM
    async def daily_onboarding_report(self):
        """Send daily onboarding status summary at 9 AM."""
        logger.info("Running daily onboarding report")

        try:
            # Get onboarding cog to run checks
            onboarding_cog = self.bot.get_cog("Onboarding")
            if not onboarding_cog:
                logger.warning("Onboarding cog not loaded")
                return

            from .onboarding import EXPECTED_SERVICES

            issues = []
            for service in EXPECTED_SERVICES:
                checks = await onboarding_cog.check_service(service)
                required = ['dns', 'traefik', 'ssl']
                failed = [c for c in required if not checks.get(c)]
                if failed:
                    issues.append(f"**{service}**: Missing {', '.join(failed)}")

            if not issues:
                # All good, no need to notify
                logger.info("All services properly onboarded")
                return

            embed = discord.Embed(
                title=":warning: Onboarding Issues Detected",
                description=f"Found {len(issues)} service(s) with configuration issues",
                color=discord.Color.yellow()
            )

            # Split if too many
            issues_text = "\n".join(issues[:15])
            if len(issues) > 15:
                issues_text += f"\n... and {len(issues) - 15} more"

            embed.add_field(name="Services", value=issues_text, inline=False)
            embed.set_footer(text="Use /onboard <service> for details")

            if self.bot.channel_router:
                await self.bot.channel_router.send('onboarding', embed=embed)

        except Exception as e:
            logger.error(f"Daily onboarding report failed: {e}")

    @daily_onboarding_report.before_loop
    async def before_daily_onboarding_report(self):
        """Wait for bot to be ready."""
        await self.bot.wait_until_ready()


async def setup(bot: 'SentinelBot'):
    """Load the Scheduler cog."""
    await bot.add_cog(SchedulerCog(bot))
