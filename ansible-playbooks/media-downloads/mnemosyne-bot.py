#!/usr/bin/env python3
"""
Mnemosyne - Media Download Discord Bot
Goddess of Memory - Tracks and manages your media downloads.

Features:
- Real-time download notifications (50%, 80%, 100% progress)
- Slash commands for media management
- Radarr/Sonarr integration
- Quality profile management
- Library browsing

Commands:
  /downloads       - Show current download queue
  /search          - Search for movies/shows
  /request         - Add media to download
  /availablemovies - List available movies
  /availableseries - List available series
  /showlist        - Quick compact media list
  /stats           - Library statistics
  /recent          - Recent downloads
  /quality         - View quality profiles
  /mnemosyne       - Show help
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Set, List
import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiohttp

# === Configuration ===
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
MEDIA_CHANNEL_ID = int(os.getenv("MEDIA_CHANNEL_ID", "0"))

# Channel restrictions
ALLOWED_CHANNELS = os.getenv("ALLOWED_CHANNELS", "media-downloads")

# Radarr/Sonarr Configuration
RADARR_URL = os.getenv("RADARR_URL", "http://192.168.40.11:7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "")
SONARR_URL = os.getenv("SONARR_URL", "http://192.168.40.11:8989")
SONARR_API_KEY = os.getenv("SONARR_API_KEY", "")
JELLYFIN_URL = os.getenv("JELLYFIN_URL", "https://jellyfin.hrmsmrflrii.xyz")

# Monitoring settings
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))  # seconds
PROGRESS_THRESHOLDS = [50, 80, 100]

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# === Channel Restriction ===
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
        # Check if name contains the allowed channel (for threads)
        for allowed in ALLOWED_CHANNEL_LIST:
            if isinstance(allowed, str) and allowed in channel_name:
                return True

        await interaction.response.send_message(
            f"This command can only be used in: **#{', #'.join(str(c) for c in ALLOWED_CHANNEL_LIST)}**",
            ephemeral=True
        )
        return False
    return app_commands.check(predicate)


# === Download Tracker ===
class DownloadTracker:
    """Tracks download progress and sent notifications."""

    def __init__(self):
        self.notified_milestones: Dict[str, Set[int]] = {}
        self.known_downloads: Set[str] = set()
        self.completed_downloads: Set[str] = set()
        self.download_info: Dict[str, dict] = {}  # Store info for notifications

    def should_notify_start(self, download_id: str, info: dict) -> bool:
        if download_id not in self.known_downloads:
            self.known_downloads.add(download_id)
            self.notified_milestones[download_id] = set()
            self.download_info[download_id] = info
            return True
        return False

    def should_notify_progress(self, download_id: str, progress: float) -> Optional[int]:
        if download_id not in self.notified_milestones:
            self.notified_milestones[download_id] = set()

        for threshold in PROGRESS_THRESHOLDS:
            if progress >= threshold and threshold not in self.notified_milestones[download_id]:
                self.notified_milestones[download_id].add(threshold)
                return threshold
        return None

    def mark_completed(self, download_id: str) -> Optional[dict]:
        if download_id not in self.completed_downloads:
            self.completed_downloads.add(download_id)
            info = self.download_info.pop(download_id, None)
            self.known_downloads.discard(download_id)
            self.notified_milestones.pop(download_id, None)
            return info
        return None

    def cleanup_stale(self, active_ids: Set[str]):
        stale_ids = self.known_downloads - active_ids - self.completed_downloads
        for stale_id in stale_ids:
            self.known_downloads.discard(stale_id)
            self.notified_milestones.pop(stale_id, None)
            self.download_info.pop(stale_id, None)


tracker = DownloadTracker()


# === Helper Functions ===
def format_size(bytes_size: int) -> str:
    """Format bytes to human readable size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"


def calculate_progress(item: dict) -> float:
    """Calculate download progress percentage."""
    size = item.get("size", 0)
    sizeleft = item.get("sizeleft", 0)
    if size <= 0:
        return 0.0
    return ((size - sizeleft) / size) * 100


def create_embed(title: str, description: str = None, color: int = 0x9b59b6, fields: list = None):
    """Create a Discord embed with Mnemosyne branding."""
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now())
    embed.set_footer(text="Mnemosyne - Media Guardian")
    if fields:
        for field in fields:
            embed.add_field(name=field["name"], value=field["value"], inline=field.get("inline", True))
    return embed


# === Bot Setup ===
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


# === API Helpers ===
async def fetch_radarr(endpoint: str, params: dict = None) -> Optional[dict]:
    """Fetch data from Radarr API."""
    if not RADARR_API_KEY:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{RADARR_URL}/api/v3/{endpoint}",
                headers={"X-Api-Key": RADARR_API_KEY},
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logger.error(f"Radarr API error: {e}")
    return None


async def fetch_sonarr(endpoint: str, params: dict = None) -> Optional[dict]:
    """Fetch data from Sonarr API."""
    if not SONARR_API_KEY:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{SONARR_URL}/api/v3/{endpoint}",
                headers={"X-Api-Key": SONARR_API_KEY},
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logger.error(f"Sonarr API error: {e}")
    return None


async def post_radarr(endpoint: str, data: dict) -> Optional[dict]:
    """POST data to Radarr API."""
    if not RADARR_API_KEY:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{RADARR_URL}/api/v3/{endpoint}",
                headers={"X-Api-Key": RADARR_API_KEY},
                json=data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status in [200, 201]:
                    return await resp.json()
                else:
                    text = await resp.text()
                    logger.error(f"Radarr POST error: {resp.status} - {text}")
    except Exception as e:
        logger.error(f"Radarr POST error: {e}")
    return None


async def post_sonarr(endpoint: str, data: dict) -> Optional[dict]:
    """POST data to Sonarr API."""
    if not SONARR_API_KEY:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{SONARR_URL}/api/v3/{endpoint}",
                headers={"X-Api-Key": SONARR_API_KEY},
                json=data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status in [200, 201]:
                    return await resp.json()
                else:
                    text = await resp.text()
                    logger.error(f"Sonarr POST error: {resp.status} - {text}")
    except Exception as e:
        logger.error(f"Sonarr POST error: {e}")
    return None


# === Slash Commands ===

@bot.tree.command(name="downloads", description="Show current download queue")
@is_allowed_channel()
async def downloads_command(interaction: discord.Interaction):
    """Show current downloads from Radarr and Sonarr."""
    await interaction.response.defer()

    embed = create_embed("Current Downloads", color=0x3498db)

    # Radarr queue
    radarr_queue = await fetch_radarr("queue", {"includeMovie": "true"})
    if radarr_queue:
        records = radarr_queue.get("records", [])
        if records:
            movie_list = []
            for item in records[:5]:
                movie = item.get("movie", {})
                title = movie.get("title", "Unknown")
                progress = calculate_progress(item)
                eta = item.get("timeleft", "Unknown")
                status = item.get("status", "Unknown")
                movie_list.append(f"**{title}** - {progress:.0f}% ({status})\nETA: {eta}")
            embed.add_field(
                name=f"Movies ({len(records)})",
                value="\n\n".join(movie_list) if movie_list else "None",
                inline=False
            )
        else:
            embed.add_field(name="Movies", value="No active downloads", inline=False)

    # Sonarr queue
    sonarr_queue = await fetch_sonarr("queue", {"includeSeries": "true", "includeEpisode": "true"})
    if sonarr_queue:
        records = sonarr_queue.get("records", [])
        if records:
            episode_list = []
            for item in records[:5]:
                series = item.get("series", {})
                episode = item.get("episode", {})
                series_title = series.get("title", "Unknown")
                season = episode.get("seasonNumber", 0)
                ep_num = episode.get("episodeNumber", 0)
                progress = calculate_progress(item)
                eta = item.get("timeleft", "Unknown")
                episode_list.append(f"**{series_title}** S{season:02d}E{ep_num:02d} - {progress:.0f}%\nETA: {eta}")
            embed.add_field(
                name=f"TV Episodes ({len(records)})",
                value="\n\n".join(episode_list) if episode_list else "None",
                inline=False
            )
        else:
            embed.add_field(name="TV Episodes", value="No active downloads", inline=False)

    if not radarr_queue and not sonarr_queue:
        embed.description = "Unable to fetch download queues. Check API configuration."
        embed.color = 0xff0000

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="search", description="Search for movies or TV shows")
@is_allowed_channel()
@app_commands.describe(query="Title to search for", media_type="Movie or TV Show")
@app_commands.choices(media_type=[
    app_commands.Choice(name="Movie", value="movie"),
    app_commands.Choice(name="TV Show", value="tv"),
])
async def search_command(interaction: discord.Interaction, query: str, media_type: str = "movie"):
    """Search for media in Radarr/Sonarr."""
    await interaction.response.defer()

    if media_type == "movie":
        results = await fetch_radarr("movie/lookup", {"term": query})
        if not results:
            await interaction.followup.send(embed=create_embed(
                "Search Failed",
                "Could not search Radarr. Check API configuration.",
                color=0xff0000
            ))
            return

        if not results:
            await interaction.followup.send(embed=create_embed(
                "No Results",
                f"No movies found matching: **{query}**",
                color=0xff9900
            ))
            return

        embed = create_embed(f"Movie Search: {query}", color=0x3498db)
        for movie in results[:5]:
            title = movie.get("title", "Unknown")
            year = movie.get("year", "N/A")
            overview = movie.get("overview", "No description")[:150]
            tmdb_id = movie.get("tmdbId", "N/A")
            embed.add_field(
                name=f"{title} ({year})",
                value=f"{overview}...\n`TMDB: {tmdb_id}`",
                inline=False
            )

        embed.set_footer(text=f"Use /request to add a movie | Found {len(results)} results")
        await interaction.followup.send(embed=embed)

    else:
        results = await fetch_sonarr("series/lookup", {"term": query})
        if not results:
            await interaction.followup.send(embed=create_embed(
                "Search Failed",
                "Could not search Sonarr. Check API configuration.",
                color=0xff0000
            ))
            return

        if not results:
            await interaction.followup.send(embed=create_embed(
                "No Results",
                f"No TV shows found matching: **{query}**",
                color=0xff9900
            ))
            return

        embed = create_embed(f"TV Search: {query}", color=0x3498db)
        for show in results[:5]:
            title = show.get("title", "Unknown")
            year = show.get("year", "N/A")
            seasons = show.get("seasonCount", "N/A")
            status = show.get("status", "Unknown")
            tvdb_id = show.get("tvdbId", "N/A")
            embed.add_field(
                name=f"{title} ({year})",
                value=f"Seasons: {seasons} | Status: {status}\n`TVDB: {tvdb_id}`",
                inline=False
            )

        embed.set_footer(text=f"Use /request to add a show | Found {len(results)} results")
        await interaction.followup.send(embed=embed)


@bot.tree.command(name="request", description="Request a movie or TV show to download")
@is_allowed_channel()
@app_commands.describe(title="Title to add", media_type="Movie or TV Show")
@app_commands.choices(media_type=[
    app_commands.Choice(name="Movie", value="movie"),
    app_commands.Choice(name="TV Show", value="tv"),
])
async def request_command(interaction: discord.Interaction, title: str, media_type: str = "movie"):
    """Add media to Radarr/Sonarr."""
    await interaction.response.defer()

    if media_type == "movie":
        # Search for the movie first
        results = await fetch_radarr("movie/lookup", {"term": title})
        if not results:
            await interaction.followup.send(embed=create_embed(
                "Not Found",
                f"Could not find movie: **{title}**",
                color=0xff9900
            ))
            return

        movie = results[0]

        # Get quality profiles
        profiles = await fetch_radarr("qualityprofile")
        root_folders = await fetch_radarr("rootfolder")

        if not profiles or not root_folders:
            await interaction.followup.send(embed=create_embed(
                "Configuration Error",
                "Could not get quality profiles or root folders from Radarr.",
                color=0xff0000
            ))
            return

        # Add the movie
        add_data = {
            "title": movie.get("title"),
            "tmdbId": movie.get("tmdbId"),
            "qualityProfileId": profiles[0].get("id"),
            "rootFolderPath": root_folders[0].get("path"),
            "monitored": True,
            "addOptions": {"searchForMovie": True}
        }

        result = await post_radarr("movie", add_data)
        if result:
            embed = create_embed(
                "Movie Added!",
                f"**{movie.get('title')}** ({movie.get('year')}) has been added to Radarr.",
                color=0x2ecc71
            )
            embed.add_field(name="Quality", value=profiles[0].get("name"), inline=True)
            embed.add_field(name="Status", value="Searching for download...", inline=True)
            if movie.get("remotePoster"):
                embed.set_thumbnail(url=movie.get("remotePoster"))
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(embed=create_embed(
                "Failed to Add",
                f"Could not add **{movie.get('title')}**. It may already exist.",
                color=0xff0000
            ))

    else:
        # Search for the show first
        results = await fetch_sonarr("series/lookup", {"term": title})
        if not results:
            await interaction.followup.send(embed=create_embed(
                "Not Found",
                f"Could not find TV show: **{title}**",
                color=0xff9900
            ))
            return

        show = results[0]

        # Get quality profiles
        profiles = await fetch_sonarr("qualityprofile")
        root_folders = await fetch_sonarr("rootfolder")

        if not profiles or not root_folders:
            await interaction.followup.send(embed=create_embed(
                "Configuration Error",
                "Could not get quality profiles or root folders from Sonarr.",
                color=0xff0000
            ))
            return

        # Add the show
        add_data = {
            "title": show.get("title"),
            "tvdbId": show.get("tvdbId"),
            "qualityProfileId": profiles[0].get("id"),
            "rootFolderPath": root_folders[0].get("path"),
            "monitored": True,
            "seasonFolder": True,
            "addOptions": {"searchForMissingEpisodes": True}
        }

        result = await post_sonarr("series", add_data)
        if result:
            embed = create_embed(
                "TV Show Added!",
                f"**{show.get('title')}** has been added to Sonarr.",
                color=0x2ecc71
            )
            embed.add_field(name="Seasons", value=str(show.get("seasonCount", "N/A")), inline=True)
            embed.add_field(name="Status", value="Searching for episodes...", inline=True)
            if show.get("remotePoster"):
                embed.set_thumbnail(url=show.get("remotePoster"))
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(embed=create_embed(
                "Failed to Add",
                f"Could not add **{show.get('title')}**. It may already exist.",
                color=0xff0000
            ))


@bot.tree.command(name="stats", description="Show media library statistics")
@is_allowed_channel()
async def stats_command(interaction: discord.Interaction):
    """Show library statistics from Radarr and Sonarr."""
    await interaction.response.defer()

    embed = create_embed("Media Library Stats", color=0x9b59b6)

    # Radarr stats
    movies = await fetch_radarr("movie")
    if movies:
        total_movies = len(movies)
        downloaded = sum(1 for m in movies if m.get("hasFile"))
        monitored = sum(1 for m in movies if m.get("monitored"))
        embed.add_field(
            name="Movies",
            value=f"Total: {total_movies}\nDownloaded: {downloaded}\nMonitored: {monitored}",
            inline=True
        )

    # Sonarr stats
    series = await fetch_sonarr("series")
    if series:
        total_series = len(series)
        continuing = sum(1 for s in series if s.get("status") == "continuing")
        ended = sum(1 for s in series if s.get("status") == "ended")
        embed.add_field(
            name="TV Shows",
            value=f"Total: {total_series}\nContinuing: {continuing}\nEnded: {ended}",
            inline=True
        )

    # System stats
    radarr_status = await fetch_radarr("system/status")
    sonarr_status = await fetch_sonarr("system/status")

    if radarr_status:
        embed.add_field(
            name="Radarr",
            value=f"Version: {radarr_status.get('version', 'N/A')}",
            inline=True
        )

    if sonarr_status:
        embed.add_field(
            name="Sonarr",
            value=f"Version: {sonarr_status.get('version', 'N/A')}",
            inline=True
        )

    if not movies and not series:
        embed.description = "Unable to fetch library stats. Check API configuration."
        embed.color = 0xff0000

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="recent", description="Show recently added media")
@is_allowed_channel()
@app_commands.describe(media_type="Movies or TV Shows")
@app_commands.choices(media_type=[
    app_commands.Choice(name="Movies", value="movie"),
    app_commands.Choice(name="TV Shows", value="tv"),
    app_commands.Choice(name="Both", value="both"),
])
async def recent_command(interaction: discord.Interaction, media_type: str = "both"):
    """Show recently downloaded media."""
    await interaction.response.defer()

    embed = create_embed("Recently Added", color=0x2ecc71)

    if media_type in ["movie", "both"]:
        movies = await fetch_radarr("movie")
        if movies:
            # Sort by added date and filter to those with files
            recent_movies = sorted(
                [m for m in movies if m.get("hasFile")],
                key=lambda x: x.get("movieFile", {}).get("dateAdded", ""),
                reverse=True
            )[:5]

            if recent_movies:
                movie_list = []
                for movie in recent_movies:
                    title = movie.get("title", "Unknown")
                    year = movie.get("year", "N/A")
                    added = movie.get("movieFile", {}).get("dateAdded", "Unknown")[:10]
                    movie_list.append(f"**{title}** ({year}) - Added: {added}")
                embed.add_field(name="Recent Movies", value="\n".join(movie_list), inline=False)
            else:
                embed.add_field(name="Recent Movies", value="No recent movies", inline=False)

    if media_type in ["tv", "both"]:
        # Get recent episode files
        history = await fetch_sonarr("history", {"pageSize": "10", "sortKey": "date", "sortDirection": "descending"})
        if history:
            records = history.get("records", [])
            downloaded = [r for r in records if r.get("eventType") == "downloadFolderImported"][:5]

            if downloaded:
                episode_list = []
                for record in downloaded:
                    series_title = record.get("series", {}).get("title", "Unknown")
                    episode = record.get("episode", {})
                    season = episode.get("seasonNumber", 0)
                    ep_num = episode.get("episodeNumber", 0)
                    date = record.get("date", "")[:10]
                    episode_list.append(f"**{series_title}** S{season:02d}E{ep_num:02d} - {date}")
                embed.add_field(name="Recent Episodes", value="\n".join(episode_list), inline=False)
            else:
                embed.add_field(name="Recent Episodes", value="No recent episodes", inline=False)

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="quality", description="View quality profiles")
@is_allowed_channel()
@app_commands.describe(service="Service to view profiles for")
@app_commands.choices(service=[
    app_commands.Choice(name="Radarr (Movies)", value="radarr"),
    app_commands.Choice(name="Sonarr (TV)", value="sonarr"),
])
async def quality_command(interaction: discord.Interaction, service: str = "radarr"):
    """View quality profiles for Radarr/Sonarr."""
    await interaction.response.defer()

    if service == "radarr":
        profiles = await fetch_radarr("qualityprofile")
        service_name = "Radarr"
    else:
        profiles = await fetch_sonarr("qualityprofile")
        service_name = "Sonarr"

    if not profiles:
        await interaction.followup.send(embed=create_embed(
            "Error",
            f"Could not fetch quality profiles from {service_name}.",
            color=0xff0000
        ))
        return

    embed = create_embed(f"{service_name} Quality Profiles", color=0x3498db)

    for profile in profiles[:10]:
        name = profile.get("name", "Unknown")
        cutoff = profile.get("cutoff", {})
        cutoff_name = "N/A"

        # Find cutoff quality name
        for item in profile.get("items", []):
            if item.get("quality", {}).get("id") == cutoff:
                cutoff_name = item.get("quality", {}).get("name", "N/A")
                break
            for subitem in item.get("items", []):
                if subitem.get("quality", {}).get("id") == cutoff:
                    cutoff_name = subitem.get("quality", {}).get("name", "N/A")
                    break

        embed.add_field(
            name=name,
            value=f"ID: {profile.get('id')} | Cutoff: {cutoff_name}",
            inline=True
        )

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="availablemovies", description="List movies available in your library")
@is_allowed_channel()
@app_commands.describe(limit="Number of movies to show (default: 20)")
async def available_movies_command(interaction: discord.Interaction, limit: int = 20):
    """Show movies that are downloaded and available to watch."""
    await interaction.response.defer()

    movies = await fetch_radarr("movie")
    if not movies:
        await interaction.followup.send(embed=create_embed(
            "Error",
            "Could not fetch movies from Radarr.",
            color=0xff0000
        ))
        return

    # Filter to only movies with files (available to watch)
    available = [m for m in movies if m.get("hasFile")]

    if not available:
        await interaction.followup.send(embed=create_embed(
            "No Movies Available",
            "No movies are currently downloaded in your library.",
            color=0xff9900
        ))
        return

    # Sort by title
    available.sort(key=lambda x: x.get("title", "").lower())

    # Limit results
    limit = min(limit, 50)
    displayed = available[:limit]

    embed = create_embed(
        f"Available Movies ({len(available)} total)",
        f"Showing {len(displayed)} of {len(available)} movies in your library.",
        color=0x2ecc71
    )

    # Split into chunks for fields
    movie_lines = []
    for movie in displayed:
        title = movie.get("title", "Unknown")
        year = movie.get("year", "N/A")
        quality = movie.get("movieFile", {}).get("quality", {}).get("quality", {}).get("name", "Unknown")
        movie_lines.append(f"**{title}** ({year}) - {quality}")

    # Add movies in chunks (max 1024 chars per field)
    current_chunk = []
    current_len = 0
    chunk_num = 1

    for line in movie_lines:
        if current_len + len(line) + 1 > 1000:
            embed.add_field(
                name=f"Movies {chunk_num}" if chunk_num > 1 else "Movies",
                value="\n".join(current_chunk),
                inline=False
            )
            current_chunk = [line]
            current_len = len(line)
            chunk_num += 1
        else:
            current_chunk.append(line)
            current_len += len(line) + 1

    if current_chunk:
        embed.add_field(
            name=f"Movies {chunk_num}" if chunk_num > 1 else "Movies",
            value="\n".join(current_chunk),
            inline=False
        )

    embed.set_footer(text=f"Mnemosyne - {len(available)} movies available | {len(movies) - len(available)} missing")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="availableseries", description="List TV series available in your library")
@is_allowed_channel()
@app_commands.describe(limit="Number of series to show (default: 20)")
async def available_series_command(interaction: discord.Interaction, limit: int = 20):
    """Show TV series that have episodes downloaded."""
    await interaction.response.defer()

    series = await fetch_sonarr("series")
    if not series:
        await interaction.followup.send(embed=create_embed(
            "Error",
            "Could not fetch series from Sonarr.",
            color=0xff0000
        ))
        return

    # Filter to series with at least one episode
    available = [s for s in series if s.get("statistics", {}).get("episodeFileCount", 0) > 0]

    if not available:
        await interaction.followup.send(embed=create_embed(
            "No Series Available",
            "No TV series episodes are currently downloaded in your library.",
            color=0xff9900
        ))
        return

    # Sort by title
    available.sort(key=lambda x: x.get("title", "").lower())

    # Limit results
    limit = min(limit, 50)
    displayed = available[:limit]

    embed = create_embed(
        f"Available Series ({len(available)} total)",
        f"Showing {len(displayed)} of {len(available)} series in your library.",
        color=0x2ecc71
    )

    # Split into chunks for fields
    series_lines = []
    for show in displayed:
        title = show.get("title", "Unknown")
        stats = show.get("statistics", {})
        episodes = stats.get("episodeFileCount", 0)
        total_eps = stats.get("totalEpisodeCount", 0)
        seasons = show.get("seasonCount", 0)
        status = show.get("status", "Unknown").title()
        series_lines.append(f"**{title}** - {episodes}/{total_eps} eps ({seasons} seasons) [{status}]")

    # Add series in chunks (max 1024 chars per field)
    current_chunk = []
    current_len = 0
    chunk_num = 1

    for line in series_lines:
        if current_len + len(line) + 1 > 1000:
            embed.add_field(
                name=f"Series {chunk_num}" if chunk_num > 1 else "Series",
                value="\n".join(current_chunk),
                inline=False
            )
            current_chunk = [line]
            current_len = len(line)
            chunk_num += 1
        else:
            current_chunk.append(line)
            current_len += len(line) + 1

    if current_chunk:
        embed.add_field(
            name=f"Series {chunk_num}" if chunk_num > 1 else "Series",
            value="\n".join(current_chunk),
            inline=False
        )

    total_episodes = sum(s.get("statistics", {}).get("episodeFileCount", 0) for s in available)
    embed.set_footer(text=f"Mnemosyne - {len(available)} series | {total_episodes} episodes available")
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="showlist", description="Quick list of all available media titles")
@is_allowed_channel()
@app_commands.describe(media_type="Type of media to list")
@app_commands.choices(media_type=[
    app_commands.Choice(name="Movies", value="movie"),
    app_commands.Choice(name="TV Shows", value="tv"),
    app_commands.Choice(name="Both", value="both"),
])
async def showlist_command(interaction: discord.Interaction, media_type: str = "both"):
    """Quick compact list of all available media."""
    await interaction.response.defer()

    lines = []

    if media_type in ["movie", "both"]:
        movies = await fetch_radarr("movie")
        if movies:
            available_movies = [m for m in movies if m.get("hasFile")]
            available_movies.sort(key=lambda x: x.get("title", "").lower())
            if available_movies:
                lines.append(f"**MOVIES ({len(available_movies)})**")
                lines.extend([f"- {m.get('title')} ({m.get('year', 'N/A')})" for m in available_movies[:25]])
                if len(available_movies) > 25:
                    lines.append(f"*...and {len(available_movies) - 25} more*")
                lines.append("")

    if media_type in ["tv", "both"]:
        series = await fetch_sonarr("series")
        if series:
            available_series = [s for s in series if s.get("statistics", {}).get("episodeFileCount", 0) > 0]
            available_series.sort(key=lambda x: x.get("title", "").lower())
            if available_series:
                lines.append(f"**TV SERIES ({len(available_series)})**")
                lines.extend([f"- {s.get('title')}" for s in available_series[:25]])
                if len(available_series) > 25:
                    lines.append(f"*...and {len(available_series) - 25} more*")

    if not lines:
        await interaction.followup.send(embed=create_embed(
            "No Media Available",
            "Your library is empty.",
            color=0xff9900
        ))
        return

    content = "\n".join(lines)
    if len(content) > 4000:
        content = content[:4000] + "\n*...truncated*"

    embed = create_embed("Media Library", content, color=0x9b59b6)
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="mnemosyne", description="Show Mnemosyne help and info")
@is_allowed_channel()
async def help_command(interaction: discord.Interaction):
    """Show help message."""
    embed = create_embed(
        "Mnemosyne - Media Guardian",
        "I track and manage your media downloads. Here are my commands:",
        color=0x9b59b6
    )

    embed.add_field(
        name="Download Management",
        value="`/downloads` - Show current queue\n`/recent` - Recently added media",
        inline=False
    )

    embed.add_field(
        name="Media Search & Request",
        value="`/search` - Search for movies/shows\n`/request` - Add media to download",
        inline=False
    )

    embed.add_field(
        name="Library Browse",
        value="`/availablemovies` - List downloaded movies\n`/availableseries` - List downloaded series\n`/showlist` - Quick compact list",
        inline=False
    )

    embed.add_field(
        name="Library Info",
        value="`/stats` - Library statistics\n`/quality` - View quality profiles",
        inline=False
    )

    embed.add_field(
        name="Services",
        value=f"Radarr: {RADARR_URL}\nSonarr: {SONARR_URL}\nJellyfin: {JELLYFIN_URL}",
        inline=False
    )

    await interaction.response.send_message(embed=embed)


# === Background Task: Download Monitor ===
@tasks.loop(seconds=POLL_INTERVAL)
async def monitor_downloads():
    """Monitor download queues and send notifications."""
    channel = bot.get_channel(MEDIA_CHANNEL_ID)
    if not channel:
        return

    active_ids = set()

    # Check Radarr queue
    radarr_queue = await fetch_radarr("queue", {"includeMovie": "true"})
    if radarr_queue:
        for item in radarr_queue.get("records", []):
            download_id = f"radarr_{item.get('id')}"
            active_ids.add(download_id)

            movie = item.get("movie", {})
            title = movie.get("title", "Unknown")
            year = movie.get("year", "")
            full_title = f"{title} ({year})" if year else title
            progress = calculate_progress(item)
            poster = None
            for img in movie.get("images", []):
                if img.get("coverType") == "poster":
                    poster = img.get("remoteUrl")
                    break

            info = {"title": full_title, "type": "movie", "poster": poster}

            # New download notification
            if tracker.should_notify_start(download_id, info):
                size = format_size(item.get("size", 0))
                embed = create_embed(
                    "New Download Started",
                    f"**{full_title}** is now downloading.",
                    color=0x3498db
                )
                embed.add_field(name="Size", value=size, inline=True)
                embed.add_field(name="Quality", value=item.get("quality", {}).get("quality", {}).get("name", "Unknown"), inline=True)
                if poster:
                    embed.set_thumbnail(url=poster)
                await channel.send(embed=embed)

            # Progress notification
            if item.get("status", "").lower() == "downloading":
                threshold = tracker.should_notify_progress(download_id, progress)
                if threshold and threshold < 100:
                    embed = create_embed(
                        f"Download Progress: {threshold}%",
                        f"**{full_title}** is {threshold}% complete.",
                        color=0xf39c12
                    )
                    embed.add_field(name="ETA", value=item.get("timeleft", "Unknown"), inline=True)
                    if poster:
                        embed.set_thumbnail(url=poster)
                    await channel.send(embed=embed)

    # Check Sonarr queue
    sonarr_queue = await fetch_sonarr("queue", {"includeSeries": "true", "includeEpisode": "true"})
    if sonarr_queue:
        for item in sonarr_queue.get("records", []):
            download_id = f"sonarr_{item.get('id')}"
            active_ids.add(download_id)

            series = item.get("series", {})
            episode = item.get("episode", {})
            series_title = series.get("title", "Unknown")
            season = episode.get("seasonNumber", 0)
            ep_num = episode.get("episodeNumber", 0)
            full_title = f"{series_title} - S{season:02d}E{ep_num:02d}"
            progress = calculate_progress(item)
            poster = None
            for img in series.get("images", []):
                if img.get("coverType") == "poster":
                    poster = img.get("remoteUrl")
                    break

            info = {"title": full_title, "type": "tv", "poster": poster}

            # New download notification
            if tracker.should_notify_start(download_id, info):
                size = format_size(item.get("size", 0))
                embed = create_embed(
                    "New Episode Downloading",
                    f"**{full_title}** is now downloading.",
                    color=0x3498db
                )
                embed.add_field(name="Size", value=size, inline=True)
                if poster:
                    embed.set_thumbnail(url=poster)
                await channel.send(embed=embed)

            # Progress notification
            if item.get("status", "").lower() == "downloading":
                threshold = tracker.should_notify_progress(download_id, progress)
                if threshold and threshold < 100:
                    embed = create_embed(
                        f"Download Progress: {threshold}%",
                        f"**{full_title}** is {threshold}% complete.",
                        color=0xf39c12
                    )
                    embed.add_field(name="ETA", value=item.get("timeleft", "Unknown"), inline=True)
                    if poster:
                        embed.set_thumbnail(url=poster)
                    await channel.send(embed=embed)

    # Check for completed downloads
    for download_id in list(tracker.known_downloads):
        if download_id not in active_ids:
            info = tracker.mark_completed(download_id)
            if info:
                embed = create_embed(
                    "Download Complete!",
                    f"**{info.get('title')}** has finished downloading!",
                    color=0x2ecc71
                )
                embed.add_field(name="Watch Now", value=f"[Open Jellyfin]({JELLYFIN_URL})", inline=True)
                if info.get("poster"):
                    embed.set_thumbnail(url=info.get("poster"))
                await channel.send(embed=embed)

    tracker.cleanup_stale(active_ids)


@monitor_downloads.before_loop
async def before_monitor():
    await bot.wait_until_ready()


# === Bot Events ===
@bot.event
async def on_ready():
    """Called when bot is ready."""
    logger.info(f"Logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} commands")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

    if not monitor_downloads.is_running():
        monitor_downloads.start()
        logger.info(f"Download monitor started (interval: {POLL_INTERVAL}s)")

    # Send welcome message to all allowed channels
    for channel_ref in ALLOWED_CHANNEL_LIST:
        channel = None
        if isinstance(channel_ref, int):
            channel = bot.get_channel(channel_ref)
        else:
            for guild in bot.guilds:
                channel = discord.utils.get(guild.channels, name=channel_ref)
                if channel:
                    break

        if channel:
            embed = create_embed(
                "Mnemosyne Online",
                "The Media Guardian is now watching your downloads!",
                color=0x9b59b6
            )
            embed.add_field(
                name="Downloads",
                value="`/downloads` - Current queue\n`/recent` - Recently added",
                inline=True
            )
            embed.add_field(
                name="Search & Request",
                value="`/search` - Find media\n`/request` - Add to library",
                inline=True
            )
            embed.add_field(
                name="Browse Library",
                value="`/availablemovies` - Movies\n`/availableseries` - Series\n`/showlist` - Quick list",
                inline=True
            )
            embed.add_field(
                name="Info & Help",
                value="`/stats` - Statistics\n`/mnemosyne` - All commands",
                inline=True
            )
            await channel.send(embed=embed)


def main():
    """Main entry point."""
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not set!")
        return

    logger.info("Starting Mnemosyne - Media Guardian...")
    logger.info(f"Radarr: {RADARR_URL}")
    logger.info(f"Sonarr: {SONARR_URL}")
    logger.info(f"Allowed channels: {ALLOWED_CHANNEL_LIST}")

    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
