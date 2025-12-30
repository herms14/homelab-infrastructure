# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - HashiCorp Packer Installation (December 30, 2025)
- **Installed Packer v1.14.3** on Ansible Controller (192.168.20.30)
  - Used for creating Proxmox VM templates with cloud-init support
  - Integrates with existing Terraform and Ansible workflows
- **Created Ansible playbook** `ansible-playbooks/infrastructure/install-packer.yml`
  - Installs Packer from official HashiCorp repository
  - Creates working directory at `/home/hermes-admin/packer/`
- **Created example Proxmox template** `/home/hermes-admin/packer/proxmox-ubuntu-template.pkr.hcl`
  - Ubuntu 24.04 Server template with cloud-init
  - VM ID 9000, 2 cores, 2GB RAM, 20GB disk
  - QEMU Guest Agent and cloud-init pre-configured
  - Ready for Terraform cloning
- **Created documentation** `docs/PACKER.md`
  - Quick start guide, command reference, troubleshooting
  - Integration examples with Terraform and Ansible
- **Updated CLAUDE.md** - Added Packer to Quick Reference table

### Changed - Repository Cleanup & Reorganization (December 30, 2025)
- **Deleted 30+ temporary files** from root directory
  - Removed all `temp-*.py` development scripts (one-time use artifacts)
  - Removed most `temp-*.json` dashboard drafts
  - Removed `temp-*.yml` config files
  - Removed empty `Service Configuration.md`
- **Created `dashboards/` directory** for Grafana dashboard definitions
  - Moved and renamed: `temp-container-status-fixed.json` → `dashboards/container-status.json`
  - Moved and renamed: `temp-omada-full-dashboard.json` → `dashboards/omada-network.json`
  - Moved and renamed: `temp-synology-nas-dashboard.json` → `dashboards/synology-nas.json`
  - Added `dashboards/README.md` with deployment instructions
- **Moved documentation to proper locations**
  - `TAILSCALE_SETUP.md` → `docs/TAILSCALE_SETUP.md`
- **Cleaned up terraform artifacts**
  - Removed `memory-upgrade.tfplan`, `tfplan`
  - Removed `terraform.tfstate.*.backup` files
- **Removed duplicate directories**
  - Deleted `wiki/` (duplicate of `Proxmox-TerraformDeployments.wiki/`)
- **Removed sensitive file** - `CREDENTIALS.md` (should never be in repo)
- **Updated `.gitignore`** with comprehensive exclusions
  - Organized into sections: Terraform, Sensitive Files, Development Artifacts, etc.
  - Added IDE/OS files (.vscode, .idea, .DS_Store, Thumbs.db)
  - Added Python artifacts (__pycache__, .env, venv/)
  - Added log file exclusions
- **Updated CLAUDE.md** - Dashboard paths now reference `dashboards/` directory

### Fixed - Glance Homepage Configuration (December 30, 2025)
- **Removed Kubernetes monitors** from Home page (VLAN routing prevents access from VLAN 40 to VLAN 20)
  - Removed: Kubernetes Control Plane monitor, Kubernetes Workers monitor
  - Root cause: Glance on LXC 200 (192.168.40.12) cannot reach K8s nodes on 192.168.20.x
- **Updated Daily Note widget** - Changed hardcoded date to current date (2025-12-30)
- **Reorganized new services into proper categories**:
  - Moved Wizarr and Tracearr to Media Services monitor
  - Moved Karakeep and Lagident to Core Services monitor
  - Removed standalone "New Services" monitor section
- **Fixed Glance LXC container startup** - Added `security_opt: apparmor=unconfined` to docker-compose.yml
  - Required for Docker containers running inside Proxmox LXC
- **Updated documentation** - docs/GLANCE.md now reflects LXC 200 location and updated service categories

### Added - Comprehensive Documentation Wiki (December 30, 2025)
- **Created HOMELAB_MASTER_WIKI.md** - Complete technical wiki/encyclopedia for the entire homelab
  - Infrastructure overview with architecture diagrams
  - Network architecture with full VLAN and IP allocation tables
  - Compute infrastructure (Proxmox cluster, VMs, LXCs, Kubernetes)
  - Storage architecture (Synology NAS, NFS exports)
  - Complete tech stack reference
  - Services catalog with all URLs and authentication methods
  - Automation & DevOps (Terraform, Ansible, GitLab CI/CD)
  - Monitoring & Observability stack reference
  - Security & access documentation
  - Operations reference with command cheatsheet
- **Documentation structure**:
  - `docs/HOMELAB_MASTER_WIKI.md` - Authoritative technical wiki (public)
  - `Book - The Complete Homelab Guide` (Obsidian) - Step-by-step tutorial
  - `docs/*.md` - Detailed technical reference for specific topics
- **Cleaned up all node03 references** across documentation:
  - CLAUDE.md, context.md, PROXMOX.md, INVENTORY.md
  - Obsidian files (02 - Proxmox Cluster.md, 00 - Homelab Index.md)
  - Updated infrastructure metrics to reflect 2-node cluster

### Fixed - Network Dashboard & Pi-hole Integration (December 30, 2025)
- **Fixed Glance YAML corruption** - Paperless/Pi-hole bookmark entries were malformed at line 261
  - Fixed YAML syntax error preventing Glance from loading
  - Restored Pi-hole bookmark in Monitoring section
- **Fixed Omada exporter connectivity** - Ansible VM (192.168.20.30) was unreachable after DNS change
  - Restarted Ansible VM to restore network connectivity
  - Omada exporter now successfully scraping data from controller (192.168.0.103)
  - Prometheus target health restored to "up"
- **Added Pi-hole DNS Stats widget** to Network page sidebar
  - Created Pi-hole Stats Proxy API (`/opt/pihole-stats-api/`) on LXC 200
  - Handles Pi-hole v6 session-based authentication
  - Displays: Queries Today, Blocked, Block Rate %, Active Clients, Blocklist Domains, Cached
  - API runs on port 5055 with 60-second cache
  - Pi-hole password stored in Obsidian Credentials (11 - Credentials.md)
- **Fixed Pi-hole DNS records** - Added missing entries and corrected pihole.hrmsmrflrii.xyz IP
  - Added: `paperless.hrmsmrflrii.xyz`, `notebook.hrmsmrflrii.xyz`
  - Fixed: `pihole.hrmsmrflrii.xyz` now points to Traefik (192.168.40.20)
  - Updated Pi-hole v6 TOML config (`/etc/pihole/pihole.toml` hosts array)

### Added - New Node Onboarding Guide (December 30, 2025)
- **Comprehensive checklist** for adding new Proxmox nodes to `docs/PROXMOX.md`
- Covers: cluster join, Prometheus, Glance, WoL, DNS, Tailscale, documentation
- Documents which systems auto-update (Grafana) vs manual (Glance, WoL scripts)

### Fixed - Grafana Dashboard Issues (December 30, 2025)
- **Compute dashboard**: Fixed Running VMs/LXCs showing wrong counts (was 36/4, now 18/2)
  - Added `max by(id)` to deduplicate metrics from multiple nodes
- **Storage dashboard**: Fixed "Healthy Disks" showing "of 6 6"
  - Changed textMode to "value", title now "Healthy Disks (of 6)"
- **Glance**: Removed node03 from Proxmox Nodes monitor widget
- Created `scripts/proxmox-nodes-api.py` - Dynamic node discovery API (port 5061)

### Added - Wake-on-LAN Support (December 30, 2025)
- **Enabled WoL** on node01 (`38:05:25:32:82:76`) and node02 (`84:47:09:4d:7a:ca`)
- Configured persistent WoL via `/etc/network/interfaces` (post-up ethtool)
- Created `scripts/wake-nodes.py` - Python script to wake nodes (no dependencies)
- Created `scripts/wake-nodes.sh` - Bash script alternative
- **Usage**: `python3 scripts/wake-nodes.py [node01|node02|all]`

### Changed - Proxmox Cluster Reduced to 2 Nodes (December 30, 2025)
- **Removed node03** (192.168.20.22) from MorpheusCluster
- Cluster now operates with 2 nodes + Qdevice for quorum
- All workloads were already migrated to node01/node02 prior to removal
- Cleaned up corosync configuration and /etc/pve/nodes/node03 directory
- Updated expected_votes from 4 to 3 for proper quorum
- **Documentation updated**: CLAUDE.md, context.md, PROXMOX.md, NETWORKING.md, INVENTORY.md

### Added - Homelab Blog (December 27, 2025)
- **Deployed Hugo blog** on GitHub Pages: https://herms14.github.io/Clustered-Thoughts/
- **Theme**: PaperMod with dark/light mode toggle
- **First post**: "My Accidental Journey Into Homelabbing: From Trip Photos to Full-Blown Infrastructure"
- **Features**: Reading time, word count, table of contents, search, archives, tags
- **Auto-deployment**: GitHub Actions workflow on push to main branch
- **Source**: Blog posts drafted in Obsidian at `07 HomeLab Things/Homelab Blog Posts/`

### Fixed - Chronos Bot GitLab Permissions (December 27, 2025)
- **Issue**: Chronos bot `/done` command returned `403 Forbidden` when closing GitLab issues
- **Root Cause**: GitLab token (user `herms14`) was not a member of project ID 2
- **Fix**: Added `herms14` as Maintainer to Homelab Project via GitLab rails console
- **Command used**: `project.add_member(user, :maintainer)` on GitLab VM (192.168.40.23)

### Security - Updated .gitignore (December 27, 2025)
- **Removed untracked files** with hardcoded secrets (never committed to git):
  - `configure_uptime_kuma.py`, `test_*.py` - Uptime Kuma passwords
  - `glance-backup/` - Yahoo OAuth secrets, Obsidian API keys
  - `temp-media-fix.py`, `temp-media-update.py` - Radarr/Sonarr API keys
- **Added .gitignore patterns** to prevent future accidental commits:
  - `test_*.py`, `configure_*.py` - Test/config files
  - `glance-backup/` - Backup directories
  - `temp-*.py`, `temp-*.json`, `temp-*.yml` - Temp files
- **Whitelisted**: Essential temp dashboards (omada, synology, container-status)

### Fixed - Glance Docker Networking (December 27, 2025)
- **Fixed Glance API connectivity** - Glance container couldn't reach local APIs (Media Stats, Reddit, NBA Stats)
- **Root Cause**: Glance config used `localhost` URLs, but Docker containers have isolated network namespaces
- **Fix**: Updated all API URLs from `localhost` to `172.17.0.1` (Docker bridge gateway)
  - `http://localhost:5054` → `http://172.17.0.1:5054` (Media Stats API)
  - `http://localhost:5053` → `http://172.17.0.1:5053` (Reddit Manager)
  - `http://localhost:5060` → `http://172.17.0.1:5060` (NBA Stats API)
- **Deployed Network Dashboard Sorting** - Updated `omada-network.json` with sort transformations
  - Top 10 Clients by Traffic: Now sorted descending by value
  - Client TX Rate: Now sorted descending by value
  - Client RX Rate: Now sorted descending by value

### Added - Immich OAuth/SSO Integration (December 27, 2025)
- **Integrated Immich with Authentik** for Single Sign-On authentication
- **Created OAuth2/OIDC provider** in Authentik for Immich application
- **Configured Immich OAuth settings** via PostgreSQL database update
- **Added Immich icon** to Authentik application dashboard
- **New tutorial**: `docs/IMMICH_AUTHENTIK_SSO_TUTORIAL.md` - comprehensive guide
- **Updated documentation**:
  - `docs/APPLICATION_CONFIGURATIONS.md` - added OAuth section
  - Obsidian `11 - Credentials.md` - added OAuth credentials

### Fixed - Grafana Iframe Embedding (December 27, 2025)
- **Fixed Traefik services.yml structure** - middlewares were incorrectly placed under serversTransports
- **Removed Authentik auth from Grafana route** - allows anonymous read-only access for iframe embedding
- **Updated Grafana ROOT_URL** to HTTPS (grafana.hrmsmrflrii.xyz)
- **Changed Glance iframe URLs** from HTTP to HTTPS to fix mixed content blocking
- **Fixed empty Host() rule** for open-notebook route (was matching all traffic)

### Fixed - Monitoring Stack Rebuild (December 27, 2025)
- **Rebuilt Prometheus configuration** on new core-utilities VM (192.168.40.13)
  - Added targets: cadvisor, cadvisor-media, docker-stats-media, traefik, omada, synology, proxmox
  - Created SNMP exporter config for Synology NAS monitoring
  - Deployed PVE Exporter for Proxmox metrics (token: tf01)
  - Fixed Traefik metrics port (8082→8083)
  - **All 10 targets now UP**: cadvisor, cadvisor-media, docker-stats-media, omada, prometheus, synology, traefik, proxmox (3/3)

- **Imported Grafana dashboards** to new instance
  - synology-nas-modern: Synology NAS Storage monitoring
  - omada-network: Omada Network Overview
  - containers-modern: Container Monitoring
  - proxmox-compute: Proxmox Cluster Overview (added 2025-12-27)

- **Fixed broken RSS feeds in Glance**
  - Replaced broken XDA category feeds with main feed (https://www.xda-developers.com/feed/)
  - Updated Google News RSS URL format

- **Deployed services on 192.168.40.13**:
  - Life Progress API (port 5051)
  - n8n workflow automation (port 5678)
  - Jaeger tracing (port 16686)
  - PVE Exporter (port 9221)
  - SNMP Exporter (port 9116)

- **Updated Traefik routes** from 192.168.40.10 to 192.168.40.13
  - Affected services: Grafana, Prometheus, Uptime Kuma, Speedtest, n8n, Paperless, Jaeger

- **Updated Glance configuration**
  - Fixed dashboard iframe URLs to use direct IP (http://192.168.40.13:3030)
  - Changed container-status to containers-modern dashboard
  - Bypasses Authentik authentication for iframe loading

- **Updated documentation**
  - context.md: New infrastructure layout with LXC 200 and VM 107
  - active-tasks.md: Session completion record

### Added - Discord Bot Reorganization (December 26, 2025)
- **Argus Bot** - Container Update Guardian (`#container-updates`)
  - Watchtower webhook integration for update notifications
  - Button-based update approvals with SSH container management
  - Commands: `/check`, `/update`, `/updateall`, `/containers`, `/status`
  - Webhook endpoint: `http://192.168.40.10:5050/webhook`
  - Deployment: `ansible-playbooks/container-updates/deploy-argus-bot.yml`

- **Mnemosyne Bot** - Media Guardian (`#media-downloads`)
  - Real-time download progress notifications (50%, 80%, 100%)
  - New commands: `/availablemovies`, `/availableseries`, `/showlist`
  - Existing: `/downloads`, `/search`, `/request`, `/stats`, `/recent`, `/quality`
  - Radarr/Sonarr integration with library browsing
  - Deployment: `ansible-playbooks/media-downloads/deploy-mnemosyne-bot.yml`

- **Chronos Bot** - Project Management (`#project-management`)
  - GitLab Boards integration for task management
  - Commands: `/todo`, `/tasks`, `/done`, `/close`, `/board`, `/quick`
  - Priority labels: high, medium, low
  - Deployment: `ansible-playbooks/project-management/deploy-chronos-bot.yml`

- **Documentation**: Created `docs/DISCORD_BOTS.md` with full bot documentation

### Added - Chess.com Stats Widget (December 26, 2025)
- **Chess.com Stats Widget** added to Glance Home page right column
  - Displays Blitz and Rapid ratings with W/L/D records
  - Uses Prometheus-style card layout with colored gradients
  - Blitz: Amber gradient (#f59e0b)
  - Rapid: Blue gradient (#3b82f6)
  - API: `https://api.chess.com/pub/player/hrmsmrflrii/stats`
  - Cache: 30 minutes
  - Clickable link to Chess.com profile

### Fixed - Network Dashboard Sorting (December 26, 2025)
- **Changed visualization type** from `bargauge` to `barchart` for proper sorting
- **Affected panels**:
  - Top 10 Clients by Traffic
  - Client TX Rate
  - Client RX Rate
- **Transformations added**: `reduce` + `sortBy` (descending by value)
- Same pattern as Container Status dashboard for consistency

### Fixed - Network Tab Infrastructure Monitors (December 26, 2025)
- **Removed broken HTTP monitors** for unreachable management VLANs
  - Network Infrastructure monitor (192.168.0.x, 192.168.90.x)
  - Wireless APs monitor (192.168.90.x)
- **Root cause**: Docker VM (VLAN 40) cannot reach management VLANs
- **Replaced with**: Prometheus-based "Network Device Status" widget
  - Shows all Omada devices with status and CPU %
  - Data source: `omada_device_cpu_percentage` metric
  - Devices shown: Core Router, Core Switch, Morpheus Switch, Atreus Switch, 3 APs

### Added - Glance Home Page Widgets (December 26, 2025)
- **Chess.com Stats Widget** - Displays Blitz and Rapid ratings with W/L records
  - Uses Chess.com public API with User-Agent header (required for API access)
  - Template uses direct JSON path syntax: `{{ .JSON.Int "chess_blitz.last.rating" }}`
  - Username: hrmsmrflrii
- **Sunrise/Sunset Widget** - Shows sun times for Manila using sunrise-sunset.org API
  - Location: Manila, Philippines (14.5995, 120.9842)
  - Displays sunrise and sunset times in 12-hour format
- **Obsidian Daily Notes Widget** - Displays today's daily note from Obsidian vault
  - Requires Obsidian Local REST API plugin on MacBook
  - Connects via Tailscale (MacBook IP: 100.90.207.58, Port: 27123)
  - Plugin must bind to 0.0.0.0 (not localhost) for server access
  - Shows Priorities, Habits, and Energy sections with link to open in Obsidian

### Fixed - Chess.com Widget (December 26, 2025)
- **Added User-Agent header** - Chess.com API blocks requests without proper User-Agent
- **Simplified template syntax** - Changed from nested `{{ with .JSON.Object }}` to direct path access
- **Removed duplicate widget** - Deleted extra "Chess.com Stats" widget from lower right column
- **Added profile photo** - Uses actual Chess.com avatar from player profile API

### Enhanced - Glance Web & Reddit Pages (December 26, 2025)
- **Web Page Revamped** as comprehensive tech news aggregator with collapsible sections:
  - **Tech YouTube**: 7 channels (MKBHD, Linus Tech Tips, Mrwhosetheboss, Dave2D, Austin Evans, JerryRigEverything, Fireship)
  - **Tech News**: The Verge, XDA, TechCrunch, Ars Technica
  - **Android & Mobile**: XDA Mobile, Google News Android, r/Android
  - **AI & Machine Learning**: TechCrunch AI, r/artificial, r/MachineLearning, r/LocalLLaMA, r/ChatGPT
  - **Cloud & Enterprise**: AWS Blog, r/aws, r/googlecloud, r/azure, r/oracle
  - **Big Tech**: r/microsoft, r/NVIDIA, r/google, r/apple, r/Meta
  - **Gaming**: r/gaming, r/pcgaming, r/Games, Ars Gaming
  - **PC Builds & Hardware**: r/buildapc, r/pcmasterrace, r/hardware, XDA Computing
  - **Travel**: r/travel, r/solotravel, r/TravelHacks
  - **Sidebar**: Tech Stocks (8), Crypto (5), Crypto/Stock news, Quick links
- **Reddit Page Enhanced** with dynamic subreddit aggregation:
  - Reddit Manager updated with 16 subreddits: homelab, selfhosted, datahoarder, linux, devops, kubernetes, docker, technology, programming, webdev, sysadmin, netsec, gaming, pcmasterrace, buildapc, mechanicalkeyboards
  - Native Reddit widgets for r/technology, r/programming, r/sysadmin with thumbnails
  - Grouped view mode enabled for organized display
  - Thumbnails on all posts where available
- **YouTube Channel IDs**:
  - MKBHD: UCBJycsmduvYEL83R_U4JriQ
  - Linus Tech Tips: UCXuqSBlHAE6Xw-yeJA0Tunw
  - Mrwhosetheboss: UCMiJRAwDNSNzuYeN2uWa0pA
  - Dave2D: UCVYamHliCI9rw1tHR1xbkfw
  - Austin Evans: UCXGgrKt94gR6lmN4aN3mYTg
  - JerryRigEverything: UCWFKCr40YwOZQx8FHU_ZqqQ
  - Fireship: UCsBjURrPoezykLs9EqgamOA
- **Files Created**:
  - `temp-glance-web-reddit-update.py` - Configuration script
  - `ansible-playbooks/glance/deploy-web-reddit-update.yml` - Deployment playbook

### Enhanced - Glance Sports Tab with Injuries & News (December 26, 2025)
- **New API Endpoints**:
  - `/injuries` - NBA injury report with player headshots from ESPN CDN
  - `/news` - NBA news headlines with article images
- **Sports Tab expanded to 7 widgets** (was 5):
  - Column 1: Today's NBA Games + **Injury Report** (with player photos, status colors)
  - Column 2: NBA Standings + **NBA News** (with article images)
  - Column 3: Fantasy League + Week Matchups + Hot Pickups
- **Hot Pickups Fixed**: Stats now display correctly (PTS/AST/REB instead of "None")
- **Player Headshots**: ESPN CDN format: `https://a.espncdn.com/i/headshots/nba/players/full/{id}.png`
- **Injury Status Colors**: Red for "Out", Yellow for "Day-To-Day"
- **Dockerfile Fix**: Changed to `COPY *.py .` to include all Python modules

### Added - Glance Sports Tab with NBA Stats API (December 26, 2025)
- **NBA Stats API** deployed on docker-utilities (192.168.40.10:5060)
  - `/games` - Today's NBA games with live scores and team logos (ESPN API)
  - `/standings` - Current NBA standings with team logos (East/West conferences)
  - `/injuries` - NBA injury report with player headshots (ESPN API)
  - `/news` - NBA news headlines with images (ESPN API)
  - `/fantasy` - Yahoo Fantasy NBA league standings (cached, updates 2pm daily)
  - `/fantasy/matchups` - Current week H2H matchups with scores
  - `/fantasy/recommendations` - Player pickup recommendations (top available free agents)
  - `/health` - Health check endpoint
- **Glance Sports Tab** added with 7 widgets in 3-column layout:
  - Column 1 (small): Today's NBA Games + Injury Report
  - Column 2 (full): NBA Standings (East/West) + NBA News
  - Column 3 (small): Fantasy League + Week Matchups + Hot Pickups (stacked)
- **Yahoo Fantasy Integration**:
  - League ID: `466.l.12095` (2024-25 NBA season)
  - OAuth2 authentication with headless token generation flow
  - Auto token refresh (stored in `/opt/nba-stats-api/data/yahoo_token.json`)
  - H2H Categories league support
- **Team Logos**: Pulled dynamically from ESPN CDN (not stored locally)
- **Files Created**:
  - `ansible-playbooks/glance/deploy-nba-stats-api.yml` - Deployment playbook
  - `/opt/nba-stats-api/nba-stats-api.py` - Main Flask API (on server)
  - `/opt/nba-stats-api/yahoo_fantasy.py` - Yahoo Fantasy API module (on server)
  - `/opt/nba-stats-api/fantasy_recommendations.py` - Player recommendations (on server)
- **Sports Tab Protected**: Do not modify without explicit user permission

### Added - Docker Services Documentation (December 26, 2025)
- **New Documentation**: `docs/DOCKER_SERVICES.md`
  - Comprehensive inventory of all Docker services across both hosts
  - docker-vm-utilities01 (192.168.40.10): 35+ containers
  - docker-vm-media01 (192.168.40.11): 15+ containers
  - Port allocation summary and reserved ports
  - Quick access URLs (local and external)
  - Maintenance instructions

### Added - Comprehensive Omada Network Dashboard (December 26, 2025)
- **Dashboard JSON**: `temp-omada-full-dashboard.json` with 7 row sections and 28 panels (Version 3)
- **Sections**:
  - **Overview**: Total/Wired/Wireless clients, Controller uptime/storage/upgrades, WiFi mode distribution
  - **Device Health**: Gateway CPU/Memory gauges, Switch/AP CPU bar gauges, Pi-hole style uptime boxes
  - **WiFi Signal Quality**: Client RSSI (-100 to -20 dBm), SNR (0-60 dB), Signal over time (h=12, h=10)
  - **Switch Port Status**: Table with Switch, Port, Status (colored), Speed, PoE, Port Name
  - **PoE Power Usage**: Total power gauge, Remaining power, Per-port power consumption
  - **Traffic Analysis**: Client trends, Top 10 clients by traffic, Device download/upload rates
  - **Client Details**: Full table with Client, IP, MAC, VLAN, Port, Mode, SSID, AP, Vendor, WiFi, Activity
- **Ansible Playbooks**:
  - `deploy-omada-full-dashboard.yml` - Deploys comprehensive dashboard from JSON
  - `update-glance-network-tab.yml` - Updates Glance Network tab with 2200px iframe
- **Configuration**: UID `omada-network`, iframe height 2200px, Omada exporter at 192.168.20.30:9202
- **Documentation**: Added comprehensive tutorial in `docs/OMADA_NETWORK_DASHBOARD.md` covering:
  - Part 1: Understanding the Data Source (Omada SDN, available metrics)
  - Part 2: Setting Up Data Collection (exporter, Prometheus)
  - Part 3: Building the Dashboard (JSON structure, panel types, PromQL)
  - Part 4: Deploying the Dashboard (API, Ansible)
  - Part 5: Design Decisions (Pi-hole style, table for ports, heights)
  - Part 6: Maintenance Notes (protected status, version history)
- **PROTECTED**: Dashboard marked as protected - do not modify without permission

### Added - Tailscale Subnet Router for Remote Access (December 26, 2025)
- **node01 configured as Tailscale subnet router** for full homelab remote access
- **Advertised subnets**:
  - `192.168.20.0/24` - Infrastructure VLAN (Proxmox nodes, Ansible, K8s)
  - `192.168.40.0/24` - Services VLAN (Docker hosts, applications)
  - `192.168.91.0/24` - Firewall VLAN (OPNsense DNS at 192.168.91.30)
- **IP forwarding enabled** on node01 (`/etc/sysctl.d/99-tailscale.conf`)
- **Split DNS configured** in Tailscale Admin Console:
  - Nameserver: `192.168.91.30` (OPNsense Unbound)
  - Restricted to domain: `hrmsmrflrii.xyz`
- **What works remotely via Tailscale**:
  - SSH to any VM/container using local IPs (e.g., `ssh 192.168.40.10`)
  - Web services via domain names (e.g., `https://grafana.hrmsmrflrii.xyz`)
  - Proxmox Web UI via local or Tailscale IP
  - Full DNS resolution for `*.hrmsmrflrii.xyz`
- **macOS client configuration**:
  - CLI path: `/Applications/Tailscale.app/Contents/MacOS/Tailscale`
  - Accept routes: `tailscale up --accept-routes`
- Documentation: Updated `docs/NETWORKING.md` with complete subnet router architecture

### Fixed - Synology NAS Memory Metric (December 26, 2025)
- **Issue**: Memory gauge showed ~95% usage when NAS was actually at ~7%
- **Root Cause**: Original formula `(1 - memAvailReal/memTotalReal) * 100` counted cache and buffers as "used" memory
- **Fix**: Updated formula to exclude reclaimable memory:
  ```promql
  ((memTotalReal - memAvailReal - memBuffer - memCached) / memTotalReal) * 100
  ```
- **Memory Over Time Chart** now shows 3 series:
  - Used (Real) - red: Actual memory in use by applications
  - Cache/Buffers - amber: Reclaimable memory used for disk caching
  - Free - green: Completely unused memory
- **Dashboard JSON**: `temp-synology-nas-dashboard.json` updated to version 4
- **Documentation**: Updated `.claude/context.md`, `docs/GLANCE.md` with correct formulas

### Fixed - Jellyfin SSO Redirect URI Error (December 25, 2025)
- **Issue**: "Redirect URI Error" when clicking "Sign in with Authentik" on Jellyfin
- **Root Cause**: Authentik provider had ForwardAuth redirect URIs (`/outpost.goauthentik.io/callback`) instead of SSO-Auth plugin URIs (`/sso/OID/redirect/authentik`)
- **Fix**: Updated Authentik provider with correct redirect URIs:
  - `https://jellyfin.hrmsmrflrii.xyz/sso/OID/redirect/authentik`
  - `http://jellyfin.hrmsmrflrii.xyz/sso/OID/redirect/authentik` (for reverse proxy scheme mismatch)
- **Documentation**: Added comprehensive troubleshooting guide in `docs/TROUBLESHOOTING.md` explaining:
  - OAuth2 redirect URI security mechanism
  - ForwardAuth vs SSO-Auth Plugin authentication methods
  - Scheme mismatch problem with TLS-terminating reverse proxies

### Fixed - Container Dashboard Top 5 Memory Sorting (December 25, 2025)
- **Issue**: Top 5 Memory panels displayed unsorted (random order instead of highest to lowest)
- **Root Cause**: Grafana `bargauge` visualization doesn't support value-based series sorting
- **Fix**: Changed visualization from `bargauge` to `barchart` with:
  - `instant: true` query for single values
  - `reduce` transformation to convert time series
  - `sortBy` transformation with descending order
- Dashboard version updated to 15

### Added - New Services Batch Deployment (December 25, 2025)
- **4 New Services** deployed to docker-vm-utilities01:
  - **Lagident** (Port 9933) - Simple photo gallery with SQLite backend
  - **Karakeep** (Port 3005) - AI-powered bookmark manager (formerly Hoarder)
  - **Wizarr** (Port 5690) - Jellyfin/Plex user invitation system
  - **Tracearr** (Port 3002) - Media tracking and analytics
- Traefik routes configured in `/opt/traefik/config/dynamic/new-services.yml`
- Glance Home page updated with:
  - New Services monitor (health checks for all 4 services)
  - Bookmark entries: Lagident (Photos), Karakeep (Productivity), Wizarr (Media), Tracearr (Media)
  - Dashboard icons from walkxcode/dashboard-icons
- DNS entries added in OPNsense for all services
- Ansible playbooks:
  - `ansible-playbooks/services/deploy-lagident.yml`
  - `ansible-playbooks/services/deploy-karakeep.yml`
  - `ansible-playbooks/services/deploy-wizarr.yml`
  - `ansible-playbooks/services/deploy-tracearr.yml`
  - `ansible-playbooks/services/deploy-all-new-services.yml` (master playbook)
  - `ansible-playbooks/services/traefik-new-services.yml`
  - `ansible-playbooks/services/update-glance-new-services.yml`
- Services not deployed:
  - Feeds Fun (no public Docker image - requires building from source)
  - Simple Photo Gallery (static site generator)
  - Stonks Dashboard (no official Docker support)
  - Personal Management System (requires separate frontend repo)

### Added - Omada Network Dashboard
- **Omada Network Overview** Grafana dashboard (`omada-network`):
  - Device summary: Total devices, Gateway, Switches (3), APs (3)
  - Client stats: Total/Wired/Wireless clients, Total traffic
  - Gateway utilization: CPU/Memory gauges + time series
  - Client connection trend over time
  - Speedtest integration: Download/Upload/Ping/Jitter stats
  - WAN traffic (from OPNsense)
  - Switch traffic (Top 5) and PoE power usage
  - Top APs by client count and traffic
  - Clients by SSID distribution (pie chart)
  - OPNsense firewall: Gateway status, services, blocked packets, firewall rates
  - DNS stats: Queries and blocked (30m window)
- Omada Exporter deployment: `ansible-playbooks/monitoring/deploy-omada-exporter.yml`
- Dashboard playbook: `ansible-playbooks/monitoring/deploy-omada-network-dashboard.yml`
- Prometheus scrape config: `ansible-playbooks/monitoring/prometheus-omada-scrape.yml`
- Glance Network tab update: `temp-update-network-tab.py`
- Documentation: `docs/OMADA_NETWORK_DASHBOARD.md`
- Glance iframe height: 1600px
- Limitations: ISP Load, Gateway Alerts, and DPI/Application data not available via Omada API

### Added - Synology NAS Storage Dashboard (PROTECTED)
- **Synology NAS Storage** Grafana dashboard (`synology-nas-modern`):
  - 6 disk health stat tiles (4 HDDs green, 2 M.2 SSDs purple when healthy)
  - Summary stats: Uptime, Total/Used/Free Storage, CPU %, Memory %
  - Disk temperatures bargauge with gradient coloring
  - CPU Usage Over Time (4 cores)
  - Memory Usage Over Time (Used/Available)
  - Storage Consumption Over Time (7-day window) showing Used/Free/Total trends
  - Prometheus SNMP metrics: synologyDiskHealthStatus, synologyRaidTotalSize, hrProcessorLoad, memTotalReal
- Dashboard JSON: `temp-synology-nas-dashboard.json`
- Ansible playbook: `ansible-playbooks/monitoring/deploy-synology-nas-dashboard.yml`
- Glance Storage tab iframe height: 1350px
- **PROTECTED**: Do not modify without explicit user permission

### Added - Container Status History Dashboard (PROTECTED)
- **Container Status History** Grafana dashboard (`container-status`):
  - **Top 5 Memory Usage panels**: Side-by-side bar gauge panels showing top 5 memory-hungry containers per VM
    - Utilities VM: Blue-Purple gradient (`continuous-BlPu`)
    - Media VM: Green-Yellow-Red gradient (`continuous-GrYlRd`)
    - Query: `topk(5, docker_container_memory_percent{job="..."})`
  - State timeline visualization showing container uptime over 1 hour window
  - Summary stats: Total/Running containers, Memory, CPU gauge
  - VM stats: Container counts and stable counts (>1h uptime) per VM
  - Container Issues table: Shows stopped and recently restarted containers
  - Key fix: Uses `state-timeline` instead of `status-history` to handle data volume
  - Query interval: `1m` to prevent "Too many points" errors
  - Stable query: `> 3600` (1h threshold) with `or vector(0)` fallback
- Dashboard JSON: `temp-container-status-with-memory.json`
- Ansible playbook: `ansible-playbooks/monitoring/deploy-container-status-dashboard.yml`
- Glance iframe height: 1500px
- **PROTECTED**: Do not modify without explicit user permission

### Added - Tailscale Remote Access Documentation
- Added Tailscale IP addresses for Proxmox nodes to documentation
- Updated: claude.md, docs/NETWORKING.md, GitHub Wiki, Obsidian vault
- Tailscale IPs: node01 (100.89.33.5), node02 (100.96.195.27), node03 (100.76.81.39)

### Added - Multi-Session Workflow
- Created `.claude/` directory structure for multi-session coordination:
  - `context.md` - Infrastructure reference
  - `active-tasks.md` - Work-in-progress tracking
  - `session-log.md` - Session history
  - `conventions.md` - Standards and patterns
- Refactored claude.md with handoff protocol

### Added - New Productivity & Tools Services
- **BentoPDF** (https://bentopdf.hrmsmrflrii.xyz)
  - Privacy-first PDF toolkit for document manipulation
  - Deployed on docker-vm-utilities01:5055
  - Authentik forward auth protection
- **Edgeshark** (https://edgeshark.hrmsmrflrii.xyz)
  - Docker container network inspector by Siemens
  - Two-container setup: Ghostwire (discovery) + Packetflix (UI)
  - Live packet capture, network namespace visualization
  - Deployed on docker-vm-utilities01:5056
- **Reactive Resume** (https://resume.hrmsmrflrii.xyz)
  - Self-hosted resume builder (30k+ GitHub stars)
  - Four-container stack: App, PostgreSQL, MinIO, Chromium
  - PDF export, multiple templates, dark mode
  - Deployed on docker-vm-utilities01:5057

### Added - Infrastructure Updates
- Traefik routes for BentoPDF, Edgeshark, Reactive Resume
- Authentik forward auth providers for all three services
- Update Manager container tracking for new services

### Fixed
- **Glance Dashboard Icons** - Replaced broken `si:` icons with Dashboard Icons URLs for Lidarr, Prowlarr, Bazarr, Jellyseerr, and Tdarr
- **SABnzbd Health Monitor** - Corrected port from 8082 to 8081 in Glance config
- **Arr Stack Path Mapping** - Added additional volume mappings for download client compatibility:
  - `/mnt/media/Completed:/downloads/complete`
  - `/mnt/media/Movies:/movies`
  - `/mnt/media/Series:/tv`

### Added
- **Jellyseerr SSO Integration** - Native OIDC support with Authentik:
  - Switched from `latest` to `preview-OIDC` branch image (OIDC only available in preview branch)
  - Created OAuth2/OpenID provider in Authentik with regex redirect URIs
  - Added extra_hosts for container DNS resolution to Authentik
  - Configured OIDC via Jellyseerr UI (Settings → Users → Configure OpenID Connect)
  - Added both HTTP and HTTPS redirect URIs to handle scheme mismatch behind reverse proxy
- **Media Page Enhancements** - "Now Showing" widget with recent downloads and poster covers
- **Download Progress Widget** - Real-time download progress bars with ETA
- Media Stats API endpoints: `/api/recent` and `/api/queue`

### Changed
- Updated `.claude/settings.local.json`
- Jellyseerr Docker image changed from `fallenbagel/jellyseerr:latest` to `fallenbagel/jellyseerr:preview-OIDC`

### Documentation
- Added Jellyseerr SSO Integration guide to docs/APPLICATION_CONFIGURATIONS.md
- Added Jellyseerr troubleshooting entries to docs/TROUBLESHOOTING.md:
  - "Jellyseerr OIDC Not Working with Latest Image" - Switch to preview-OIDC branch
  - "Jellyseerr SSO Redirect URI Error" - HTTP/HTTPS scheme mismatch fix
- Added Jellyfin and Jellyseerr SSO sections to GitHub Wiki Application-Configurations.md
- Updated Obsidian documentation (21 - Application Configurations.md, 12 - Troubleshooting.md)
- Added Glance icon troubleshooting guide to TROUBLESHOOTING.md
- Documented Dashboard Icons as preferred icon source for arr stack apps

## [2025-12-24] - Glance Dashboard Revamp with Modern Container Monitoring

### Added - Glance Dashboard 7-Tab Structure
- **Complete dashboard revamp** with 7 organized tabs:
  - Home (protected), Compute, Storage, Network, Media (protected), Web, Reddit
- **Compute Tab** - Proxmox cluster metrics + Container monitoring via embedded Grafana
- **Storage Tab** - Synology NAS dashboard with SNMP metrics
- **Network Tab** - OPNsense firewall metrics + Speedtest results widget
- **Web Tab** - Tech news, AI/ML feeds, stocks, crypto, NBA scores (replaces Sports)

### Added - Grafana Dashboards
- **Proxmox Cluster Dashboard** (`proxmox-compute`):
  - Nodes Online, Avg CPU/Memory %, Running/Stopped VMs
  - CPU & Memory usage by node (time series)
  - Storage usage bar gauges (Local LVM, VMDisks, ProxmoxData)
- **Container Monitoring Dashboard** (`containers-modern`) with modern visual style:
  - Summary stats row: Total/Running containers, Total Memory, CPU gauge
  - Memory usage bar gauges (Blue-Yellow-Red gradient) grouped by VM
  - CPU usage bar gauges (Green-Yellow-Red gradient) grouped by VM
  - Horizontal gradient bars instead of tables for modern look
- **Synology Storage Dashboard** (`synology-storage`):
  - CPU Load, Root Volume %, Total/Free Storage
  - Storage usage over time
- **Network Overview Dashboard** (`network-overview`):
  - OPNsense Gateway status, Services running, TCP connections
  - WAN traffic, Firewall pass/block rates, Protocol packet rates

### Added - Prometheus Exporters
- **OPNsense Exporter** on port 9198 - Firewall metrics from 192.168.91.30
- **Docker Stats Exporter** on port 9417 - Container metrics from both Docker VMs
- Updated Prometheus scrape config with new targets

### Changed
- Container monitoring now uses modern gradient bar gauges instead of tables
- **Container sorting**: All bar gauges now sort containers from highest to lowest utilization using `topk()` queries with `sortBy` transformation
- **Transparent dashboards**: All Grafana iframes use `theme=transparent` for seamless Glance integration
- **Hidden scrollbars**: Custom CSS added to Glance to hide iframe scrollbars
- Glance iframe heights optimized: Proxmox 1100px, Containers 850px, Storage 500px, Network 750px

### Documentation
- Updated CLAUDE.md with complete Compute tab configuration
- Updated docs/GLANCE.md with 7-tab structure and dashboard details
- Updated docs/SERVICES.md with new Grafana dashboards table
- Updated Obsidian vault with dashboard architecture

## [2025-12-23] - Glance Dashboard Home Page Configuration

### Added - Glance Home Page
- **Comprehensive Home page layout** with 3-column structure:
  - Left column: Clock, Weather, Calendar, Infrastructure & Services bookmarks
  - Center column: Life Progress, GitHub Contributions, service health monitors
  - Right column: Crypto/Stock markets, Tech News RSS
- **Service health monitoring** for:
  - Proxmox Cluster (Node 01-03)
  - Storage (Synology NAS on VLAN 10 & 20)
  - Core Services (Traefik, Authentik, GitLab, Immich, n8n, Paperless)
  - Media Services (Jellyfin, Arr stack, Deluge, SABnzbd)
  - Monitoring Stack (Uptime Kuma, Prometheus, Grafana, Jaeger, Glance, Speedtest)
  - Kubernetes Control Plane (API server port 6443)
  - Kubernetes Workers (kubelet port 10248)
- **GitHub Contribution Graph** with green theme and dark mode support
- **Home page preservation guidelines** - layout is finalized, changes require explicit permission

### Added - Documentation
- `docs/GLANCE.md` - Comprehensive Glance dashboard documentation with:
  - Media Stats API architecture and code
  - Home page widget configuration reference
  - Health check endpoint documentation
  - Deployment instructions
- `temp-home-fix.py` - Home page configuration management script
- Updated `CLAUDE.md` with Home page structure and preservation warning
- Updated wiki `Glance-Dashboard.md` with Home page configuration
- Updated Obsidian `23 - Glance Dashboard.md` with complete widget reference

### Added - Media Stats API
- `ansible-playbooks/glance/media-stats-api.py` - API aggregator for Radarr/Sonarr stats
- `ansible-playbooks/glance/deploy-media-stats-api.yml` - Deployment playbook
- 3x2 colored tile grid layout (Pi-hole style) for media statistics

## [2025-12-19] - Service Infrastructure Expansion

### Added
- **Traefik v3.2 Reverse Proxy** deployment on traefik-vm01 (192.168.40.20)
  - Pre-configured routes for Jellyfin, Radarr, Sonarr, and other services
  - Dashboard accessible at port 8080
  - HTTP entrypoint on port 80
- **GitLab CE** deployment on gitlab-vm01 (192.168.40.23)
  - Optimized for homelab environment
  - Initial root setup required at first access
- **Authentik SSO** deployment on authentik-vm01 (192.168.40.21)
  - PostgreSQL and Redis containers included
  - Initial admin setup flow available

### Added - Ansible Playbooks
- `ansible-playbooks/traefik/deploy-traefik.yml` - Automated Traefik deployment
- `ansible-playbooks/gitlab/deploy-gitlab.yml` - GitLab CE installation
- `ansible-playbooks/authentik/deploy-authentik.yml` - Authentik SSO setup
- `ansible-playbooks/docker/install-docker.yml` - Docker installation automation
- `ansible-playbooks/docker/deploy-arr-stack.yml` - Complete Arr media stack
- `ansible-playbooks/immich/deploy-immich.yml` - Immich photo management
- `ansible-playbooks/synology/configure-nfs-permissions.yml` - NAS automation

### Added - Documentation
- **SERVICES_GUIDE.md** - Comprehensive 636-line learning guide covering:
  - Traefik reverse proxy architecture and configuration
  - GitLab deployment and setup
  - Authentik SSO integration
  - Complete service explanations for learners
- **ARR_STACK_DEPLOYMENT.md** - 1,063-line media stack deployment guide:
  - Detailed Jellyfin, Radarr, Sonarr, Lidarr setup
  - Prowlarr, Bazarr, Overseerr, Jellyseerr configuration
  - Tdarr transcoding and Autobrr automation
  - Complete troubleshooting section

### Changed
- Updated ANSIBLE_SETUP.md with new playbook references and usage examples
- Updated README.md with Traefik and GitLab deployment sections
- Updated claude.md with comprehensive service deployment details
- Modified main.tf to include new service VMs in infrastructure

## [2025-12-16] - Kubernetes Infrastructure and Educational Documentation

### Added - Kubernetes Playbook Learning Guide
- **Kubernetes_Playbook_Guide.md** - Comprehensive 1,819-line educational guide:
  - Kubernetes architecture fundamentals (control plane, workers, components)
  - Line-by-line explanation of every playbook task
  - Detailed command breakdowns with real-world examples
  - Container networking concepts (CNI, pod networking, services)
  - cgroups, kernel modules, and sysctl parameters explained
  - Certificate management and cluster security
  - Complete deployment flow visualization
  - Comprehensive glossary of Kubernetes terms
  - Learning resources and community links

### Added - Production-Grade Kubernetes Infrastructure
- **9-node HA Kubernetes cluster** configuration:
  - 3 control plane nodes (k8s-controller01-03) on 192.168.20.32-34
  - 6 worker nodes (k8s-worker01-06) on 192.168.20.40-45
  - Stacked etcd on control plane nodes
  - Containerd runtime with systemd cgroup driver
  - Calico CNI v3.27.0 for pod networking (10.244.0.0/16)

### Added - Ansible Automation
- **Complete Kubernetes deployment playbooks** in `ansible-playbooks/k8s/`:
  - `k8s-deploy-all.yml` - Master orchestration playbook
  - `01-k8s-prerequisites.yml` - System preparation (swap, modules, sysctl)
  - `02-k8s-install.yml` - Kubernetes packages installation
  - `03-k8s-init-cluster.yml` - Control plane initialization
  - `04-k8s-install-cni.yml` - Calico CNI deployment
  - `05-k8s-join-nodes.yml` - Worker node cluster join
  - `ops-cluster-status.yml` - Cluster health verification
  - `verify-deployment.sh` - Comprehensive verification script
- Ansible inventory with logical host groups (controllers, workers, k8s_cluster)
- Custom ansible.cfg with optimized settings

### Added - Documentation
- **Kubernetes_Setup.md** - 1,152-line complete deployment guide
- **ANSIBLE_SETUP.md** - 132-line Ansible configuration documentation
- **ansible-playbooks/k8s/00-START-HERE.md** - Quick start guide
- **ansible-playbooks/k8s/DEPLOYMENT-GUIDE.md** - Detailed deployment steps
- **ansible-playbooks/k8s/README.md** - Playbook documentation

### Changed
- Migrated ansible-controller to node01 (renamed from ansible-control)
- Updated total infrastructure to 17 VMs (1 Ansible + 9 Kubernetes + 7 Services)
- Updated resource totals: 36 vCPUs, 72GB RAM, 370GB storage
- Updated README.md with current infrastructure status

### Removed
- ISO-based VM deployment method (`iso-vms.tf`)
- All infrastructure now uses cloud-init deployment exclusively

### Added - Node Health Troubleshooting
- Comprehensive documentation for Proxmox cluster node health issues
- Detailed diagnosis steps for "question mark" / unhealthy node status
- Resolution procedures based on December 16, 2025 node03 incident:
  - Node showed "NR" (Not Ready) status in cluster membership
  - Root cause: Unexpected node shutdown
  - Resolution: Power-on and cluster service verification
  - Successful cluster rejoin documented
- Added verification commands for cluster health monitoring
- Prevention strategies for unexpected shutdowns

## [2025-12-15] - Cloud-init Boot Fix and Initial VM Deployment

### Fixed - Critical Boot Issue
- **Cloud-init VM boot failure** - UEFI/BIOS mismatch resolution:
  - **Problem**: Cloud-init VMs hung during boot at "Btrfs loaded" message
  - **Root Cause**: Template used UEFI boot (bios: ovmf) but Terraform configured legacy BIOS (seabios)
  - **Solution**: Updated `modules/linux-vm/main.tf` with proper UEFI configuration:
    - Added `bios = "ovmf"` for UEFI boot mode
    - Added `efidisk` block for EFI disk configuration
    - Added `machine = "q35"` explicitly
    - Changed `scsihw` from "lsi" to "virtio-scsi-single"
  - **Result**: All cloud-init deployments now fully operational

### Added
- Comprehensive UEFI troubleshooting documentation in TROUBLESHOOTING.md
- Detailed boot failure resolution in CLAUDE.md "Resolved Issues" section
- Cloud-init deployment status and common issues in README.md
- Reference ISO deployment method in `iso-vms.tf` (kept for documentation)

### Changed
- Updated deployment methodology to exclusively use cloud-init with UEFI
- All VMs now boot successfully with proper network initialization
- SSH key authentication fully functional across all deployments

### Deployed
- Initial VM infrastructure deployment completed
- Multiple VMs successfully provisioned using fixed cloud-init configuration

## [2025-12-14] - Node03 Integration and Network Configuration

### Added - Node03 Support
- Successfully deployed ansible-control VMs across node02 and node03
  - ansible-control01: node02, 192.168.20.50
  - ansible-control02: node03, 192.168.20.51
- **Critical network configuration** for node03:
  - VLAN-aware bridge setup (bridge-vlan-aware yes)
  - VLAN ID range configuration (bridge-vids 2-4094)
  - Physical interface auto-start (auto nic0)

### Added - Documentation
- **TROUBLESHOOTING.md** - Comprehensive troubleshooting guide:
  - Node03 QEMU deployment failure resolution
  - Network bridge VLAN configuration steps
  - Diagnostic process and prevention strategies
  - Common error patterns and solutions
- Updated CLAUDE.md with:
  - Node network requirements section
  - Critical bridge configuration examples
  - Current deployment status
  - Updated IP allocation scheme
  - Reference to troubleshooting guide
- Updated README.md with:
  - Quick troubleshooting section for VLAN issues
  - Links to detailed troubleshooting documentation
  - Updated documentation references

### Changed
- Updated DNS nameserver to 192.168.91.30 across all configurations
- Disabled LXC deployments temporarily (focus on VM infrastructure first)

### Fixed
- Node03 network configuration preventing VM deployments
- QEMU error: "no physical interface on bridge 'vmbr0'"
- VLAN filtering and bridge configuration issues

## [2025-12-14] - Production-Grade NFS Storage Architecture

### Added - Storage Architecture
- **Dedicated NFS exports** for each content type:
  - **VMDisks** (`/volume2/ProxmoxCluster-VMDisks`) - Proxmox-managed VM disk images
  - **ISOs** (`/volume2/ProxmoxCluster-ISOs`) - Proxmox-managed ISO storage
  - **LXC Configs** (`/volume2/Proxmox-LXCs`) - Manual mount for app data at `/mnt/nfs/lxcs`
  - **Media** (`/volume2/Proxmox-Media`) - Manual mount for media files at `/mnt/nfs/media`
- **Storage architecture principles**:
  - One NFS export = One Proxmox storage pool
  - Prevents storage state ambiguity and content type conflicts
  - Ensures consistent behavior across all nodes

### Added - Multi-Node Deployment Support
- Auto-incrementing node names with `starting_node` parameter
- Support for cross-node VM deployments (e.g., ansible-control VMs on node02/node03)
- Flexible node allocation for workload distribution

### Added - Documentation
- Comprehensive storage architecture documentation in CLAUDE.md:
  - Synology NAS configuration table
  - Storage architecture principles and design rules
  - Proxmox storage configuration examples
  - Manual NFS mount configuration
  - LXC bind mount strategy with examples
  - Problem prevention and key insights
- Detailed README.md with:
  - Quick start guide
  - Usage examples
  - Storage configuration section
  - Network architecture details

### Changed
- Migrated from `ProxmoxData` to dedicated storage pools (VMDisks, ISOs)
- Updated all Terraform configurations to use new storage architecture
- LXC containers now use `local-lvm` for rootfs
- Application data managed through manual NFS mounts and bind mounts

### Improved
- Eliminated inactive storage warnings in Proxmox UI
- Removed `?` icons caused by mixed content types
- Fixed template clone failures across nodes
- Prevented LXC rootfs errors for app configs
- Improved performance by excluding media from Proxmox scanning
- Ensured consistent migration paths across nodes

## [2025-12-14] - Initial Repository Setup

### Added
- **Terraform Infrastructure** for Proxmox VE 9.1.2:
  - Provider configuration using telmate/proxmox v3.0.2-rc06
  - Support for VM and LXC container deployments
  - Modular structure with reusable modules
- **Modules**:
  - `modules/linux-vm/` - Linux VM deployment module
  - `modules/lxc/` - LXC container deployment module
  - `modules/windows-vm/` - Windows VM deployment module (future use)
- **Core Configuration Files**:
  - `main.tf` - Main VM orchestration and group definitions
  - `lxc.tf` - LXC container definitions
  - `variables.tf` - Global variables and defaults
  - `outputs.tf` - Output definitions for deployed resources
  - `providers.tf` - Proxmox provider configuration
- **Environment Support**:
  - `env/lab.tfvars` - Lab environment variables
  - `env/prod.tfvars` - Production environment variables
  - `terraform.tfvars.example` - Example variable file
- **Documentation**:
  - `README.md` - Project overview and quick start
  - `claude.md` - Comprehensive infrastructure documentation
  - `QUICKSTART.md` - Quick deployment guide
  - `CONFIGURATION_EXAMPLES.md` - Configuration examples and patterns
  - `DYNAMIC_VMS_GUIDE.md` - Dynamic VM deployment guide
  - `LXC_GUIDE.md` - LXC container deployment documentation
  - `TEMPLATE_LIBRARY_GUIDE.md` - Template creation and management
  - `CREATE_TEMPLATE_GUIDE.md` - Step-by-step template creation
  - `PERMISSIONS_SETUP.md` - Proxmox API permissions configuration
- **Examples**:
  - `lxc-example.tf` - Example LXC configurations
  - `scripts/cloud-init/user-data.yaml` - Cloud-init template
- **Project Configuration**:
  - `.gitignore` - Git ignore rules for sensitive files
  - `.terraform.lock.hcl` - Terraform provider lock file
  - `.claude/settings.local.json` - Claude Code settings

### Infrastructure Design
- **3-node Proxmox cluster**:
  - node01 (192.168.20.20) - VM Host
  - node02 (192.168.20.21) - LXC Host
  - node03 (192.168.20.22) - General Purpose
- **Network Architecture**:
  - VLAN 20 (192.168.20.0/24) - Kubernetes Infrastructure
  - VLAN 40 (192.168.40.0/24) - Services & Management
  - Bridge: vmbr0 (VLAN-aware required)
- **Authentication**:
  - SSH key authentication (hermes-admin user)
  - Proxmox API token authentication
  - Cloud-init automated provisioning

### Features
- Auto-incrementing hostnames and IP addresses
- Dynamic resource creation with Terraform for_each
- Cloud-init automation for VM provisioning
- Consistent configuration through DRY modules
- Support for both UEFI and BIOS boot modes
- QEMU guest agent integration
- Comprehensive output variables for deployed resources

---

## Version History Summary

- **2025-12-23**: Glance Dashboard Home page configuration and documentation
- **2025-12-19**: Service infrastructure expansion (Traefik, GitLab, Authentik, Arr Stack)
- **2025-12-16**: Kubernetes infrastructure (9-node HA cluster) and educational documentation
- **2025-12-15**: Cloud-init boot fix (UEFI/BIOS) and initial VM deployment
- **2025-12-14**: Node03 integration, VLAN configuration, and NFS storage architecture
- **2025-12-14**: Initial repository setup with Terraform modules and documentation

[Unreleased]: https://github.com/herms14/Proxmox-TerraformDeployments/compare/v2025-12-23...HEAD
[2025-12-23]: https://github.com/herms14/Proxmox-TerraformDeployments/compare/v2025-12-19...v2025-12-23
[2025-12-19]: https://github.com/herms14/Proxmox-TerraformDeployments/compare/v2025-12-16...v2025-12-19
[2025-12-16]: https://github.com/herms14/tf-proxmox/compare/v2025-12-15...v2025-12-16
[2025-12-15]: https://github.com/herms14/tf-proxmox/compare/v2025-12-14...v2025-12-15
[2025-12-14]: https://github.com/herms14/tf-proxmox/releases/tag/v2025-12-14
