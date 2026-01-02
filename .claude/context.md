# Infrastructure Context

> Core infrastructure reference. This file contains stable information that rarely changes.
> Last updated: 2025-12-31

## Proxmox Cluster

**Cluster**: MorpheusCluster (2-node + Qdevice)

| Node | Local IP | Tailscale IP | Purpose |
|------|----------|--------------|---------|
| node01 | 192.168.20.20 | 100.89.33.5 | Primary VM Host (K8s, LXCs, Core Services) |
| node02 | 192.168.20.21 | 100.96.195.27 | Service Host (Traefik, Authentik, GitLab, Immich) |

### Wake-on-LAN

| Node | MAC Address | Status |
|------|-------------|--------|
| node01 | `38:05:25:32:82:76` | Enabled & Persistent |
| node02 | `84:47:09:4d:7a:ca` | Enabled & Persistent |

**Wake nodes from MacBook**:
```bash
python3 scripts/wake-nodes.py          # Wake both
python3 scripts/wake-nodes.py node01   # Wake node01 only
```

**BIOS**: Ensure WoL is enabled in each node's BIOS/UEFI (Power Management → Wake on LAN).

### Remote Access (Tailscale)

When outside the local network, use Tailscale IPs:

```bash
# SSH via Tailscale
ssh root@100.89.33.5         # node01
ssh root@100.96.195.27       # node02

# Proxmox Web UI via Tailscale
# https://100.89.33.5:8006    (node01)
# https://100.96.195.27:8006  (node02)
```

**Other Tailscale Devices**:
- Synology NAS: 100.84.128.43 (inactive)
- Kratos PC: 100.124.141.17 (user device)

---

## Networks

| VLAN | Network | Purpose |
|------|---------|---------|
| VLAN 20 | 192.168.20.0/24 | Infrastructure (K8s, Ansible) |
| VLAN 40 | 192.168.40.0/24 | Services (Docker, Apps) |
| VLAN 90 | 192.168.90.0/24 | Management (Pi-hole DNS) |

**DNS Server**: 192.168.90.53 (Pi-hole v6 + Unbound)

---

## Deployed Infrastructure

**Current Infrastructure** (December 2025):

| Host | IP | Type | Services |
|------|-----|------|----------|
| docker-lxc-glance | 192.168.40.12 | LXC 200 | Glance, Media Stats API, Reddit Manager, NBA Stats API |
| docker-lxc-bots | 192.168.40.14 | LXC 201 | (Deprecated - bots consolidated to Sentinel) |
| pihole | 192.168.90.53 | LXC 202 | Pi-hole v6 + Unbound DNS |
| docker-vm-core-utilities | 192.168.40.13 | VM 107 | Grafana, Prometheus, Uptime Kuma, Speedtest, cAdvisor, SNMP Exporter, Life Progress API, **Sentinel Bot** |
| docker-media | 192.168.40.11 | VM | Jellyfin, *arr stack, MeTube, YouTube Stats API |
| traefik | 192.168.40.20 | VM | Reverse proxy |
| authentik | 192.168.40.21 | VM | SSO/Authentication |

**Note**: docker-utilities (192.168.40.10) has been decommissioned. All monitoring services now run on 192.168.40.13.

| Category | Hosts | Details |
|----------|-------|---------|
| Kubernetes | 9 VMs | 3 controllers + 6 workers (v1.28.15) |
| Services | 8 VMs | Traefik, Authentik, Immich, GitLab, GitLab Runner, Arr Stack |
| LXC Containers | 3 LXC | Glance (200), Discord Bots (201), Pi-hole (202) |
| Ansible | 1 VM | Configuration management controller |

---

## Authentication

| Access | Details |
|--------|---------|
| SSH User | hermes-admin (VMs), root (Proxmox) |
| SSH Key | `~/.ssh/homelab_ed25519` (no passphrase) |
| SSH Config | `~/.ssh/config` with host aliases |
| Proxmox API | terraform-deployment-user@pve!tf |

### SSH Quick Access

```bash
# Using host aliases (from ~/.ssh/config)
ssh node01              # Proxmox node01 as root
ssh ansible             # Ansible controller
ssh k8s-controller01    # K8s primary controller
ssh docker-vm-core-utilities01    # Docker utilities host

# Direct IP access (auto-selects key)
ssh root@192.168.20.20
ssh hermes-admin@192.168.20.30
```

---

## Synology NAS

**Address**: 192.168.20.31
**DSM Web UI**: https://192.168.20.31:5001
**Tailscale IP**: 100.84.128.43 (inactive)

### NAS Services

| Service | Port | Purpose |
|---------|------|---------|
| DSM | 5001 (HTTPS) | Synology management |
| **Plex Media Server** | 32400 | Media streaming |
| NFS | 2049 | File shares for Proxmox |
| SNMP | 161 | Monitoring metrics |

### Plex Media Server

| Setting | Value |
|---------|-------|
| Web UI | http://192.168.20.31:32400/web |
| Direct Stream | http://192.168.20.31:32400 |
| Media Location | `/volume2/Proxmox-Media/` |

**Library Paths** (on Synology):
- Movies: `/volume2/Proxmox-Media/Movies`
- TV Shows: `/volume2/Proxmox-Media/Series`
- Music: `/volume2/Proxmox-Media/Music`

---

## Service URLs

| Service | URL |
|---------|-----|
| Proxmox | https://proxmox.hrmsmrflrii.xyz |
| **Plex** | http://192.168.20.31:32400/web |
| Traefik | https://traefik.hrmsmrflrii.xyz |
| Authentik | https://auth.hrmsmrflrii.xyz |
| Immich | https://photos.hrmsmrflrii.xyz |
| GitLab | https://gitlab.hrmsmrflrii.xyz |
| Jellyfin | https://jellyfin.hrmsmrflrii.xyz |
| Deluge | https://deluge.hrmsmrflrii.xyz |
| SABnzbd | https://sabnzbd.hrmsmrflrii.xyz |
| MeTube | https://metube.hrmsmrflrii.xyz |
| n8n | https://n8n.hrmsmrflrii.xyz |
| **Productivity** | |
| BentoPDF | https://bentopdf.hrmsmrflrii.xyz |
| Reactive Resume | https://resume.hrmsmrflrii.xyz |
| **Network Tools** | |
| Edgeshark | https://edgeshark.hrmsmrflrii.xyz |
| **Dashboards** | |
| Glance | https://glance.hrmsmrflrii.xyz |
| **Monitoring** | |
| Uptime Kuma | https://uptime.hrmsmrflrii.xyz |
| Prometheus | https://prometheus.hrmsmrflrii.xyz |
| Grafana | https://grafana.hrmsmrflrii.xyz |
| **Observability** | |
| Jaeger | https://jaeger.hrmsmrflrii.xyz |
| Demo App | https://demo.hrmsmrflrii.xyz |
| **Sentinel Bot** | All Discord channels (unified bot) |

---

## Discord Bot Ecosystem

| Bot | Channel(s) | Host | Config Location |
|-----|------------|------|-----------------|
| **Sentinel** | All channels | docker-vm-core-utilities01 (192.168.40.13) | `/opt/sentinel-bot/` |

**Sentinel Bot** (Consolidated January 2026):
Unified homelab management bot combining the functionality of 4 previous bots (Argus, Chronos, Mnemosyne, Athena).

**Cog Modules:**
| Cog | Channel | Purpose |
|-----|---------|---------|
| **Homelab** | #homelab-infrastructure | Proxmox cluster status, VM/LXC/node management |
| **Updates** | #container-updates | Container updates, Watchtower webhooks, reaction approvals |
| **Media** | #media-downloads | Download tracking, failed download alerts, Radarr/Sonarr integration |
| **GitLab** | #project-management | Issue creation/tracking via slash commands |
| **Tasks** | #claude-tasks | Claude task queue, REST API for Claude instances |
| **Onboarding** | #new-service-onboarding | DNS/Traefik/SSL verification |
| **Scheduler** | Various | Background tasks (7pm updates, download monitoring, failed downloads) |

**Key Commands:**
| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/insight` | Health check (memory, errors, storage, downloads) |
| `/homelab status` | Cluster overview |
| `/homelab uptime` | All node/host uptimes |
| `/node <name> restart` | Restart Proxmox node (with confirmation) |
| `/vm <id> restart` | Restart a VM |
| `/lxc <id> restart` | Restart an LXC container |
| `/check` | Scan for container updates |
| `/downloads` | Current download queue |

**Features:**
- Progress bars on all long-running commands
- Reaction-based update approvals (thumbsup to approve)
- Failed download alerts with reaction-based removal (wastebasket emoji)
- REST API for Claude Code integration (port 5050)
- SQLite database for persistent storage
- SSH-based infrastructure management (root for Proxmox, hermes-admin for VMs)

**Deployment Notes:**
- Runs on docker-vm-core-utilities01 (VM 107)
- Webhook port: 5050
- SSH key mounted at `/app/.ssh/homelab_ed25519`
- See `docs/DISCORD_BOTS.md` for full documentation

---

## Glance Dashboard - Protected Pages

**DO NOT modify these layouts without explicit user permission.**

### Home Page Structure
- **Left Column**: Clock, Weather, Calendar, Bookmarks
- **Center Column**: Life Progress, GitHub, Proxmox Monitor, Storage Monitor, Service Monitors, K8s Monitors
- **Right Column**: Crypto, Stocks, Tech News RSS

### Media Page Structure
- **Main Column**: Media Stats Grid (6-tile), Recent Downloads, Currently Downloading, RSS
- **Sidebar**: Media Apps Bookmarks, Services Status

### Compute Tab Structure
- **Main**: Proxmox Cluster Dashboard (Grafana), Container Status History Dashboard (Grafana)
- **Sidebar**: Proxmox Nodes Monitor, Quick Links

### Container Status History Dashboard (PROTECTED)

**Grafana UID**: `container-status`
**Glance Iframe Height**: 1500px

**Layout:**
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

**Top 5 Memory Panels:**
- Type: `bargauge` with horizontal orientation
- Utilities VM: `continuous-BlPu` color scheme
- Media VM: `continuous-GrYlRd` color scheme
- Query: `topk(5, docker_container_memory_percent{job="docker-stats-..."})`
- Unit: percent, max: 100

**Key Configuration:**
- Visualization: `state-timeline` (not status-history)
- Query interval: `1m` to reduce data points
- Time range: `now-1h`
- Stable threshold: `> 3600` (1 hour) with `or vector(0)` fallback
- Row height: `0.9`
- mergeValues: `true`

**Files:**
- Dashboard JSON: `dashboards/container-status.json`
- Ansible Playbook: `ansible-playbooks/monitoring/deploy-container-status-dashboard.yml`

### Storage Tab Structure (PROTECTED)

**DO NOT MODIFY without explicit user permission.**

**Grafana Dashboard**: `synology-nas-modern` (UID)
**Glance Iframe Height**: 1350px
**URL**: `https://grafana.hrmsmrflrii.xyz/d/synology-nas-modern/synology-nas-storage?orgId=1&kiosk&theme=transparent&refresh=30s`
**Time Range**: 7 days (for storage consumption trends)

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│ [Uptime]  [Total Storage]  [Used Storage]  [Storage %]  [CPU %] [Mem %] │  Row 1: h=4
├─────────────────────────────────────────────────────────────────────────┤
│ [Drive 1 HDD] [Drive 2 HDD] [Drive 3 HDD] [Drive 4 HDD] [M.2 1] [M.2 2] │  Row 2: h=4
├──────────────────────────────────┬──────────────────────────────────────┤
│ Disk Temperatures (bargauge)     │ [Sys Temp] [Healthy] [Total RAM]    │  Row 3: h=6
│ All 6 drives with gradient       │ [CPU Cores] [Free]   [Avail RAM]    │
├──────────────────────────────────┼──────────────────────────────────────┤
│ CPU Usage Over Time (4 cores)    │ Memory Usage Over Time              │  Row 4: h=7
├──────────────────────────────────┴──────────────────────────────────────┤
│ Storage Consumption Over Time (Used/Free/Total, 7-day window)           │  Row 5: h=8
└─────────────────────────────────────────────────────────────────────────┘
```

**Disk Configuration (6 drives):**
- Drive 1: Seagate 8TB HDD (ST8000VN004)
- Drive 2: Seagate 4TB HDD (ST4000VN006)
- Drive 3: Seagate 12TB HDD (ST12000VN0008)
- Drive 4: Seagate 10TB HDD (ST10000VN000)
- M.2 SSD 1: Kingston 1TB NVMe (SNV2S1000G)
- M.2 SSD 2: Crucial 1TB NVMe (CT1000P2SSD8)

**Color Scheme:**
- HDDs: Green when healthy (#22c55e)
- SSDs: Purple when healthy (#8b5cf6)
- Failed: Red (#ef4444)
- Storage Timeline: Used (amber #f59e0b), Free (green #22c55e), Total (blue dashed #3b82f6)
- Memory Chart: Used Real (red #ef4444), Cache/Buffers (amber #f59e0b), Free (green #22c55e)

**Memory Metrics** (IMPORTANT):
- **Memory Usage Gauge**: `((memTotalReal - memAvailReal - memBuffer - memCached) / memTotalReal) * 100`
  - Excludes cache and buffers (reclaimable memory) from "used" calculation
  - Shows ~7% actual usage instead of ~95% (which incorrectly included cache)
- **Memory Over Time Chart**: Shows 3 series:
  - Used (Real): `memTotalReal - memAvailReal - memBuffer - memCached`
  - Cache/Buffers: `memCached + memBuffer`
  - Free: `memAvailReal`
- **Units**: `kbytes` (memTotalReal/memAvailReal/memBuffer/memCached are in KB)

**Files:**
- Dashboard JSON: `dashboards/synology-nas.json`
- Ansible Playbook: `ansible-playbooks/monitoring/deploy-synology-nas-dashboard.yml`

### Network Tab Structure (PROTECTED)

**DO NOT MODIFY without explicit user permission.**

**Grafana Dashboard**: `omada-network` (UID)
**Glance Iframe Height**: 2200px
**URL**: `https://grafana.hrmsmrflrii.xyz/d/omada-network/omada-network-overview?orgId=1&kiosk&theme=transparent&refresh=30s`
**Dashboard Version**: 3

**Layout:**
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 📊 OVERVIEW                                                                   │
│ [Total Clients] [Wired] [Wireless] [Uptime] [Storage] [Upgrade] [WiFi Pie]   │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🖥️ DEVICE HEALTH                                                              │
│ [Gateway CPU] [Gateway Mem] [Switch CPU Bar] [AP CPU Bar]                    │
│ [Gateway] [Core Switch] [Switch 2] [Living AP] [Outdoor AP] [Computer AP]   │  <- Pi-hole style boxes
├──────────────────────────────────────────────────────────────────────────────┤
│ 📶 WIFI SIGNAL QUALITY (h=12 each)                                           │
│ [Client RSSI Bar Gauge]              │ [SNR Bar Gauge]                       │
│ [WiFi Signal Over Time - h=10]                                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🔌 SWITCH PORT STATUS                                                         │
│ [Port Status Table: Switch, Port, Status, Speed, PoE, Port Name, PoE Mode]   │
│ [Port Link Speeds Bar]               │ [Port Traffic RX/TX Time Series]      │
├──────────────────────────────────────────────────────────────────────────────┤
│ ⚡ POE POWER USAGE                                                            │
│ [Total PoE Gauge] [PoE Remaining]    │ [PoE Per Port Bar Gauge]              │
├──────────────────────────────────────────────────────────────────────────────┤
│ 📈 TRAFFIC ANALYSIS                                                           │
│ [Client Connection Trend]            │ [Top 10 Clients by Traffic]           │
│ [Device Download Traffic]            │ [Device Upload Traffic]               │
│ [Client TX Rate]                     │ [Client RX Rate]                      │
├──────────────────────────────────────────────────────────────────────────────┤
│ 📋 CLIENT DETAILS                                                             │
│ [All Connected Clients Table]                                                │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Data Source**: Omada Exporter (`192.168.20.30:9202`)
**Exporter**: `ghcr.io/charlie-haley/omada_exporter`
**Omada Controller**: `192.168.0.103` (OC300)
**Credentials**: `claude-reader` (viewer role)

**Sidebar Widgets:**
- Network Device Status (Prometheus query)
- Pi-hole DNS Stats (via `/opt/pihole-stats-api/` on port 5055)
- Latest Speedtest

**Pi-hole Stats API:**
- URL: `http://172.17.0.1:5055/api/pihole/stats`
- Authenticates with Pi-hole v6 API (password stored in Obsidian Credentials)
- Caches stats for 60 seconds
- Displays: Queries, Blocked, Block Rate, Active Clients, Blocklist Domains, Cached
- Config file: `/opt/pihole-stats-api/pihole-stats-api.py` (on LXC 200)

**Files:**
- Dashboard JSON: `dashboards/omada-network.json`
- Ansible Playbook: `ansible-playbooks/monitoring/deploy-omada-full-dashboard.yml`
- Glance Update: `ansible-playbooks/monitoring/update-glance-network-tab.yml`
- Documentation: `docs/OMADA_NETWORK_DASHBOARD.md`

### Tab Order
Home | Compute | Storage | Network | Media | Web | Reddit

---

## Key File Locations

**On LXC 200 (192.168.40.12)**:
| Purpose | Path |
|---------|------|
| Glance Config | `/opt/glance/config/glance.yml` |
| Media Stats API | `/opt/media-stats-api/media-stats-api.py` |
| Reddit Manager | `/opt/reddit-manager/reddit-manager.py` |
| NBA Stats API | `/opt/nba-stats-api/nba-stats-api.py` |
| Pi-hole Stats API | `/opt/pihole-stats-api/pihole-stats-api.py` |

**On LXC 201 (192.168.40.14)** (DEPRECATED - bots consolidated to Sentinel):
| Purpose | Path |
|---------|------|
| ~~Argus Bot~~ | `/opt/argus-bot/` (deprecated) |
| ~~Chronos Bot~~ | `/opt/chronos-bot/` (deprecated) |

**On VM 107 (192.168.40.13)**:
| Purpose | Path |
|---------|------|
| **Sentinel Bot** | `/opt/sentinel-bot/` |
| Sentinel Config | `/opt/sentinel-bot/.env` |
| Sentinel SSH Keys | `/opt/sentinel-bot/ssh/homelab_ed25519` |
| Monitoring Stack | `/opt/monitoring/` |
| Prometheus Config | `/opt/monitoring/prometheus/prometheus.yml` |
| Grafana Dashboards | `/opt/monitoring/grafana/dashboards/` |
| Life Progress API | `/opt/life-progress/app.py` |
| SNMP Exporter | `/opt/monitoring/snmp-exporter/snmp.yml` |

**On Traefik VM (192.168.40.20)**:
| Purpose | Path |
|---------|------|
| Traefik Config | `/opt/traefik/config/` |
| Traefik Dynamic | `/opt/traefik/config/dynamic/services.yml` |

---

## Infrastructure as Code Tools

| Tool | Location | Purpose |
|------|----------|---------|
| **Terraform** | Local (this repo) | VM/LXC provisioning on Proxmox |
| **Ansible** | 192.168.20.30 (`~/ansible/`) | Configuration management |
| **Packer** | 192.168.20.30 (`~/packer/`) | VM template creation |

### Packer Configuration

| Item | Details |
|------|---------|
| **Version** | 1.14.3 |
| **Working Directory** | `/home/hermes-admin/packer/` |
| **Example Template** | `proxmox-ubuntu-template.pkr.hcl` |
| **Credentials** | `credentials.pkrvars.hcl` (not in git) |

**Quick Start:**
```bash
ssh ansible
cd ~/packer
packer init proxmox-ubuntu-template.pkr.hcl
packer build -var-file=credentials.pkrvars.hcl proxmox-ubuntu-template.pkr.hcl
```

---

## Technical Notes

- All VMs use Ubuntu 24.04 LTS cloud-init template
- VMs use UEFI boot mode (ovmf)
- LXC containers use Ubuntu 22.04 or Debian 12
- Auto-start enabled on production infrastructure
- Proxmox node01 hosts LXC 200 and VM 107 (core services)
- Glance v0.7.0+ requires config directory mount (`./config:/app/config`)
- Docker in LXC requires `--security-opt apparmor=unconfined` flag
- Traefik uses ping entrypoint on port 8082 for health checks
- Kubelet healthz endpoint binds to 0.0.0.0:10248 on all workers
- Life Progress API runs on docker-vm-core-utilities (192.168.40.13:5051)
- Prometheus targets: cadvisor, docker-stats-media, traefik, omada, synology
