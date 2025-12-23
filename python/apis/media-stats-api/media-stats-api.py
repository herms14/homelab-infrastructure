#!/usr/bin/env python3
"""
Enhanced Media Stats API
Combines Radarr and Sonarr stats, recent downloads, and download queue for Glance dashboard.

Endpoints:
- /api/stats - Stats tiles (6-tile grid)
- /api/recent - Top 5 most recent downloads (movies + episodes) with posters
- /api/queue - Currently downloading items with progress bars
- /health - Health check
"""

import os
import re
import requests
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configuration from environment variables
RADARR_URL = os.getenv('RADARR_URL', 'http://192.168.40.11:7878')
RADARR_API_KEY = os.getenv('RADARR_API_KEY', '')
SONARR_URL = os.getenv('SONARR_URL', 'http://192.168.40.11:8989')
SONARR_API_KEY = os.getenv('SONARR_API_KEY', '')


def fetch_radarr_stats():
    """Fetch all Radarr statistics."""
    headers = {'X-Api-Key': RADARR_API_KEY}
    stats = {'wanted': 0, 'downloading': 0, 'downloaded': 0}

    try:
        # Wanted movies
        resp = requests.get(f'{RADARR_URL}/api/v3/wanted/missing',
                           headers=headers, params={'pageSize': 1}, timeout=5)
        if resp.ok:
            stats['wanted'] = resp.json().get('totalRecords', 0)

        # Downloading
        resp = requests.get(f'{RADARR_URL}/api/v3/queue',
                           headers=headers, params={'pageSize': 1}, timeout=5)
        if resp.ok:
            stats['downloading'] = resp.json().get('totalRecords', 0)

        # Downloaded (movies with files)
        resp = requests.get(f'{RADARR_URL}/api/v3/movie', headers=headers, timeout=10)
        if resp.ok:
            movies = resp.json()
            stats['downloaded'] = sum(1 for m in movies if m.get('hasFile', False))

    except requests.RequestException as e:
        print(f"Radarr error: {e}")

    return stats


def fetch_sonarr_stats():
    """Fetch all Sonarr statistics."""
    headers = {'X-Api-Key': SONARR_API_KEY}
    stats = {'wanted': 0, 'downloading': 0, 'downloaded': 0}

    try:
        # Wanted episodes
        resp = requests.get(f'{SONARR_URL}/api/v3/wanted/missing',
                           headers=headers, params={'pageSize': 1}, timeout=5)
        if resp.ok:
            stats['wanted'] = resp.json().get('totalRecords', 0)

        # Downloading
        resp = requests.get(f'{SONARR_URL}/api/v3/queue',
                           headers=headers, params={'pageSize': 1}, timeout=5)
        if resp.ok:
            stats['downloading'] = resp.json().get('totalRecords', 0)

        # Downloaded episodes
        resp = requests.get(f'{SONARR_URL}/api/v3/series', headers=headers, timeout=10)
        if resp.ok:
            series = resp.json()
            stats['downloaded'] = sum(
                s.get('statistics', {}).get('episodeFileCount', 0) for s in series
            )

    except requests.RequestException as e:
        print(f"Sonarr error: {e}")

    return stats


def get_poster_url(images, fallback='movie'):
    """Extract poster URL from images array."""
    for img in images:
        if img.get('coverType') == 'poster':
            return img.get('remoteUrl', '')
    return ''


def fetch_recent_downloads():
    """Fetch the 5 most recent downloads (movies + episodes combined)."""
    recent = []
    seen_titles = set()  # Avoid duplicates

    # Fetch movies with files from Radarr
    try:
        headers = {'X-Api-Key': RADARR_API_KEY}
        resp = requests.get(f'{RADARR_URL}/api/v3/movie', headers=headers, timeout=10)
        if resp.ok:
            movies = resp.json()
            for m in movies:
                if m.get('hasFile') and m.get('movieFile'):
                    movie_file = m.get('movieFile', {})
                    date_added = movie_file.get('dateAdded', '')
                    if date_added:
                        title_key = f"movie_{m.get('title')}"
                        if title_key not in seen_titles:
                            seen_titles.add(title_key)
                            recent.append({
                                'type': 'movie',
                                'title': m.get('title', 'Unknown'),
                                'year': m.get('year', ''),
                                'poster': get_poster_url(m.get('images', [])),
                                'date_added': date_added,
                                'quality': movie_file.get('quality', {}).get('quality', {}).get('name', 'Unknown')
                            })
    except requests.RequestException as e:
        print(f"Radarr recent error: {e}")

    # Fetch episode files from Sonarr
    try:
        headers = {'X-Api-Key': SONARR_API_KEY}
        # Get all series
        resp = requests.get(f'{SONARR_URL}/api/v3/series', headers=headers, timeout=10)
        if resp.ok:
            series_list = resp.json()

            # Collect all episode files with series info
            all_files = []
            for series in series_list:
                series_id = series['id']
                files_resp = requests.get(f'{SONARR_URL}/api/v3/episodefile',
                                         headers=headers,
                                         params={'seriesId': series_id},
                                         timeout=10)
                if files_resp.ok:
                    files = files_resp.json()
                    for f in files:
                        all_files.append({
                            'series': series,
                            'file': f
                        })

            # Sort by dateAdded and get most recent
            all_files.sort(key=lambda x: x['file'].get('dateAdded', ''), reverse=True)

            for item in all_files[:10]:
                series = item['series']
                f = item['file']
                date_added = f.get('dateAdded', '')
                relative_path = f.get('relativePath', '')

                # Parse episode info from path
                ep_info = ''
                match = re.search(r'S(\d{2})E(\d{2})', relative_path, re.IGNORECASE)
                if match:
                    ep_info = f"S{match.group(1)}E{match.group(2)}"

                title_key = f"episode_{series.get('title')}_{ep_info}"
                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    recent.append({
                        'type': 'episode',
                        'title': series.get('title', 'Unknown'),
                        'episode': ep_info,
                        'poster': get_poster_url(series.get('images', [])),
                        'date_added': date_added,
                        'quality': f.get('quality', {}).get('quality', {}).get('name', 'Unknown')
                    })
    except requests.RequestException as e:
        print(f"Sonarr recent error: {e}")

    # Sort by date_added descending and return top 5
    recent.sort(key=lambda x: x.get('date_added', ''), reverse=True)
    return recent[:5]


def fetch_download_queue():
    """Fetch currently downloading items with progress."""
    queue = []

    # Radarr queue
    try:
        headers = {'X-Api-Key': RADARR_API_KEY}
        resp = requests.get(f'{RADARR_URL}/api/v3/queue/details',
                           headers=headers,
                           params={'includeMovie': 'true'},
                           timeout=10)
        if resp.ok:
            items = resp.json()
            for item in items:
                if item.get('trackedDownloadState') in ['downloading', 'importPending', 'importing']:
                    movie = item.get('movie', {})
                    size = item.get('size', 0)
                    sizeleft = item.get('sizeleft', 0)
                    progress = 0
                    if size > 0:
                        progress = round((size - sizeleft) / size * 100, 1)
                    elif item.get('status') == 'completed':
                        progress = 100

                    queue.append({
                        'type': 'movie',
                        'title': movie.get('title', item.get('title', 'Unknown')),
                        'poster': get_poster_url(movie.get('images', [])),
                        'progress': progress,
                        'status': item.get('trackedDownloadState', 'unknown'),
                        'eta': item.get('timeleft', '--:--:--'),
                        'quality': item.get('quality', {}).get('quality', {}).get('name', 'Unknown'),
                        'client': item.get('downloadClient', 'Unknown')
                    })
    except requests.RequestException as e:
        print(f"Radarr queue error: {e}")

    # Sonarr queue
    try:
        headers = {'X-Api-Key': SONARR_API_KEY}
        resp = requests.get(f'{SONARR_URL}/api/v3/queue/details',
                           headers=headers,
                           params={'includeSeries': 'true', 'includeEpisode': 'true'},
                           timeout=10)
        if resp.ok:
            items = resp.json()
            for item in items:
                if item.get('trackedDownloadState') in ['downloading', 'importPending', 'importing']:
                    series = item.get('series', {})
                    episode = item.get('episode', {})
                    size = item.get('size', 0)
                    sizeleft = item.get('sizeleft', 0)
                    progress = 0
                    if size > 0:
                        progress = round((size - sizeleft) / size * 100, 1)
                    elif item.get('status') == 'completed':
                        progress = 100

                    ep_info = f"S{episode.get('seasonNumber', 0):02d}E{episode.get('episodeNumber', 0):02d}"

                    queue.append({
                        'type': 'episode',
                        'title': series.get('title', 'Unknown'),
                        'episode': ep_info,
                        'poster': get_poster_url(series.get('images', [])),
                        'progress': progress,
                        'status': item.get('trackedDownloadState', 'unknown'),
                        'eta': item.get('timeleft', '--:--:--'),
                        'quality': item.get('quality', {}).get('quality', {}).get('name', 'Unknown'),
                        'client': item.get('downloadClient', 'Unknown')
                    })
    except requests.RequestException as e:
        print(f"Sonarr queue error: {e}")

    # Sort: active downloads first (by progress desc), then pending imports
    # Filter out 100% completed items that are just waiting for import
    active = [q for q in queue if q.get('status') == 'downloading' and q.get('progress', 0) < 100]
    pending = [q for q in queue if q.get('status') != 'downloading' or q.get('progress', 0) >= 100]

    # Sort active by progress descending
    active.sort(key=lambda x: x.get('progress', 0), reverse=True)
    pending.sort(key=lambda x: x.get('progress', 0), reverse=True)

    # Return top 10: prioritize active downloads
    result = active[:10]
    if len(result) < 10:
        result.extend(pending[:10 - len(result)])

    return result


@app.route('/api/stats')
def get_stats():
    """Return combined media stats for Glance dashboard grid."""
    radarr = fetch_radarr_stats()
    sonarr = fetch_sonarr_stats()

    return jsonify({
        'stats': [
            {'label': 'WANTED MOVIES', 'value': radarr['wanted'], 'color': '#f59e0b', 'icon': 'movie'},
            {'label': 'MOVIES DOWNLOADING', 'value': radarr['downloading'], 'color': '#3b82f6', 'icon': 'download'},
            {'label': 'MOVIES DOWNLOADED', 'value': radarr['downloaded'], 'color': '#22c55e', 'icon': 'check'},
            {'label': 'WANTED EPISODES', 'value': sonarr['wanted'], 'color': '#ef4444', 'icon': 'tv'},
            {'label': 'EPISODES DOWNLOADING', 'value': sonarr['downloading'], 'color': '#8b5cf6', 'icon': 'download'},
            {'label': 'EPISODES DOWNLOADED', 'value': sonarr['downloaded'], 'color': '#06b6d4', 'icon': 'check'}
        ],
        'radarr': radarr,
        'sonarr': sonarr
    })


@app.route('/api/recent')
def get_recent():
    """Return 5 most recent downloads (movies + episodes) with posters."""
    recent = fetch_recent_downloads()
    return jsonify({
        'items': recent,
        'count': len(recent)
    })


@app.route('/api/queue')
def get_queue():
    """Return current download queue with progress."""
    queue = fetch_download_queue()
    return jsonify({
        'items': queue,
        'count': len(queue)
    })


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5054, debug=False)
