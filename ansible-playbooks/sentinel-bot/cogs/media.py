"""
Sentinel Bot - Media Cog
Media download tracking and library management.
Ported from Mnemosyne bot.
"""

import logging
import discord
from discord import app_commands
from discord.ext import commands
from typing import TYPE_CHECKING, Optional, List

from core.progress import make_progress_bar, ProgressEmbed

if TYPE_CHECKING:
    from core import SentinelBot

logger = logging.getLogger('sentinel.cogs.media')


class MediaCog(commands.Cog, name="Media"):
    """Media download tracking and library management."""

    def __init__(self, bot: 'SentinelBot'):
        self.bot = bot

    @property
    def config(self):
        return self.bot.config

    # ==================== Download Commands ====================

    @app_commands.command(name="downloads", description="Show current download queue")
    async def downloads(self, interaction: discord.Interaction):
        """Show currently downloading media."""
        await interaction.response.defer()

        # 2 steps: Radarr queue, Sonarr queue
        progress = ProgressEmbed(":arrow_down: Fetching Download Queue...", 2)
        status_msg = await interaction.followup.send(embed=progress.embed)

        # Get from Radarr
        progress.update(0, ":hourglass: Checking Radarr queue...")
        await status_msg.edit(embed=progress.embed)
        radarr_queue = await self._get_radarr_queue()

        # Get from Sonarr
        progress.update(1, ":hourglass: Checking Sonarr queue...")
        await status_msg.edit(embed=progress.embed)
        sonarr_queue = await self._get_sonarr_queue()

        # Build final embed
        embed = progress.complete(":arrow_down: Download Queue", "Queue retrieved")
        embed.clear_fields()

        if radarr_queue:
            queue_text = "\n".join([f"• {item['title']} ({item.get('progress', 0):.0f}%)" for item in radarr_queue[:5]])
            embed.add_field(name=":movie_camera: Movies", value=queue_text or "No active downloads", inline=False)

        if sonarr_queue:
            queue_text = "\n".join([f"• {item['title']} ({item.get('progress', 0):.0f}%)" for item in sonarr_queue[:5]])
            embed.add_field(name=":tv: TV Shows", value=queue_text or "No active downloads", inline=False)

        if not radarr_queue and not sonarr_queue:
            embed.description = "No active downloads"

        await status_msg.edit(embed=embed)

    @app_commands.command(name="download", description="Request a movie or TV show")
    @app_commands.describe(
        title="Title to search for",
        media_type="Type of media"
    )
    @app_commands.choices(media_type=[
        app_commands.Choice(name="Movie", value="movie"),
        app_commands.Choice(name="TV Show", value="tv"),
    ])
    async def download(
        self,
        interaction: discord.Interaction,
        title: str,
        media_type: str = "movie"
    ):
        """Request a movie or TV show via Jellyseerr."""
        await interaction.response.defer()

        # Search Jellyseerr
        results = await self._search_jellyseerr(title, media_type)

        if not results:
            await interaction.followup.send(f":x: No results found for: {title}")
            return

        # Show top result
        top = results[0]
        embed = discord.Embed(
            title=f":mag: Found: {top.get('title', title)}",
            description=top.get('overview', '')[:500],
            color=discord.Color.blue()
        )

        if top.get('posterPath'):
            embed.set_thumbnail(url=f"https://image.tmdb.org/t/p/w500{top['posterPath']}")

        embed.add_field(name="Year", value=top.get('releaseDate', 'Unknown')[:4], inline=True)
        embed.add_field(name="Type", value=media_type.title(), inline=True)
        embed.set_footer(text="React with :thumbsup: to request this title")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="search", description="Search for media without downloading")
    @app_commands.describe(
        query="Search query",
        media_type="Type of media"
    )
    @app_commands.choices(media_type=[
        app_commands.Choice(name="Movie", value="movie"),
        app_commands.Choice(name="TV Show", value="tv"),
        app_commands.Choice(name="Both", value="multi"),
    ])
    async def search(
        self,
        interaction: discord.Interaction,
        query: str,
        media_type: str = "multi"
    ):
        """Search for media without requesting."""
        await interaction.response.defer()

        results = await self._search_jellyseerr(query, media_type)

        if not results:
            await interaction.followup.send(f":x: No results found for: {query}")
            return

        embed = discord.Embed(
            title=f":mag: Search Results: {query}",
            color=discord.Color.blue()
        )

        for i, item in enumerate(results[:5], 1):
            status = ":white_check_mark:" if item.get('mediaInfo') else ":grey_question:"
            embed.add_field(
                name=f"{i}. {item.get('title', 'Unknown')}",
                value=f"{status} {item.get('releaseDate', 'Unknown')[:4] if item.get('releaseDate') else 'Unknown'}",
                inline=False
            )

        await interaction.followup.send(embed=embed)

    # ==================== Library Commands ====================

    library_group = app_commands.Group(name="library", description="Media library commands")

    @library_group.command(name="movies", description="List movies in library")
    @app_commands.describe(limit="Number of movies to show")
    async def library_movies(self, interaction: discord.Interaction, limit: int = 10):
        """List movies in the Radarr library."""
        await interaction.response.defer()

        movies = await self._get_radarr_movies(limit)

        if not movies:
            await interaction.followup.send(":information_source: No movies found")
            return

        embed = discord.Embed(
            title=":movie_camera: Movie Library",
            color=discord.Color.blue()
        )

        for movie in movies[:limit]:
            status = ":white_check_mark:" if movie.get('hasFile') else ":hourglass:"
            embed.add_field(
                name=f"{status} {movie.get('title', 'Unknown')}",
                value=f"{movie.get('year', 'Unknown')}",
                inline=True
            )

        await interaction.followup.send(embed=embed)

    @library_group.command(name="shows", description="List TV shows in library")
    @app_commands.describe(limit="Number of shows to show")
    async def library_shows(self, interaction: discord.Interaction, limit: int = 10):
        """List TV shows in the Sonarr library."""
        await interaction.response.defer()

        shows = await self._get_sonarr_shows(limit)

        if not shows:
            await interaction.followup.send(":information_source: No shows found")
            return

        embed = discord.Embed(
            title=":tv: TV Show Library",
            color=discord.Color.blue()
        )

        for show in shows[:limit]:
            status = ":white_check_mark:" if show.get('statistics', {}).get('percentOfEpisodes', 0) == 100 else ":hourglass:"
            embed.add_field(
                name=f"{status} {show.get('title', 'Unknown')}",
                value=f"Episodes: {show.get('statistics', {}).get('episodeFileCount', 0)}",
                inline=True
            )

        await interaction.followup.send(embed=embed)

    @library_group.command(name="stats", description="Show library statistics")
    async def library_stats(self, interaction: discord.Interaction):
        """Show media library statistics."""
        await interaction.response.defer()

        embed = discord.Embed(
            title=":bar_chart: Library Statistics",
            color=discord.Color.blue()
        )

        # Get Radarr stats
        movies = await self._get_radarr_movies(limit=9999)
        if movies:
            total_movies = len(movies)
            available = sum(1 for m in movies if m.get('hasFile'))
            embed.add_field(
                name=":movie_camera: Movies",
                value=f"Total: {total_movies}\nAvailable: {available}",
                inline=True
            )

        # Get Sonarr stats
        shows = await self._get_sonarr_shows(limit=9999)
        if shows:
            total_shows = len(shows)
            total_episodes = sum(s.get('statistics', {}).get('episodeFileCount', 0) for s in shows)
            embed.add_field(
                name=":tv: TV Shows",
                value=f"Shows: {total_shows}\nEpisodes: {total_episodes}",
                inline=True
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="recent", description="Show recently added media")
    @app_commands.describe(media_type="Type of media")
    @app_commands.choices(media_type=[
        app_commands.Choice(name="Movies", value="movie"),
        app_commands.Choice(name="TV Shows", value="tv"),
        app_commands.Choice(name="Both", value="both"),
    ])
    async def recent(self, interaction: discord.Interaction, media_type: str = "both"):
        """Show recently added media."""
        await interaction.response.defer()

        embed = discord.Embed(
            title=":new: Recently Added",
            color=discord.Color.green()
        )

        if media_type in ["movie", "both"]:
            # Get recently added movies
            embed.add_field(
                name=":movie_camera: Movies",
                value="Feature coming soon",
                inline=False
            )

        if media_type in ["tv", "both"]:
            # Get recently added shows
            embed.add_field(
                name=":tv: TV Shows",
                value="Feature coming soon",
                inline=False
            )

        await interaction.followup.send(embed=embed)

    # ==================== API Helpers ====================

    async def _get_radarr_queue(self) -> List[dict]:
        """Get Radarr download queue."""
        url = f"{self.config.api.radarr_url}/api/v3/queue"
        data = await self.bot.api_get(url, 'radarr')
        return data.get('records', []) if data else []

    async def _get_sonarr_queue(self) -> List[dict]:
        """Get Sonarr download queue."""
        url = f"{self.config.api.sonarr_url}/api/v3/queue"
        data = await self.bot.api_get(url, 'sonarr')
        return data.get('records', []) if data else []

    async def _search_jellyseerr(self, query: str, media_type: str = "multi") -> List[dict]:
        """Search Jellyseerr for media."""
        url = f"{self.config.api.jellyseerr_url}/api/v1/search?query={query}&page=1&language=en"
        data = await self.bot.api_get(url, 'jellyseerr')

        if not data:
            return []

        results = data.get('results', [])

        if media_type == "movie":
            return [r for r in results if r.get('mediaType') == 'movie']
        elif media_type == "tv":
            return [r for r in results if r.get('mediaType') == 'tv']
        return results

    async def _get_radarr_movies(self, limit: int = 10) -> List[dict]:
        """Get movies from Radarr."""
        url = f"{self.config.api.radarr_url}/api/v3/movie"
        data = await self.bot.api_get(url, 'radarr')
        return (data or [])[:limit]

    async def _get_sonarr_shows(self, limit: int = 10) -> List[dict]:
        """Get shows from Sonarr."""
        url = f"{self.config.api.sonarr_url}/api/v3/series"
        data = await self.bot.api_get(url, 'sonarr')
        return (data or [])[:limit]


async def setup(bot: 'SentinelBot'):
    """Load the Media cog."""
    await bot.add_cog(MediaCog(bot))
