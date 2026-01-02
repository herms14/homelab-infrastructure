#!/usr/bin/env python3
"""
Sentinel Bot - Consolidated Homelab Discord Bot

Combines functionality from:
- Argus (container updates)
- Mnemosyne (media downloads)
- Chronos (GitLab integration)
- Athena (Claude task queue)

Plus new features:
- Homelab management (Proxmox)
- Service onboarding verification
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from dotenv import load_dotenv

from config import load_config
from core import SentinelBot

# Load environment variables from .env file
load_dotenv()


def setup_logging() -> None:
    """Configure logging for the bot."""
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # File handler (optional)
    file_handler = logging.FileHandler('sentinel.log', encoding='utf-8')
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Set specific log levels
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    logging.getLogger('asyncssh').setLevel(logging.WARNING)
    logging.getLogger('aiosqlite').setLevel(logging.WARNING)

    # Our modules at INFO
    logging.getLogger('sentinel').setLevel(logging.INFO)
    logging.getLogger('sentinel.database').setLevel(logging.INFO)
    logging.getLogger('sentinel.ssh').setLevel(logging.INFO)
    logging.getLogger('sentinel.router').setLevel(logging.INFO)


class SentinelRunner:
    """Main runner for Sentinel bot with graceful shutdown."""

    def __init__(self):
        self.bot: Optional[SentinelBot] = None
        self.webhook_server = None
        self.logger = logging.getLogger('sentinel.runner')

    async def start(self) -> None:
        """Start the bot and webhook server."""
        config = load_config()

        if not config.discord.token:
            self.logger.error("DISCORD_TOKEN not set!")
            sys.exit(1)

        # Create bot instance
        self.bot = SentinelBot(config)

        # Start webhook server in background
        asyncio.create_task(self._start_webhook_server(config))

        # Start the bot
        self.logger.info("Starting Sentinel Bot...")
        await self.bot.start(config.discord.token)

    async def _start_webhook_server(self, config) -> None:
        """Start the Quart webhook server."""
        try:
            from webhooks.server import create_app
            app = create_app(self.bot, config)

            # Run with hypercorn for async support
            from hypercorn.asyncio import serve
            from hypercorn.config import Config as HypercornConfig

            hypercorn_config = HypercornConfig()
            hypercorn_config.bind = [f"0.0.0.0:{config.webhook.port}"]
            hypercorn_config.accesslog = '-'  # Log to stdout

            self.logger.info(f"Starting webhook server on port {config.webhook.port}")
            await serve(app, hypercorn_config)
        except ImportError:
            self.logger.warning("Webhook server not available (missing webhooks module)")
        except Exception as e:
            self.logger.error(f"Webhook server error: {e}")

    async def stop(self) -> None:
        """Gracefully stop the bot."""
        self.logger.info("Shutting down Sentinel...")

        if self.bot:
            await self.bot.close()

        self.logger.info("Sentinel shutdown complete")


async def main() -> None:
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger('sentinel')

    logger.info("=" * 50)
    logger.info("Sentinel Bot Starting")
    logger.info("=" * 50)

    runner = SentinelRunner()

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def handle_signal():
        logger.info("Received shutdown signal")
        asyncio.create_task(runner.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    try:
        await runner.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
    finally:
        await runner.stop()


if __name__ == '__main__':
    asyncio.run(main())
