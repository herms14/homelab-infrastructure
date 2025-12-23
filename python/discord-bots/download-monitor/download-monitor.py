#!/usr/bin/env python3
"""
Enhanced Media Download Monitor for Radarr/Sonarr/Jellyseerr
Features:
- Jellyseerr request notifications (with proper title lookup)
- Aggregated episode notifications (e.g., "Downloading 5/10 episodes")
- Indexer searching status
- Progress updates at 50%, 80%, 100%
- Completion notifications with Jellyfin links
"""

import os
import time
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Set, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict

# Configuration from environment
RADARR_URL = os.getenv("RADARR_URL", "http://localhost:7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "")
SONARR_URL = os.getenv("SONARR_URL", "http://localhost:8989")
SONARR_API_KEY = os.getenv("SONARR_API_KEY", "")
JELLYSEERR_URL = os.getenv("JELLYSEERR_URL", "http://localhost:5056")
JELLYSEERR_API_KEY = os.getenv("JELLYSEERR_API_KEY", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
JELLYFIN_URL = os.getenv("JELLYFIN_URL", "https://jellyfin.hrmsmrflrii.xyz")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Progress thresholds
PROGRESS_THRESHOLDS = [50, 80, 100]

# Logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TrackedMovie:
    movie_id: int
    title: str
    year: str
    poster_url: Optional[str] = None
    status: str = "pending"
    progress: float = 0.0
    size: int = 0
    notified_milestones: Set[int] = field(default_factory=set)
    notified_searching: bool = False
    notified_start: bool = False


@dataclass
class TrackedSeries:
    series_id: int
    title: str
    poster_url: Optional[str] = None
    episodes_total: int = 0
    episodes_downloading: int = 0
    episodes_completed: int = 0
    overall_progress: float = 0.0
    total_size: int = 0
    downloaded_size: int = 0
    notified_milestones: Set[int] = field(default_factory=set)
    notified_searching: bool = False
    notified_start: bool = False
    last_episode_count: int = 0


class MediaTracker:
    """Tracks all media with aggregation for TV series."""

    def __init__(self):
        self.movies: Dict[int, TrackedMovie] = {}
        self.series: Dict[int, TrackedSeries] = {}
        self.seen_jellyseerr_requests: Set[int] = set()
        self.completed_movies: Set[int] = set()
        self.completed_series: Set[int] = set()

    def cleanup_stale_movies(self, active_ids: Set[int]):
        stale = set(self.movies.keys()) - active_ids - self.completed_movies
        for mid in stale:
            del self.movies[mid]

    def cleanup_stale_series(self, active_ids: Set[int]):
        stale = set(self.series.keys()) - active_ids - self.completed_series
        for sid in stale:
            del self.series[sid]


def send_discord_notification(title: str, description: str, color: int = 0x00ff00,
                              thumbnail_url: Optional[str] = None,
                              fields: Optional[List[dict]] = None):
    """Send Discord embed notification."""
    if not DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook not configured")
        return False

    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {"text": "Media Manager"}
    }

    if thumbnail_url:
        embed["thumbnail"] = {"url": thumbnail_url}

    if fields:
        embed["fields"] = fields

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
        response.raise_for_status()
        logger.info(f"Discord notification sent: {title}")
        return True
    except Exception as e:
        logger.error(f"Discord notification failed: {e}")
        return False


def format_size(bytes_size: int) -> str:
    """Format bytes to human readable."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"


# ============= JELLYSEERR INTEGRATION =============

def get_jellyseerr_movie_details(tmdb_id: int) -> Optional[dict]:
    """Fetch movie details from Jellyseerr using TMDB ID."""
    if not JELLYSEERR_API_KEY:
        return None
    try:
        headers = {"X-Api-Key": JELLYSEERR_API_KEY}
        response = requests.get(
            f"{JELLYSEERR_URL}/api/v1/movie/{tmdb_id}",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch movie details for TMDB {tmdb_id}: {e}")
        return None


def get_jellyseerr_tv_details(tmdb_id: int) -> Optional[dict]:
    """Fetch TV series details from Jellyseerr using TMDB ID."""
    if not JELLYSEERR_API_KEY:
        return None
    try:
        headers = {"X-Api-Key": JELLYSEERR_API_KEY}
        response = requests.get(
            f"{JELLYSEERR_URL}/api/v1/tv/{tmdb_id}",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch TV details for TMDB {tmdb_id}: {e}")
        return None


def get_jellyseerr_requests() -> List[dict]:
    """Fetch pending/processing requests from Jellyseerr."""
    if not JELLYSEERR_API_KEY:
        return []

    try:
        headers = {"X-Api-Key": JELLYSEERR_API_KEY}
        response = requests.get(
            f"{JELLYSEERR_URL}/api/v1/request",
            headers=headers,
            params={"take": 20, "skip": 0, "sort": "added", "filter": "all"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except Exception as e:
        logger.error(f"Jellyseerr API error: {e}")
        return []


def process_jellyseerr_requests(tracker: MediaTracker):
    """Check for new Jellyseerr requests and notify."""
    requests_list = get_jellyseerr_requests()

    for req in requests_list:
        req_id = req.get("id")
        if req_id in tracker.seen_jellyseerr_requests:
            continue

        tracker.seen_jellyseerr_requests.add(req_id)

        media = req.get("media", {})
        media_type = req.get("type", "movie")
        status = req.get("status", 1)
        tmdb_id = media.get("tmdbId")

        # Get requester info
        requested_by = req.get("requestedBy", {})
        requester_name = requested_by.get("displayName") or requested_by.get("jellyfinUsername") or requested_by.get("username", "Someone")

        # Fetch actual media details from Jellyseerr
        if media_type == "movie":
            details = get_jellyseerr_movie_details(tmdb_id) if tmdb_id else None
            if details:
                title = details.get("title", "Unknown Movie")
                year = details.get("releaseDate", "")[:4] if details.get("releaseDate") else ""
                poster_path = details.get("posterPath", "")
            else:
                title = "Unknown Movie"
                year = ""
                poster_path = ""

            full_title = f"{title} ({year})" if year else title
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
            emoji = "🎬"
            type_text = "Movie"
        else:
            details = get_jellyseerr_tv_details(tmdb_id) if tmdb_id else None
            if details:
                title = details.get("name", "Unknown Series")
                year = details.get("firstAirDate", "")[:4] if details.get("firstAirDate") else ""
                poster_path = details.get("posterPath", "")
            else:
                title = "Unknown Series"
                year = ""
                poster_path = ""

            full_title = f"{title} ({year})" if year else title
            poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
            emoji = "📺"
            type_text = "TV Series"

        status_text = {1: "Pending", 2: "Approved", 3: "Declined"}.get(status, "Unknown")

        send_discord_notification(
            title=f"{emoji} New Media Request",
            description=f"**{requester_name}** requested **{full_title}**\n\n"
                       f"**Type:** {type_text}\n"
                       f"**Status:** {status_text}",
            color=0x9b59b6,
            thumbnail_url=poster_url
        )


# ============= RADARR INTEGRATION =============

def get_radarr_queue() -> List[dict]:
    """Fetch Radarr download queue."""
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
        return response.json().get("records", [])
    except Exception as e:
        logger.error(f"Radarr queue error: {e}")
        return []


def process_radarr(tracker: MediaTracker):
    """Process Radarr queue - one notification per movie."""
    queue = get_radarr_queue()
    active_ids = set()

    for item in queue:
        movie = item.get("movie", {})
        movie_id = movie.get("id")
        if not movie_id:
            continue

        active_ids.add(movie_id)
        title = movie.get("title", "Unknown")
        year = movie.get("year", "")
        full_title = f"{title} ({year})" if year else title

        poster = None
        for img in movie.get("images", []):
            if img.get("coverType") == "poster":
                poster = img.get("remoteUrl") or img.get("url")
                break

        if movie_id not in tracker.movies:
            tracker.movies[movie_id] = TrackedMovie(
                movie_id=movie_id,
                title=full_title,
                year=str(year),
                poster_url=poster
            )

        tracked = tracker.movies[movie_id]
        status = item.get("status", "").lower()
        size = item.get("size", 0)
        sizeleft = item.get("sizeleft", 0)
        progress = ((size - sizeleft) / size * 100) if size > 0 else 0
        tracked.progress = progress
        tracked.size = size

        # Searching notification
        if status in ["delay", "pending", "queued"] and not tracked.notified_searching:
            tracked.notified_searching = True
            send_discord_notification(
                title="🔍 Searching Indexers",
                description=f"**{full_title}** is searching for available releases...",
                color=0xf1c40f,
                thumbnail_url=poster
            )

        # Download started
        elif status == "downloading" and not tracked.notified_start:
            tracked.notified_start = True
            send_discord_notification(
                title="⬇️ Movie Download Started",
                description=f"**{full_title}** is now downloading!\n\n"
                           f"**Size:** {format_size(size)}\n"
                           f"**Quality:** {item.get('quality', {}).get('quality', {}).get('name', 'Unknown')}",
                color=0x3498db,
                thumbnail_url=poster
            )

        # Progress milestones
        if status == "downloading":
            for threshold in PROGRESS_THRESHOLDS:
                if progress >= threshold and threshold not in tracked.notified_milestones:
                    tracked.notified_milestones.add(threshold)

                    if threshold == 100:
                        send_discord_notification(
                            title="✅ Movie Complete!",
                            description=f"**{full_title}** has finished downloading!\n\n"
                                       f"**[Watch on Jellyfin]({JELLYFIN_URL})**",
                            color=0x2ecc71,
                            thumbnail_url=poster
                        )
                        tracker.completed_movies.add(movie_id)
                    else:
                        eta = item.get("timeleft", "Calculating...")
                        send_discord_notification(
                            title=f"📊 Movie Progress: {threshold}%",
                            description=f"**{full_title}**\n\n"
                                       f"**Progress:** {threshold}%\n"
                                       f"**ETA:** {eta}\n"
                                       f"**Downloaded:** {format_size(size - sizeleft)} / {format_size(size)}",
                            color=0xf39c12,
                            thumbnail_url=poster
                        )

    tracker.cleanup_stale_movies(active_ids)


# ============= SONARR INTEGRATION (AGGREGATED) =============

def get_sonarr_queue() -> List[dict]:
    """Fetch Sonarr download queue."""
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
        return response.json().get("records", [])
    except Exception as e:
        logger.error(f"Sonarr queue error: {e}")
        return []


def process_sonarr(tracker: MediaTracker):
    """Process Sonarr queue with aggregated notifications per series."""
    queue = get_sonarr_queue()

    # Group episodes by series
    series_episodes: Dict[int, List[dict]] = defaultdict(list)
    series_info: Dict[int, dict] = {}

    for item in queue:
        series = item.get("series", {})
        series_id = series.get("id")
        if not series_id:
            continue

        series_episodes[series_id].append(item)
        if series_id not in series_info:
            series_info[series_id] = series

    active_series_ids = set(series_episodes.keys())

    # Process each series as a group
    for series_id, episodes in series_episodes.items():
        series = series_info[series_id]
        series_title = series.get("title", "Unknown Series")

        poster = None
        for img in series.get("images", []):
            if img.get("coverType") == "poster":
                poster = img.get("remoteUrl") or img.get("url")
                break

        # Calculate aggregated stats
        total_episodes = len(episodes)
        downloading_count = sum(1 for e in episodes if e.get("status", "").lower() == "downloading")
        searching_count = sum(1 for e in episodes if e.get("status", "").lower() in ["delay", "pending", "queued"])

        total_size = sum(e.get("size", 0) for e in episodes)
        total_sizeleft = sum(e.get("sizeleft", 0) for e in episodes)
        overall_progress = ((total_size - total_sizeleft) / total_size * 100) if total_size > 0 else 0

        # Get episode range for display
        ep_numbers = []
        for e in episodes:
            ep = e.get("episode", {})
            season = ep.get("seasonNumber", 0)
            ep_num = ep.get("episodeNumber", 0)
            ep_numbers.append(f"S{season:02d}E{ep_num:02d}")
        ep_range = f"{ep_numbers[0]}" if len(ep_numbers) == 1 else f"{ep_numbers[0]} - {ep_numbers[-1]}"

        # Initialize or update tracking
        if series_id not in tracker.series:
            tracker.series[series_id] = TrackedSeries(
                series_id=series_id,
                title=series_title,
                poster_url=poster
            )

        tracked = tracker.series[series_id]
        tracked.episodes_total = total_episodes
        tracked.episodes_downloading = downloading_count
        tracked.overall_progress = overall_progress
        tracked.total_size = total_size
        tracked.downloaded_size = total_size - total_sizeleft

        # Searching notification (aggregated)
        if searching_count > 0 and not tracked.notified_searching:
            tracked.notified_searching = True
            send_discord_notification(
                title="🔍 Searching Indexers",
                description=f"**{series_title}**\n\n"
                           f"Searching for **{searching_count} episode{'s' if searching_count > 1 else ''}**\n"
                           f"Episodes: {ep_range}",
                color=0xf1c40f,
                thumbnail_url=poster
            )

        # Download started (aggregated)
        if downloading_count > 0 and not tracked.notified_start:
            tracked.notified_start = True
            send_discord_notification(
                title="⬇️ Series Download Started",
                description=f"**{series_title}**\n\n"
                           f"**Downloading:** {downloading_count} episode{'s' if downloading_count > 1 else ''}\n"
                           f"**Episodes:** {ep_range}\n"
                           f"**Total Size:** {format_size(total_size)}",
                color=0x3498db,
                thumbnail_url=poster
            )

        # Progress milestones (aggregated)
        if downloading_count > 0:
            for threshold in PROGRESS_THRESHOLDS:
                if overall_progress >= threshold and threshold not in tracked.notified_milestones:
                    tracked.notified_milestones.add(threshold)

                    if threshold == 100:
                        send_discord_notification(
                            title="✅ Series Episodes Complete!",
                            description=f"**{series_title}**\n\n"
                                       f"**{total_episodes} episode{'s' if total_episodes > 1 else ''}** finished downloading!\n"
                                       f"**Episodes:** {ep_range}\n\n"
                                       f"**[Watch on Jellyfin]({JELLYFIN_URL})**",
                            color=0x2ecc71,
                            thumbnail_url=poster
                        )
                        tracker.completed_series.add(series_id)
                    else:
                        # Calculate average ETA
                        etas = [e.get("timeleft", "") for e in episodes if e.get("timeleft")]
                        eta_display = etas[0] if etas else "Calculating..."

                        send_discord_notification(
                            title=f"📊 Series Progress: {threshold}%",
                            description=f"**{series_title}**\n\n"
                                       f"**Episodes:** {downloading_count}/{total_episodes} downloading\n"
                                       f"**Overall Progress:** {overall_progress:.1f}%\n"
                                       f"**Downloaded:** {format_size(total_size - total_sizeleft)} / {format_size(total_size)}\n"
                                       f"**ETA:** {eta_display}",
                            color=0xf39c12,
                            thumbnail_url=poster
                        )

    tracker.cleanup_stale_series(active_series_ids)


# ============= WEBHOOK SERVER =============

def run_webhook_server():
    """Run webhook server for Radarr/Sonarr/Jellyseerr notifications."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json
    import threading

    class WebhookHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "healthy", "service": "media-manager"}')
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                data = json.loads(body) if body else {}
            except:
                data = {}

            if "/jellyseerr" in self.path:
                self.handle_jellyseerr_webhook(data)
            elif "/radarr" in self.path:
                self.handle_radarr_webhook(data)
            elif "/sonarr" in self.path:
                self.handle_sonarr_webhook(data)

            self.send_response(200)
            self.end_headers()

        def handle_jellyseerr_webhook(self, data):
            notification_type = data.get("notification_type", "")
            media_title = data.get("subject", "Unknown")
            request_data = data.get("request", {})
            requester = request_data.get("requestedBy_username", "Someone")

            if notification_type == "MEDIA_PENDING":
                send_discord_notification(
                    title="📨 New Request Pending",
                    description=f"**{requester}** requested **{media_title}**\n\nWaiting for approval.",
                    color=0x9b59b6
                )
            elif notification_type == "MEDIA_APPROVED":
                send_discord_notification(
                    title="✅ Request Approved",
                    description=f"**{media_title}** has been approved and will start downloading soon.",
                    color=0x2ecc71
                )
            elif notification_type == "MEDIA_AVAILABLE":
                send_discord_notification(
                    title="🎉 Media Available",
                    description=f"**{media_title}** is now available!\n\n**[Watch on Jellyfin]({JELLYFIN_URL})**",
                    color=0x2ecc71
                )

        def handle_radarr_webhook(self, data):
            event_type = data.get("eventType", "")
            movie = data.get("movie", {})
            title = movie.get("title", "Unknown")
            year = movie.get("year", "")
            full_title = f"{title} ({year})" if year else title

            poster = None
            for img in movie.get("images", []):
                if img.get("coverType") == "poster":
                    poster = img.get("remoteUrl")
                    break

            if event_type == "Grab":
                send_discord_notification(
                    title="🎬 Movie Grabbed",
                    description=f"**{full_title}** grabbed - download starting soon.",
                    color=0x3498db,
                    thumbnail_url=poster
                )
            elif event_type == "Download":
                send_discord_notification(
                    title="✅ Movie Ready",
                    description=f"**{full_title}** is ready to watch!\n\n**[Watch on Jellyfin]({JELLYFIN_URL})**",
                    color=0x2ecc71,
                    thumbnail_url=poster
                )

        def handle_sonarr_webhook(self, data):
            event_type = data.get("eventType", "")
            series = data.get("series", {})
            episodes = data.get("episodes", [])

            series_title = series.get("title", "Unknown")
            ep_count = len(episodes)

            if ep_count == 1:
                ep = episodes[0]
                season = ep.get("seasonNumber", 0)
                ep_num = ep.get("episodeNumber", 0)
                ep_title = ep.get("title", "")
                ep_display = f"S{season:02d}E{ep_num:02d}"
                if ep_title:
                    ep_display += f" - {ep_title}"
            else:
                ep_display = f"{ep_count} episodes"

            poster = None
            for img in series.get("images", []):
                if img.get("coverType") == "poster":
                    poster = img.get("remoteUrl")
                    break

            if event_type == "Grab":
                send_discord_notification(
                    title="📺 Episodes Grabbed",
                    description=f"**{series_title}**\n{ep_display}\n\nDownload starting soon.",
                    color=0x3498db,
                    thumbnail_url=poster
                )
            elif event_type == "Download":
                send_discord_notification(
                    title="✅ Episodes Ready",
                    description=f"**{series_title}**\n{ep_display}\n\n**[Watch on Jellyfin]({JELLYFIN_URL})**",
                    color=0x2ecc71,
                    thumbnail_url=poster
                )

        def log_message(self, format, *args):
            logger.debug(f"Webhook: {args[0]}")

    server = HTTPServer(("0.0.0.0", 5052), WebhookHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Webhook server started on port 5052")
    return server


# ============= MAIN =============

def main():
    logger.info("=" * 50)
    logger.info("Media Manager Starting")
    logger.info("=" * 50)
    logger.info(f"Radarr: {RADARR_URL}")
    logger.info(f"Sonarr: {SONARR_URL}")
    logger.info(f"Jellyseerr: {JELLYSEERR_URL}")
    logger.info(f"Jellyfin: {JELLYFIN_URL}")
    logger.info(f"Poll interval: {POLL_INTERVAL}s")

    if not DISCORD_WEBHOOK_URL:
        logger.error("DISCORD_WEBHOOK_URL not set!")

    run_webhook_server()

    send_discord_notification(
        title="🚀 Media Manager Online",
        description="Media Manager is now active!\n\n"
                   "**Monitoring:**\n"
                   "• Jellyseerr requests\n"
                   "• Radarr movies\n"
                   "• Sonarr series (aggregated)\n"
                   "• Progress at 50%, 80%, 100%",
        color=0x9b59b6
    )

    tracker = MediaTracker()

    while True:
        try:
            process_jellyseerr_requests(tracker)
            process_radarr(tracker)
            process_sonarr(tracker)
        except Exception as e:
            logger.error(f"Monitor loop error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
