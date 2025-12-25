# Infrastructure Context

> Core infrastructure reference. This file contains stable information that rarely changes.
> Last updated: 2025-12-25

## Proxmox Cluster

| Node | Local IP | Tailscale IP | Purpose |
|------|----------|--------------|---------|
| node01 | 192.168.20.20 | 100.89.33.5 | VM Host |
| node02 | 192.168.20.21 | 100.96.195.27 | LXC/Service Host |
| node03 | 192.168.20.22 | 100.76.81.39 | Kubernetes |

### Remote Access (Tailscale)

When outside the local network, use Tailscale IPs:

```bash
# SSH via Tailscale
ssh root@100.89.33.5         # node01
ssh root@100.96.195.27       # node02
ssh root@100.76.81.39        # node03

# Proxmox Web UI via Tailscale
# https://100.89.33.5:8006    (node01)
# https://100.96.195.27:8006  (node02)
# https://100.76.81.39:8006   (node03)
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

---

## Deployed Infrastructure

**18 VMs Total**: 1 Ansible + 9 Kubernetes + 8 Services

| Category | Hosts | Details |
|----------|-------|---------|
| Kubernetes | 9 VMs | 3 controllers + 6 workers (v1.28.15) |
| Services | 8 VMs | Traefik, Authentik, Immich, GitLab, GitLab Runner, Arr Stack, n8n |
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
ssh docker-utilities    # Docker utilities host

# Direct IP access (auto-selects key)
ssh root@192.168.20.20
ssh hermes-admin@192.168.20.30
```

---

## Service URLs

| Service | URL |
|---------|-----|
| Proxmox | https://proxmox.hrmsmrflrii.xyz |
| Traefik | https://traefik.hrmsmrflrii.xyz |
| Authentik | https://auth.hrmsmrflrii.xyz |
| Immich | https://photos.hrmsmrflrii.xyz |
| GitLab | https://gitlab.hrmsmrflrii.xyz |
| Jellyfin | https://jellyfin.hrmsmrflrii.xyz |
| Deluge | https://deluge.hrmsmrflrii.xyz |
| SABnzbd | https://sabnzbd.hrmsmrflrii.xyz |
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
| **Discord Bots** | |
| Argus (SysAdmin) | Discord: #argus-assistant |
| Update Manager | Discord: #update-manager |
| Download Monitor | Discord: #media-downloads |
| Project Bot | Discord: #project-management |

---

## Discord Bot Ecosystem

| Bot | Channel | Purpose | Config Location |
|-----|---------|---------|-----------------|
| **Update Manager** | #update-manager | Container updates, onboarding | `/opt/update-manager/` |
| **Argus SysAdmin** | #argus-assistant | VM/container control | `/opt/sysadmin-bot/` |
| **Download Monitor** | #media-downloads | Radarr/Sonarr notifications | `/opt/download-monitor/` |
| **Project Bot** | #project-management | GitLab Kanban task management | `/opt/project-bot/` |

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
**Glance Iframe Height**: 1250px

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│ [Total Containers] [Running]    [Total Memory Used]   [Total CPU Gauge] │  Row 1: h=4
├─────────────────────────────────────────────────────────────────────────┤
│ [Utilities VM]  [Utilities Stable] [Media VM]      [Media Stable]       │  Row 2: h=3
├──────────────────────────────────┬──────────────────────────────────────┤
│ State Timeline - Utilities VM    │ State Timeline - Media VM            │  Row 3: h=14
│ (container uptime, 1h window)    │ (container uptime, 1h window)        │
├──────────────────────────────────┴──────────────────────────────────────┤
│ Container Issues (Last 15 min) - Table of stopped/restarted containers  │  Row 4: h=8
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Configuration:**
- Visualization: `state-timeline` (not status-history)
- Query interval: `1m` to reduce data points
- Time range: `now-1h`
- Stable threshold: `> 3600` (1 hour) with `or vector(0)` fallback
- Row height: `0.9`
- mergeValues: `true`

**Files:**
- Dashboard JSON: `temp-container-status-fixed.json`
- Ansible Playbook: `ansible-playbooks/monitoring/deploy-container-status-dashboard.yml`

### Tab Order
Home | Compute | Storage | Network | Media | Web | Reddit

---

## Key File Locations

| Purpose | Path |
|---------|------|
| Traefik Config | `/opt/traefik/config/` |
| Traefik Dynamic | `/opt/traefik/config/dynamic/services.yml` |
| Glance Config | `/opt/glance/config/glance.yml` |
| Media Stats API | `/opt/media-stats-api/media-stats-api.py` |
| Monitoring Stack | `/opt/monitoring/` |
| Grafana Dashboards | `/opt/monitoring/grafana/dashboards/` |

---

## Technical Notes

- All VMs use Ubuntu 24.04 LTS cloud-init template
- VMs use UEFI boot mode (ovmf)
- LXC containers use Ubuntu 22.04 or Debian 12
- Auto-start enabled on production infrastructure
- Proxmox node02 dedicated to service VMs
- Glance v0.7.0+ requires config directory mount (`./config:/app/config`)
- Traefik uses ping entrypoint on port 8082 for health checks
- Kubelet healthz endpoint binds to 0.0.0.0:10248 on all workers
- Life Progress API runs on docker-vm-utilities01:5051
