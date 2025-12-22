# Deployed Services

> Part of the [Proxmox Infrastructure Documentation](../CLAUDE.md)

## Service Overview

All services deployed via Docker Compose, managed by Ansible automation from `ansible-controller01`.

| Category | Host | Services |
|----------|------|----------|
| Reverse Proxy | traefik-vm01 | Traefik |
| Identity | authentik-vm01 | Authentik |
| Photos | immich-vm01 | Immich |
| DevOps | gitlab-vm01 | GitLab CE |
| CI/CD | gitlab-runner-vm01 | GitLab Runner, Ansible |
| Media | docker-vm-media01 | Arr Stack (12 services), Download Monitor |
| Dashboard | docker-vm-utilities01 | Glance, Life Progress API |
| Utilities | docker-vm-utilities01 | n8n, Paperless, OpenSpeedTest |
| Update Management | docker-vm-utilities01 | Watchtower, Update Manager (Discord bot) |
| Discord Bots | docker-vm-utilities01 | Argus SysAdmin Bot |
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
- Media: `/mnt/media/` (NFS)
  - Movies: `/mnt/media/Movies`
  - Series: `/mnt/media/Series`
  - Music: `/mnt/media/Music`

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
- Download paths (NFS mounted):
  - Downloading: `/downloads/downloading`
  - Completed: `/downloads/completed`
  - Incomplete: `/downloads/incomplete`

**SABnzbd** (Usenet):
- Web UI: http://192.168.40.11:8081 | https://sabnzbd.hrmsmrflrii.xyz
- Complete setup wizard on first access
- Add Usenet server credentials in Config
- Get API key from Config → General → Security
- Configure categories: `radarr`, `sonarr`, `lidarr`
- Download paths (NFS mounted):
  - Temporary: `/downloads/incomplete`
  - Completed: `/downloads/complete`
  - Downloading: `/downloads/downloading`

### Download Storage (NFS)

Both download clients store files on the NAS via NFS mounts:

| Container Path | NAS Location |
|---------------|--------------|
| `/downloads/completed` (deluge) | NAS:/MediaFiles/Completed |
| `/downloads/complete` (sabnzbd) | NAS:/MediaFiles/Completed |
| `/downloads/downloading` | NAS:/MediaFiles/Downloading |
| `/downloads/incomplete` | NAS:/MediaFiles/Incomplete |

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

## Glance Dashboard

**Host**: docker-vm-utilities01 (192.168.40.10)
**Status**: Deployed December 2025

| Port | URL | Purpose |
|------|-----|---------|
| 8080 | http://192.168.40.10:8080 | Dashboard |
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

### Pages

| Page | Widgets |
|------|---------|
| Home | Life Progress, Service Health, K8s Cluster, Markets, RSS |
| Media | Arr Stack Downloads, Radarr Calendar, Media Bookmarks |
| Sports | NBA Scores, NFL Scores |
| Network | Network Devices, OPNsense Unbound Stats |
| Storage | Synology NAS Dashboard (iframe) |

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

## Related Documentation

- [Networking](./NETWORKING.md) - Service URLs and routing
- [Storage](./STORAGE.md) - Service storage configuration
- [Ansible](./ANSIBLE.md) - Deployment playbooks
- [CI/CD](./CICD.md) - GitLab automation pipeline
- [Watchtower](./WATCHTOWER.md) - Interactive container updates
- [Observability](./OBSERVABILITY.md) - Tracing and metrics
- [SERVICES_GUIDE.md](./legacy/SERVICES_GUIDE.md) - Learning resources
