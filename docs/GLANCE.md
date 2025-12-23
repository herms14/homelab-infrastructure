# Glance Dashboard

Glance is a self-hosted dashboard that provides a central view of all homelab services, monitoring, and media statistics. This guide explains how the Glance dashboard was built, including the custom Media Stats grid widget.

## Overview

| Component | Description |
|-----------|-------------|
| **Glance** | Main dashboard application |
| **Media Stats API** | Custom API that combines Radarr/Sonarr data |
| **Location** | docker-vm-utilities01 (192.168.40.10) |
| **URL** | https://glance.hrmsmrflrii.xyz |

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

**Location:** `/opt/media-stats-api/` on docker-vm-utilities01

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

**Location:** `temp-media-fix.py` (run on docker-vm-utilities01)

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
                    "url": "http://192.168.40.10:5054/api/stats",
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
   - Points to our Media Stats API (`http://192.168.40.10:5054/api/stats`)
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
  hosts: docker-vm-utilities01
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
curl http://192.168.40.10:5054/api/stats
```

You should see JSON output with all 6 stats.

### 3. Update Glance Configuration

```bash
# Copy the update script to the server
scp temp-media-fix.py hermes-admin@192.168.40.10:/tmp/

# Run the script and restart Glance
ssh hermes-admin@192.168.40.10 "sudo python3 /tmp/temp-media-fix.py && cd /opt/glance && sudo docker compose restart"
```

### 4. Verify Dashboard

Open https://glance.hrmsmrflrii.xyz and navigate to the **Media** tab. You should see the colorful 3x2 grid of stats.

## Troubleshooting

### API Not Responding

```bash
# Check container status
ssh hermes-admin@192.168.40.10 "docker ps | grep media-stats"

# Check logs
ssh hermes-admin@192.168.40.10 "docker logs media-stats-api"
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
│ Clock            │ Life Progress Widget                      │ Crypto Markets   │
│ Weather          │ GitHub Contributions (green, dark mode)   │ Stock Markets    │
│ Calendar         │ Proxmox Cluster Monitor                   │ Tech News RSS    │
│ Infrastructure   │ Storage Monitor                           │                  │
│ Services         │ Core Services Monitor                     │                  │
│                  │ Media Services Monitor                    │                  │
│                  │ Monitoring Stack Monitor                  │                  │
│                  │ Kubernetes Control Plane Monitor          │                  │
│                  │ Kubernetes Workers Monitor                │                  │
└──────────────────┴──────────────────────────────────────────┴──────────────────┘
```

### Widget Details

#### Left Column (Small)
| Widget | Configuration |
|--------|---------------|
| Clock | 24h format, Asia/Manila timezone |
| Weather | Manila, Philippines, metric units |
| Calendar | Monday first day |
| Infrastructure Bookmarks | Authentik, Omada Cloud, Proxmox, Traefik, OPNsense, Portainer, Synology NAS |
| Services Bookmarks | Media (8 services), Downloads (2), Productivity (4), Monitoring (5) |

#### Center Column (Full)
| Widget | Type | Endpoint |
|--------|------|----------|
| Life Progress | custom-api | http://192.168.40.10:5051/progress |
| GitHub Contributions | custom-api | https://api.github.com/users/herms14 |
| Proxmox Cluster | monitor | Node 01-03 on port 8006 |
| Storage | monitor | Synology NAS on VLAN 10 & 20, port 5001 |
| Core Services | monitor | Traefik, Authentik, GitLab, Immich, n8n, Paperless |
| Media Services | monitor | Jellyfin, Radarr, Sonarr, Lidarr, Prowlarr, Bazarr, Jellyseerr, Tdarr, Deluge, SABnzbd |
| Monitoring Stack | monitor | Uptime Kuma, Prometheus, Grafana, Jaeger, Glance, Speedtest |
| K8s Control Plane | monitor | Controllers 1-3 via API (port 6443) |
| K8s Workers | monitor | Workers 1-6 via kubelet (port 10248) |

#### Right Column (Small)
| Widget | Configuration |
|--------|---------------|
| Crypto Markets | BTC-USD, ETH-USD, XRP-USD, BNB-USD, ADA-USD |
| Stock Markets | MSFT, AAPL, ORCL, NVDA, GOOGL, TSLA, NFLX, AMZN |
| Tech News RSS | r/homelab, r/selfhosted (horizontal cards, limit 5) |

### GitHub Contribution Graph

The contribution graph uses:
- **Service**: ghchart.rshah.org
- **Color**: `#40c463` (GitHub green)
- **Dark Mode**: CSS filter `invert(1) hue-rotate(180deg)`
- **Stats**: Repos, followers, following from GitHub API

### Health Check Endpoints

| Service | Endpoint | Port |
|---------|----------|------|
| Proxmox Nodes | / | 8006 (HTTPS, allow-insecure) |
| Synology NAS | / | 5001 (HTTPS, allow-insecure) |
| K8s Control Plane | /healthz | 6443 (HTTPS, allow-insecure) |
| K8s Workers | /healthz | 10248 (HTTP) |
| Traefik | /ping | 8082 |
| Authentik | /-/health/ready/ | 9000 |
| Prometheus | /-/healthy | 9090 |
| Grafana | /api/health | 3030 |

### Configuration Script

The Home page is managed via `temp-home-fix.py` in the repository root:

```bash
# Deploy Home page configuration
scp temp-home-fix.py hermes-admin@192.168.40.10:/tmp/
ssh hermes-admin@192.168.40.10 "sudo python3 /tmp/temp-home-fix.py && cd /opt/glance && sudo docker compose restart"
```

## Glance Dashboard Tab Structure

The Glance dashboard has 7 tabs in this order:

| Tab | Purpose | Protected |
|-----|---------|-----------|
| **Home** | Service monitors, bookmarks, markets | YES |
| **Compute** | Proxmox cluster + Container monitoring | No |
| **Storage** | Synology NAS Grafana dashboard | No |
| **Network** | Network overview + Speedtest | No |
| **Media** | Media stats, downloads, queue | YES |
| **Web** | Tech news, AI/ML, stocks, NBA | No |
| **Reddit** | Dynamic Reddit feed | No |

### Compute Tab

Displays Proxmox cluster metrics and container monitoring via two embedded Grafana dashboards.

#### Proxmox Cluster Dashboard

**Grafana Dashboard**: `proxmox-compute` (UID)
- URL: `https://grafana.hrmsmrflrii.xyz/d/proxmox-compute/proxmox-cluster-overview?kiosk&theme=transparent&refresh=30s`
- Iframe Height: 1100px

**Panels**:
- Nodes Online, Avg CPU %, Avg Memory %
- Running/Total/Stopped VMs
- CPU & Memory Usage by Node (time series)
- Storage Usage % (Local LVM, VMDisks, ProxmoxData)

#### Container Monitoring Dashboard (Modern Visual Style)

**Grafana Dashboard**: `containers-modern` (UID)
- URL: `https://grafana.hrmsmrflrii.xyz/d/containers-modern/container-monitoring?kiosk&theme=transparent&refresh=30s`
- Iframe Height: 850px

**Summary Stats Row** (colored tiles):
- Total Containers (blue background)
- Running Containers (green background)
- Total Memory Used (orange background)
- Total CPU (circular gauge with thresholds)

**Memory Usage Bar Gauges** (horizontal gradient bars):
- Utilities VM containers - Blue-Yellow-Red gradient (sorted highest to lowest)
- Media VM containers - Blue-Yellow-Red gradient (sorted highest to lowest)

**CPU Usage Bar Gauges** (horizontal gradient bars):
- Utilities VM containers - Green-Yellow-Red gradient (sorted highest to lowest)
- Media VM containers - Green-Yellow-Red gradient (sorted highest to lowest)

**Sorting**: All bar gauge panels use `topk()` queries with `sortBy` transformation to display containers from highest to lowest utilization.

**Color Thresholds**:
- Memory: Green <70%, Yellow 70-90%, Red >90%
- CPU: Green <50%, Yellow 50-80%, Red >80%

**Visual Features**:
- Transparent dashboard background (`theme=transparent`)
- Hidden scrollbars via custom CSS
- Gradient bar gauges with continuous color mode

**Metrics Source**: docker-exporter on port 9417
- `docker_container_running`
- `docker_container_memory_percent`
- `docker_container_cpu_percent`
- `docker_container_memory_usage_bytes`

### Storage Tab

**Grafana Dashboard**: `synology-storage` (UID)
- URL: `https://grafana.hrmsmrflrii.xyz/d/synology-storage/synology-nas?kiosk&refresh=30s`
- Iframe Height: 500px

### Network Tab

**Grafana Dashboard**: `network-overview` (UID)
- URL: `https://grafana.hrmsmrflrii.xyz/d/network-overview/network-overview?kiosk&refresh=30s`
- Iframe Height: 750px

**Speedtest Widget**: Custom API showing Download/Upload/Ping from Speedtest Tracker

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
