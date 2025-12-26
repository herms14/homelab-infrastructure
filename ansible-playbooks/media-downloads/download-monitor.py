#!/usr/bin/env python3
"""
Media Download Monitor for Radarr/Sonarr
Sends Discord notifications for download progress at key milestones.

Features:
- Notifies when downloads start
- Progress updates at 50%, 80%, 100%
- Completion notification with Jellyfin link
"""

import os
import time
import logging
import requests
from datetime import datetime
from typing import Dict, Set, Optional

# Configuration from environment
RADARR_URL = os.getenv("RADARR_URL", "http://192.168.40.11:7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "")
SONARR_URL = os.getenv("SONARR_URL", "http://192.168.40.11:8989")
SONARR_API_KEY = os.getenv("SONARR_API_KEY", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
JELLYFIN_URL = os.getenv("JELLYFIN_URL", "https://jellyfin.hrmsmrflrii.xyz")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))  # seconds
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Progress thresholds for notifications
PROGRESS_THRESHOLDS = [50, 80, 100]

# Logging setup
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DownloadTracker:
    """Tracks download progress and sent notifications."""

    def __init__(self):
        # Track which notifications have been sent: {download_id: set of milestones}
        self.notified_milestones: Dict[str, Set[int]] = {}
        # Track downloads we've seen start
        self.known_downloads: Set[str] = set()
        # Track completed downloads to avoid duplicate completion messages
        self.completed_downloads: Set[str] = set()

    def should_notify_start(self, download_id: str) -> bool:
        """Check if we should send a start notification."""
        if download_id not in self.known_downloads:
            self.known_downloads.add(download_id)
            self.notified_milestones[download_id] = set()
            return True
        return False

    def should_notify_progress(self, download_id: str, progress: float) -> Optional[int]:
        """Check if we should send a progress notification. Returns threshold or None."""
        if download_id not in self.notified_milestones:
            self.notified_milestones[download_id] = set()

        for threshold in PROGRESS_THRESHOLDS:
            if progress >= threshold and threshold not in self.notified_milestones[download_id]:
                self.notified_milestones[download_id].add(threshold)
                return threshold
        return None

    def mark_completed(self, download_id: str) -> bool:
        """Mark download as completed. Returns True if this is a new completion."""
        if download_id not in self.completed_downloads:
            self.completed_downloads.add(download_id)
            # Clean up tracking data
            self.known_downloads.discard(download_id)
            self.notified_milestones.pop(download_id, None)
            return True
        return False

    def cleanup_stale(self, active_ids: Set[str]):
        """Remove tracking for downloads that are no longer active."""
        stale_ids = self.known_downloads - active_ids - self.completed_downloads
        for stale_id in stale_ids:
            logger.debug(f"Cleaning up stale download: {stale_id}")
            self.known_downloads.discard(stale_id)
            self.notified_milestones.pop(stale_id, None)


def send_discord_notification(title: str, description: str, color: int = 0x00ff00,
                              thumbnail_url: Optional[str] = None):
    """Send a Discord embed notification."""
    if not DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook URL not configured")
        return False

    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "Media Download Monitor"}
    }

    if thumbnail_url:
        embed["thumbnail"] = {"url": thumbnail_url}

    payload = {"embeds": [embed]}

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Discord notification sent: {title}")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to send Discord notification: {e}")
        return False


def get_radarr_queue() -> list:
    """Fetch current download queue from Radarr."""
    if not RADARR_API_KEY:
        return []

    try:
        response = requests.get(
            f"{RADARR_URL}/api/v3/queue",
            headers={"X-Api-Key": RADARR_API_KEY},
            params={"includeMovie": "true"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("records", [])
    except requests.RequestException as e:
        logger.error(f"Failed to fetch Radarr queue: {e}")
        return []


def get_sonarr_queue() -> list:
    """Fetch current download queue from Sonarr."""
    if not SONARR_API_KEY:
        return []

    try:
        response = requests.get(
            f"{SONARR_URL}/api/v3/queue",
            headers={"X-Api-Key": SONARR_API_KEY},
            params={"includeSeries": "true", "includeEpisode": "true"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("records", [])
    except requests.RequestException as e:
        logger.error(f"Failed to fetch Sonarr queue: {e}")
        return []


def get_movie_poster(movie: dict) -> Optional[str]:
    """Get movie poster URL from Radarr movie data."""
    images = movie.get("images", [])
    for img in images:
        if img.get("coverType") == "poster":
            return img.get("remoteUrl") or img.get("url")
    return None


def get_series_poster(series: dict) -> Optional[str]:
    """Get series poster URL from Sonarr series data."""
    images = series.get("images", [])
    for img in images:
        if img.get("coverType") == "poster":
            return img.get("remoteUrl") or img.get("url")
    return None


def calculate_progress(item: dict) -> float:
    """Calculate download progress percentage."""
    size = item.get("size", 0)
    sizeleft = item.get("sizeleft", 0)

    if size <= 0:
        return 0.0

    downloaded = size - sizeleft
    return (downloaded / size) * 100


def format_size(bytes_size: int) -> str:
    """Format bytes to human readable size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"


def process_radarr_downloads(tracker: DownloadTracker):
    """Process Radarr download queue and send notifications."""
    queue = get_radarr_queue()
    active_ids = set()

    for item in queue:
        download_id = f"radarr_{item.get('id')}"
        active_ids.add(download_id)

        movie = item.get("movie", {})
        title = movie.get("title", "Unknown Movie")
        year = movie.get("year", "")
        full_title = f"{title} ({year})" if year else title

        progress = calculate_progress(item)
        status = item.get("status", "").lower()
        poster = get_movie_poster(movie)

        # Check for new download
        if tracker.should_notify_start(download_id):
            size = format_size(item.get("size", 0))
            send_discord_notification(
                title="New Download Started",
                description=f"Hey Master Hermes, **{full_title}** is now downloading.\n\n"
                           f"**Size:** {size}\n"
                           f"**Quality:** {item.get('quality', {}).get('quality', {}).get('name', 'Unknown')}",
                color=0x3498db,  # Blue
                thumbnail_url=poster
            )

        # Check for progress milestones
        if status == "downloading":
            threshold = tracker.should_notify_progress(download_id, progress)
            if threshold and threshold < 100:
                eta = item.get("timeleft", "Unknown")
                send_discord_notification(
                    title=f"Download Progress: {threshold}%",
                    description=f"**{full_title}** is {threshold}% complete.\n\n"
                               f"**ETA:** {eta}\n"
                               f"**Downloaded:** {format_size(item.get('size', 0) - item.get('sizeleft', 0))}",
                    color=0xf39c12,  # Orange
                    thumbnail_url=poster
                )

    tracker.cleanup_stale(active_ids)
    return active_ids


def process_sonarr_downloads(tracker: DownloadTracker):
    """Process Sonarr download queue and send notifications."""
    queue = get_sonarr_queue()
    active_ids = set()

    for item in queue:
        download_id = f"sonarr_{item.get('id')}"
        active_ids.add(download_id)

        series = item.get("series", {})
        episode = item.get("episode", {})
        series_title = series.get("title", "Unknown Series")
        season = episode.get("seasonNumber", 0)
        ep_num = episode.get("episodeNumber", 0)
        ep_title = episode.get("title", "")

        full_title = f"{series_title} - S{season:02d}E{ep_num:02d}"
        if ep_title:
            full_title += f" - {ep_title}"

        progress = calculate_progress(item)
        status = item.get("status", "").lower()
        poster = get_series_poster(series)

        # Check for new download
        if tracker.should_notify_start(download_id):
            size = format_size(item.get("size", 0))
            send_discord_notification(
                title="New Episode Downloading",
                description=f"Hey Master Hermes, **{full_title}** is now downloading.\n\n"
                           f"**Size:** {size}\n"
                           f"**Quality:** {item.get('quality', {}).get('quality', {}).get('name', 'Unknown')}",
                color=0x3498db,  # Blue
                thumbnail_url=poster
            )

        # Check for progress milestones
        if status == "downloading":
            threshold = tracker.should_notify_progress(download_id, progress)
            if threshold and threshold < 100:
                eta = item.get("timeleft", "Unknown")
                send_discord_notification(
                    title=f"Download Progress: {threshold}%",
                    description=f"**{full_title}** is {threshold}% complete.\n\n"
                               f"**ETA:** {eta}\n"
                               f"**Downloaded:** {format_size(item.get('size', 0) - item.get('sizeleft', 0))}",
                    color=0xf39c12,  # Orange
                    thumbnail_url=poster
                )

    tracker.cleanup_stale(active_ids)
    return active_ids


def check_completed_downloads(tracker: DownloadTracker, prev_radarr: Set[str], prev_sonarr: Set[str]):
    """Check for downloads that completed (disappeared from queue)."""
    current_radarr = set()
    current_sonarr = set()

    # Get current queue items
    for item in get_radarr_queue():
        current_radarr.add(f"radarr_{item.get('id')}")

    for item in get_sonarr_queue():
        current_sonarr.add(f"sonarr_{item.get('id')}")

    # Find completed Radarr downloads
    completed_radarr = prev_radarr - current_radarr
    for download_id in completed_radarr:
        if download_id in tracker.known_downloads and tracker.mark_completed(download_id):
            # We don't have the movie info anymore, but we can send a generic completion
            # In a more sophisticated setup, we'd cache the movie info
            logger.info(f"Radarr download completed: {download_id}")

    # Find completed Sonarr downloads
    completed_sonarr = prev_sonarr - current_sonarr
    for download_id in completed_sonarr:
        if download_id in tracker.known_downloads and tracker.mark_completed(download_id):
            logger.info(f"Sonarr download completed: {download_id}")


def setup_completion_webhooks():
    """
    Note: For completion notifications with full details, configure webhooks in Radarr/Sonarr:

    Radarr: Settings -> Connect -> Add -> Webhook
    - Name: Download Monitor Completion
    - On Download: Yes
    - URL: http://localhost:5052/radarr/completed

    Sonarr: Settings -> Connect -> Add -> Webhook
    - Name: Download Monitor Completion
    - On Download: Yes
    - URL: http://localhost:5052/sonarr/completed

    This service also runs a webhook receiver for these completion events.
    """
    pass


def run_webhook_server():
    """Run a simple webhook server for completion notifications from Radarr/Sonarr."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json
    import threading

    class WebhookHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            """Handle GET requests for health checks."""
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                data = {}

            if self.path == "/radarr/completed":
                self.handle_radarr_completion(data)
            elif self.path == "/sonarr/completed":
                self.handle_sonarr_completion(data)
            elif self.path == "/health":
                pass  # Health check

            self.send_response(200)
            self.end_headers()

        def handle_radarr_completion(self, data):
            """Handle Radarr download completion webhook."""
            event_type = data.get("eventType", "")
            if event_type != "Download":
                return

            movie = data.get("movie", {})
            title = movie.get("title", "Unknown Movie")
            year = movie.get("year", "")
            full_title = f"{title} ({year})" if year else title

            # Get movie ID for Jellyfin link (if available)
            tmdb_id = movie.get("tmdbId", "")
            jellyfin_link = JELLYFIN_URL
            if tmdb_id:
                # Jellyfin search link
                jellyfin_link = f"{JELLYFIN_URL}/web/index.html#!/search.html?query={title.replace(' ', '%20')}"

            # Get poster
            images = movie.get("images", [])
            poster = None
            for img in images:
                if img.get("coverType") == "poster":
                    poster = img.get("remoteUrl")
                    break

            send_discord_notification(
                title="Download Complete!",
                description=f"**{full_title}** has finished downloading!\n\n"
                           f"Watch it now at **[Jellyfin]({jellyfin_link})**",
                color=0x2ecc71,  # Green
                thumbnail_url=poster
            )

        def handle_sonarr_completion(self, data):
            """Handle Sonarr download completion webhook."""
            event_type = data.get("eventType", "")
            if event_type != "Download":
                return

            series = data.get("series", {})
            episodes = data.get("episodes", [{}])
            episode = episodes[0] if episodes else {}

            series_title = series.get("title", "Unknown Series")
            season = episode.get("seasonNumber", 0)
            ep_num = episode.get("episodeNumber", 0)
            ep_title = episode.get("title", "")

            full_title = f"{series_title} - S{season:02d}E{ep_num:02d}"
            if ep_title:
                full_title += f" - {ep_title}"

            jellyfin_link = f"{JELLYFIN_URL}/web/index.html#!/search.html?query={series_title.replace(' ', '%20')}"

            # Get poster
            images = series.get("images", [])
            poster = None
            for img in images:
                if img.get("coverType") == "poster":
                    poster = img.get("remoteUrl")
                    break

            send_discord_notification(
                title="Episode Downloaded!",
                description=f"**{full_title}** has finished downloading!\n\n"
                           f"Watch it now at **[Jellyfin]({jellyfin_link})**",
                color=0x2ecc71,  # Green
                thumbnail_url=poster
            )

        def log_message(self, format, *args):
            logger.debug(f"Webhook: {args[0]}")

    server = HTTPServer(("0.0.0.0", 5052), WebhookHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Webhook server started on port 5052")
    return server


def main():
    """Main monitoring loop."""
    logger.info("Starting Media Download Monitor")
    logger.info(f"Radarr URL: {RADARR_URL}")
    logger.info(f"Sonarr URL: {SONARR_URL}")
    logger.info(f"Jellyfin URL: {JELLYFIN_URL}")
    logger.info(f"Poll interval: {POLL_INTERVAL}s")
    logger.info(f"Progress thresholds: {PROGRESS_THRESHOLDS}")

    if not DISCORD_WEBHOOK_URL:
        logger.error("DISCORD_WEBHOOK_URL not set! Notifications will not be sent.")

    # Start webhook server for completion notifications
    webhook_server = run_webhook_server()

    # Send startup notification
    send_discord_notification(
        title="Download Monitor Online",
        description="Media download monitor is now active and watching for new downloads.",
        color=0x9b59b6  # Purple
    )

    tracker = DownloadTracker()
    prev_radarr_ids: Set[str] = set()
    prev_sonarr_ids: Set[str] = set()

    while True:
        try:
            # Process downloads and get current active IDs
            radarr_ids = process_radarr_downloads(tracker)
            sonarr_ids = process_sonarr_downloads(tracker)

            # Check for completions (items that disappeared from queue)
            # Note: Webhook-based completion is more reliable
            check_completed_downloads(tracker, prev_radarr_ids, prev_sonarr_ids)

            prev_radarr_ids = radarr_ids
            prev_sonarr_ids = sonarr_ids

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
