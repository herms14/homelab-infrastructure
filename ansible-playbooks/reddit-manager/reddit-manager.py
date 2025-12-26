#!/usr/bin/env python3
"""
Reddit Manager API for Glance Dashboard
Manages subreddit list and fetches posts with thumbnails
Supports grouped view by subreddit and sorting options
"""

import os
import json
import html
import requests
from flask import Flask, jsonify, request, Response
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

app = Flask(__name__)

# Configuration
DATA_DIR = os.getenv("DATA_DIR", "/app/data")
SUBREDDITS_FILE = os.path.join(DATA_DIR, "subreddits.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
POSTS_PER_SUBREDDIT = int(os.getenv("POSTS_PER_SUBREDDIT", "10"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes

# Default subreddits
DEFAULT_SUBREDDITS = ["homelab", "selfhosted", "linux", "devops", "kubernetes", "docker"]
DEFAULT_SETTINGS = {"sort": "hot", "view": "grouped"}  # sort: hot/new/top, view: grouped/combined

# Cache for Reddit API responses
_cache = {}
_cache_times = {}


def load_subreddits():
    """Load subreddits from JSON file"""
    try:
        if os.path.exists(SUBREDDITS_FILE):
            with open(SUBREDDITS_FILE, "r") as f:
                data = json.load(f)
                return data.get("subreddits", DEFAULT_SUBREDDITS)
    except Exception as e:
        print(f"Error loading subreddits: {e}")
    return DEFAULT_SUBREDDITS.copy()


def save_subreddits(subreddits):
    """Save subreddits to JSON file"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SUBREDDITS_FILE, "w") as f:
        json.dump({"subreddits": subreddits}, f, indent=2)


def load_settings():
    """Load settings from JSON file"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                return {**DEFAULT_SETTINGS, **data}
    except Exception as e:
        print(f"Error loading settings: {e}")
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    """Save settings to JSON file"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def get_cached(key, fetch_func, ttl=CACHE_TTL):
    """Simple cache with TTL"""
    now = time.time()
    if key in _cache and now - _cache_times.get(key, 0) < ttl:
        return _cache[key]

    result = fetch_func()
    _cache[key] = result
    _cache_times[key] = now
    return result


def fetch_subreddit_posts(subreddit, sort="hot", limit=POSTS_PER_SUBREDDIT):
    """Fetch posts from a subreddit using Reddit JSON API"""
    try:
        # Map sort option to Reddit endpoint
        sort_map = {"hot": "hot", "new": "new", "top": "top"}
        sort_endpoint = sort_map.get(sort, "hot")

        url = f"https://www.reddit.com/r/{subreddit}/{sort_endpoint}.json?limit={limit}"
        if sort == "top":
            url += "&t=day"  # Top posts from today

        headers = {
            "User-Agent": "GlanceRedditManager/1.0 (homelab dashboard)"
        }
        response = requests.get(url, headers=headers, timeout=5)  # Reduced timeout
        response.raise_for_status()
        data = response.json()

        posts = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})

            # Get thumbnail - filter out placeholders
            thumbnail = post.get("thumbnail", "")
            if thumbnail in ["self", "default", "nsfw", "spoiler", "", None]:
                thumbnail = None

            # Try to get preview image if no thumbnail
            if not thumbnail:
                preview = post.get("preview", {})
                images = preview.get("images", [])
                if images:
                    source = images[0].get("source", {})
                    thumbnail = source.get("url", "").replace("&amp;", "&")

            # Clean up HTML entities in thumbnail URL
            if thumbnail:
                thumbnail = html.unescape(thumbnail)

            posts.append({
                "id": post.get("id"),
                "title": post.get("title", ""),
                "url": f"https://reddit.com{post.get('permalink', '')}",
                "score": post.get("score", 0),
                "comments": post.get("num_comments", 0),
                "subreddit": subreddit,
                "thumbnail": thumbnail,
                "created": post.get("created_utc", 0),
                "author": post.get("author", ""),
                "is_self": post.get("is_self", False),
            })

        return posts
    except Exception as e:
        print(f"Error fetching r/{subreddit}: {e}")
        return []


# API Routes

@app.route("/api/subreddits", methods=["GET"])
def get_subreddits():
    """Get list of configured subreddits"""
    subreddits = load_subreddits()
    return jsonify({"subreddits": subreddits})


@app.route("/api/subreddits", methods=["POST"])
def add_subreddit():
    """Add a new subreddit"""
    data = request.get_json() or {}
    name = data.get("name", "").strip().lower()

    if not name:
        return jsonify({"error": "Subreddit name required"}), 400

    # Remove r/ prefix if present
    if name.startswith("r/"):
        name = name[2:]

    # Validate subreddit exists
    try:
        url = f"https://www.reddit.com/r/{name}/about.json"
        headers = {"User-Agent": "GlanceRedditManager/1.0"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 404:
            return jsonify({"error": f"Subreddit r/{name} not found"}), 404
    except Exception as e:
        print(f"Warning: Could not validate subreddit: {e}")

    subreddits = load_subreddits()
    if name in subreddits:
        return jsonify({"error": f"r/{name} already exists"}), 409

    subreddits.append(name)
    save_subreddits(subreddits)

    # Clear cache
    _cache.clear()
    _cache_times.clear()

    return jsonify({"success": True, "subreddits": subreddits})


@app.route("/api/subreddits/<name>", methods=["DELETE"])
def remove_subreddit(name):
    """Remove a subreddit"""
    name = name.strip().lower()
    if name.startswith("r/"):
        name = name[2:]

    subreddits = load_subreddits()
    if name not in subreddits:
        return jsonify({"error": f"r/{name} not found"}), 404

    subreddits.remove(name)
    save_subreddits(subreddits)

    # Clear cache
    _cache.clear()
    _cache_times.clear()

    return jsonify({"success": True, "subreddits": subreddits})


@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Get current settings"""
    settings = load_settings()
    return jsonify(settings)


@app.route("/api/settings", methods=["POST"])
def update_settings():
    """Update settings"""
    data = request.get_json() or {}
    settings = load_settings()

    if "sort" in data and data["sort"] in ["hot", "new", "top"]:
        settings["sort"] = data["sort"]
    if "view" in data and data["view"] in ["grouped", "combined"]:
        settings["view"] = data["view"]

    save_settings(settings)

    # Clear cache when settings change
    _cache.clear()
    _cache_times.clear()

    return jsonify({"success": True, "settings": settings})


@app.route("/api/feed", methods=["GET"])
def get_combined_feed():
    """Get combined feed from all subreddits"""
    subreddits = load_subreddits()
    settings = load_settings()
    sort = request.args.get("sort", settings["sort"])
    view = request.args.get("view", settings["view"])

    def fetch_all():
        all_posts = []

        # Fetch all subreddits in parallel for faster response
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_sub = {
                executor.submit(fetch_subreddit_posts, sub, sort): sub
                for sub in subreddits
            }
            for future in as_completed(future_to_sub, timeout=15):
                try:
                    posts = future.result()
                    all_posts.extend(posts)
                except Exception as e:
                    sub = future_to_sub[future]
                    print(f"Error fetching r/{sub}: {e}")

        # Sort based on preference
        if sort == "new":
            all_posts.sort(key=lambda x: x["created"], reverse=True)
        elif sort == "top":
            all_posts.sort(key=lambda x: x["score"], reverse=True)
        else:  # hot - keep Reddit's order but interleave
            all_posts.sort(key=lambda x: x["score"], reverse=True)

        return all_posts[:50]  # Limit to top 50

    cache_key = f"feed_all_{sort}_{view}"
    posts = get_cached(cache_key, fetch_all)

    if view == "grouped":
        # Group posts by subreddit - return as array for easy templating
        groups = []
        for sub in subreddits:
            sub_posts = [p for p in posts if p["subreddit"] == sub][:10]
            if sub_posts:  # Only include subreddits with posts
                groups.append({
                    "name": sub,
                    "posts": sub_posts
                })
        return jsonify({
            "groups": groups,
            "subreddits": subreddits,
            "settings": {"sort": sort, "view": view}
        })
    else:
        return jsonify({
            "posts": posts,
            "subreddits": subreddits,
            "settings": {"sort": sort, "view": view}
        })


@app.route("/api/feed/<subreddit>", methods=["GET"])
def get_subreddit_feed(subreddit):
    """Get feed from a specific subreddit"""
    subreddit = subreddit.strip().lower()
    settings = load_settings()
    sort = request.args.get("sort", settings["sort"])

    def fetch():
        return fetch_subreddit_posts(subreddit, sort=sort, limit=20)

    posts = get_cached(f"feed_{subreddit}_{sort}", fetch)
    return jsonify({"posts": posts, "subreddit": subreddit})


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})


# Management UI

@app.route("/", methods=["GET"])
def management_ui():
    """Serve the management UI"""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reddit Manager - Glance Dashboard</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 700px;
            margin: 0 auto;
        }
        h1 {
            color: #ff4500;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        h1 svg {
            width: 32px;
            height: 32px;
        }
        .subtitle {
            color: #888;
            margin-bottom: 30px;
        }
        .settings-section {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .settings-section h2 {
            font-size: 16px;
            color: #ff4500;
            margin-bottom: 15px;
        }
        .settings-row {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
        .setting-group {
            flex: 1;
            min-width: 200px;
        }
        .setting-group label {
            display: block;
            font-size: 12px;
            color: #888;
            margin-bottom: 8px;
            text-transform: uppercase;
        }
        .toggle-group {
            display: flex;
            gap: 8px;
        }
        .toggle-btn {
            flex: 1;
            padding: 10px 16px;
            border: 2px solid #333;
            border-radius: 8px;
            background: transparent;
            color: #888;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .toggle-btn:hover {
            border-color: #ff4500;
            color: #fff;
        }
        .toggle-btn.active {
            background: #ff4500;
            border-color: #ff4500;
            color: #fff;
        }
        .add-form {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .add-form input {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #333;
            border-radius: 8px;
            background: #16213e;
            color: #fff;
            font-size: 16px;
            outline: none;
            transition: border-color 0.2s;
        }
        .add-form input:focus {
            border-color: #ff4500;
        }
        .add-form input::placeholder {
            color: #666;
        }
        .add-form button {
            padding: 12px 24px;
            background: #ff4500;
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        .add-form button:hover {
            background: #ff5722;
        }
        .add-form button:disabled {
            background: #555;
            cursor: not-allowed;
        }
        .subreddit-list {
            background: #16213e;
            border-radius: 12px;
            overflow: hidden;
        }
        .subreddit-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            border-bottom: 1px solid #333;
            transition: background 0.2s;
        }
        .subreddit-item:last-child {
            border-bottom: none;
        }
        .subreddit-item:hover {
            background: rgba(255, 69, 0, 0.1);
        }
        .subreddit-name {
            font-size: 16px;
            font-weight: 500;
        }
        .subreddit-name a {
            color: #ff4500;
            text-decoration: none;
        }
        .subreddit-name a:hover {
            text-decoration: underline;
        }
        .remove-btn {
            background: #dc3545;
            color: #fff;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.2s;
        }
        .remove-btn:hover {
            background: #c82333;
        }
        .message {
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
        .message.success {
            background: rgba(40, 167, 69, 0.2);
            border: 1px solid #28a745;
            color: #28a745;
        }
        .message.error {
            background: rgba(220, 53, 69, 0.2);
            border: 1px solid #dc3545;
            color: #dc3545;
        }
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #888;
        }
        .back-link {
            display: inline-block;
            margin-top: 20px;
            color: #888;
            text-decoration: none;
        }
        .back-link:hover {
            color: #ff4500;
        }
        .section-title {
            font-size: 14px;
            color: #888;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>
            <svg viewBox="0 0 24 24" fill="#ff4500">
                <path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 0 0 .029-.463.33.33 0 0 0-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 0 0-.232-.095z"/>
            </svg>
            Reddit Manager
        </h1>
        <p class="subtitle">Manage subreddits for your Glance dashboard</p>

        <div id="message" class="message"></div>

        <div class="settings-section">
            <h2>Display Settings</h2>
            <div class="settings-row">
                <div class="setting-group">
                    <label>Sort By</label>
                    <div class="toggle-group" id="sort-toggle">
                        <button class="toggle-btn" data-value="hot">Hot</button>
                        <button class="toggle-btn" data-value="new">New</button>
                        <button class="toggle-btn" data-value="top">Top</button>
                    </div>
                </div>
                <div class="setting-group">
                    <label>View Mode</label>
                    <div class="toggle-group" id="view-toggle">
                        <button class="toggle-btn" data-value="grouped">By Subreddit</button>
                        <button class="toggle-btn" data-value="combined">Combined</button>
                    </div>
                </div>
            </div>
        </div>

        <p class="section-title">Subreddits</p>

        <form class="add-form" onsubmit="addSubreddit(event)">
            <input type="text" id="subreddit-input" placeholder="Enter subreddit name (e.g., programming)" autocomplete="off">
            <button type="submit" id="add-btn">Add</button>
        </form>

        <div id="subreddit-list" class="subreddit-list">
            <div class="loading">Loading...</div>
        </div>

        <a href="https://glance.hrmsmrflrii.xyz" class="back-link">&larr; Back to Glance Dashboard</a>
    </div>

    <script>
        const API_BASE = '';
        let currentSettings = { sort: 'hot', view: 'grouped' };

        function showMessage(text, type) {
            const msg = document.getElementById('message');
            msg.textContent = text;
            msg.className = 'message ' + type;
            msg.style.display = 'block';
            setTimeout(() => { msg.style.display = 'none'; }, 3000);
        }

        async function loadSettings() {
            try {
                const response = await fetch(API_BASE + '/api/settings');
                currentSettings = await response.json();
                updateToggleUI();
            } catch (error) {
                console.error('Error loading settings:', error);
            }
        }

        function updateToggleUI() {
            // Update sort toggle
            document.querySelectorAll('#sort-toggle .toggle-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.value === currentSettings.sort);
            });
            // Update view toggle
            document.querySelectorAll('#view-toggle .toggle-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.value === currentSettings.view);
            });
        }

        async function updateSetting(key, value) {
            try {
                const response = await fetch(API_BASE + '/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ [key]: value })
                });
                const data = await response.json();
                if (response.ok) {
                    currentSettings = data.settings;
                    updateToggleUI();
                    showMessage(`Updated ${key} to ${value}`, 'success');
                }
            } catch (error) {
                console.error('Error updating settings:', error);
                showMessage('Failed to update settings', 'error');
            }
        }

        // Set up toggle listeners
        document.querySelectorAll('#sort-toggle .toggle-btn').forEach(btn => {
            btn.addEventListener('click', () => updateSetting('sort', btn.dataset.value));
        });
        document.querySelectorAll('#view-toggle .toggle-btn').forEach(btn => {
            btn.addEventListener('click', () => updateSetting('view', btn.dataset.value));
        });

        async function loadSubreddits() {
            try {
                const response = await fetch(API_BASE + '/api/subreddits');
                const data = await response.json();
                renderSubreddits(data.subreddits);
            } catch (error) {
                console.error('Error loading subreddits:', error);
                document.getElementById('subreddit-list').innerHTML =
                    '<div class="empty-state">Error loading subreddits</div>';
            }
        }

        function renderSubreddits(subreddits) {
            const list = document.getElementById('subreddit-list');
            if (subreddits.length === 0) {
                list.innerHTML = '<div class="empty-state">No subreddits configured. Add one above!</div>';
                return;
            }

            list.innerHTML = subreddits.map(sub => `
                <div class="subreddit-item" data-name="${sub}">
                    <span class="subreddit-name">
                        <a href="https://reddit.com/r/${sub}" target="_blank">r/${sub}</a>
                    </span>
                    <button class="remove-btn" onclick="removeSubreddit('${sub}')">Remove</button>
                </div>
            `).join('');
        }

        async function addSubreddit(event) {
            event.preventDefault();
            const input = document.getElementById('subreddit-input');
            const btn = document.getElementById('add-btn');
            const name = input.value.trim();

            if (!name) return;

            btn.disabled = true;
            btn.textContent = 'Adding...';

            try {
                const response = await fetch(API_BASE + '/api/subreddits', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name })
                });

                const data = await response.json();

                if (response.ok) {
                    showMessage(`Added r/${name}`, 'success');
                    input.value = '';
                    renderSubreddits(data.subreddits);
                } else {
                    showMessage(data.error || 'Failed to add subreddit', 'error');
                }
            } catch (error) {
                console.error('Error adding subreddit:', error);
                showMessage('Failed to add subreddit', 'error');
            }

            btn.disabled = false;
            btn.textContent = 'Add';
        }

        async function removeSubreddit(name) {
            if (!confirm(`Remove r/${name}?`)) return;

            try {
                const response = await fetch(API_BASE + '/api/subreddits/' + name, {
                    method: 'DELETE'
                });

                const data = await response.json();

                if (response.ok) {
                    showMessage(`Removed r/${name}`, 'success');
                    renderSubreddits(data.subreddits);
                } else {
                    showMessage(data.error || 'Failed to remove subreddit', 'error');
                }
            } catch (error) {
                console.error('Error removing subreddit:', error);
                showMessage('Failed to remove subreddit', 'error');
            }
        }

        // Load on page load
        loadSettings();
        loadSubreddits();
    </script>
</body>
</html>
"""
    return Response(html_content, mimetype="text/html")


if __name__ == "__main__":
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Initialize with defaults if no file exists
    if not os.path.exists(SUBREDDITS_FILE):
        save_subreddits(DEFAULT_SUBREDDITS)
        print(f"Initialized with default subreddits: {DEFAULT_SUBREDDITS}")

    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        print(f"Initialized with default settings: {DEFAULT_SETTINGS}")

    print("Starting Reddit Manager API on port 5053")
    app.run(host="0.0.0.0", port=5053, debug=False)
