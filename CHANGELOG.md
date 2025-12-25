# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - Container Status History Dashboard (PROTECTED)
- **Container Status History** Grafana dashboard (`container-status`):
  - State timeline visualization showing container uptime over 1 hour window
  - Summary stats: Total/Running containers, Memory, CPU gauge
  - VM stats: Container counts and stable counts (>1h uptime) per VM
  - Container Issues table: Shows stopped and recently restarted containers
  - Key fix: Uses `state-timeline` instead of `status-history` to handle data volume
  - Query interval: `1m` to prevent "Too many points" errors
  - Stable query: `> 3600` (1h threshold) with `or vector(0)` fallback
- Dashboard JSON: `temp-container-status-fixed.json`
- Ansible playbook: `ansible-playbooks/monitoring/deploy-container-status-dashboard.yml`
- Glance iframe height: 1250px
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
