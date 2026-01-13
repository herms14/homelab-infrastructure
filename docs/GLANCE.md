# Glance Dashboard

Glance is a self-hosted dashboard that provides a central view of all homelab services, monitoring, and media statistics. This guide explains how the Glance dashboard was built, including the custom Media Stats grid widget.

## Overview

| Component | Description |
|-----------|-------------|
| **Glance** | Main dashboard application |
| **Media Stats API** | Custom API that combines Radarr/Sonarr data |
| **Location** | LXC 200 (192.168.40.12) |
| **URL** | https://glance.hrmsmrflrii.xyz |

> **Note**: Glance runs on an LXC container with Docker. The docker-compose.yml requires `security_opt: apparmor=unconfined` due to AppArmor restrictions in LXC environments.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Glance Dashboard                             │
│                   (Port 8080)                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Home      │  │   Media     │  │   Other     │             │
│  │   Page      │  │   Page      │  │   Pages     │             │
│  └─────────────┘  └──────┬──────┘  └─────────────┘             │
│                          │                                       │
│                          ▼                                       │
│              ┌───────────────────────┐                          │
│              │   Media Stats Widget  │                          │
│              │   (custom-api type)   │                          │
│              └───────────┬───────────┘                          │
│                          │                                       │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           ▼
              ┌───────────────────────┐
              │   Media Stats API     │
              │   (Port 5054)         │
              └───────────┬───────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
   ┌─────────────────┐        ┌─────────────────┐
   │     Radarr      │        │     Sonarr      │
   │   (Port 7878)   │        │   (Port 8989)   │
   │   Movies        │        │   TV Shows      │
   └─────────────────┘        └─────────────────┘
```

## How It Works (Simple Explanation)

### The Problem

Glance's `custom-api` widget can only fetch data from ONE web address at a time. But we wanted to show 6 different statistics (3 from Radarr for movies, 3 from Sonarr for TV shows) in a nice grid layout.

### The Solution

We created a "middleman" service called **Media Stats API** that:
1. Talks to Radarr and asks "How many movies are wanted? Downloading? Downloaded?"
2. Talks to Sonarr and asks "How many episodes are wanted? Downloading? Downloaded?"
3. Combines all 6 answers into one response
4. Glance asks THIS service for all the data in one request

Think of it like ordering food: instead of calling 6 different restaurants, you call one delivery service that picks up from all of them and brings everything together.

## Components

### 1. Media Stats API

This is a small Python program that runs in a Docker container. It acts as the "middleman" between Glance and your media apps.

**What it does:**
- Connects to Radarr and Sonarr using their API keys
- Fetches statistics about your movies and TV shows
- Packages everything into a single, easy-to-read format
- Responds to Glance when asked for data

**Location:** `/opt/media-stats-api/` on docker-vm-core-utilities01

**Files:**

#### media-stats-api.py
```python
#!/usr/bin/env python3
"""
Media Stats API Aggregator
Combines Radarr and Sonarr stats into a single endpoint for Glance dashboard.
Returns all media stats in a format suitable for the 3x3 tile grid layout.
"""

import os
import requests
from flask import Flask, jsonify
from flask_cors import CORS

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
    stats = {
        'wanted': 0,
        'downloading': 0,
        'downloaded': 0
    }

    try:
        # Wanted movies
        resp = requests.get(
            f'{RADARR_URL}/api/v3/wanted/missing',
            headers=headers,
            params={'pageSize': 1},
            timeout=5
        )
        if resp.ok:
            stats['wanted'] = resp.json().get('totalRecords', 0)

        # Downloading
        resp = requests.get(
            f'{RADARR_URL}/api/v3/queue',
            headers=headers,
            params={'pageSize': 1},
            timeout=5
        )
        if resp.ok:
            stats['downloading'] = resp.json().get('totalRecords', 0)

        # Downloaded (movies with files)
        resp = requests.get(
            f'{RADARR_URL}/api/v3/movie',
            headers=headers,
            timeout=10
        )
        if resp.ok:
            movies = resp.json()
            stats['downloaded'] = sum(1 for m in movies if m.get('hasFile', False))

    except requests.RequestException as e:
        print(f"Radarr error: {e}")

    return stats


def fetch_sonarr_stats():
    """Fetch all Sonarr statistics."""
    headers = {'X-Api-Key': SONARR_API_KEY}
    stats = {
        'wanted': 0,
        'downloading': 0,
        'downloaded': 0
    }

    try:
        # Wanted episodes
        resp = requests.get(
            f'{SONARR_URL}/api/v3/wanted/missing',
            headers=headers,
            params={'pageSize': 1},
            timeout=5
        )
        if resp.ok:
            stats['wanted'] = resp.json().get('totalRecords', 0)

        # Downloading
        resp = requests.get(
            f'{SONARR_URL}/api/v3/queue',
            headers=headers,
            params={'pageSize': 1},
            timeout=5
        )
        if resp.ok:
            stats['downloading'] = resp.json().get('totalRecords', 0)

        # Downloaded episodes
        resp = requests.get(
            f'{SONARR_URL}/api/v3/series',
            headers=headers,
            timeout=10
        )
        if resp.ok:
            series = resp.json()
            stats['downloaded'] = sum(
                s.get('statistics', {}).get('episodeFileCount', 0)
                for s in series
            )

    except requests.RequestException as e:
        print(f"Sonarr error: {e}")

    return stats


@app.route('/api/stats')
def get_stats():
    """Return combined media stats for Glance dashboard grid."""
    radarr = fetch_radarr_stats()
    sonarr = fetch_sonarr_stats()

    # Return structured data for the 6-tile grid (3x2)
    return jsonify({
        'stats': [
            {
                'label': 'WANTED MOVIES',
                'value': radarr['wanted'],
                'color': '#f59e0b',
                'icon': 'movie'
            },
            {
                'label': 'MOVIES DOWNLOADING',
                'value': radarr['downloading'],
                'color': '#3b82f6',
                'icon': 'download'
            },
            {
                'label': 'MOVIES DOWNLOADED',
                'value': radarr['downloaded'],
                'color': '#22c55e',
                'icon': 'check'
            },
            {
                'label': 'WANTED EPISODES',
                'value': sonarr['wanted'],
                'color': '#ef4444',
                'icon': 'tv'
            },
            {
                'label': 'EPISODES DOWNLOADING',
                'value': sonarr['downloading'],
                'color': '#8b5cf6',
                'icon': 'download'
            },
            {
                'label': 'EPISODES DOWNLOADED',
                'value': sonarr['downloaded'],
                'color': '#06b6d4',
                'icon': 'check'
            }
        ],
        'radarr': radarr,
        'sonarr': sonarr
    })


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5054, debug=False)
```

**Code Explanation (for non-technical readers):**

1. **Lines 1-14**: Setup - loads the tools needed (Flask for web server, requests for talking to other services)

2. **Lines 16-20**: Configuration - reads the addresses and passwords for Radarr/Sonarr from environment variables (like secret settings)

3. **Lines 23-66**: `fetch_radarr_stats()` function
   - Asks Radarr three questions:
     - "How many movies do I want but don't have?" (wanted)
     - "How many movies are currently downloading?" (downloading)
     - "How many movies do I have downloaded?" (downloaded)
   - Returns the answers as numbers

4. **Lines 69-115**: `fetch_sonarr_stats()` function
   - Same as above but for TV show episodes

5. **Lines 118-166**: `get_stats()` function
   - When someone visits `/api/stats`, this runs
   - Gets data from both Radarr and Sonarr
   - Packages it into a nice format with labels and colors
   - Colors are in "hex" format (like #f59e0b for amber/orange)

6. **Lines 169-172**: Health check - a simple "I'm alive" response for monitoring

### 2. Glance Configuration Update Script

This Python script updates the Glance dashboard configuration to use the new grid layout.

**Location:** `temp-media-fix.py` (run on docker-vm-core-utilities01)

```python
import yaml

with open("/opt/glance/config/glance.yml", "r") as f:
    config = yaml.safe_load(f)

# Media Stats Grid Template - 3x2 compact tile layout (Pi-hole style)
# Uses inline CSS grid since external classes don't work inside widget templates
MEDIA_STATS_GRID_TEMPLATE = '''
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; padding: 4px;">
  {{ range .JSON.Array "stats" }}
  <div style="background: {{ .String "color" }}; border-radius: 8px; padding: 16px; min-height: 90px; display: flex; flex-direction: column; justify-content: center;">
    <div style="font-size: 11px; color: rgba(255,255,255,0.85); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; font-weight: 500;">
      {{ .String "label" }}
    </div>
    <div style="font-size: 32px; font-weight: bold; color: #fff;">
      {{ .Int "value" | formatNumber }}
    </div>
  </div>
  {{ end }}
</div>
'''

media_page = {
    "name": "Media",
    "columns": [
        {
            "size": "full",
            "widgets": [
                {
                    "type": "custom-api",
                    "title": "Media Stats",
                    "cache": "1m",
                    "url": "http://192.168.40.12:5054/api/stats",
                    "template": MEDIA_STATS_GRID_TEMPLATE
                },
                # ... other widgets (Recent Movies, RSS feeds, etc.)
            ]
        },
        # ... sidebar widgets
    ]
}

for i, page in enumerate(config["pages"]):
    if page.get("name") == "Media":
        config["pages"][i] = media_page
        break

with open("/opt/glance/config/glance.yml", "w") as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False, indent=2)

print("Media page updated with correct template syntax")
```

**Code Explanation (for non-technical readers):**

1. **Lines 1-4**: Opens the Glance configuration file and reads it

2. **Lines 6-21**: The HTML template for the grid
   - `display: grid` - arranges items in a grid pattern
   - `grid-template-columns: repeat(3, 1fr)` - creates 3 equal columns
   - `gap: 12px` - adds 12 pixels of space between each tile
   - `{{ range .JSON.Array "stats" }}` - loops through each stat from the API
   - Each stat becomes a colored tile with the label on top and number below

3. **Lines 23-43**: Defines the Media page structure
   - Uses the `custom-api` widget type
   - Points to our Media Stats API (`http://192.168.40.12:5054/api/stats`)
   - Caches data for 1 minute to avoid hammering the API

4. **Lines 45-52**: Finds the existing Media page and replaces it with the new one

### 3. Ansible Deployment Playbook

This automates the deployment of the Media Stats API.

**Location:** `ansible-playbooks/glance/deploy-media-stats-api.yml`

```yaml
---
# Media Stats API Deployment
# Aggregates Radarr/Sonarr statistics for Glance dashboard grid layout
#
# Usage:
#   ansible-playbook glance/deploy-media-stats-api.yml

- name: Deploy Media Stats API
  hosts: docker-vm-core-utilities01
  become: yes
  vars:
    app_path: /opt/media-stats-api
    app_port: 5054
    radarr_api_key: "YOUR_RADARR_API_KEY"
    sonarr_api_key: "YOUR_SONARR_API_KEY"

  tasks:
    - name: Create application directory
      file:
        path: "{{ app_path }}"
        state: directory
        mode: '0755'

    - name: Copy media-stats-api.py
      copy:
        src: media-stats-api.py
        dest: "{{ app_path }}/media-stats-api.py"
        mode: '0755'

    - name: Create requirements.txt
      copy:
        dest: "{{ app_path }}/requirements.txt"
        content: |
          flask>=2.0.0
          flask-cors>=3.0.0
          requests>=2.28.0
          gunicorn>=21.0.0
        mode: '0644'

    - name: Create Dockerfile
      copy:
        dest: "{{ app_path }}/Dockerfile"
        content: |
          FROM python:3.11-slim

          WORKDIR /app

          COPY requirements.txt .
          RUN pip install --no-cache-dir -r requirements.txt

          COPY media-stats-api.py .

          EXPOSE 5054

          CMD ["gunicorn", "--bind", "0.0.0.0:5054", "--workers", "2", "media-stats-api:app"]
        mode: '0644'

    - name: Create Docker Compose file
      copy:
        dest: "{{ app_path }}/docker-compose.yml"
        content: |
          services:
            media-stats-api:
              build: .
              container_name: media-stats-api
              restart: unless-stopped
              ports:
                - "{{ app_port }}:5054"
              environment:
                - RADARR_URL=http://192.168.40.11:7878
                - RADARR_API_KEY={{ radarr_api_key }}
                - SONARR_URL=http://192.168.40.11:8989
                - SONARR_API_KEY={{ sonarr_api_key }}
              healthcheck:
                test: ["CMD", "curl", "-f", "http://localhost:5054/health"]
                interval: 30s
                timeout: 10s
                retries: 3
        mode: '0644'

    - name: Build and deploy container
      community.docker.docker_compose_v2:
        project_src: "{{ app_path }}"
        state: present
        build: always

    - name: Wait for API to be ready
      uri:
        url: "http://localhost:{{ app_port }}/health"
        status_code: [200]
      register: api_status
      until: api_status.status == 200
      retries: 30
      delay: 2
```

**Playbook Explanation (for non-technical readers):**

This is like a recipe that tells Ansible (our automation tool) how to set up the Media Stats API:

1. **Create folder**: Makes a new folder at `/opt/media-stats-api`
2. **Copy Python code**: Puts the `media-stats-api.py` file in the folder
3. **Create requirements.txt**: Lists what Python libraries are needed
4. **Create Dockerfile**: Instructions for building the container (like a shipping container for software)
5. **Create docker-compose.yml**: Configuration for running the container
6. **Build and deploy**: Actually builds and starts the container
7. **Wait and verify**: Checks that the API is responding before finishing

## The Grid Layout Explained

The Media Stats widget displays 6 tiles in a 3x2 grid:

```
┌─────────────────┬─────────────────┬─────────────────┐
│  WANTED MOVIES  │MOVIES DOWNLOADING│MOVIES DOWNLOADED│
│       15        │        9        │        0        │
│    (amber)      │     (blue)      │     (green)     │
├─────────────────┼─────────────────┼─────────────────┤
│ WANTED EPISODES │EPISODES DOWNLOAD│EPISODES DOWNLOAD│
│     1,906       │       98        │        5        │
│     (red)       │    (purple)     │     (cyan)      │
└─────────────────┴─────────────────┴─────────────────┘
```

**Color meanings:**
- **Amber (#f59e0b)**: Wanted movies - movies you want but don't have yet
- **Blue (#3b82f6)**: Movies downloading - movies currently being downloaded
- **Green (#22c55e)**: Movies downloaded - movies you have
- **Red (#ef4444)**: Wanted episodes - TV episodes you want but don't have
- **Purple (#8b5cf6)**: Episodes downloading - TV episodes being downloaded
- **Cyan (#06b6d4)**: Episodes downloaded - TV episodes you have

## Dependencies

### Services Required
| Service | Port | Purpose |
|---------|------|---------|
| Radarr | 7878 | Movie management |
| Sonarr | 8989 | TV show management |
| Glance | 8080 | Dashboard |
| Media Stats API | 5054 | Data aggregator |

### Python Libraries (for Media Stats API)
| Library | Purpose |
|---------|---------|
| Flask | Web server framework |
| Flask-CORS | Allows cross-origin requests |
| requests | Makes HTTP requests to Radarr/Sonarr |
| gunicorn | Production web server |

## Deployment Steps

### 1. Deploy Media Stats API

```bash
# From the Ansible controller
cd ~/ansible
ansible-playbook glance/deploy-media-stats-api.yml
```

### 2. Verify API is Working

```bash
# Test the API endpoint
curl http://192.168.40.12:5054/api/stats
```

You should see JSON output with all 6 stats.

### 3. Update Glance Configuration

```bash
# Copy the update script to the server
scp ... hermes-admin@192.168.40.13:/tmp/

# Run the script and restart Glance
ssh hermes-admin@192.168.40.12:/opt/glance && sudo docker compose restart"
```

### 4. Verify Dashboard

Open https://glance.hrmsmrflrii.xyz and navigate to the **Media** tab. You should see the colorful 3x2 grid of stats.

## Troubleshooting

### API Not Responding

```bash
# Check container status
ssh hermes-admin@192.168.40.13 "docker ps | grep media-stats"

# Check logs
ssh hermes-admin@192.168.40.13 "docker logs media-stats-api"
```

### Stats Showing Zero

1. Verify Radarr/Sonarr are running
2. Check API keys are correct in `/opt/media-stats-api/docker-compose.yml`
3. Test direct API access:
   ```bash
   curl "http://192.168.40.11:7878/api/v3/movie" -H "X-Api-Key: YOUR_KEY"
   ```

### Grid Not Displaying Correctly

1. Clear browser cache
2. Check Glance logs: `docker logs glance`
3. Verify the template was applied: `cat /opt/glance/config/glance.yml | grep "Media Stats"`

## File Locations Summary

| File | Location | Purpose |
|------|----------|---------|
| media-stats-api.py | `/opt/media-stats-api/` | API source code |
| docker-compose.yml | `/opt/media-stats-api/` | Container config |
| glance.yml | `/opt/glance/config/` | Dashboard config |
| deploy-media-stats-api.yml | `ansible-playbooks/glance/` | Ansible playbook |
| temp-media-fix.py | Repository root | Config update script |

## Home Page Configuration

**IMPORTANT: DO NOT modify the Home page layout without explicit user permission.**

The Home page has been carefully configured and should be preserved as-is.

### Layout Structure

```
┌──────────────────┬──────────────────────────────────────────┬──────────────────┐
│   LEFT (small)   │              CENTER (full)                │  RIGHT (small)   │
├──────────────────┼──────────────────────────────────────────┼──────────────────┤
│ Clock            │ Life Progress Widget                      │ Chess.com Stats  │
│ Weather          │ GitHub Contributions (green, dark mode)   │ Crypto Markets   │
│ Sun Times        │ Proxmox Cluster Monitor (3 nodes)         │ Stock Markets    │
│ Calendar         │ Storage Monitor                           │ Tech News RSS    │
│ Daily Note       │ Core Services Monitor                     │                  │
│ Infrastructure   │ Media Services Monitor                    │                  │
│ Services         │ Monitoring Stack Monitor                  │                  │
└──────────────────┴──────────────────────────────────────────┴──────────────────┘
```

> **Note**: Kubernetes monitors were removed because Glance (VLAN 40) cannot reach K8s nodes (VLAN 20) due to firewall/routing rules.

### Widget Details

#### Left Column (Small)
| Widget | Configuration |
|--------|---------------|
| Clock | 24h format, Asia/Manila timezone |
| Weather | Manila, Philippines, metric units |
| Sun Times | sunrise-sunset.org API, Manila coords (14.5995, 120.9842) |
| Calendar | Monday first day |
| Daily Note | Obsidian Local REST API via Tailscale (100.90.207.58:27123) |
| Infrastructure Bookmarks | Authentik, Omada Cloud, Proxmox, Traefik, OPNsense, Portainer, Synology NAS, Home Assistant |
| Services Bookmarks | Media (8 services), Downloads (2), Productivity (4), Monitoring (5) |

##### Obsidian Daily Notes Widget
- **Requires**: Obsidian running on MacBook with Local REST API plugin
- **Plugin setting**: Must bind to `0.0.0.0` (not localhost)
- **Connection**: Via Tailscale (MacBook IP: 100.90.207.58)
- **Daily note path**: `05 Periodic Notes/00 Daily/YYYY-MM-DD.md`
- **Displays**: Link to open note in Obsidian app

#### Center Column (Full)
| Widget | Type | Endpoint |
|--------|------|----------|
| Life Progress | custom-api | http://192.168.40.13:5051/progress |
| GitHub Contributions | custom-api | https://api.github.com/users/herms14 |
| Proxmox Cluster | monitor | Node 01-03 on port 8006 |
| Storage | monitor | Synology NAS on VLAN 10 & 20, port 5001 |
| Core Services | monitor | Traefik, Authentik, GitLab, Immich, n8n, Paperless, Pi-hole, Karakeep, Lagident, Home Assistant |
| Media Services | monitor | Jellyfin, Radarr, Sonarr, Lidarr, Prowlarr, Bazarr, Jellyseerr, Tdarr, Deluge, SABnzbd, Wizarr, Tracearr |
| Monitoring Stack | monitor | Uptime Kuma, Prometheus, Grafana, Jaeger, Glance, Speedtest |

#### Right Column (Small)
| Widget | Configuration |
|--------|---------------|
| Chess.com Stats | custom-api, username: hrmsmrflrii, Blitz & Rapid ratings |
| Crypto Markets | BTC-USD, ETH-USD, XRP-USD, BNB-USD, ADA-USD |
| Stock Markets | MSFT, AAPL, ORCL, NVDA, GOOGL, TSLA, NFLX, AMZN |
| Tech News RSS | r/homelab, r/selfhosted (horizontal cards, limit 5) |

##### Chess.com Stats Widget (Right Column)
- **API**: `https://api.chess.com/pub/player/hrmsmrflrii/stats`
- **Cache**: 30 minutes
- **Displays**: Blitz rating, Rapid rating, W/L/D records
- **Colors**: Blitz (amber #f59e0b), Rapid (blue #3b82f6)
- **Template**: Uses `.JSON.Array "data.result"` to iterate Prometheus-style response

### GitHub Contribution Graph

The contribution graph uses:
- **Service**: ghchart.rshah.org
- **Color**: `#40c463` (GitHub green)
- **Dark Mode**: CSS filter `invert(1) hue-rotate(180deg)`
- **Stats**: Repos, followers, following from GitHub API

### Health Check Endpoints

| Service | Endpoint | Port |
|---------|----------|------|
| Proxmox Nodes (3) | / | 8006 (HTTPS, allow-insecure) |
| Synology NAS | / | 5001 (HTTPS, allow-insecure) |
| Traefik | /ping | 8082 |
| Authentik | /-/health/ready/ | 9000 |
| Prometheus | /-/healthy | 9090 |
| Grafana | /api/health | 3030 |

### Configuration Script

The Home page is managed via `temp-home-fix.py` in the repository root:

```bash
# Deploy Home page configuration
scp ... hermes-admin@192.168.40.13:/tmp/
ssh hermes-admin@192.168.40.12:/opt/glance && sudo docker compose restart"
```

## Glance Dashboard Tab Structure

The Glance dashboard has 8 tabs in this order:

| Tab | Purpose | Protected |
|-----|---------|-----------|
| **Home** | Service monitors, bookmarks, markets | YES |
| **Compute** | Proxmox cluster + Container monitoring | YES |
| **Storage** | Synology NAS Grafana dashboard | YES |
| **Network** | Network overview + Speedtest | YES |
| **Media** | Media stats, downloads, queue | YES |
| **Web** | Tech news, AI/ML, stocks, crypto | No |
| **Reddit** | Dynamic Reddit feed | No |
| **Sports** | NBA games, standings, Yahoo Fantasy | YES |

### Compute Tab

**IMPORTANT: DO NOT modify the Compute tab layout without explicit user permission.**

Displays Proxmox cluster metrics and container monitoring via three embedded Grafana dashboards.

#### Proxmox Cluster Health Dashboard (Added January 11, 2026)

**Grafana Dashboard**: `proxmox-cluster-health` (UID)
- URL: `https://grafana.hrmsmrflrii.xyz/d/proxmox-cluster-health/proxmox-cluster-health?kiosk&theme=transparent&refresh=30s`
- Iframe Height: 1100px
- Dashboard JSON: `dashboards/proxmox-cluster-health.json`

**Panels**:
| Row | Panels |
|-----|--------|
| Cluster Status | Quorum status, Nodes online, Total VMs, Total Containers |
| CPU Temperature | Per-node temperature gauges (node01, node02, node03) |
| Temperature History | 24-hour line chart for all 3 nodes |
| Drive Temperatures | NVMe and GPU temperature bar gauges |
| Resource Usage | Top VMs by CPU, Top VMs by Memory |
| VM Timeline | State timeline showing VM status history |
| Storage | Storage pool usage bar gauges |

**Temperature Thresholds**:
| Range | Color | Status |
|-------|-------|--------|
| < 60°C | Green | Normal |
| 60-80°C | Yellow | Warning |
| > 80°C | Red | Critical |

**Data Sources**:
- `proxmox-nodes` job: node_exporter on ports 9100 (hardware metrics, temps)
- `proxmox` job: PVE exporter on port 9221 (VM/container/storage metrics)

#### Proxmox Cluster Overview Dashboard

**Grafana Dashboard**: `proxmox-compute` (UID)
- URL: `https://grafana.hrmsmrflrii.xyz/d/proxmox-compute/proxmox-cluster-overview?kiosk&theme=transparent&refresh=30s`
- Iframe Height: 1100px

**Panels**:
- Nodes Online, Avg CPU %, Avg Memory %
- Running/Total/Stopped VMs
- CPU & Memory Usage by Node (time series)
- Storage Usage % (Local LVM, VMDisks, ProxmoxData)

#### Container Status History Dashboard (PROTECTED)

**DO NOT MODIFY without explicit user permission.**

**Grafana Dashboard**: `container-status` (UID)
- URL: `https://grafana.hrmsmrflrii.xyz/d/container-status/container-status-history?kiosk&theme=transparent&refresh=30s`
- Iframe Height: 1500px
- Dashboard JSON: `temp-container-status-with-memory.json`
- Ansible Playbook: `ansible-playbooks/monitoring/deploy-container-status-dashboard.yml`

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [Total Containers] [Running]    [Total Memory Used]   [Total CPU Gauge] │  Row 1: h=4
├─────────────────────────────────────────────────────────────────────────┤
│ [Utilities VM]  [Utilities Stable] [Media VM]      [Media Stable]       │  Row 2: h=3
├──────────────────────────────────┬──────────────────────────────────────┤
│  Top 5 Memory - Utilities VM     │    Top 5 Memory - Media VM           │  Row 3: h=8
│  (bar gauge, Blue-Purple)        │    (bar gauge, Green-Yellow-Red)     │
├──────────────────────────────────┼──────────────────────────────────────┤
│ State Timeline - Utilities VM    │ State Timeline - Media VM            │  Row 4: h=14
│ (container uptime, 1h window)    │ (container uptime, 1h window)        │
├──────────────────────────────────┴──────────────────────────────────────┤
│ Container Issues (Last 15 min) - Table of stopped/restarted containers  │  Row 5: h=8
└─────────────────────────────────────────────────────────────────────────┘
```

**Row 1: Summary Stats** (y=0, h=4)
| Panel | Color | Query |
|-------|-------|-------|
| Total Containers | Blue (#3b82f6) | `count(docker_container_running)` |
| Running | Green (#22c55e) | `sum(docker_container_running)` |
| Total Memory Used | Orange (#f59e0b) | `sum(docker_container_memory_usage_bytes)` |
| Total CPU % | Gauge with thresholds | `sum(docker_container_cpu_percent)` |

**Row 2: VM Stats** (y=4, h=3)
| Panel | Color | Query |
|-------|-------|-------|
| Utilities VM | Purple (#8b5cf6) | `count(docker_container_running{job="docker-stats-utilities"})` |
| Utilities: Stable (>1h) | Green (#22c55e) | `count(docker_container_uptime_seconds{job="docker-stats-utilities"} > 3600) or vector(0)` |
| Media VM | Pink (#ec4899) | `count(docker_container_running{job="docker-stats-media"})` |
| Media: Stable (>1h) | Green (#22c55e) | `count(docker_container_uptime_seconds{job="docker-stats-media"} > 3600) or vector(0)` |

**Row 3: Top 5 Memory Panels** (y=7, h=8)
| Panel | Color Scheme | Query |
|-------|--------------|-------|
| Top 5 Memory - Utilities VM | `continuous-BlPu` (Blue-Purple) | `topk(5, docker_container_memory_percent{job="docker-stats-utilities"})` |
| Top 5 Memory - Media VM | `continuous-GrYlRd` (Green-Yellow-Red) | `topk(5, docker_container_memory_percent{job="docker-stats-media"})` |

- Type: `bargauge` with horizontal orientation
- Unit: percent, max: 100
- Display mode: gradient with unfilled area shown

**Row 4: State Timeline Panels** (y=15, h=14)
- State Timeline - Utilities VM: `docker_container_running{job="docker-stats-utilities"}`
- State Timeline - Media VM: `docker_container_running{job="docker-stats-media"}`
- Visualization: `state-timeline` (not status-history)
- Query interval: `1m` to reduce data points
- Time range: `now-1h`
- Value mappings: 0 = Down (red #ef4444), 1 = Running (green #22c55e)
- Row height: `0.9`
- mergeValues: `true`

**Row 5: Container Issues Table** (y=29, h=8)
- Shows containers that are stopped or recently restarted (uptime < 15 min)
- Query A: `docker_container_running == 0` (stopped containers)
- Query B: `docker_container_uptime_seconds < 900 and docker_container_running == 1` (recently restarted)
- Status mappings: 0 = Stopped (red), 1 = Restarted (amber)

**Key Configuration:**
- Visualization type: `state-timeline` (handles more data points than status-history)
- Query interval: `1m` to prevent "Too many points" errors
- Stable threshold: `> 3600` (1 hour) with `or vector(0)` fallback for empty results
- Time range: 1 hour window

**Visual Features**:
- Transparent dashboard background (`theme=transparent`)
- Modern stat tiles with colored backgrounds
- State timeline with green/red status indicators
- Issues table for quick problem identification

**Metrics Source**: docker-exporter on port 9417
- `docker_container_running` - Container status (1=running, 0=stopped)
- `docker_container_memory_percent` - Memory usage percentage
- `docker_container_memory_usage_bytes` - Memory usage in bytes
- `docker_container_cpu_percent` - CPU usage percentage
- `docker_container_uptime_seconds` - Container uptime in seconds
- `docker_container_started_at` - Container start time (Unix timestamp)

#### How It Was Built

The Container Monitoring dashboard was built with these key components:

**1. Docker Stats Exporter Enhancement**

The docker-stats-exporter (`ansible-playbooks/monitoring/docker-stats-exporter.py`) was enhanced to expose container uptime metrics:

```python
# New metrics added to docker-stats-exporter.py
container_uptime_seconds = Gauge(
    'docker_container_uptime_seconds',
    'Container uptime in seconds',
    ['name', 'id', 'image']
)

container_started_at = Gauge(
    'docker_container_started_at',
    'Container start time as Unix timestamp',
    ['name', 'id', 'image']
)

# In collect_metrics(), calculate uptime from container state
if status == 'running':
    started_at_str = container.attrs['State'].get('StartedAt', '')
    if started_at_str:
        start_time = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        uptime = (now - start_time).total_seconds()
        container_uptime_seconds.labels(name=name, id=cid, image=image).set(uptime)
        container_started_at.labels(name=name, id=cid, image=image).set(start_time.timestamp())
```

**2. Grafana Dashboard (Provisioned)**

The dashboard is provisioned from a JSON file, not managed via API:
- **Location**: `/opt/monitoring/grafana/dashboards/container-monitoring.json`
- **UID**: `containers-modern`
- **Provisioning**: Grafana auto-loads dashboards from this directory on startup

Key design decisions:
- **Bar gauges instead of tables** - Modern visual style matching the rest of the dashboard
- **Continuous color gradients** - `continuous-BlYlRd` for memory, `continuous-GrYlRd` for CPU
- **topk() queries with sortBy** - Ensures containers are sorted highest to lowest
- **Transparent backgrounds** - Seamless embedding in Glance iframes

**3. Prometheus Scrape Configuration**

Two jobs scrape the docker-stats-exporters:

```yaml
# In prometheus.yml
- job_name: 'docker-stats-utilities'
  static_configs:
    - targets: ['192.168.40.13:9417']
      labels:
        vm: 'docker-vm-core-utilities01'

- job_name: 'docker-stats-media'
  static_configs:
    - targets: ['192.168.40.11:9417']
      labels:
        vm: 'docker-vm-media01'
```

**4. Glance Iframe Configuration**

The Compute tab embeds the Grafana dashboard via iframe:

```python
# In temp-glance-update.py COMPUTE_PAGE
{
    'type': 'iframe',
    'title': 'Container Monitoring',
    'source': 'https://grafana.hrmsmrflrii.xyz/d/containers-modern/container-monitoring?orgId=1&kiosk&theme=transparent&refresh=30s',
    'height': 1400
}
```

**5. Deployment Process**

```bash
# 1. Deploy docker-stats-exporter to both VMs
ssh hermes-admin@192.168.20.30 "cd ~/ansible && ansible-playbook monitoring/deploy-docker-exporter.yml"

# 2. Copy dashboard JSON to Grafana host
scp ... hermes-admin@192.168.40.13:/opt/monitoring/grafana/dashboards/container-monitoring.json

# 3. Restart Grafana to load new dashboard
ssh hermes-admin@192.168.40.13 "cd /opt/monitoring && docker compose restart grafana"

# 4. Update Glance config and restart
scp ... hermes-admin@192.168.40.13:/tmp/
ssh hermes-admin@192.168.40.12:/opt/glance && sudo docker compose restart"
```

**File Locations Summary**:
| File | Location | Purpose |
|------|----------|---------|
| docker-stats-exporter.py | `ansible-playbooks/monitoring/` | Prometheus exporter source |
| container-monitoring.json | `/opt/monitoring/grafana/dashboards/` | Grafana dashboard JSON |
| temp-glance-update.py | Repository root | Glance config update script |
| temp-enhanced-container-dashboard.py | Repository root | Dashboard generation script |

### Storage Tab (PROTECTED)

**DO NOT MODIFY without explicit user permission.**

**Grafana Dashboard**: `synology-nas-modern` (UID)
- URL: `https://grafana.hrmsmrflrii.xyz/d/synology-nas-modern/synology-nas-storage?orgId=1&kiosk&theme=transparent&refresh=30s`
- Iframe Height: 1350px
- Dashboard JSON: `dashboards/synology-nas.json`
- Ansible Playbook: `ansible-playbooks/monitoring/deploy-synology-nas-dashboard.yml`
- Time Range: 7 days (for storage consumption trends)

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│ [RAID Status] [SSD Cache] [Uptime] [Total] [Used] [Storage %]           │  Row 1: h=4
├─────────────────────────────────────────────────────────────────────────┤
│ [Drive 1 HDD] [Drive 2 HDD] [Drive 3 HDD] [Drive 4 HDD] [M.2 1] [M.2 2] │  Row 2: h=4
├──────────────────────────────────┬──────────────────────────────────────┤
│ Disk Temperatures (bargauge)     │ [Sys Temp] [Healthy] [CPU Gauge]    │  Row 3: h=6
│ All 6 drives with gradient       │ [CPU Cores] [Free]   [Mem Gauge]    │
├──────────────────────────────────┼──────────────────────────────────────┤
│ CPU Gauge        Memory Gauge    │ [Total RAM]  [Available RAM]        │  Row 4: h=5
├──────────────────────────────────┼──────────────────────────────────────┤
│ CPU Usage Over Time (4 cores)    │ Memory Usage Over Time              │  Row 5: h=8
├──────────────────────────────────┴──────────────────────────────────────┤
│ Storage Consumption Over Time (Used/Free/Total, 7-day window)           │  Row 6: h=8
└─────────────────────────────────────────────────────────────────────────┘
```

#### RAID Status Panels (Added January 8, 2026)

Two new panels at the top of the dashboard monitor RAID array health:

| Panel | Metric | Status Mappings |
|-------|--------|-----------------|
| **RAID Status** | `synologyRaidStatus{raidIndex="0"}` | Storage Pool 1 (HDD array) |
| **SSD Cache Status** | `synologyRaidStatus{raidIndex="1"}` | SSD Cache Pool |

**RAID Status Value Mappings:**
| Value | Status | Color | Description |
|-------|--------|-------|-------------|
| 1 | Normal | Green (#22c55e) | Array healthy |
| 2 | REPAIRING | Orange (#f59e0b) | Rebuilding after drive replacement |
| 3-6 | Maintenance | Orange (#f59e0b) | Migrating, Expanding, Deleting, Creating |
| 7 | SYNCING | Blue (#3b82f6) | Data verification/sync in progress |
| 11 | DEGRADED | Red (#ef4444) | Drive failure, needs attention |
| 12 | CRASHED | Red (#ef4444) | Array failed |

**Why This Matters:**
- Individual disk health (`synologyDiskHealthStatus`) only shows per-disk SMART status
- RAID status (`synologyRaidStatus`) shows the overall array health
- A degraded RAID can have all disks showing "Healthy" while the array rebuilds

**Disk Configuration (6 drives):**
| Slot | Drive | Model | Type |
|------|-------|-------|------|
| 1 | Seagate 8TB | ST8000VN004-3CP101 | HDD |
| 2 | Seagate 4TB | ST4000VN006-3CW104 | HDD |
| 3 | Seagate 12TB | ST12000VN0008-2YS101 | HDD |
| 4 | Seagate 10TB | ST10000VN000-3AK101 | HDD |
| M.2 1 | Kingston 1TB | SNV2S1000G | NVMe SSD |
| M.2 2 | Crucial 1TB | CT1000P2SSD8 | NVMe SSD |

**Color Scheme:**
- HDDs: Green when healthy (#22c55e)
- SSDs: Purple when healthy (#8b5cf6)
- Failed: Red (#ef4444)
- Storage Timeline: Used (amber #f59e0b), Free (green #22c55e), Total (blue dashed #3b82f6)
- Memory Chart: Used Real (red #ef4444), Cache/Buffers (amber #f59e0b), Free (green #22c55e)
- Thresholds on gauges: Green < 70%, Amber 70-90%, Red > 90%

**Memory Metrics (IMPORTANT):**

The memory gauge uses a corrected formula that excludes reclaimable cache and buffers:

```promql
# Memory Usage % (correct - excludes cache/buffers)
((memTotalReal - memAvailReal - memBuffer - memCached) / memTotalReal) * 100
```

This shows ~7% actual usage instead of ~95% (which incorrectly treated cache as "used").

**Memory Over Time Chart** shows 3 series:
| Series | Query | Color |
|--------|-------|-------|
| Used (Real) | `memTotalReal - memAvailReal - memBuffer - memCached` | Red |
| Cache/Buffers | `memCached + memBuffer` | Amber |
| Free | `memAvailReal` | Green |

**Units**: `kbytes` (all memory metrics are in KB)

**Prometheus Metrics (SNMP):**
| Metric | Description |
|--------|-------------|
| `synologyDiskHealthStatus` | Disk health (1=healthy, 0=failed) |
| `synologyDiskTemperature` | Disk temperature in Celsius |
| `synologyRaidTotalSize` | Total RAID volume size in bytes |
| `synologyRaidFreeSize` | Free RAID space in bytes |
| `synologySystemTemperature` | System temperature |
| `hrProcessorLoad` | CPU load per core |
| `memTotalReal` | Total RAM in KB |
| `memAvailReal` | Available (free) RAM in KB |
| `memBuffer` | Buffer memory in KB (reclaimable) |
| `memCached` | Cached memory in KB (reclaimable) |
| `sysUpTime` | System uptime in centiseconds |

### Network Tab

**Layout (2 columns)**:
```
┌───────────────────────────────────────────────────────┬──────────────────┐
│                    MAIN (full)                         │  SIDEBAR (small) │
├───────────────────────────────────────────────────────┼──────────────────┤
│ Network Utilization Dashboard (Grafana iframe, h=1100)│ Network Device   │
│ - Cluster & NAS bandwidth stats                       │ Status (custom)  │
│ - Per-node utilization (node01/02/03)                 │                  │
│ - Bandwidth timelines with 1Gbps reference            │ Latest Speedtest │
│ - NAS eth0/eth1 traffic monitoring                    │ (Download/Upload │
│ - Combined cluster + NAS view                         │  Ping/Jitter)    │
├───────────────────────────────────────────────────────┤                  │
│ Omada Network Dashboard (Grafana iframe, h=2200)      │                  │
│ - Overview: Clients, Controller, WiFi modes           │                  │
│ - Device Health: CPU/Memory gauges                    │                  │
│ - WiFi Signal Quality: RSSI, SNR                      │                  │
│ - Switch Port Status: Table                           │                  │
│ - PoE Power Usage                                     │                  │
│ - Traffic Analysis: Top 10 clients (barchart)         │                  │
│ - Client Details: Full table                          │                  │
└───────────────────────────────────────────────────────┴──────────────────┘
```

#### Network Utilization Dashboard (Added January 13, 2026)

**Grafana Dashboard**: `network-utilization` (UID)
- URL: `https://grafana.hrmsmrflrii.xyz/d/network-utilization/network-utilization?orgId=1&kiosk&theme=transparent&refresh=30s`
- Iframe Height: 1100px
- Dashboard JSON: `dashboards/network-utilization.json`
- Ansible Playbook: `ansible/playbooks/monitoring/deploy-network-utilization-dashboard.yml`

**Purpose**: Monitor network bandwidth utilization to determine if a 2.5GbE switch upgrade would be beneficial.

**Panels:**
| Row | Panels |
|-----|--------|
| **Stats** | Total Cluster BW, Cluster %, Peak 24h, Avg 24h, NAS BW, NAS % |
| **Per-Node** | node01, node02, node03 bandwidth stats + NAS Peak 24h |
| **Timeline 1** | Cluster Bandwidth Over Time (per-node RX/TX with 1Gbps reference) |
| **Timeline 2** | Synology NAS Bandwidth Over Time (eth0/eth1 RX/TX) |
| **Timeline 3** | Combined Bandwidth (Cluster Total + NAS Total with 1Gbps reference) |

**Data Sources:**
- `proxmox-nodes` job: node_exporter on port 9100 (`node_network_*_bytes_total`)
- `synology` job: SNMP exporter with IF-MIB (`ifHCInOctets`, `ifHCOutOctets`)

**NAS Interface Mapping:**
| Interface | ifIndex | Speed |
|-----------|---------|-------|
| eth0 | 3 | 1Gbps |
| eth1 | 4 | 1Gbps |

**Utilization Thresholds:**
| Range | Color | Status |
|-------|-------|--------|
| < 50% | Green | Normal |
| 50-80% | Yellow | Elevated |
| > 80% | Red | High utilization |

#### Omada Network Dashboard

**Grafana Dashboard**: `omada-network` (UID)
- URL: `https://grafana.hrmsmrflrii.xyz/d/omada-network/omada-network-overview?orgId=1&kiosk&theme=transparent&refresh=30s`
- Iframe Height: 2200px

**Traffic Panels** (converted from bargauge to barchart for proper sorting):
| Panel | Type | Query | Sorting |
|-------|------|-------|---------|
| Top 10 Clients by Traffic | barchart | `topk(10, omada_client_traffic_down_bytes + omada_client_traffic_up_bytes)` | Descending |
| Client TX Rate | barchart | `topk(10, omada_client_tx_rate * 1000000)` | Descending |
| Client RX Rate | barchart | `topk(10, omada_client_rx_rate * 1000000)` | Descending |

**Transformations** (same as Container dashboard):
```yaml
transformations:
  - id: reduce
    options:
      reducers: [lastNotNull]
  - id: sortBy
    options:
      sort:
        - field: "Last *"
          desc: true
```

**Network Device Status Widget** (Sidebar):
- Type: `custom-api`
- URL: `http://192.168.40.13:9090/api/v1/query?query=omada_device_cpu_percentage`
- Shows all Omada devices with status indicator and CPU %
- Replaced broken HTTP monitors (management VLANs unreachable from VLAN 40)

**Speedtest Widget** (Sidebar):
- Type: `custom-api`
- URL: `http://192.168.40.13:3000/api/speedtest/latest`
- Shows Download/Upload speeds, Ping, Jitter

### Web Tab

Comprehensive tech news aggregator with collapsible sections for all categories.

**Layout (2 columns)**:
```
┌───────────────────────────────────────────────────────┬──────────────────┐
│                    MAIN (full)                         │  SIDEBAR (small) │
├───────────────────────────────────────────────────────┼──────────────────┤
│ Tech YouTube (7 channels, horizontal-cards)           │ Tech Stocks (8)  │
│ Tech News (The Verge, XDA, TechCrunch, Ars Technica) │ Crypto (5)       │
│ Android & Mobile (XDA Mobile, Google News, r/Android) │ Crypto News      │
│ AI & Machine Learning (TechCrunch AI, Reddit feeds)   │ Stock Market     │
│ Cloud & Enterprise (AWS, Azure, GCP, Oracle)          │ Quick Links      │
│ Big Tech (Microsoft, NVIDIA, Google, Apple, Meta)     │                  │
│ Gaming (r/gaming, r/pcgaming, Ars Gaming)             │                  │
│ PC Builds & Hardware (r/buildapc, r/pcmasterrace)     │                  │
│ Travel (r/travel, r/solotravel, r/TravelHacks)        │                  │
└───────────────────────────────────────────────────────┴──────────────────┘
```

**YouTube Channels** (Glance `videos` widget):
| Channel | Channel ID |
|---------|------------|
| MKBHD | UCBJycsmduvYEL83R_U4JriQ |
| Linus Tech Tips | UCXuqSBlHAE6Xw-yeJA0Tunw |
| Mrwhosetheboss | UCMiJRAwDNSNzuYeN2uWa0pA |
| Dave2D | UCVYamHliCI9rw1tHR1xbkfw |
| Austin Evans | UCXGgrKt94gR6lmN4aN3mYTg |
| JerryRigEverything | UCWFKCr40YwOZQx8FHU_ZqqQ |
| Fireship | UCsBjURrPoezykLs9EqgamOA |

**News Sources**:
| Category | Sources |
|----------|---------|
| Tech News | The Verge, XDA, TechCrunch, Ars Technica |
| AI/ML | TechCrunch AI, r/artificial, r/MachineLearning, r/LocalLLaMA, r/ChatGPT |
| Cloud | AWS Blog, r/aws, r/googlecloud, r/azure, r/oracle |
| Big Tech | r/microsoft, r/NVIDIA, r/google, r/apple, r/Meta |
| Gaming | r/gaming, r/pcgaming, r/Games, Ars Gaming |
| PC Builds | r/buildapc, r/pcmasterrace, r/hardware, XDA Computing |
| Travel | r/travel, r/solotravel, r/TravelHacks |

**Markets (Sidebar)**:
| Type | Symbols |
|------|---------|
| Tech Stocks | MSFT, NVDA, ORCL, AMZN, GOOGL, META, AAPL, BABA |
| Crypto | BTC-USD, ETH-USD, XRP-USD, SOL-USD, DOGE-USD |

**Configuration Script**: `temp-glance-web-reddit-update.py`

### Reddit Tab

Dynamic Reddit feed aggregator with thumbnails and native Reddit widgets.

**Layout (2 columns)**:
```
┌───────────────────────────────────────────────────────┬──────────────────┐
│                    MAIN (full)                         │  SIDEBAR (small) │
├───────────────────────────────────────────────────────┼──────────────────┤
│ Reddit Manager Dynamic Feed (16 subreddits)           │ r/technology     │
│ - Posts grouped by subreddit                          │ r/programming    │
│ - Thumbnails on posts                                 │ r/sysadmin       │
│ - Score and comment counts                            │ Subreddit Links  │
│ - Manage subreddits link                              │                  │
└───────────────────────────────────────────────────────┴──────────────────┘
```

**Reddit Manager API**: http://192.168.40.12:5053
- **Manage Subreddits**: http://192.168.40.12:5053 (Web UI)
- **API Endpoint**: http://192.168.40.12:5053/api/feed

**Configured Subreddits** (16 total):
| Category | Subreddits |
|----------|------------|
| Homelab | homelab, selfhosted, datahoarder |
| DevOps | linux, devops, kubernetes, docker |
| Tech | technology, programming, webdev, sysadmin, netsec |
| Hobby | gaming, pcmasterrace, buildapc, mechanicalkeyboards |

**Settings**:
- Sort: `hot` (options: hot, new, top)
- View: `grouped` (options: grouped, combined)

**Native Reddit Widgets** (Sidebar):
- r/technology (hot, thumbnails, limit 8)
- r/programming (hot, thumbnails, limit 6)
- r/sysadmin (hot, thumbnails, limit 6)

**Deployment Playbook**: `ansible-playbooks/glance/deploy-web-reddit-update.yml`

### Backup Tab (Added January 11, 2026)

The Backup tab provides monitoring for Proxmox Backup Server (PBS) with embedded Grafana dashboard, NAS backup sync status, and drive health.

**Layout (2 columns)**:
```
┌───────────────────────────────────────────────────────────────┬──────────────────┐
│                     MAIN (full)                                │  SIDEBAR (small) │
├───────────────────────────────────────────────────────────────┼──────────────────┤
│ PBS Backup Status Dashboard (Grafana iframe, h=900)           │ NAS Backup Sync  │
│ - Status Overview: pbs_up, version, uptime                    │ (sync status,    │
│ - Datastore Storage: Pie charts for daily/main                │  sizes, last     │
│ - Backup Snapshots: Counts per datastore                      │  sync time)      │
│ - Storage Usage Over Time                                     │                  │
│ - PBS Host Metrics: CPU, memory, load                         │ Backups on NAS   │
│                                                               │ (VM/CT list with │
│                                                               │  backup dates)   │
│                                                               │                  │
│                                                               │ Drive Health     │
│                                                               │ Status (SMART)   │
│                                                               │                  │
│                                                               │ PBS Server       │
│                                                               │ (monitor)        │
│                                                               │                  │
│                                                               │ Quick Links      │
└───────────────────────────────────────────────────────────────┴──────────────────┘
```

**Grafana Dashboard**: `pbs-backup-status` (UID)
- URL: `https://grafana.hrmsmrflrii.xyz/d/pbs-backup-status/pbs-backup-status?kiosk&theme=transparent&refresh=1m`
- Iframe Height: 900px
- Dashboard JSON: `dashboards/pbs-backup-status.json`
- Datasource UID: `PBFA97CFB590B2093` (Prometheus)

**NAS Backup Sync Widget** (Added January 12, 2026):

Shows the status of PBS-to-NAS backup synchronization.

| Property | Value |
|----------|-------|
| API Endpoint | `http://192.168.40.13:9102/status` |
| Cache | 5 minutes |

Displays:
- Sync status indicator (green=success, blue=running, red=failed)
- Last successful sync timestamp
- Main datastore size on NAS
- Daily datastore size on NAS
- NAS target path
- Sync schedule

**Backups on NAS Widget** (Added January 12, 2026):

Lists all VMs and CTs that have backups stored on the Synology NAS.

| Property | Value |
|----------|-------|
| API Endpoint | `http://192.168.40.13:9102/backups` |
| Cache | 10 minutes |

Displays:
- Total protected count
- VM count and CT count
- Scrollable list of all backed up VMs/CTs with:
  - Type indicator (VM in blue, CT in amber)
  - VMID
  - Last backup timestamp

**Drive Health Status Widget**:

Displays SMART health status for PBS storage drives.

| Property | Value |
|----------|-------|
| API Endpoint | `http://192.168.20.22:9101/health` |
| Cache | 5 minutes |
| Host | node03 (192.168.20.22) |
| Service | `smart-health-api.service` |
| Monitored Drives | Seagate 4TB HDD (main), Kingston 1TB NVMe (daily) |

**NAS Backup Status API**:

| Property | Value |
|----------|-------|
| Host | docker-vm-core-utilities01 (192.168.40.13) |
| Port | 9102 |
| Container | `nas-backup-status-api` |
| Endpoints | `/status`, `/backups`, `/health` |
| Ansible Playbook | `ansible/playbooks/glance/deploy-nas-backup-status-api.yml` |

See [PBS Monitoring](./PBS_MONITORING.md) for complete API documentation.

### Sports Tab (PROTECTED)

**DO NOT MODIFY without explicit user permission.**

The Sports tab displays NBA data and Yahoo Fantasy league information using the NBA Stats API.

**API Location**: docker-vm-core-utilities01:5060 (`/opt/nba-stats-api/`)

**Layout (3 columns, 7 widgets)**:
```
┌──────────────────┬───────────────────────────────────┬──────────────────┐
│  TODAY'S GAMES   │         NBA STANDINGS             │  FANTASY LEAGUE  │
│  (small column)  │         (full column)             │  (small column)  │
│                  │                                   │                  │
│  Live scores     │  Eastern      │     Western       │  League Standings│
│  with logos      │  Conference   │     Conference    │  W-L Records     │
├──────────────────┤  15 teams     │     15 teams      ├──────────────────┤
│  INJURY REPORT   │               │                   │  WEEK MATCHUPS   │
│  Player photos   │  Green = Playoff (1-6)            │  Current week    │
│  Status colors   │  Yellow = Play-in (7-10)          │  matchup scores  │
│  Out/Day-to-Day  ├───────────────────────────────────┼──────────────────┤
│                  │         NBA NEWS                  │  HOT PICKUPS     │
│                  │  Headlines with images            │  Top 10 available│
│                  │  6 latest articles                │  PTS/AST/REB     │
└──────────────────┴───────────────────────────────────┴──────────────────┘
```

**Widgets**:

| Widget | API Endpoint | Cache | Description |
|--------|--------------|-------|-------------|
| Today's NBA Games | `/games` | 2m | Live scores with team logos from ESPN CDN |
| Injury Report | `/injuries` | 15m | Player injuries with headshots, status colors (red=Out, yellow=Day-to-Day) |
| NBA Standings | `/standings` | 15m | East/West conferences with playoff indicators |
| NBA News | `/news` | 15m | Latest headlines with article images |
| Fantasy League | `/fantasy` | 15m | Yahoo Fantasy league standings |
| Week Matchups | `/fantasy/matchups` | 5m | Current week H2H matchups with scores |
| Hot Pickups | `/fantasy/recommendations` | 30m | Top 10 available free agents with stats (PTS/AST/REB) |

**NBA Stats API Endpoints**:

| Endpoint | Description | Data Source |
|----------|-------------|-------------|
| `/health` | Health check | - |
| `/games` | Today's NBA games with scores | ESPN API |
| `/standings` | NBA standings (East/West) | ESPN API |
| `/injuries` | NBA injury report with player headshots | ESPN API |
| `/news` | NBA news headlines with images | ESPN API |
| `/fantasy` | Fantasy league standings | Yahoo Fantasy API |
| `/fantasy/matchups` | Current week matchups | Yahoo Fantasy API |
| `/fantasy/recommendations` | Player pickup recommendations | Yahoo Fantasy API |
| `/fantasy/refresh` | Force refresh fantasy data | Yahoo Fantasy API |

**Yahoo Fantasy Configuration**:
- League ID: `466.l.12095` (2024-25 NBA season)
- OAuth Token: `/opt/nba-stats-api/data/yahoo_token.json` (auto-refreshes)
- Update Schedule: Daily at 2pm (Asia/Manila timezone)
- League Type: Head-to-Head Categories

**Team Logos**: Pulled dynamically from ESPN CDN (not stored locally)

**Files on Server**:
| File | Location | Purpose |
|------|----------|---------|
| nba-stats-api.py | `/opt/nba-stats-api/` | Main Flask API |
| yahoo_fantasy.py | `/opt/nba-stats-api/` | Yahoo Fantasy API module |
| fantasy_recommendations.py | `/opt/nba-stats-api/` | Player recommendations |
| yahoo_token.json | `/opt/nba-stats-api/data/` | OAuth token storage |
| docker-compose.yml | `/opt/nba-stats-api/` | Container config |

**Ansible Playbook**: `ansible-playbooks/glance/deploy-nba-stats-api.yml`

### Prometheus Exporters

| Exporter | Port | Target | Status |
|----------|------|--------|--------|
| OPNsense Exporter | 9198 | 192.168.91.30 | Active |
| Omada Exporter | 9202 | 192.168.0.103 | Pending |
| Docker Stats Exporter | 9417 | Both Docker VMs | Active |

## Related Documentation

- [SERVICES.md](./SERVICES.md) - All deployed services
- [APPLICATION_CONFIGURATIONS.md](./APPLICATION_CONFIGURATIONS.md) - Detailed app configurations
- [ANSIBLE.md](./ANSIBLE.md) - Ansible automation guide
