# Proxmox Terraform Infrastructure

Terraform infrastructure-as-code for deploying VMs and LXC containers on a Proxmox VE 9.1.2 cluster. Designed for a homelab environment with Kubernetes, Docker services, and supporting infrastructure.

## Quick Reference

| Resource | Documentation |
|----------|---------------|
| **Network** | [docs/NETWORKING.md](./docs/NETWORKING.md) - VLANs, IPs, DNS, SSL |
| **Compute** | [docs/PROXMOX.md](./docs/PROXMOX.md) - Cluster nodes, VM/LXC standards |
| **Storage** | [docs/STORAGE.md](./docs/STORAGE.md) - NFS, Synology, storage pools |
| **Terraform** | [docs/TERRAFORM.md](./docs/TERRAFORM.md) - Modules, deployment |
| **Services** | [docs/SERVICES.md](./docs/SERVICES.md) - Docker services |
| **App Config** | [docs/APPLICATION_CONFIGURATIONS.md](./docs/APPLICATION_CONFIGURATIONS.md) - Detailed app setup |
| **Ansible** | [docs/ANSIBLE.md](./docs/ANSIBLE.md) - Automation, playbooks |
| **Inventory** | [docs/INVENTORY.md](./docs/INVENTORY.md) - Deployed infrastructure |
| **Observability** | [docs/OBSERVABILITY.md](./docs/OBSERVABILITY.md) - Tracing, metrics |
| **Watchtower** | [docs/WATCHTOWER.md](./docs/WATCHTOWER.md) - Interactive container updates |
| **Glance** | [docs/GLANCE.md](./docs/GLANCE.md) - Dashboard, Media Stats widget |
| **CI/CD** | [docs/CICD.md](./docs/CICD.md) - Automated service onboarding |
| **Service Onboarding** | [docs/SERVICE_ONBOARDING.md](./docs/SERVICE_ONBOARDING.md) - Automated status checker |
| **Troubleshooting** | [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) - Common issues |

## Infrastructure Overview

### Proxmox Cluster

| Node | IP | Purpose |
|------|----|---------|
| node01 | 192.168.20.20 | VM Host |
| node02 | 192.168.20.21 | LXC/Service Host |
| node03 | 192.168.20.22 | Kubernetes |

### Networks

| VLAN | Network | Purpose |
|------|---------|---------|
| VLAN 20 | 192.168.20.0/24 | Infrastructure (K8s, Ansible) |
| VLAN 40 | 192.168.40.0/24 | Services (Docker, Apps) |

### Deployed Infrastructure

**18 VMs Total**: 1 Ansible + 9 Kubernetes + 8 Services

| Category | Hosts | Details |
|----------|-------|---------|
| Kubernetes | 9 VMs | 3 controllers + 6 workers (v1.28.15) |
| Services | 8 VMs | Traefik, Authentik, Immich, GitLab, GitLab Runner, Arr Stack, n8n |
| Ansible | 1 VM | Configuration management controller |

See [docs/INVENTORY.md](./docs/INVENTORY.md) for full details.

## Quick Start

### Deploy Infrastructure

```bash
terraform init
terraform plan
terraform apply
```

### Access Ansible Controller

```bash
ssh hermes-admin@192.168.20.30
cd ~/ansible
```

### Common Operations

```bash
# Deploy VMs only
terraform apply -target=module.vms

# Check Ansible connectivity
ansible all -m ping

# Deploy Kubernetes
ansible-playbook k8s/k8s-deploy-all.yml
```

See [docs/TERRAFORM.md](./docs/TERRAFORM.md) for more operations.

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

See [docs/NETWORKING.md](./docs/NETWORKING.md) for complete URL list.

## Repository Structure

```
tf-proxmox/
├── main.tf                 # VM definitions
├── lxc.tf                  # LXC container definitions
├── variables.tf            # Global variables
├── outputs.tf              # Output definitions
├── modules/
│   ├── linux-vm/           # VM module
│   └── lxc/                # LXC module
├── ansible-playbooks/      # Ansible playbooks
├── docs/                   # Modular documentation
│   ├── NETWORKING.md       # Network configuration
│   ├── PROXMOX.md          # Cluster & VM standards
│   ├── STORAGE.md          # Storage configuration
│   ├── TERRAFORM.md        # IaC deployment
│   ├── SERVICES.md         # Docker services
│   ├── APPLICATION_CONFIGURATIONS.md  # Detailed app setup guides
│   ├── ANSIBLE.md          # Automation
│   ├── INVENTORY.md        # Deployed resources
│   ├── OBSERVABILITY.md    # Tracing & metrics
│   ├── WATCHTOWER.md       # Container updates
│   ├── CICD.md             # GitLab CI/CD automation
│   ├── TROUBLESHOOTING.md  # Issue resolution
│   └── legacy/             # Extended documentation
├── Proxmox-TerraformDeployments.wiki/  # GitHub wiki (synced)
└── CLAUDE.md               # This file
```

## Troubleshooting Documentation Format

Troubleshooting docs are organized by category in [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md):

- **Proxmox Cluster Issues** - Corosync, node health, boot failures
- **Kubernetes Issues** - kubectl, kubeconfig, cluster problems
- **Authentication Issues** - Authentik, ForwardAuth, SSO
- **Container & Docker Issues** - Watchtower, build cache, SSH keys
- **Service-Specific Issues** - GitLab, individual service problems
- **Dashboard Issues** - Glance configuration, monitoring endpoints
- **Network Issues** - VLAN, NFS, connectivity
- **Common Issues** - Terraform, templates, general errors
- **Diagnostic Commands** - Quick reference commands

When adding new issues, use this format:

```markdown
### Issue Title

**Resolved**: Month Day, Year

**Symptoms**: What the user sees (error messages, behavior)

**Root Cause**: Why it happened

**Fix**:
```bash
# Commands to resolve
```

**Verification**: How to confirm it's fixed

**Prevention**: How to avoid in the future (optional)
```

## Key Configuration

### Adding New VMs

Edit `main.tf`, add to `vm_groups`:

```hcl
new-service = {
  count       = 1
  starting_ip = "192.168.40.50"
  template    = "tpl-ubuntu-shared-v1"
  cores       = 4
  memory      = 8192
  disk_size   = "20G"
  storage     = "VMDisks"
  vlan_tag    = 40              # null for VLAN 20
  gateway     = "192.168.40.1"
  nameserver  = "192.168.91.30"
}
```

See [docs/TERRAFORM.md](./docs/TERRAFORM.md) for complete guide.

### Adding New Services

1. Deploy VM via Terraform
2. Create Ansible playbook in `ansible-playbooks/`
3. Add to Traefik dynamic config (`/opt/traefik/config/dynamic/services.yml`)
4. Update DNS in OPNsense
5. **Add Authentik protection** (if needed):
   - Create Proxy Provider in Authentik Admin
   - Create Application linked to provider
   - **Assign provider to Embedded Outpost** (critical!)
6. **Update Discord Bots**:
   - Add container to `CONTAINER_HOSTS` in Update Manager (`/opt/update-manager/update_manager.py`)
   - Add VM to `VM_MAPPING` in Argus bot (`/opt/sysadmin-bot/sysadmin-bot.py`)
   - Configure webhooks to Download Monitor (for media services)
7. **Update Documentation**: All three locations (docs/, wiki, Obsidian)

See [docs/SERVICES.md](./docs/SERVICES.md) and [docs/SERVICE_ONBOARDING.md](./docs/SERVICE_ONBOARDING.md).

### Discord Bot Ecosystem

Three Discord bots manage different aspects of the homelab:

| Bot | Channel | Purpose | Config Location |
|-----|---------|---------|-----------------|
| **Update Manager** | #update-manager | Container updates, onboarding | `/opt/update-manager/` |
| **Argus SysAdmin** | #argus-assistant | VM/container control | `/opt/sysadmin-bot/` |
| **Download Monitor** | #media-downloads | Radarr/Sonarr notifications | `/opt/download-monitor/` |

See [docs/SERVICE_ONBOARDING.md](./docs/SERVICE_ONBOARDING.md) for complete onboarding checklist.

## Documentation Update Protocol

**IMPORTANT: When the user says "update documentation", you MUST update ALL of the following:**

### Mandatory Updates

1. **Obsidian Vault** (`C:\Users\herms\OneDrive\Obsidian Vault\Hermes's Life Knowledge Base\07 HomeLab Things\Claude Managed Homelab\`)
   - Update relevant numbered markdown files
   - Include callout warnings where appropriate
   - Add to 00 - Homelab Index.md if new feature

2. **CHANGELOG.md** (Repository root)
   - Add entry under current date or [Unreleased]
   - Follow Keep a Changelog format
   - Update Version History Summary section

3. **GitHub Wiki** (`Proxmox-TerraformDeployments.wiki/`)
   - Update relevant wiki pages
   - Update `_Sidebar.md` if new page added
   - Beginner-friendly explanations

4. **CLAUDE.md** (Repository root)
   - Update Quick Reference table if new service
   - Update Service URLs if new endpoint
   - Add preservation notes if layout is finalized

5. **docs/ folder** - Update relevant documentation:
   - `SERVICES.md` - New services, ports, URLs
   - `APPLICATION_CONFIGURATIONS.md` - Detailed setup guides
   - `SERVICE_ONBOARDING.md` - If onboarding workflow changes
   - `TROUBLESHOOTING.md` - Any issues encountered and fixes
   - Service-specific docs (GLANCE.md, OBSERVABILITY.md, etc.)

### Documentation Content Requirements

Each documentation update MUST include:

1. **Code Configuration** - All code with inline comments explaining each section
2. **Architecture Diagrams** - ASCII diagrams showing component relationships
3. **Decision Explanations** - Why certain approaches were chosen
4. **Troubleshooting Steps** - Common issues encountered and their fixes
5. **Health Check Endpoints** - URLs and expected responses
6. **Deployment Commands** - Copy-paste ready commands
7. **File Locations** - Where configs and scripts are stored

### Commit Requirements

After updating documentation:
1. Stage all changed files
2. Commit with descriptive message
3. Push to GitHub (both main repo and wiki if applicable)

---

## Documentation Sync Guide

Documentation is maintained in **three locations** that must stay synchronized:

| Location | Purpose | Format |
|----------|---------|--------|
| `docs/` | Git-tracked technical reference | Concise, technical |
| `Proxmox-TerraformDeployments.wiki/` | GitHub wiki (public) | Beginner-friendly, detailed |
| `~/OneDrive/Obsidian Vault/.../Claude Managed Homelab/` | Personal Obsidian vault | Internal, includes credentials |

### Obsidian Vault Path

```
C:\Users\herms\OneDrive\Obsidian Vault\Hermes's Life Knowledge Base\07 HomeLab Things\Claude Managed Homelab\
```

### Document Mapping (All Three Locations)

| docs/ File | Wiki Page | Obsidian File |
|------------|-----------|---------------|
| NETWORKING.md | Network-Architecture.md | 01 - Network Architecture.md |
| PROXMOX.md | Proxmox-Cluster.md | 02 - Proxmox Cluster.md |
| STORAGE.md | Storage-Architecture.md | 03 - Storage Architecture.md |
| TERRAFORM.md | Terraform-Basics.md | 05 - Terraform Configuration.md |
| SERVICES.md | Services-Overview.md | 07 - Deployed Services.md |
| APPLICATION_CONFIGURATIONS.md | Application-Configurations.md | 21 - Application Configurations.md |
| ANSIBLE.md | Ansible-Basics.md | 06 - Ansible Automation.md |
| INVENTORY.md | Inventory-Management.md | (embedded in Index) |
| OBSERVABILITY.md | Observability.md | 18 - Observability Stack.md |
| WATCHTOWER.md | Watchtower.md | 19 - Watchtower Updates.md |
| CICD.md | GitLab-CICD.md | 20 - GitLab CI-CD Automation.md |
| SERVICE_ONBOARDING.md | Service-Onboarding.md | 22 - Service Onboarding Workflow.md |
| TROUBLESHOOTING.md | Troubleshooting.md | 12 - Troubleshooting.md |
| - | - | 11 - Credentials.md (private) |

### Sync Requirements

When updating documentation:

1. **Update both locations** - Changes to `docs/` must be reflected in wiki and vice versa
2. **Maintain consistency** - Same facts, commands, and configurations in both
3. **Preserve format differences** - Wiki is more detailed/beginner-friendly, docs are concise
4. **Update cross-references** - Links in Related Documentation sections
5. **Update sidebar** - Wiki `_Sidebar.md` for new pages

### Sync Checklist for New Features

When adding a new feature or service, update ALL THREE locations:

```markdown
## Infrastructure
- [ ] Add Traefik route to /opt/traefik/config/dynamic/services.yml
- [ ] Add DNS entry in OPNsense
- [ ] Create Authentik provider + application (if SSO protected)
- [ ] Assign provider to Embedded Outpost (critical!)

## docs/ (Git-tracked)
- [ ] Update relevant docs/*.md file
- [ ] Add to CLAUDE.md Quick Reference (if major feature)

## GitHub Wiki
- [ ] Update corresponding wiki page
- [ ] Update wiki _Sidebar.md (if new page)
- [ ] Update wiki Home.md quick reference table

## Obsidian Vault (Personal)
- [ ] Update corresponding Obsidian file
- [ ] Update 00 - Homelab Index.md with new link
- [ ] Update 07 - Deployed Services.md service tables
- [ ] Add credentials to 11 - Credentials.md (if any)

## All Locations
- [ ] Add troubleshooting entries to all three locations
- [ ] Verify cross-references are consistent
```

### Push Wiki Changes

```bash
cd Proxmox-TerraformDeployments.wiki
git add .
git commit -m "Sync: description of changes"
git push
```

### Obsidian Sync

Obsidian vault syncs automatically via OneDrive. No manual push needed.

## Security

- **API Tokens**: Stored in `terraform.tfvars` (gitignored)
- **SSH**: Public key only, password auth disabled
- **LXC**: Unprivileged by default
- **Network**: VLAN segmentation

## Glance Dashboard - Home Page Configuration

**IMPORTANT: DO NOT modify the Glance Home page layout without explicit user permission.**

The Home page has been carefully configured with the following structure and should be preserved:

### Left Column (Small)
- Clock (24h, Asia/Manila)
- Weather (Manila, metric)
- Calendar
- Infrastructure Bookmarks (Authentik, Omada, Proxmox, Traefik, OPNsense, Portainer, Synology NAS)
- Services Bookmarks (Media, Downloads, Productivity, Monitoring)

### Center Column (Full)
- Life Progress Widget (custom-api, port 5051)
- GitHub Contributions (green theme, dark mode)
- Proxmox Cluster Monitor (Node 01, 02, 03)
- Storage Monitor (Synology NAS VLAN 10 & 20)
- Core Services Monitor (Traefik, Authentik, GitLab, Immich, n8n, Paperless)
- Media Services Monitor (Jellyfin, Radarr, Sonarr, Lidarr, Prowlarr, Bazarr, Jellyseerr, Tdarr, Deluge, SABnzbd)
- Monitoring Stack Monitor (Uptime Kuma, Prometheus, Grafana, Jaeger, Glance, Speedtest)
- Kubernetes Control Plane Monitor (Controllers 1-3 via API port 6443)
- Kubernetes Workers Monitor (Workers 1-6 via kubelet port 10248)

### Right Column (Small)
- Crypto Markets (BTC, ETH, XRP, BNB, ADA)
- Stock Markets (MSFT, AAPL, ORCL, NVDA, GOOGL, TSLA, NFLX, AMZN)
- Tech News RSS (r/homelab, r/selfhosted)

### Configuration Script
The Home page is managed via `temp-home-fix.py`. Any changes should be documented and require user approval.

See [docs/GLANCE.md](./docs/GLANCE.md) for full dashboard documentation.

## Glance Dashboard - Media Page Configuration

**IMPORTANT: DO NOT modify the Glance Media page layout without explicit user permission.**

The Media page has been carefully configured with the following structure and should be preserved:

### Main Column (Full)

**1. Media Stats Grid** (6-tile, Pi-hole style)
- Wanted Movies (amber)
- Movies Downloading (blue)
- Movies Downloaded (green)
- Wanted Episodes (red)
- Episodes Downloading (purple)
- Episodes Downloaded (cyan)
- API: `http://192.168.40.10:5054/api/stats`

**2. Now Showing - Recent Downloads**
- Top 5 most recent downloads (movies + TV episodes)
- Poster images with type badges (Movie=amber, TV=purple)
- Shows title, episode info, quality
- API: `http://192.168.40.10:5054/api/recent`

**3. Currently Downloading**
- Up to 10 active downloads with progress bars
- Poster thumbnails, type badges
- Quality, download client, ETA
- Color-coded progress bars (movies=amber, TV=purple)
- API: `http://192.168.40.10:5054/api/queue`

**4. Movie & TV News RSS**
- Deadline, Hollywood Reporter, Variety feeds
- Limit 10, collapse after 5

### Sidebar Column (Small)

**1. Media Apps Bookmarks**
- Arr Stack: Radarr, Sonarr, Lidarr, Prowlarr, Bazarr, Jellyseerr
- Media Players: Jellyfin, Tdarr
- Downloads: Deluge, SABnzbd

**2. Services Status Monitor**
- All Arr stack services health checks
- Uses `/ping` endpoints where available

### Media Stats API

| Endpoint | Port | Description |
|----------|------|-------------|
| `/api/stats` | 5054 | Stats for 6-tile grid |
| `/api/recent` | 5054 | Top 5 recent downloads with posters |
| `/api/queue` | 5054 | Active downloads with progress (max 10) |
| `/health` | 5054 | Health check |

### Configuration Scripts
- Media page: `temp-media-page-update.py`
- Media Stats API: `temp-media-api-update.py`
- API location: `/opt/media-stats-api/media-stats-api.py`

## Glance Dashboard - Tab Structure

The Glance dashboard has 7 tabs in this order:

| Tab | Purpose | Protected |
|-----|---------|-----------|
| **Home** | Service monitors, bookmarks, markets | YES |
| **Compute** | Proxmox cluster Grafana dashboard | No |
| **Storage** | Synology NAS Grafana dashboard | No |
| **Network** | Network overview + Speedtest | No |
| **Media** | Media stats, downloads, queue | YES |
| **Web** | Tech news, AI/ML, stocks, NBA | No |
| **Reddit** | Dynamic Reddit feed | No |

### Compute Tab

Displays Proxmox cluster metrics and container monitoring via two embedded Grafana dashboards.

#### Proxmox Cluster Dashboard

**Grafana Dashboard**: `proxmox-compute` (UID)
- URL: `https://grafana.hrmsmrflrii.xyz/d/proxmox-compute/proxmox-cluster-overview?kiosk&refresh=30s`
- Iframe Height: 950px
- Panels: Transparent backgrounds

**Panels Include**:
- Nodes Online (stat with green/red)
- Avg CPU % (stat with thresholds)
- Avg Memory % (stat with thresholds)
- Running VMs / Total VMs / Stopped VMs
- CPU Usage by Node (time series)
- Memory Usage by Node (time series)
- Local LVM Storage Usage % (bar gauge, red at 90%)
- VM Disks Storage Usage % (bar gauge)
- Proxmox Data Storage Usage % (bar gauge)
- Storage totals (VMDisks, ProxmoxData, Local LVM)

#### Container Monitoring Dashboard (Modern Visual Style)

**Grafana Dashboard**: `containers-modern` (UID)
- URL: `https://grafana.hrmsmrflrii.xyz/d/containers-modern/container-monitoring?kiosk&refresh=30s`
- Iframe Height: 600px
- Panels: Transparent backgrounds

**Summary Stats Row** (colored tiles):
- Total Containers (blue background)
- Running Containers (green background)
- Total Memory Used (orange background, bytes)
- Total CPU (circular gauge with thresholds)

**Memory Usage Bar Gauges** (horizontal gradient bars):
- Utilities VM containers - Blue-Yellow-Red gradient
- Media VM containers - Blue-Yellow-Red gradient
- Shows container name with memory % per container

**CPU Usage Bar Gauges** (horizontal gradient bars):
- Utilities VM containers - Green-Yellow-Red gradient
- Media VM containers - Green-Yellow-Red gradient
- Shows container name with CPU % per container

**Color Thresholds**:
- Memory: Green <70%, Yellow 70-90%, Red >90%
- CPU: Green <50%, Yellow 50-80%, Red >80%

**Metrics Source**: docker-exporter on port 9417
- `docker_container_running`
- `docker_container_memory_percent`
- `docker_container_cpu_percent`
- `docker_container_memory_usage_bytes`

**Sidebar Widgets**:
- Proxmox Nodes Monitor (Node 01, 02, 03)
- Quick Links Bookmarks (Proxmox UI, Grafana)

### Storage Tab

Displays Synology NAS metrics via embedded Grafana dashboard.

**Grafana Dashboard**: `synology-storage` (UID)
- URL: `https://grafana.hrmsmrflrii.xyz/d/synology-storage/synology-nas?kiosk&refresh=30s`
- Iframe Height: 500px
- Panels: Transparent backgrounds

**Panels Include**:
- CPU Load (stat)
- Root Volume Usage % (stat with thresholds)
- Total Storage (bytes)
- Free Storage (bytes)
- CPU Load per Core (time series)
- Storage Usage Over Time (time series)

### Network Tab

Displays network metrics via Grafana + Speedtest widget.

**Grafana Dashboard**: `network-overview` (UID)
- URL: `https://grafana.hrmsmrflrii.xyz/d/network-overview/network-overview?kiosk&refresh=30s`
- Iframe Height: 750px
- Panels: Transparent backgrounds

**Panels Include**:
- OPNsense Gateway Status
- OPNsense Services Running
- TCP Connections (Established)
- Firewall Blocked Packets
- WAN Interface Traffic (time series)
- Firewall Pass/Block Rate (time series)
- OPNsense Services Status (bar gauge)
- TCP Connection States (time series)
- Protocol Packet Rates (time series)

**Speedtest Widget**:
- API: `http://192.168.40.10:3000/api/speedtest/latest`
- Shows: Download (Mbps), Upload (Mbps), Ping (ms)
- Gradient color tiles (blue/green/amber)

### Web Tab

Tech news, AI/ML feeds, enterprise tech, stocks, and NBA scores.

**Widgets**:
1. Tech News RSS (The Verge, Google Tech)
2. AI & Machine Learning RSS (r/artificial, r/MachineLearning, r/LocalLLaMA)
3. Enterprise Tech RSS (r/microsoft, r/github, r/NVIDIA)
4. NBA Scores (ESPN API)
5. Tech Stocks (MSFT, NVDA, ORCL, AMZN, CRM, GOOGL)
6. Crypto (BTC, ETH, XRP)
7. Crypto News RSS (r/cryptocurrency)

### Prometheus Exporters

| Exporter | Port | Target | Status |
|----------|------|--------|--------|
| OPNsense Exporter | 9198 | 192.168.91.30 | Active |
| Omada Exporter | 9202 | 192.168.0.103 | Pending network rule |

**OPNsense Exporter Location**: `/opt/opnsense-exporter/docker-compose.yml`
**Omada Exporter Location**: `/opt/omada-exporter/docker-compose.yml`

### Configuration Script
- Full dashboard update: `temp-glance-update.py`
- Updates all tabs while preserving Home and Media pages

## Homelab Blog Series Project

A blog series documenting the homelab journey for technical audiences.

### Blog Status

| # | Title | Status |
|---|-------|--------|
| 1 | My Accidental Journey Into Homelabbing | Draft |
| 2 | How AI Jumpstarted My Homelab Journey | Planned |
| 3-6 | Foundation Layer (Proxmox, VLANs, Terraform, Ansible) | Planned |
| 7-10 | Containerization (Docker, Traefik, Authentik, Media Stack) | Planned |
| 11-14 | Production Practices (Monitoring, Tracing, Watchtower, Discord Bots) | Planned |
| 15-17 | Advanced (Kubernetes, Cloudflare Tunnel, CI/CD) | Planned |
| 18-20 | Retrospectives (Mistakes, Costs, Lessons) | Planned |

### Target Audience

- Technical people wanting to start a homelab
- Developers interested in Docker containerization
- Self-hosters looking for production-grade patterns

### Unique Angles

1. **Real infrastructure** - Production patterns, not toy examples
2. **Mistakes included** - Path mismatches, forgotten configs (learning content)
3. **AI-assisted journey** - Using Claude as pair programmer
4. **Three-tier documentation** - docs/, wiki, Obsidian sync
5. **Discord integration** - Practical automation

### Content Sources

Real troubleshooting examples to reference:
- Omada Exporter site name mismatch
- Arr Stack unified path configuration
- Jellyfin empty library issue
- Authentik outpost assignment

### Documentation

- Full TODO: `Obsidian Vault/.../Claude Managed Homelab/TODO - Homelab Blog Series.md`
- Post template included in TODO file

---

## Notes

- All VMs use Ubuntu 24.04 LTS cloud-init template
- VMs use UEFI boot mode (ovmf)
- LXC containers use Ubuntu 22.04 or Debian 12
- Auto-start enabled on production infrastructure
- Proxmox node02 dedicated to service VMs
- Glance v0.7.0+ requires config directory mount (`./config:/app/config`), not single file mount
- Traefik uses ping entrypoint on port 8082 for health checks
- Kubelet healthz endpoint binds to 0.0.0.0:10248 on all workers for external monitoring
- Life Progress API runs on docker-vm-utilities01:5051 (see [APPLICATION_CONFIGURATIONS.md](./docs/APPLICATION_CONFIGURATIONS.md))
