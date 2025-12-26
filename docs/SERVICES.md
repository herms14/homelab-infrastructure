# Deployed Services

> Part of the [Proxmox Infrastructure Documentation](../CLAUDE.md)

## Service Overview

All services deployed via Docker Compose, managed by Ansible automation from `ansible-controller01`.

| Category | Host | Services |
|----------|------|----------|
| Reverse Proxy | traefik-vm01 | Traefik |
| Identity | authentik-vm01 | Authentik |
| Photos | immich-vm01, docker-vm-utilities01 | Immich, Lagident |
| DevOps | gitlab-vm01 | GitLab CE |
| CI/CD | gitlab-runner-vm01 | GitLab Runner, Ansible |
| Media | docker-vm-media01 | Arr Stack (12 services), Download Monitor |
| Media Tools | docker-vm-utilities01 | Wizarr (invites), Tracearr (tracking) |
| Dashboard | docker-vm-utilities01 | Glance, Life Progress API, Reddit Manager |
| Utilities | docker-vm-utilities01 | n8n, Paperless, Speedtest Tracker |
| Productivity | docker-vm-utilities01 | BentoPDF, Reactive Resume, Karakeep |
| RSS & News | docker-vm-utilities01 | Feeds Fun (AI RSS Reader) |
| Network Tools | docker-vm-utilities01 | Edgeshark (container network inspector) |
| Update Management | docker-vm-utilities01 | Watchtower, Update Manager (Discord bot) |
| Discord Bots | docker-vm-utilities01 | Argus SysAdmin Bot, Project Bot |
| Container Metrics | Both Docker hosts | Docker Stats Exporter |

## Traefik Reverse Proxy

**Host**: traefik-vm01 (192.168.40.20)
**Status**: Deployed December 19, 2025

| Port | URL | Purpose |
|------|-----|---------|
| 80 | http://192.168.40.20 | HTTP (redirects to HTTPS) |
| 443 | https://192.168.40.20 | HTTPS traffic |
| 8080 | http://192.168.40.20:8080 | Dashboard |

### Features

- Automatic HTTP to HTTPS redirect
- Dynamic service discovery via file configuration
- Pre-configured routes for all homelab services
- TLS termination with Let's Encrypt

### Storage

- Config: `/opt/traefik/`
  - Static: `/opt/traefik/config/traefik.yml`
  - Dynamic: `/opt/traefik/config/dynamic/services.yml`
  - Certs: `/opt/traefik/certs/`
  - Logs: `/opt/traefik/logs/`

### Add New Services

Edit `/opt/traefik/config/dynamic/services.yml` - changes auto-reload.

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.20 "cd /opt/traefik && sudo docker compose logs -f"

# Restart
ssh hermes-admin@192.168.40.20 "cd /opt/traefik && sudo docker compose restart"
```

**Ansible**: `~/ansible/traefik/deploy-traefik.yml`

---

## Arr Media Stack

**Host**: docker-vm-media01 (192.168.40.11)
**Status**: Deployed December 18, 2025

| Service | Port | Purpose |
|---------|------|---------|
| Jellyfin | 8096 | Media server |
| Radarr | 7878 | Movie management |
| Sonarr | 8989 | TV series management |
| Lidarr | 8686 | Music management |
| Prowlarr | 9696 | Indexer manager |
| Bazarr | 6767 | Subtitle management |
| Overseerr | 5055 | Media requests (Plex) |
| Jellyseerr | 5056 | Media requests (Jellyfin) |
| Tdarr | 8265 | Transcoding automation |
| Autobrr | 7474 | Torrent automation |
| Deluge | 8112 | BitTorrent download client |
| SABnzbd | 8081 | Usenet download client |

### Storage

- Config: `/opt/arr-stack/` (local)
- Media: `/mnt/media/` (NFS) - Unified mount for all services

**Unified Path Structure** (Updated December 23, 2025):

All arr-stack services use a unified `/data` mount inside containers pointing to `/mnt/media` on the host. This enables hardlinks and consistent paths across all services.

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `/mnt/media` | `/data` | Unified media mount (Radarr, Sonarr, Lidarr, Deluge, SABnzbd) |
| `/mnt/media/Movies` | `/data/Movies` | Movie library (Radarr root folder) |
| `/mnt/media/Series` | `/data/Series` | TV library (Sonarr root folder) |
| `/mnt/media/Music` | `/data/Music` | Music library (Lidarr root folder) |
| `/mnt/media/Completed` | `/data/Completed` | Download client completed folder |
| `/mnt/media/Downloading` | `/data/Downloading` | Active downloads |
| `/mnt/media/Incomplete` | `/data/Incomplete` | Incomplete downloads |

**App Path Configuration**:

| App | Root Folder | Download Path |
|-----|-------------|---------------|
| Radarr | `/data/Movies` | `/data/Completed` |
| Sonarr | `/data/Series` | `/data/Completed` |
| Lidarr | `/data/Music` | `/data/Completed` |
| Bazarr | `/data/Movies`, `/data/Series` | N/A |
| Deluge | N/A | `/data/Completed` |
| SABnzbd | N/A | `/data/Completed` |

### Inter-App Connections

| Connection | Status | Details |
|------------|--------|---------|
| Prowlarr -> Radarr | Configured | Full Sync, Movies categories |
| Prowlarr -> Sonarr | Configured | Full Sync, TV categories |
| Prowlarr -> Lidarr | Configured | Full Sync, Audio categories |
| Bazarr -> Radarr | Configured | Container: `radarr:7878` |
| Bazarr -> Sonarr | Configured | Container: `sonarr:8989` |
| Jellyseerr -> Jellyfin | Pending | Needs setup wizard |
| Radarr -> Deluge | Pending | Container: `deluge:8112` |
| Radarr -> SABnzbd | Pending | Container: `sabnzbd:8080` |
| Sonarr -> Deluge | Pending | Container: `deluge:8112` |
| Sonarr -> SABnzbd | Pending | Container: `sabnzbd:8080` |
| Lidarr -> Deluge | Pending | Container: `deluge:8112` |
| Lidarr -> SABnzbd | Pending | Container: `sabnzbd:8080` |

### Download Clients

**Deluge** (BitTorrent):
- Web UI: http://192.168.40.11:8112 | https://deluge.hrmsmrflrii.xyz
- Default password: `deluge` (change immediately)
- Enable label plugin for category support
- Ports: 8112 (web), 6881 (incoming TCP/UDP)
- Download paths (unified `/data` mount):
  - Downloading: `/data/Downloading`
  - Completed: `/data/Completed`
  - Incomplete: `/data/Incomplete`

**SABnzbd** (Usenet):
- Web UI: http://192.168.40.11:8081 | https://sabnzbd.hrmsmrflrii.xyz
- Complete setup wizard on first access
- Add Usenet server credentials in Config
- Get API key from Config → General → Security
- Configure categories: `radarr`, `sonarr`, `lidarr`
- Download paths (unified `/data` mount):
  - Temporary: `/data/Incomplete`
  - Completed: `/data/Completed`
  - Downloading: `/data/Downloading`

### Download Storage (NFS)

All media services use a unified NFS mount for hardlink support:

| Container Path | Host Path | NAS Location |
|---------------|-----------|--------------|
| `/data/Completed` | `/mnt/media/Completed` | NAS:/MediaFiles/Completed |
| `/data/Downloading` | `/mnt/media/Downloading` | NAS:/MediaFiles/Downloading |
| `/data/Incomplete` | `/mnt/media/Incomplete` | NAS:/MediaFiles/Incomplete |
| `/data/Movies` | `/mnt/media/Movies` | NAS:/MediaFiles/Movies |
| `/data/Series` | `/mnt/media/Series` | NAS:/MediaFiles/Series |

### API Keys

API keys are stored in your internal documentation. Access Settings > General > API Key in each service to retrieve them.

### Manual Setup Needed

- **Jellyfin**: Complete startup wizard, add media libraries
- **Bazarr**: Create language profile (Settings > Languages)
- **Jellyseerr**: Complete wizard, connect to Jellyfin + Radarr/Sonarr

**Ansible**: `~/ansible/docker/deploy-arr-stack.yml`
**Full Guide**: [ARR_STACK_DEPLOYMENT.md](./legacy/ARR_STACK_DEPLOYMENT.md)

---

## Authentik Identity Provider

**Host**: authentik-vm01 (192.168.40.21)
**Status**: Deployed December 18, 2025

| Port | URL | Purpose |
|------|-----|---------|
| 9000 | http://192.168.40.21:9000 | Web interface & API |
| 9443 | https://192.168.40.21:9443 | Secure web interface |

### Components

- Authentik Server (main application)
- Authentik Worker (background tasks)
- PostgreSQL (database)
- Redis (cache)

### Storage

`/opt/authentik/` (local storage)

> NFS storage not compatible due to all_squash permission restrictions

### Initial Setup

1. Navigate to http://192.168.40.21:9000/if/flow/initial-setup/
2. Create admin account (default username: `akadmin`)

**Ansible**: `~/ansible/authentik/deploy-authentik.yml`

---

## Immich Photo Management

**Host**: immich-vm01 (192.168.40.22)
**Status**: Deployed December 19, 2025, Updated December 21, 2025

| Port | URL | Purpose |
|------|-----|---------|
| 2283 | http://192.168.40.22:2283 | Web interface & API |

### Components

- Immich Server (web UI)
- Immich Machine Learning (face/object recognition)
- PostgreSQL with pgvecto-rs (vector database)
- Redis (cache and job queue)

### Storage Architecture

Immich uses a dual-storage architecture with Synology NAS:

| Zone | Host Mount | Container Path | Mode | Purpose |
|------|------------|----------------|------|---------|
| Active Uploads | `/mnt/immich-uploads` | `/usr/src/app/upload` | RW | New photos from Immich |
| Legacy Photos | `/mnt/synology-photos` | `/usr/src/app/external/synology` | RO | Historical archive |
| Local Config | `/opt/immich/` | Various | RW | PostgreSQL, ML models |

**NAS Configuration** (192.168.20.31):
- Active uploads: `/volume2/Immich Photos` (dedicated share)
- Legacy photos: `/volume2/homes/hermes-admin/Photos` (bind mount from homes)

**Local Storage**:
- Docker Compose: `/opt/immich/docker-compose.yml`
- PostgreSQL: `/opt/immich/postgres/`
- ML Models: `/opt/immich/model-cache/`

### Features

- Automatic photo/video backup from mobile devices
- Face recognition and person tagging
- Object and scene detection
- Timeline and map view
- Album sharing
- Duplicate detection
- External library support (read-only legacy photos)

### Initial Setup

1. Navigate to http://192.168.40.22:2283
2. Create admin account
3. Download Immich mobile app (iOS/Android)
4. Server URL for mobile: `http://192.168.40.22:2283/api`
5. Add external library: Admin → External Libraries → Path: `/usr/src/app/external/synology`

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.22 "cd /opt/immich && sudo docker compose logs -f"

# Update
ssh hermes-admin@192.168.40.22 "cd /opt/immich && sudo docker compose pull && sudo docker compose up -d"

# Verify mounts
ssh hermes-admin@192.168.40.22 "mount | grep -E 'synology|immich'"
```

**Ansible**: `~/ansible/immich/deploy-immich.yml`
**Detailed Config**: [APPLICATION_CONFIGURATIONS.md](./APPLICATION_CONFIGURATIONS.md#immich-photo-management)

---

## GitLab CE DevOps Platform

**Host**: gitlab-vm01 (192.168.40.23)
**Status**: Deployed December 19, 2025

| Port | URL | Purpose |
|------|-----|---------|
| 80 | http://192.168.40.23 | Web UI |
| 443 | https://192.168.40.23 | Secure web |
| 2222 | ssh://git@192.168.40.23:2222 | Git SSH |

### Features

- Unlimited private repositories
- CI/CD pipelines with GitLab Runner
- Issue tracking and project management
- Wiki and documentation
- Merge requests with code review
- Container registry (disabled by default)

### Components (all-in-one container)

Nginx, Puma, Sidekiq, PostgreSQL, Redis, Gitaly

### Storage

All data: `/opt/gitlab/`
- Config: `/opt/gitlab/config/`
- Logs: `/opt/gitlab/logs/`
- Data: `/opt/gitlab/data/`

### Initial Setup

1. Wait 3-5 minutes for GitLab to initialize
2. Get initial root password:
   ```bash
   ssh hermes-admin@192.168.40.23 "sudo docker exec gitlab grep 'Password:' /etc/gitlab/initial_root_password"
   ```
3. Login with username `root`
4. Change password immediately!

> Initial password file deleted after 24 hours!

### Clone Repositories

```bash
# HTTPS
git clone http://192.168.40.23/username/project.git

# SSH
git clone ssh://git@192.168.40.23:2222/username/project.git
```

### Management

```bash
# GitLab status
ssh hermes-admin@192.168.40.23 "sudo docker exec gitlab gitlab-ctl status"

# Reconfigure
ssh hermes-admin@192.168.40.23 "sudo docker exec gitlab gitlab-ctl reconfigure"
```

**Ansible**: `~/ansible/gitlab/deploy-gitlab.yml`

---

## GitLab Runner CI/CD

**Host**: gitlab-runner-vm01 (192.168.40.24)
**Status**: Deployed December 21, 2025

### Purpose

Dedicated CI/CD job executor for GitLab pipelines. Automates the entire service onboarding workflow when `service.yml` is committed to a repository.

### Components

- **GitLab Runner**: Shell executor registered with GitLab
- **Ansible**: Playbook execution for container deployment
- **Python Automation Scripts**: 9 scripts for pipeline stages

### Automation Pipeline

When a `service.yml` is committed, the pipeline:

1. Validates configuration
2. Deploys container via Ansible
3. Configures Traefik reverse proxy
4. Adds DNS record in OPNsense
5. Registers with Watchtower
6. Sends Discord notification
7. (Optional) Configures Authentik SSO

### Storage

- Scripts: `/opt/gitlab-runner/scripts/`
- Ansible: `/home/gitlab-runner/ansible/`

### Management

```bash
# Check runner status
ssh hermes-admin@192.168.40.24 "sudo gitlab-runner status"

# Verify runner registration
ssh hermes-admin@192.168.40.24 "sudo gitlab-runner verify"

# Test Ansible connectivity
ssh hermes-admin@192.168.40.24 "sudo -u gitlab-runner ansible docker-vm-utilities01 -m ping"
```

**Full Guide**: [CICD.md](./CICD.md)

---

## n8n Workflow Automation

**Host**: docker-vm-utilities01 (192.168.40.10)
**Status**: Deployed December 19, 2025

| Port | URL | Purpose |
|------|-----|---------|
| 5678 | http://192.168.40.10:5678 | Workflow editor |
| 443 | https://n8n.hrmsmrflrii.xyz | Via Traefik |

### Features

- Visual workflow builder (node-based)
- 400+ integrations
- Webhook triggers
- Schedule-based execution
- Self-hosted with full data control

### Storage

- Config & Workflows: `/opt/n8n/data/` (local)
- Database: SQLite (default)

### Initial Setup

1. Navigate to https://n8n.hrmsmrflrii.xyz
2. Create admin account on first access

### Management

```bash
# Update
ssh hermes-admin@192.168.40.10 "cd /opt/n8n && sudo docker compose pull && sudo docker compose up -d"
```

**Ansible**: `~/ansible/n8n/deploy-n8n.yml`

---

## Speedtest Tracker

**Host**: docker-vm-utilities01 (192.168.40.10)
**Status**: Deployed December 22, 2025

| Port | URL | Purpose |
|------|-----|---------|
| 3000 | http://192.168.40.10:3000 | Web interface |
| 443 | https://speedtest.hrmsmrflrii.xyz | Via Traefik |

### Purpose

Scheduled network speed tests with historical tracking and visualization. Automatically runs tests every 6 hours and stores results for trend analysis.

### Features

- Scheduled speed tests (Ookla Speedtest CLI)
- Historical results with graphs
- Download, upload, and ping tracking
- Multi-server support
- Dark theme interface
- SQLite database for lightweight storage

### Schedule

Tests run automatically every 6 hours (configurable via `SPEEDTEST_SCHEDULE` cron expression).

### Storage

- Config & Database: `/opt/speedtest-tracker/data/`
- Docker Compose: `/opt/speedtest-tracker/docker-compose.yml`

### Initial Setup

1. Navigate to https://speedtest.hrmsmrflrii.xyz
2. Default login: `admin@example.com` / `password`
3. Change credentials immediately in Settings

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.10 "docker logs speedtest-tracker"

# Trigger manual test
ssh hermes-admin@192.168.40.10 "docker exec speedtest-tracker php artisan app:ookla-speedtest"

# Update
ssh hermes-admin@192.168.40.10 "cd /opt/speedtest-tracker && sudo docker compose pull && sudo docker compose up -d"
```

**GitHub**: https://github.com/alexjustesen/speedtest-tracker

---

## Glance Dashboard

**Host**: docker-vm-utilities01 (192.168.40.10)
**Status**: Deployed December 2025

| Port | URL | Purpose |
|------|-----|---------|
| 8080 | http://192.168.40.10:8080 | Dashboard |
| 5054 | http://192.168.40.10:5054 | Media Stats API |
| 443 | https://glance.hrmsmrflrii.xyz | Via Traefik |

### Features

- Self-hosted dashboard with multiple widget types
- Service health monitoring (Proxmox, K8s, Traefik, etc.)
- Market data (Bitcoin, stocks)
- RSS feeds from Reddit
- NBA/NFL scores
- Network device monitoring
- Life Progress widget with API integration
- Synology NAS monitoring (embedded Grafana)
- **Media Stats Grid** - Radarr/Sonarr stats in colorful 3x2 tile grid

### Pages (7 Tabs)

| Page | Widgets | Protected |
|------|---------|-----------|
| **Home** | Life Progress, Service Health, K8s Cluster, Markets, RSS | YES |
| **Compute** | Proxmox Cluster Dashboard + Container Monitoring (modern bar gauges) | No |
| **Storage** | Synology NAS Dashboard (iframe) | No |
| **Network** | Network Overview Dashboard + Speedtest widget | No |
| **Media** | Media Stats Grid, Recent Downloads, Download Queue | YES |
| **Web** | Tech News, AI/ML feeds, Stocks, NBA Scores | No |
| **Reddit** | Dynamic Reddit Feed (via Reddit Manager) | No |

### Grafana Dashboards (Embedded)

| Dashboard | UID | Tab | Height |
|-----------|-----|-----|--------|
| Proxmox Cluster | `proxmox-compute` | Compute | 1100px |
| Container Monitoring | `containers-modern` | Compute | 850px |
| Synology NAS | `synology-storage` | Storage | 500px |
| Network Overview | `network-overview` | Network | 750px |

**Features**: All dashboards use `theme=transparent` and hidden scrollbars via custom CSS.

### Media Stats API

Aggregates Radarr and Sonarr statistics for the dashboard grid widget.

| Endpoint | Purpose |
|----------|---------|
| `/api/stats` | Combined media statistics |
| `/health` | Health check |

Location: `/opt/media-stats-api/`

See [GLANCE.md](./GLANCE.md) for detailed implementation guide.

### Storage

- Config: `/opt/glance/config/glance.yml`
- Secrets: `/opt/glance/.env`
- Assets: `/opt/glance/assets/`

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.10 "cd /opt/glance && sudo docker compose logs -f"

# Restart
ssh hermes-admin@192.168.40.10 "cd /opt/glance && sudo docker compose restart"

# Update
ssh hermes-admin@192.168.40.10 "cd /opt/glance && sudo docker compose pull && sudo docker compose up -d"
```

**Ansible**: `~/ansible/glance/deploy-glance-dashboard.yml`

---

## Reddit Manager

**Host**: docker-vm-utilities01 (192.168.40.10)
**Status**: Deployed December 22, 2025

| Port | URL | Purpose |
|------|-----|---------|
| 5053 | http://192.168.40.10:5053 | Management UI & API |

### Purpose

Flask API that provides dynamic subreddit management for Glance dashboard. Allows adding/removing subreddits via web UI and fetches Reddit posts with thumbnails for display.

### Features

- **Dynamic Subreddit Management**: Add/remove subreddits without config file editing
- **Web Management UI**: Simple interface at port 5053
- **Thumbnail Support**: Fetches and displays post thumbnails from Reddit
- **Grouped View**: Posts organized by subreddit with headers
- **Sort Options**: Hot, New, or Top posts (configurable)
- **Parallel Fetching**: All subreddits fetched concurrently for fast response
- **Caching**: 5-minute cache to reduce Reddit API calls

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Management UI (web interface) |
| GET | `/api/subreddits` | List configured subreddits |
| POST | `/api/subreddits` | Add subreddit `{"name": "programming"}` |
| DELETE | `/api/subreddits/<name>` | Remove subreddit |
| GET | `/api/settings` | Get current sort/view settings |
| POST | `/api/settings` | Update settings `{"sort": "new", "view": "grouped"}` |
| GET | `/api/feed` | Get combined feed (grouped or combined) |
| GET | `/api/feed/<subreddit>` | Get single subreddit feed |
| GET | `/health` | Health check |

### Settings

| Setting | Options | Default | Description |
|---------|---------|---------|-------------|
| sort | hot, new, top | hot | Post sort order |
| view | grouped, combined | grouped | Display mode |

### Glance Integration

Uses `custom-api` widget with Go template:

```yaml
- type: custom-api
  title: Reddit Feed
  cache: 5m
  url: http://192.168.40.10:5053/api/feed
  template: |
    {{ range .JSON.Array "groups" }}
    <div>r/{{ .String "name" }}</div>
    {{ range .Array "posts" }}
      {{ .String "title" }} - {{ .Int "score" }} pts
    {{ end }}
    {{ end }}
```

### Storage

- Flask App: `/opt/reddit-manager/reddit-manager.py`
- Dockerfile: `/opt/reddit-manager/Dockerfile`
- Docker Compose: `/opt/reddit-manager/docker-compose.yml`
- Data: `/opt/reddit-manager/data/`
  - `subreddits.json`: Configured subreddit list
  - `settings.json`: Sort/view preferences

### Default Subreddits

homelab, selfhosted, linux, devops, kubernetes, docker

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.10 "docker logs reddit-manager --tail 50"

# Test API
curl http://192.168.40.10:5053/api/feed

# Add subreddit
curl -X POST http://192.168.40.10:5053/api/subreddits -H "Content-Type: application/json" -d '{"name": "programming"}'

# Change sort to "new"
curl -X POST http://192.168.40.10:5053/api/settings -H "Content-Type: application/json" -d '{"sort": "new"}'

# Rebuild after code changes
ssh hermes-admin@192.168.40.10 "cd /opt/reddit-manager && sudo docker compose build --no-cache && sudo docker compose up -d"
```

### Troubleshooting

**Glance shows timeout error**:
- Reddit Manager fetches all subreddits in parallel to stay under Glance's timeout
- Check if Reddit API is accessible from the container
- Verify with: `curl http://192.168.40.10:5053/api/feed`

**Template errors in Glance**:
- Glance uses Go templates with specific syntax
- Use `.JSON.Array "key"` for arrays, `.String "key"` for strings
- Nested access: `.Array "posts"` inside a range block

**Ansible**: `~/ansible/reddit-manager/deploy-reddit-manager.yml`

---

## Life Progress API

**Host**: docker-vm-utilities01 (192.168.40.10)
**Status**: Deployed December 22, 2025

| Port | URL | Purpose |
|------|-----|---------|
| 5051 | http://192.168.40.10:5051/progress | JSON API |
| 5051 | http://192.168.40.10:5051/health | Health check |

### Purpose

Flask API that calculates life progress percentages for Glance dashboard integration. Shows Year/Month/Day/Life progress bars with daily rotating motivational quotes.

### Configuration

| Setting | Value |
|---------|-------|
| Birth Date | February 14, 1989 |
| Target Age | 75 years |
| Quote Pool | 30 quotes (daily rotation) |

### API Response

```json
{
  "year": 97.4,
  "month": 69.5,
  "day": 53.3,
  "life": 49.1,
  "age": 36.9,
  "remaining_years": 38.1,
  "remaining_days": 13933,
  "quote": "Time is the wisest counselor of all. - Pericles",
  "target_age": 75
}
```

### Glance Integration

Uses `custom-api` widget with gjson templates:

```yaml
- type: custom-api
  url: http://192.168.40.10:5051/progress
  template: |
    {{ .JSON.Float "year" }}
    {{ .JSON.String "quote" }}
    {{ .JSON.Int "remaining_days" }}
```

### Storage

- Flask App: `/opt/life-progress/app.py`
- Dockerfile: `/opt/life-progress/Dockerfile`
- Docker Compose: `/opt/life-progress/docker-compose.yml`

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.10 "docker logs life-progress"

# Test API
curl http://192.168.40.10:5051/progress

# Rebuild (after config changes)
ssh hermes-admin@192.168.40.10 "cd /opt/life-progress && sudo docker compose up -d --build"
```

**Ansible**: `~/ansible/glance/deploy-life-progress-api.yml`
**GitHub**: https://github.com/herms14/life-progress-api

---

## Monitoring Stack

**Host**: docker-vm-utilities01 (192.168.40.10)
**Status**: Deployed December 20, 2025

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| Uptime Kuma | 3001 | https://uptime.hrmsmrflrii.xyz | Service uptime monitoring |
| Prometheus | 9090 | https://prometheus.hrmsmrflrii.xyz | Metrics collection |
| Grafana | 3030 | https://grafana.hrmsmrflrii.xyz | Dashboards & visualization |

### Components

- **Uptime Kuma**: Service availability monitoring with ICMP ping and HTTP checks
- **Prometheus**: Time-series metrics database for infrastructure monitoring
- **Grafana**: Dashboard visualization (default login: admin/admin)

### Datasources

- **Prometheus**: Default datasource for metrics
- **Jaeger**: Distributed tracing datasource

### Dashboards

- **Proxmox Cluster Overview**: Node status, memory, CPU metrics
- **Traefik Observability**: Request rate, latency, error rate, status codes

### Prometheus Scrape Targets

| Target | Endpoint | Purpose |
|--------|----------|---------|
| Prometheus | localhost:9090 | Self-monitoring |
| Proxmox VE | via PVE Exporter | Node metrics |
| Traefik | 192.168.40.20:8082 | Request metrics |
| OTEL Collector | 192.168.40.10:8888 | Collector metrics |
| OTEL Pipeline | 192.168.40.10:8889 | Pipeline metrics |
| Jaeger | 192.168.40.10:14269 | Tracing metrics |
| Demo App | 192.168.40.10:8080 | Application metrics |

### Storage

- Config: `/opt/monitoring/`
  - Docker Compose: `/opt/monitoring/docker-compose.yml`
  - Uptime Kuma: `/opt/monitoring/uptime-kuma/`
  - Prometheus: `/opt/monitoring/prometheus/`
  - Grafana: `/opt/monitoring/grafana/`

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.10 "cd /opt/monitoring && sudo docker compose logs -f"

# Restart all
ssh hermes-admin@192.168.40.10 "cd /opt/monitoring && sudo docker compose restart"

# Update
ssh hermes-admin@192.168.40.10 "cd /opt/monitoring && sudo docker compose pull && sudo docker compose up -d"
```

**Ansible**: `~/ansible-playbooks/monitoring/deploy-monitoring-stack.yml`

---

## Observability Stack

**Host**: docker-vm-utilities01 (192.168.40.10)
**Status**: Deployed December 21, 2025

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| OTEL Collector | 4317/4318 | Internal | Trace/metrics collection |
| Jaeger | 16686 | https://jaeger.hrmsmrflrii.xyz | Distributed tracing UI |
| Demo App | 8080 | https://demo.hrmsmrflrii.xyz | Instrumented test app |

### Components

- **OpenTelemetry Collector**: Central receiver for traces and metrics from Traefik and applications
- **Jaeger**: Distributed tracing visualization with OTLP support
- **Demo App**: Python/Flask application instrumented with OpenTelemetry for testing

### Trace Flow

```
Traefik → OTEL Collector → Jaeger → Grafana (optional)
Demo App ↗
```

### Demo App Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Simple response with user info |
| `/api/data` | Complex operation showing cache, DB, external API spans |
| `/api/slow` | Slow operation (1-3s) for latency testing |
| `/api/error` | Random failures for error trace testing |
| `/health` | Health check |
| `/metrics` | Prometheus metrics |

### Storage

- Config: `/opt/observability/`
  - Docker Compose: `/opt/observability/docker-compose.yml`
  - OTEL Collector: `/opt/observability/otel-collector/`
  - Demo App: `/opt/observability/demo-app/`
  - Jaeger data: Docker volume (in-memory, 50k traces max)

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.10 "cd /opt/observability && sudo docker compose logs -f"

# Restart all
ssh hermes-admin@192.168.40.10 "cd /opt/observability && sudo docker compose restart"

# Update
ssh hermes-admin@192.168.40.10 "cd /opt/observability && sudo docker compose pull && sudo docker compose up -d"
```

**Ansible**: `~/ansible-playbooks/monitoring/deploy-observability-stack.yml`
**Full Guide**: [OBSERVABILITY.md](./OBSERVABILITY.md)

---

## Watchtower & Update Manager

**Host**: docker-vm-utilities01 (192.168.40.10) + All Docker hosts
**Status**: Deployed December 2025

| Service | Port | Purpose |
|---------|------|---------|
| Watchtower | - | Container update monitoring (6 hosts) |
| Update Manager | 5050 | Discord bot for interactive approvals + onboarding checker |

### Overview

Watchtower monitors all Docker containers across 6 hosts for available updates. Instead of auto-updating, it sends notifications to a Discord channel where the user can approve or reject updates with emoji reactions.

### Components

- **Watchtower**: Deployed on all 6 Docker hosts in monitor-only mode
- **Update Manager**: Python Discord bot + Flask webhook receiver + Service Onboarding Checker

### Discord Bot Commands

| Command | Description |
|---------|-------------|
| `check versions` | Scan all services for available updates |
| `update all` | Update all pending services |
| `update <service>` | Update specific service |
| `help` | Show available commands |

### Service Onboarding Checker (Slash Commands)

| Command | Description |
|---------|-------------|
| `/onboard <service>` | Check onboarding status for a specific service |
| `/onboard-all` | Check all services and show status table |
| `/onboard-services` | List all discovered services from Traefik |

### Onboarding Checks

The checker validates these configurations for each service:

| Check | Method |
|-------|--------|
| Terraform | Searches `main.tf` for VM definition |
| Ansible | Searches playbooks in `~/ansible/` |
| DNS | Resolves `service.hrmsmrflrii.xyz` |
| Traefik | Parses `/opt/traefik/config/dynamic/services.yml` |
| SSL | Checks for `certResolver` in Traefik config |
| Authentik | Queries Authentik API for application (optional) |
| Documentation | Searches `docs/SERVICES.md` |

### Output Format

```
Service         | TF  | Ans | DNS | Traf | SSL | Auth | Docs
----------------|-----|-----|-----|------|-----|------|-----
jellyfin        |  ✓  |  ✓  |  ✓  |   ✓  |  ✓  |   -  |   ✓
radarr          |  ✓  |  ✓  |  ✓  |   ✓  |  ✓  |   -  |   ✓
```

### Scheduled Reports

- **Daily 9am EST**: Automatic status report posted to #new-service-onboarding-workflow channel
- **CI/CD Trigger**: Webhook endpoint `/onboard-check` called after successful deployments

### Workflow

1. Watchtower detects update at 3 AM daily
2. Webhook sent to Update Manager
3. Discord notification with 👍/👎 reactions
4. User approves → SSH update executed
5. Completion notification sent

### Storage

- Watchtower Config: `/opt/watchtower/` (each host)
- Update Manager: `/opt/update-manager/` (utilities host)

### Management

```bash
# Check Update Manager status
ssh hermes-admin@192.168.40.10 "docker ps --filter name=update-manager"

# View Update Manager logs
ssh hermes-admin@192.168.40.10 "docker logs update-manager --tail 50"

# Trigger manual update check (media host)
ssh hermes-admin@192.168.40.11 "docker exec watchtower /watchtower --run-once"

# Rebuild after code changes
ssh hermes-admin@192.168.40.10 "cd /opt/update-manager && sudo docker compose build --no-cache && sudo docker compose up -d"
```

**Full Guide**: [WATCHTOWER.md](./WATCHTOWER.md)

---

## BentoPDF

**Host**: docker-vm-utilities01 (192.168.40.10)
**Status**: Deployed December 24, 2025

| Port | URL | Purpose |
|------|-----|---------|
| 5055 | http://192.168.40.10:5055 | Web interface |
| 443 | https://bentopdf.hrmsmrflrii.xyz | Via Traefik |

### Purpose

Privacy-first PDF toolkit for document manipulation without uploading to cloud services. All processing happens locally within your infrastructure.

### Features

- PDF merging, splitting, and conversion
- Document compression
- Page extraction and reordering
- Watermarking and annotation
- No data leaves your server

### Storage

- Docker Compose: `/opt/bentopdf/docker-compose.yml`

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.10 "docker logs bentopdf"

# Update
ssh hermes-admin@192.168.40.10 "cd /opt/bentopdf && sudo docker compose pull && sudo docker compose up -d"
```

**Docker Image**: `bentopdf/bentopdf:latest`

---

## Edgeshark

**Host**: docker-vm-utilities01 (192.168.40.10)
**Status**: Deployed December 24, 2025

| Port | URL | Purpose |
|------|-----|---------|
| 5056 | http://192.168.40.10:5056 | Web interface |
| 443 | https://edgeshark.hrmsmrflrii.xyz | Via Traefik |

### Purpose

Docker container network inspector by Siemens. Visualizes container network connections, namespaces, and packet flows. Useful for debugging container networking issues.

### Components

| Container | Image | Purpose |
|-----------|-------|---------|
| ghostwire | ghcr.io/siemens/ghostwire | Network discovery engine |
| edgeshark | ghcr.io/siemens/packetflix | Web UI and packet capture |

### Features

- Container network namespace visualization
- Live packet capture (Wireshark compatible)
- Cross-container connection mapping
- Network namespace inspection
- Docker socket monitoring

### Storage

- Docker Compose: `/opt/edgeshark/docker-compose.yml`

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.10 "docker logs edgeshark && docker logs ghostwire"

# Update
ssh hermes-admin@192.168.40.10 "cd /opt/edgeshark && sudo docker compose pull && sudo docker compose up -d"
```

**GitHub**: https://github.com/siemens/edgeshark

---

## Reactive Resume

**Host**: docker-vm-utilities01 (192.168.40.10)
**Status**: Deployed December 24, 2025

| Port | URL | Purpose |
|------|-----|---------|
| 5057 | http://192.168.40.10:5057 | Web interface |
| 443 | https://resume.hrmsmrflrii.xyz | Via Traefik |

### Purpose

Self-hosted resume builder with modern templates and real-time preview. Create professional resumes and export to PDF without relying on third-party services.

### Components

| Container | Image | Purpose |
|-----------|-------|---------|
| reactive-resume | amruthpillai/reactive-resume | Main application |
| reactive-resume-db | postgres:16-alpine | PostgreSQL database |
| reactive-resume-minio | minio/minio | Object storage for files |
| reactive-resume-chrome | ghcr.io/browserless/chromium | PDF generation |

### Features

- Multiple professional templates
- Real-time preview
- JSON resume import/export
- PDF export via headless Chrome
- Multi-language support
- Dark mode interface

### Storage

- Docker Compose: `/opt/reactive-resume/docker-compose.yml`
- PostgreSQL Data: Docker volume `postgres_data`
- MinIO Storage: Docker volume `minio_data`

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.10 "docker logs reactive-resume"

# Update
ssh hermes-admin@192.168.40.10 "cd /opt/reactive-resume && sudo docker compose pull && sudo docker compose up -d"
```

**GitHub**: https://github.com/AmruthPillai/Reactive-Resume (30k+ stars)

---

## Argus SysAdmin Discord Bot

**Host**: docker-vm-utilities01 (192.168.40.10)
**Status**: Deployed December 22, 2025

### Purpose

Discord bot for comprehensive homelab management via slash commands. Named "Argus" after the all-seeing giant of Greek mythology.

### Features

- Proxmox cluster management (VMs, nodes)
- Docker container operations
- System monitoring and health checks
- Media request integration (Radarr/Sonarr)
- Infrastructure deployment via Ansible

### Commands

| Command | Description |
|---------|-------------|
| `/status` | Get Proxmox cluster status |
| `/shutdown <node>` | Shutdown Proxmox node |
| `/reboot <target>` | Reboot VM or node |
| `/start <vm>` | Start a VM |
| `/stop <vm>` | Stop a VM |
| `/vms` | List all VMs with status |
| `/uptime` | Show cluster uptime |
| `/restart <container>` | Restart Docker container |
| `/logs <container>` | View container logs |
| `/containers <host>` | List containers on host |
| `/deploy <playbook>` | Run Ansible playbook |
| `/health` | System health check |
| `/disk` | Show disk usage |
| `/top` | Top resource consumers |
| `/bandwidth` | Network bandwidth stats |
| `/request <type> <title>` | Request movie/show |
| `/media` | Media library stats |
| `/help` | Show all commands |

### Architecture

Uses SSH for all Proxmox operations (no API token required):
- Connects to nodes as `root` via SSH key
- Connects to VMs as `hermes-admin`
- All operations executed via paramiko SSH client

### Discord Channel

- **Channel**: `#argus-assistant` (1452673126314803338)
- All commands and responses restricted to this channel

### Storage

- Bot Code: `/opt/sysadmin-bot/sysadmin-bot.py`
- Docker Compose: `/opt/sysadmin-bot/docker-compose.yml`
- SSH Keys: `/opt/sysadmin-bot/ssh/` (mounted read-only)

### Management

```bash
# View bot logs
ssh hermes-admin@192.168.40.10 "docker logs sysadmin-bot --tail 50"

# Restart bot
ssh hermes-admin@192.168.40.10 "cd /opt/sysadmin-bot && sudo docker compose restart"

# Rebuild after code changes
ssh hermes-admin@192.168.40.10 "cd /opt/sysadmin-bot && sudo docker compose build --no-cache && sudo docker compose up -d"
```

**Ansible**: `~/ansible-playbooks/sysadmin-bot/deploy-sysadmin-bot.yml`

---

## Download Monitor

**Host**: docker-vm-media01 (192.168.40.11)
**Status**: Deployed December 22, 2025

| Port | Purpose |
|------|---------|
| 5052 | Flask API & webhook receiver |

### Purpose

Monitors Radarr and Sonarr for download completions and sends formatted Discord notifications with media details including poster images.

### Features

- Real-time download completion notifications
- Poster images embedded in Discord messages
- Movie details: title, year, quality, size, runtime
- TV show details: series, season, episode, quality
- Webhook integration with Radarr/Sonarr

### Discord Channel

- **Channel**: `#media-downloads` (1452132982436401346)
- All download notifications posted here

### Radarr/Sonarr Configuration

Add webhook in each application:
- **URL**: `http://download-monitor:5052/webhook/radarr` or `/webhook/sonarr`
- **Trigger**: On Download / On Upgrade

### Storage

- Flask App: `/opt/download-monitor/download-monitor.py`
- Docker Compose: `/opt/download-monitor/docker-compose.yml`

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.11 "docker logs download-monitor --tail 50"

# Test webhook
curl -X POST http://192.168.40.11:5052/webhook/radarr -H "Content-Type: application/json" -d '{"eventType": "Test"}'

# Restart
ssh hermes-admin@192.168.40.11 "cd /opt/download-monitor && sudo docker compose restart"
```

**Ansible**: `~/ansible-playbooks/arr-stack/deploy-download-monitor.yml`

---

## Docker Stats Exporter

**Hosts**: docker-vm-utilities01 (192.168.40.10), docker-vm-media01 (192.168.40.11)
**Status**: Deployed December 22, 2025

| Port | Purpose |
|------|---------|
| 9417 | Prometheus metrics endpoint |

### Purpose

Exports Docker container metrics to Prometheus for monitoring in Grafana dashboards.

### Metrics Exported

| Metric | Description |
|--------|-------------|
| `container_cpu_usage_percent` | CPU usage percentage |
| `container_memory_usage_bytes` | Memory usage in bytes |
| `container_memory_limit_bytes` | Memory limit |
| `container_network_rx_bytes` | Network bytes received |
| `container_network_tx_bytes` | Network bytes transmitted |
| `container_block_read_bytes` | Block I/O read |
| `container_block_write_bytes` | Block I/O write |
| `container_running` | Running status (1/0) |

### Prometheus Scrape Config

```yaml
- job_name: 'docker-stats'
  static_configs:
    - targets:
      - 192.168.40.10:9417
      - 192.168.40.11:9417
```

### Storage

- Exporter: `/opt/docker-stats-exporter/`
- Docker Compose: Part of monitoring stack

### Management

```bash
# View metrics
curl http://192.168.40.10:9417/metrics

# Check status
ssh hermes-admin@192.168.40.10 "docker ps --filter name=docker-stats-exporter"
```

### Grafana Dashboard

Container metrics displayed in Grafana at:
- Dashboard: "Container Monitoring"
- Datasource: Prometheus
- Refresh: 30s

**Ansible**: Deployed with monitoring stack

---

## New Services (December 2025)

### Lagident - Photo Gallery

**Host**: docker-vm-utilities01 (192.168.40.10)
**Port**: 9933
**URL**: https://lagident.hrmsmrflrii.xyz
**Status**: Deployed December 25, 2025

Simple, elegant photo gallery with SQLite backend.

| Feature | Description |
|---------|-------------|
| Database | SQLite (lightweight) |
| Platform | Go + Node.js |
| Architecture | amd64, arm64 |

### Storage

- Config & Database: `/opt/lagident/`
- Photos: `/opt/lagident/photos/`

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.10 "docker logs lagident"

# Update
ssh hermes-admin@192.168.40.10 "cd /opt/lagident && sudo docker compose pull && sudo docker compose up -d"
```

**Ansible**: `ansible-playbooks/services/deploy-lagident.yml`

---

### Karakeep - Bookmark Manager

**Host**: docker-vm-utilities01 (192.168.40.10)
**Port**: 3005
**URL**: https://karakeep.hrmsmrflrii.xyz
**Status**: Deployed December 25, 2025

AI-powered bookmark and content manager (formerly Hoarder).

| Component | Port | Purpose |
|-----------|------|---------|
| Karakeep | 3005 | Main application |
| Meilisearch | 7700 | Full-text search |
| Chrome | 9222 | Screenshot capture |

**Features**:
- Automatic content tagging (with OpenAI API)
- Full-text search via Meilisearch
- Screenshot capture for bookmarks
- Browser extension support

### Storage

- Config: `/opt/karakeep/`
- Data: Docker volumes `karakeep-data`, `meilisearch-data`

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.10 "docker logs karakeep"

# Update
ssh hermes-admin@192.168.40.10 "cd /opt/karakeep && sudo docker compose pull && sudo docker compose up -d"
```

**Ansible**: `ansible-playbooks/services/deploy-karakeep.yml`

---

### Wizarr - Jellyfin Invitation System

**Host**: docker-vm-utilities01 (192.168.40.10)
**Port**: 5690
**URL**: https://wizarr.hrmsmrflrii.xyz
**Status**: Deployed December 25, 2025

User invitation and onboarding system for Jellyfin.

| Feature | Description |
|---------|-------------|
| Integration | Jellyfin, Plex, Emby, AudiobookShelf |
| Invitations | Generate shareable invite links |
| Onboarding | Guided setup wizard for new users |

**Jellyfin Configuration**:
1. Access https://wizarr.hrmsmrflrii.xyz
2. Complete setup wizard
3. Configure Jellyfin URL: http://192.168.40.11:8096
4. Get API key from Jellyfin Admin > API Keys
5. Create invitation links to share with users

### Storage

- Config & Database: `/opt/wizarr/data/`

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.10 "docker logs wizarr"

# Update
ssh hermes-admin@192.168.40.10 "cd /opt/wizarr && sudo docker compose pull && sudo docker compose up -d"
```

**Ansible**: `ansible-playbooks/services/deploy-wizarr.yml`

---

### Feeds Fun - AI RSS Reader

**Host**: docker-vm-utilities01 (192.168.40.10)
**Port**: 8001
**URL**: https://feeds.hrmsmrflrii.xyz
**Status**: Not Deployed (no public Docker image)

Self-hosted RSS reader with AI-powered tagging.

> **Note**: This service requires building from source. No official Docker image is published.

| Component | Port | Purpose |
|-----------|------|---------|
| API Server | 8001 | Main application |
| Worker | - | Feed processing |
| PostgreSQL | 5432 | Database |

**Features**:
- AI-powered content tagging (OpenAI/Ollama)
- Full-text search
- Single-user mode (simplified auth)
- Background feed processing

**GitHub**: https://github.com/Tiendil/feeds.fun

---

### Tracearr - Media Tracking

**Host**: docker-vm-utilities01 (192.168.40.10)
**Port**: 3002
**URL**: https://tracearr.hrmsmrflrii.xyz
**Status**: Deployed December 25, 2025

Streaming access manager for Plex, Jellyfin, and Emby servers. Tracks who's using your server and detects shared logins.

| Component | Notes |
|-----------|-------|
| Image | Supervised (all-in-one) |
| Database | TimescaleDB (bundled) |
| Cache | Redis (bundled) |

**Features**:
- Track streaming activity across users
- Detect shared/abused logins
- Analytics dashboard
- User session history

### Storage

- Data: Docker volume `tracearr-data`

### Management

```bash
# View logs
ssh hermes-admin@192.168.40.10 "docker logs tracearr"

# Update
ssh hermes-admin@192.168.40.10 "cd /opt/tracearr && sudo docker compose pull && sudo docker compose up -d"
```

**Ansible**: `ansible-playbooks/services/deploy-tracearr.yml`
**GitHub**: https://github.com/connorgallopo/Tracearr

---

## Related Documentation

- [Networking](./NETWORKING.md) - Service URLs and routing
- [Storage](./STORAGE.md) - Service storage configuration
- [Ansible](./ANSIBLE.md) - Deployment playbooks
- [CI/CD](./CICD.md) - GitLab automation pipeline
- [Watchtower](./WATCHTOWER.md) - Interactive container updates
- [Observability](./OBSERVABILITY.md) - Tracing and metrics
- [SERVICES_GUIDE.md](./legacy/SERVICES_GUIDE.md) - Learning resources
