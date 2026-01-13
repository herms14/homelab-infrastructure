# Hermes' Homelab Technical Manual

> **Complete Infrastructure Technical Reference**
>
> Started: December 2024 | Documentation Version: 3.0 | January 2026
>
> Author: Hermes Miraflor II with Claude Code

---

## Table of Contents

- [Part 1: Foundation](#part-1-foundation)
- [Part 2: Network Infrastructure](#part-2-network-infrastructure)
- [Part 3: Storage Infrastructure](#part-3-storage-infrastructure)
- [Part 4: Compute Infrastructure](#part-4-compute-infrastructure)
- [Part 5: Infrastructure as Code](#part-5-infrastructure-as-code)
- [Part 6: Core Services](#part-6-core-services)
- [Part 7: Media Stack](#part-7-media-stack)
- [Part 8: Observability Stack](#part-8-observability-stack)
- [Part 9: Discord Bot Ecosystem](#part-9-discord-bot-ecosystem)
- [Part 10: Custom APIs](#part-10-custom-apis)
- [Part 11: Backup and Disaster Recovery](#part-11-backup-and-disaster-recovery)
- [Part 12: Azure Cloud Integration](#part-12-azure-cloud-integration)
- [Appendices](#appendices)

---

# Part 1: Foundation

## 1.1 Infrastructure Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           HERMES HOMELAB INFRASTRUCTURE                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│    ┌─────────────────────────────────────────────────────────────────────────┐  │
│    │                         INTERNET                                         │  │
│    │                            │                                             │  │
│    │                   ┌────────▼────────┐                                   │  │
│    │                   │   Cloudflare    │                                   │  │
│    │                   │  (DNS + SSL)    │                                   │  │
│    │                   └────────┬────────┘                                   │  │
│    │                            │                                             │  │
│    │                   ┌────────▼────────┐                                   │  │
│    │                   │   ER605 Router  │                                   │  │
│    │                   │   192.168.0.1   │                                   │  │
│    │                   └────────┬────────┘                                   │  │
│    └─────────────────────────────────────────────────────────────────────────┘  │
│                                 │                                                │
│    ┌─────────────────────────────────────────────────────────────────────────┐  │
│    │                      CORE NETWORK LAYER                                  │  │
│    │                                                                          │  │
│    │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │  │
│    │  │   SG3210     │────│   SG2210P    │────│   OPNsense   │               │  │
│    │  │ Core Switch  │    │  Morpheus    │    │   Firewall   │               │  │
│    │  │ 192.168.90.2 │    │ 192.168.90.3 │    │192.168.91.30 │               │  │
│    │  └──────────────┘    └──────────────┘    └──────────────┘               │  │
│    └─────────────────────────────────────────────────────────────────────────┘  │
│                                 │                                                │
│    ┌─────────────────────────────────────────────────────────────────────────┐  │
│    │                     PROXMOX CLUSTER                                      │  │
│    │                                                                          │  │
│    │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │  │
│    │  │    node01    │    │    node02    │    │    node03    │               │  │
│    │  │192.168.20.20 │    │192.168.20.21 │    │192.168.20.22 │               │  │
│    │  │ Primary Host │    │ Service Host │    │ Desktop Node │               │  │
│    │  └──────────────┘    └──────────────┘    └──────────────┘               │  │
│    └─────────────────────────────────────────────────────────────────────────┘  │
│                                 │                                                │
│    ┌─────────────────────────────────────────────────────────────────────────┐  │
│    │                       STORAGE LAYER                                      │  │
│    │                                                                          │  │
│    │  ┌───────────────────────────────┐    ┌───────────────────────────────┐ │  │
│    │  │       Synology NAS            │    │      Proxmox Backup Server   │ │  │
│    │  │      192.168.20.31            │    │       192.168.20.50          │ │  │
│    │  └───────────────────────────────┘    └───────────────────────────────┘ │  │
│    └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### By the Numbers

| Category | Count | Details |
|----------|-------|---------|
| **Proxmox Nodes** | 3 | node01, node02, node03 |
| **Virtual Machines** | 18+ | K8s nodes, service VMs |
| **LXC Containers** | 5+ | Lightweight services |
| **Docker Containers** | 60+ | Monitored across all hosts |
| **VLANs** | 8 | Segmented network |
| **Services** | 40+ | Applications and APIs |
| **Discord Bots** | 5 | Automation and notifications |
| **Custom APIs** | 6 | Dashboard integrations |

---

## 1.2 Quick Reference Tables

### Proxmox Cluster Nodes

| Node | Local IP | Tailscale IP | Role |
|------|----------|--------------|------|
| **node01** | 192.168.20.20 | 100.89.33.5 | Primary VM Host |
| **node02** | 192.168.20.21 | 100.96.195.27 | Service Host |
| **node03** | 192.168.20.22 | 100.88.228.34 | Desktop Node |

### Key Service URLs

| Service | Internal URL | External URL |
|---------|--------------|--------------|
| **Proxmox** | https://192.168.20.21:8006 | https://proxmox.hrmsmrflrii.xyz |
| **Glance** | http://192.168.40.12:8080 | https://glance.hrmsmrflrii.xyz |
| **Grafana** | http://192.168.40.13:3030 | https://grafana.hrmsmrflrii.xyz |
| **Traefik** | http://192.168.40.20:8082 | https://traefik.hrmsmrflrii.xyz |
| **GitLab** | http://192.168.40.23 | https://gitlab.hrmsmrflrii.xyz |
| **Jellyfin** | http://192.168.40.11:8096 | https://jellyfin.hrmsmrflrii.xyz |
| **PBS** | https://192.168.20.50:8007 | https://pbs.hrmsmrflrii.xyz |

### Docker Hosts

| Host | IP Address | Purpose |
|------|------------|---------|
| **docker-vm-media01** | 192.168.40.11 | Media Stack (Jellyfin, *arr suite) |
| **docker-lxc-glance** | 192.168.40.12 | Dashboard (Glance, custom APIs) |
| **docker-vm-utilities01** | 192.168.40.13 | Monitoring (Grafana, Prometheus, Discord bots) |

### Network VLANs

| VLAN | Network | Purpose |
|------|---------|---------|
| 10 | 192.168.10.0/24 | Internal (Main LAN) |
| 20 | 192.168.20.0/24 | Infrastructure (Proxmox, K8s) |
| 30 | 192.168.30.0/24 | IoT Devices |
| 40 | 192.168.40.0/24 | Production Services |
| 50 | 192.168.50.0/24 | Guest WiFi |
| 60 | 192.168.60.0/24 | Sonos Speakers |
| 90 | 192.168.90.0/24 | Management |
| 91 | 192.168.91.0/24 | Firewall |

---

# Part 2: Network Infrastructure

## 2.1 Physical Network Topology

```
                                    Internet
                                        │
                                        ▼
                              ┌─────────────────┐
                              │   ISP Router    │
                              │  192.168.100.1  │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │   Core Router   │
                              │   ER605 v2.20   │
                              │   192.168.0.1   │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │   Core Switch   │
                              │  SG3210 v3.20   │
                              │  192.168.90.2   │
                              └────────┬────────┘
                                       │
          ┌────────────┬───────────────┼───────────────┬────────────┐
          ▼            ▼               ▼               ▼            ▼
    ┌──────────┐ ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐
    │ Morpheus │ │ OPNsense │  │ Synology │  │  Wireless │  │ Proxmox  │
    │  Switch  │ │ Firewall │  │   NAS    │  │    APs    │  │  Nodes   │
    │ SG2210P  │ │  .91.30  │  │  .20.31  │  │           │  │          │
    └──────────┘ └──────────┘  └──────────┘  └───────────┘  └──────────┘
```

## 2.2 Hardware Inventory

| Device | Model | IP Address | Purpose |
|--------|-------|------------|---------|
| **Core Router** | ER605 | 192.168.0.1 | Main gateway, inter-VLAN routing |
| **Core Switch** | SG3210 | 192.168.90.2 | Primary L2 switch, VLAN trunking |
| **Morpheus Switch** | SG2210P | 192.168.90.3 | Proxmox node connectivity (PoE) |
| **Living Room AP** | EAP610 | 192.168.90.10 | Primary WiFi AP |
| **Outdoor AP** | EAP603 | 192.168.90.11 | Outdoor WiFi AP |

## 2.3 Tailscale Remote Access

All Proxmox nodes have Tailscale installed, with node01 configured as a **subnet router**.

### Subnet Router Configuration

node01 advertises these networks:

| Network | Purpose |
|---------|---------|
| 192.168.20.0/24 | Infrastructure VLAN |
| 192.168.40.0/24 | Services VLAN |
| 192.168.91.0/24 | Firewall VLAN (DNS) |

---

# Part 3: Storage Infrastructure

## 3.1 Synology NAS Configuration

| Property | Value |
|----------|-------|
| Model | Synology DS920+ |
| IP Address | 192.168.20.31 |
| Storage | SHR RAID (2x 4TB) |
| SSD Cache | 2x 500GB NVMe (Read-Write) |

### NFS Shares

| Share Name | Path | Purpose |
|------------|------|---------|
| **VMDisks** | /volume1/VMDisks | Proxmox VM disk images |
| **Media** | /volume2/Proxmox-Media | Movies, Series, Music |
| **Immich** | /volume1/Immich | Photo library |

## 3.2 Proxmox Backup Server (PBS)

| Property | Value |
|----------|-------|
| LXC VMID | 100 on node03 |
| IP Address | 192.168.20.50 |
| Web UI | https://192.168.20.50:8007 |

### Datastores

| Datastore | Storage | Size | Purpose |
|-----------|---------|------|---------|
| **main** | Seagate 4TB HDD | 3.4TB | Weekly/monthly archival |
| **daily** | Kingston 1TB NVMe | 870GB | Daily backups (fast restore) |

---

# Part 4: Compute Infrastructure

## 4.1 What is Proxmox?

**Proxmox Virtual Environment (Proxmox VE)** is an open-source server virtualization platform that combines:
- **KVM**: Full virtualization for complete operating systems
- **LXC**: Lightweight container-based virtualization

### Current Deployment

| Property | Value |
|----------|-------|
| **Version** | Proxmox VE 9.1.2 |
| **Cluster Name** | MorpheusCluster |
| **Nodes** | 3 + Qdevice |

## 4.2 Node Specifications

### node01 (Primary VM Host)

| Spec | Value |
|------|-------|
| IP | 192.168.20.20 |
| CPU | 8 cores |
| RAM | 32 GB |
| Role | K8s cluster, LXCs, Core Services |

### node03 (Desktop Node)

| Spec | Value |
|------|-------|
| IP | 192.168.20.22 |
| CPU | 16 cores (AMD Ryzen 9 5900XT) |
| RAM | 32 GB |
| Role | GitLab, Immich, PBS |

## 4.3 VM and LXC Commands

### VM Commands

| Command | Description |
|---------|-------------|
| `qm list` | List all VMs |
| `qm start <vmid>` | Start VM |
| `qm shutdown <vmid>` | Graceful shutdown |
| `qm config <vmid>` | Show VM config |

### LXC Commands

| Command | Description |
|---------|-------------|
| `pct list` | List all containers |
| `pct start <vmid>` | Start container |
| `pct enter <vmid>` | Enter container shell |

---

# Part 5: Infrastructure as Code

## 5.1 Terraform Configuration

### Provider

| Property | Value |
|----------|-------|
| Provider | telmate/proxmox v3.0.2-rc06 |
| API URL | https://192.168.20.21:8006/api2/json |

### Repository Structure

```
homelab-infra-automation-project/
├── ansible/                     # Ansible configuration management
│   ├── inventory/               # Host inventories
│   │   ├── azure-ad.yml         # Azure AD lab inventory
│   │   └── k8s.ini              # Kubernetes inventory
│   ├── playbooks/               # Organized by category
│   │   ├── monitoring/          # Grafana dashboards, exporters
│   │   ├── services/            # Service deployments
│   │   ├── glance/              # Glance dashboard configs
│   │   ├── sentinel-bot/        # Discord bot deployment
│   │   ├── infrastructure/      # Base infrastructure
│   │   └── ...                  # Other playbook categories
│   └── roles/                   # Reusable Ansible roles
├── terraform/                   # Infrastructure as Code
│   ├── proxmox/                 # Proxmox VM/LXC deployments
│   │   ├── main.tf              # VM definitions
│   │   ├── lxc.tf               # LXC definitions
│   │   ├── variables.tf         # Global variables
│   │   └── terraform.tfvars     # Variable values (gitignored)
│   ├── azure/                   # Azure infrastructure
│   ├── modules/                 # Terraform modules
│   │   ├── linux-vm/            # Linux VM module
│   │   ├── windows-vm/          # Windows VM module
│   │   └── lxc/                 # LXC container module
│   └── env/                     # Environment configs
│       ├── lab.tfvars           # Lab environment
│       └── prod.tfvars          # Production environment
├── docs/                        # Documentation
│   ├── legacy/                  # Archived documentation
│   └── diagrams/                # Architecture diagrams
├── dashboards/                  # Grafana dashboard JSON files
├── scripts/                     # Utility scripts
│   ├── utilities/               # Helper scripts
│   └── diagrams/                # Diagram generation
├── apps/                        # Custom applications
│   └── homelab-chronicle/       # Homelab changelog app
├── homelab-services/            # Service configurations
├── wiki/                        # GitHub Wiki content
├── Azure-Hybrid-Lab/            # Azure AD lab project
├── CLAUDE.md                    # Claude Code context
├── CHANGELOG.md                 # Project changelog
└── README.md                    # Project readme
```

### Common Commands

| Command | Description |
|---------|-------------|
| `terraform init` | Initialize providers |
| `terraform plan` | Preview changes |
| `terraform apply` | Apply changes |
| `terraform state list` | List resources |

## 5.2 Ansible Controller

All configuration management runs from **ansible-controller01** (192.168.20.30).

### Directory Structure

```
ansible/
├── inventory/              # Host inventory files
│   ├── k8s.ini             # Kubernetes hosts
│   └── azure-ad.yml        # Azure AD lab hosts
├── playbooks/              # Playbooks organized by category
│   ├── monitoring/         # Grafana, Prometheus configs
│   ├── services/           # Application deployments
│   ├── glance/             # Glance dashboard
│   ├── sentinel-bot/       # Discord bot
│   └── infrastructure/     # Base infrastructure
└── roles/                  # Reusable roles
```

### Inventory Groups

| Group | Purpose |
|-------|---------|
| `k8s_controllers` | Kubernetes control plane |
| `k8s_workers` | Kubernetes worker nodes |
| `docker_hosts` | Docker VM hosts |
| `services` | Service VMs |

### Common Commands

| Command | Description |
|---------|-------------|
| `ansible-playbook ansible/playbooks/services/<name>.yml` | Deploy a service |
| `ansible-playbook ansible/playbooks/monitoring/<name>.yml` | Deploy monitoring |
| `ansible-playbook -i ansible/inventory/k8s.ini <playbook>` | Use specific inventory |

---

# Part 6: Core Services

## 6.1 Traefik Reverse Proxy

| Property | Value |
|----------|-------|
| Host | traefik-vm01 (192.168.40.20) |
| HTTPS Port | 443 |
| External | https://traefik.hrmsmrflrii.xyz |

### Features

- Automatic HTTP to HTTPS redirect
- Let's Encrypt certificates via Cloudflare DNS-01
- Dynamic service discovery
- OpenTelemetry tracing integration

## 6.2 Authentik SSO

| Property | Value |
|----------|-------|
| Host | authentik-vm01 (192.168.40.21) |
| Port | 9000 |
| External | https://auth.hrmsmrflrii.xyz |

## 6.3 Pi-hole DNS

| Property | Value |
|----------|-------|
| LXC | 202 on node01 |
| IP | 192.168.90.53 |
| External | https://pihole.hrmsmrflrii.xyz |

## 6.4 GitLab

| Property | Value |
|----------|-------|
| Host | gitlab-vm01 (192.168.40.23) |
| HTTP | http://192.168.40.23 |
| SSH | ssh://git@192.168.40.23:2222 |

## 6.5 Immich Photo Management

| Property | Value |
|----------|-------|
| Host | immich-vm01 (192.168.40.22) |
| Port | 2283 |
| External | https://immich.hrmsmrflrii.xyz |

---

# Part 7: Media Stack

## 7.1 Architecture Overview

```
                    Jellyseerr
                    (Requests)
                        │
           ┌───────────┬┴───────────┐
           ▼           ▼            ▼
        Radarr      Sonarr       Lidarr
        (Movies)    (TV)         (Music)
           │           │            │
           └───────────┴────────────┘
                       │
                  Prowlarr
              (Indexer Manager)
                       │
              ┌────────┴────────┐
              ▼                 ▼
           Deluge           SABnzbd
         (Torrents)        (Usenet)
                       │
                    NFS Share
                  /mnt/media/
                       │
              ┌────────┴────────┐
              ▼                 ▼
          Jellyfin            Plex
        (Open Source)      (Synology)
```

## 7.2 Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| Jellyfin | 8096 | Media server |
| Radarr | 7878 | Movie management |
| Sonarr | 8989 | TV series management |
| Lidarr | 8686 | Music management |
| Prowlarr | 9696 | Indexer manager |
| Bazarr | 6767 | Subtitle management |
| Jellyseerr | 5056 | Media requests |
| Deluge | 8112 | BitTorrent client |

---

# Part 8: Observability Stack

## 8.1 Architecture Overview

```
                    Applications
                         │
                    ┌────┴────┐
                    ▼         ▼
                Traefik    Custom APIs
                         │
                OTEL Collector
                   (4317/4318)
                    │    │
           ┌────────┘    └────────┐
           ▼                      ▼
       Jaeger                Prometheus
      (Traces)               (Metrics)
                      │
                   Grafana
                 (Dashboards)
```

## 8.2 Services

| Service | Port | External URL |
|---------|------|--------------|
| Prometheus | 9090 | https://prometheus.hrmsmrflrii.xyz |
| Grafana | 3030 | https://grafana.hrmsmrflrii.xyz |
| Jaeger | 16686 | https://jaeger.hrmsmrflrii.xyz |
| Uptime Kuma | 3001 | https://uptime.hrmsmrflrii.xyz |

## 8.3 Grafana Dashboards

| Dashboard | UID | Purpose |
|-----------|-----|---------|
| Network Utilization | `network-utilization` | Bandwidth monitoring (cluster + NAS) |
| Container Status History | `container-status` | Container up/down timeline |
| Synology NAS | `synology-nas-modern` | NAS storage and health |
| Omada Network | `omada-network` | Network device metrics |
| Proxmox Cluster Health | `proxmox-cluster-health` | Node status and temps |
| PBS Backup Status | `pbs-backup-status` | Backup job monitoring |

## 8.4 Glance Dashboard

| Property | Value |
|----------|-------|
| Host | docker-lxc-glance (192.168.40.12) |
| Port | 8080 |
| External | https://glance.hrmsmrflrii.xyz |

### Pages

| Page | Widgets |
|------|---------|
| **Home** | Life Progress, Service Health, K8s Cluster |
| **Compute** | Proxmox Dashboard, Container Monitoring |
| **Storage** | Synology NAS Dashboard |
| **Network** | Omada Network Dashboard, Speedtest |
| **Media** | Media Stats, Recent Downloads |
| **Backup** | PBS Dashboard, Drive Health |

## 8.5 Network Utilization Monitoring (Deep Dive)

Added January 13, 2026 - comprehensive network bandwidth monitoring to determine if upgrading to 2.5GbE switches would be beneficial.

### Purpose

Before investing in a 2.5GbE network upgrade, I needed data to answer:
- What's my actual network utilization?
- When do bandwidth spikes occur (backups, migrations, streaming)?
- Is my Synology NAS or Proxmox cluster the bottleneck?

This dashboard provides that visibility.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     NETWORK UTILIZATION MONITORING                               │
│                                                                                  │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│   │   node01     │    │   node02     │    │   node03     │    │ Synology NAS │  │
│   │ 192.168.20.20│    │ 192.168.20.21│    │ 192.168.20.22│    │192.168.20.31 │  │
│   │              │    │              │    │              │    │              │  │
│   │node_exporter │    │node_exporter │    │node_exporter │    │  SNMP Agent  │  │
│   │    :9100     │    │    :9100     │    │    :9100     │    │    :161      │  │
│   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│          │                   │                   │                   │           │
│          │                   │                   │                   │           │
│          │     ┌─────────────┴───────────────────┘                   │           │
│          │     │                                                     │           │
│          │     │                                             ┌───────▼────────┐  │
│          │     │                                             │  SNMP Exporter │  │
│          │     │                                             │ 192.168.40.13  │  │
│          │     │                                             │     :9116      │  │
│          │     │                                             └───────┬────────┘  │
│          │     │                                                     │           │
│          └─────┼─────────────────────────────────────────────────────┘           │
│                │                                                                  │
│         ┌──────▼────────────────────────────────────────────────────────────┐    │
│         │                     PROMETHEUS (192.168.40.13:9090)                │    │
│         │  • Job: proxmox-nodes (scrapes node_exporter every 30s)           │    │
│         │  • Job: synology (scrapes SNMP exporter every 60s)                │    │
│         └──────────────────────────────┬─────────────────────────────────────┘    │
│                                        │                                          │
│                                 ┌──────▼──────┐                                  │
│                                 │   GRAFANA   │                                  │
│                                 │    :3030    │                                  │
│                                 │             │                                  │
│                                 │ Dashboard:  │                                  │
│                                 │ network-    │                                  │
│                                 │ utilization │                                  │
│                                 └──────┬──────┘                                  │
│                                        │                                          │
│                                 ┌──────▼──────┐                                  │
│                                 │   GLANCE    │                                  │
│                                 │   :8080     │                                  │
│                                 │             │                                  │
│                                 │ Network Tab │                                  │
│                                 │  (iframe)   │                                  │
│                                 └─────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Part 1: Data Collection

#### Proxmox Nodes - node_exporter

Each Proxmox node runs **node_exporter v1.7.0** which exposes network interface metrics.

**Installation** (already done on all nodes):
```bash
apt install prometheus-node-exporter
systemctl enable --now prometheus-node-exporter
```

**Key Metrics Exposed:**

| Metric | Type | Description |
|--------|------|-------------|
| `node_network_receive_bytes_total` | Counter | Total bytes received on interface |
| `node_network_transmit_bytes_total` | Counter | Total bytes transmitted on interface |
| `node_network_up` | Gauge | Interface link status (1=up) |
| `node_network_speed_bytes` | Gauge | Link speed in bytes/sec |

**Interface of Interest:** `vmbr0` - the main bridge interface that handles all VM/container traffic.

**Verify metrics are available:**
```bash
curl -s http://192.168.20.20:9100/metrics | grep node_network_receive_bytes_total
# Output: node_network_receive_bytes_total{device="vmbr0"} 1.234567890123e+12
```

#### Synology NAS - SNMP Exporter

The Synology NAS doesn't run node_exporter, but it has a built-in SNMP agent. I use the **SNMP Exporter** to translate SNMP OIDs to Prometheus metrics.

**SNMP Agent Configuration on Synology:**
1. DSM → Control Panel → Terminal & SNMP → SNMP Tab
2. Enable SNMPv2c service
3. Community string: `public` (or your custom string)

**SNMP Exporter Container** (on docker-vm-core-utilities01):
```yaml
# /opt/monitoring/snmp-exporter/docker-compose.yml
version: '3.8'
services:
  snmp-exporter:
    image: prom/snmp-exporter:latest
    container_name: snmp-exporter
    ports:
      - "9116:9116"
    volumes:
      - ./snmp.yml:/etc/snmp_exporter/snmp.yml:ro
    restart: unless-stopped
```

**IF-MIB OIDs for Network Interfaces:**

The key to monitoring NAS network traffic is adding the IF-MIB (Interface Management Information Base) OIDs to the SNMP exporter configuration.

```yaml
# /opt/monitoring/snmp-exporter/snmp.yml (excerpt)
synology:
  walk:
    - 1.3.6.1.2.1.31.1.1.1     # ifXTable (64-bit counters)
  metrics:
    # 64-bit inbound byte counter (handles high traffic without wraparound)
    - name: ifHCInOctets
      oid: 1.3.6.1.2.1.31.1.1.1.6
      type: counter
      help: Total number of octets received on the interface (64-bit)
      indexes:
        - labelname: ifIndex
          type: gauge
      lookups:
        - labels: [ifIndex]
          labelname: ifName
          oid: 1.3.6.1.2.1.31.1.1.1.1

    # 64-bit outbound byte counter
    - name: ifHCOutOctets
      oid: 1.3.6.1.2.1.31.1.1.1.10
      type: counter
      help: Total number of octets transmitted on the interface (64-bit)
      indexes:
        - labelname: ifIndex
          type: gauge

    # Interface speed in Mbps
    - name: ifHighSpeed
      oid: 1.3.6.1.2.1.31.1.1.1.15
      type: gauge
      help: Interface speed in Mbps
      indexes:
        - labelname: ifIndex
          type: gauge
```

**Why 64-bit counters (HC = High Capacity)?**

32-bit counters (`ifInOctets`/`ifOutOctets`) can only count up to ~4.3GB before wrapping around. On a 1Gbps link, that happens in about 34 seconds at full speed! The 64-bit HC counters handle exabytes before wrapping.

**Synology Interface Mapping:**

After enabling SNMP, I discovered the interface indexes by querying:
```bash
snmpwalk -v2c -c public 192.168.20.31 1.3.6.1.2.1.31.1.1.1.1
# Output shows:
# IF-MIB::ifName.3 = STRING: eth0
# IF-MIB::ifName.4 = STRING: eth1
```

| Interface | ifIndex | Description | Speed |
|-----------|---------|-------------|-------|
| eth0 | 3 | Primary NIC | 1 Gbps |
| eth1 | 4 | Secondary NIC | 1 Gbps |

The NAS has 2x 1Gbps NICs in Link Aggregation, giving 2Gbps total capacity.

**Restart SNMP exporter after config change:**
```bash
docker restart snmp-exporter
```

**Verify NAS metrics are available:**
```bash
curl -s "http://192.168.40.13:9116/snmp?target=192.168.20.31&module=synology" | grep ifHCInOctets
# Output: ifHCInOctets{ifIndex="3"} 1.23456789e+13
```

### Part 2: Prometheus Configuration

**Add scrape jobs** to `/opt/monitoring/prometheus/prometheus.yml`:

```yaml
scrape_configs:
  # Proxmox node_exporter (already exists)
  - job_name: 'proxmox-nodes'
    scrape_interval: 30s
    static_configs:
      - targets:
          - '192.168.20.20:9100'
          - '192.168.20.21:9100'
          - '192.168.20.22:9100'
        labels:
          job: 'proxmox-nodes'

  # Synology NAS via SNMP exporter (already exists)
  - job_name: 'synology'
    scrape_interval: 60s
    static_configs:
      - targets:
          - '192.168.20.31'  # NAS IP
    metrics_path: /snmp
    params:
      module: [synology]
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: 192.168.40.13:9116  # SNMP exporter address
```

**Reload Prometheus:**
```bash
curl -X POST http://192.168.40.13:9090/-/reload
```

**Verify scrape targets are healthy:**
```bash
curl -s "http://192.168.40.13:9090/api/v1/targets" | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

### Part 3: Grafana Dashboard Queries (PromQL)

The real magic is in the PromQL queries that transform raw byte counters into meaningful bandwidth metrics.

#### Understanding `rate()` for Network Metrics

Counters like `node_network_receive_bytes_total` only go up. To get bandwidth (bytes/second), we use `rate()`:

```promql
rate(node_network_receive_bytes_total[5m])
```

This calculates: (current_value - value_5_minutes_ago) / 300 seconds

**Multiply by 8 to convert bytes/s to bits/s** (standard for network bandwidth):

```promql
rate(node_network_receive_bytes_total[5m]) * 8
```

#### Dashboard Queries

**1. Total Cluster Bandwidth (all nodes combined):**
```promql
sum(
  rate(node_network_receive_bytes_total{device="vmbr0"}[5m]) +
  rate(node_network_transmit_bytes_total{device="vmbr0"}[5m])
) * 8
```
- `{device="vmbr0"}` - only the main bridge interface
- `sum()` - adds all nodes together
- `* 8` - converts bytes to bits

**2. Cluster Utilization Gauge (% of 1Gbps):**
```promql
sum(
  rate(node_network_receive_bytes_total{device="vmbr0"}[5m]) +
  rate(node_network_transmit_bytes_total{device="vmbr0"}[5m])
) * 8 / 1000000000 * 100
```
- Divides by 1e9 (1 Gbps in bits)
- Multiplies by 100 for percentage

**3. Per-Node Bandwidth (example: node01):**
```promql
(
  rate(node_network_receive_bytes_total{instance="192.168.20.20:9100",device="vmbr0"}[5m]) +
  rate(node_network_transmit_bytes_total{instance="192.168.20.20:9100",device="vmbr0"}[5m])
) * 8
```

**4. 24-Hour Peak Bandwidth:**
```promql
max_over_time(
  sum(
    rate(node_network_receive_bytes_total{device="vmbr0"}[5m]) +
    rate(node_network_transmit_bytes_total{device="vmbr0"}[5m])
  ) * 8
[24h])
```
- `max_over_time(...[24h])` - finds the maximum value in the last 24 hours

**5. 24-Hour Average Bandwidth:**
```promql
avg_over_time(
  sum(
    rate(node_network_receive_bytes_total{device="vmbr0"}[5m]) +
    rate(node_network_transmit_bytes_total{device="vmbr0"}[5m])
  ) * 8
[24h])
```

**6. Synology NAS Total Bandwidth (eth0 + eth1):**
```promql
sum(
  rate(ifHCInOctets{ifIndex=~"3|4"}[5m]) +
  rate(ifHCOutOctets{ifIndex=~"3|4"}[5m])
) * 8
```
- `{ifIndex=~"3|4"}` - matches eth0 (index 3) OR eth1 (index 4) using regex

**7. NAS Utilization (% of 2Gbps bonded):**
```promql
sum(
  rate(ifHCInOctets{ifIndex=~"3|4"}[5m]) +
  rate(ifHCOutOctets{ifIndex=~"3|4"}[5m])
) * 8 / 2000000000 * 100
```
- Divides by 2e9 (2 Gbps for bonded NICs)

**8. Timeline with Per-Node RX/TX Breakdown:**
```promql
# node01 RX
rate(node_network_receive_bytes_total{instance="192.168.20.20:9100",device="vmbr0"}[5m]) * 8

# node01 TX
rate(node_network_transmit_bytes_total{instance="192.168.20.20:9100",device="vmbr0"}[5m]) * 8
```

**9. 1Gbps Reference Line (for timeline charts):**
```promql
vector(1000000000)
```
- Creates a constant 1e9 (1 Gbps) horizontal line for visual reference

### Part 4: Dashboard Panel Configuration

The Grafana dashboard uses these panel types:

| Panel Type | Use Case | Key Settings |
|------------|----------|--------------|
| **stat** | Single current value | Unit: `bps` (bits per second) |
| **gauge** | Percentage with thresholds | Min: 0, Max: 100, Unit: `percent` |
| **timeseries** | Bandwidth over time | Unit: `bps`, Line interpolation: smooth |

**Color Thresholds for Gauges:**

| Range | Color | Meaning |
|-------|-------|---------|
| 0-50% | Green | Normal utilization |
| 50-80% | Yellow | Elevated, monitor |
| 80-100% | Red | High utilization, potential bottleneck |

**Dashboard JSON Location:** `dashboards/network-utilization.json`

**Ansible Deployment Playbook:** `ansible/playbooks/monitoring/deploy-network-utilization-dashboard.yml`

### Part 5: Glance Integration

The dashboard is embedded in the Glance Network tab using an iframe widget.

**Glance Configuration** (`/opt/glance/config/glance.yml`):

```yaml
pages:
  - name: Network
    columns:
      - size: full
        widgets:
          - type: iframe
            url: https://grafana.hrmsmrflrii.xyz/d/network-utilization/network-utilization?orgId=1&kiosk&theme=transparent&refresh=30s
            height: 1100
```

**URL Parameters Explained:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `kiosk` | (no value) | Hides Grafana navbar/sidebar |
| `theme=transparent` | transparent | Blends with Glance dark theme |
| `refresh=30s` | 30s | Auto-refresh interval |
| `orgId=1` | 1 | Grafana organization ID |

### Part 6: Using the Dashboard

**What to Watch For:**

| Metric | Threshold | Action |
|--------|-----------|--------|
| Cluster Utilization > 70% sustained | High | Consider 2.5GbE upgrade |
| NAS Utilization > 80% during backups | Very High | NAS is bottleneck |
| Peak 24h > 800 Mbps | Frequent peaks | 2.5GbE recommended |
| Per-node consistently higher | Imbalanced | Migrate VMs for balance |

**Common Bandwidth Patterns:**

| Time | Expected Activity | Normal Bandwidth |
|------|-------------------|------------------|
| 2:00-4:00 AM | PBS daily backups | 400-800 Mbps |
| Evenings | Plex/Jellyfin streaming | 50-200 Mbps |
| Live migration | VM movement between nodes | 500-900 Mbps |
| Idle | Background traffic | < 50 Mbps |

### Part 7: Deployment Commands

**Deploy the complete monitoring stack:**

```bash
# From Ansible controller (192.168.20.30)
cd ~/ansible

# 1. Deploy the Grafana dashboard
ansible-playbook ansible/playbooks/monitoring/deploy-network-utilization-dashboard.yml

# 2. Restart Glance to pick up iframe (if config was updated)
ssh root@192.168.40.12 "cd /opt/glance && docker compose restart glance"
```

**Manual dashboard update (if JSON changes):**

```bash
# Copy dashboard JSON to Grafana host
scp dashboards/network-utilization.json hermes-admin@192.168.40.13:/tmp/

# Deploy via Grafana API
ssh hermes-admin@192.168.40.13 'curl -X POST \
  -H "Content-Type: application/json" \
  -u admin:admin \
  -d "{\"dashboard\": $(cat /tmp/network-utilization.json), \"overwrite\": true}" \
  http://localhost:3030/api/dashboards/db'
```

### Part 8: Troubleshooting

**No data for Proxmox nodes:**
```bash
# Check node_exporter is running
ssh root@192.168.20.20 "systemctl status prometheus-node-exporter"

# Check Prometheus can scrape
curl -s "http://192.168.40.13:9090/api/v1/query?query=node_network_receive_bytes_total{device='vmbr0'}" | jq '.data.result'
```

**No data for Synology NAS:**
```bash
# Test SNMP from docker host
docker exec snmp-exporter snmpwalk -v2c -c public 192.168.20.31 1.3.6.1.2.1.31.1.1.1.6

# Check SNMP exporter logs
docker logs snmp-exporter

# Verify Prometheus scrape
curl -s "http://192.168.40.13:9090/api/v1/query?query=ifHCInOctets" | jq '.data.result'
```

**Dashboard shows 0 or N/A:**
- Check time range (last 1h may have no data if just deployed)
- Verify device label matches (`vmbr0` for Proxmox, `ifIndex` for NAS)
- Check units (bytes vs bits - should use `bps` unit in Grafana)

---

# Part 9: Discord Bot Ecosystem

## 9.1 Sentinel Bot

Unified Discord bot consolidating all homelab automation.

| Property | Value |
|----------|-------|
| Host | docker-vm-core-utilities01 (192.168.40.13) |
| Webhook Port | 5050 |
| Location | /opt/sentinel-bot/ |

### Cog Modules

| Cog | Channel | Purpose |
|-----|---------|---------|
| **homelab.py** | #homelab-infrastructure | Proxmox cluster status |
| **updates.py** | #container-updates | Container update approvals, infrastructure updates |
| **media.py** | #media-downloads | Download notifications |
| **gitlab.py** | #project-management | GitLab issues |
| **tasks.py** | #claude-tasks | Claude task queue |

### Key Commands

| Command | Description |
|---------|-------------|
| `/homelab status` | Cluster overview |
| `/check` | Scan for container updates |
| `/updateall` | **Check and update ALL VMs, containers, LXCs** |
| `/checknow` | Manually trigger scheduled update check |
| `/updateschedule` | Show automatic update check schedule |
| `/downloads` | Show download queue |
| `/todo <description>` | Create GitLab issue |
| `/task <description>` | Submit Claude task |

## 9.2 Automated Infrastructure Update System

Added January 2026 - comprehensive update management via Discord.

### Architecture

```
Discord User
     │
     │ /updateall (or scheduled check at 6 AM/6 PM UTC)
     ▼
Sentinel Bot (192.168.40.13)
     │
     ├─► Phase 1: VMs (apt upgrade)
     │   ├── docker-utilities (192.168.40.13)
     │   ├── docker-media (192.168.40.11)
     │   ├── traefik (192.168.40.20)
     │   ├── authentik (192.168.40.21)
     │   ├── immich (192.168.40.22)
     │   ├── gitlab (192.168.40.23)
     │   ├── gitlab-runner (192.168.40.24)
     │   └── ansible (192.168.20.30)
     │
     ├─► Phase 2: Docker Containers (pull + restart)
     │   ├── 192.168.40.13 (15 containers)
     │   ├── 192.168.40.11 (12 containers)
     │   ├── 192.168.40.12 (5 containers)
     │   └── Service VMs (traefik, authentik, etc.)
     │
     └─► Phase 3: LXC Containers (pct exec apt upgrade)
         ├── pbs (CTID 100) on node03
         ├── docker-lxc-glance (CTID 200) on node03
         ├── pi-hole (CTID 202) on node01
         └── homeassistant (CTID 206) on node03
              │
              ▼
        Completion Report in Discord
```

### Workflow

1. **Check Phase**: Bot scans all VMs and LXCs for available apt updates
2. **Summary**: Posts embed with update counts per resource type
3. **Approval**: Waits for thumbs up reaction before proceeding
4. **Update Phase**: Applies updates in order (VMs → Containers → LXCs)
5. **Report**: Sends comprehensive report with success/failure counts

### Scheduled Checks

| Schedule | Time (UTC) | Action |
|----------|------------|--------|
| Morning | 6:00 AM | Check all resources, notify if updates |
| Evening | 6:00 PM | Check all resources, notify if updates |

Notifications only sent if updates are found. Updates only applied after user approval.

### Configuration

```python
# config.py - Host mappings

VM_HOSTS = {
    'docker-utilities': '192.168.40.13',
    'docker-media': '192.168.40.11',
    'traefik': '192.168.40.20',
    'authentik': '192.168.40.21',
    'immich': '192.168.40.22',
    'gitlab': '192.168.40.23',
    'gitlab-runner': '192.168.40.24',
    'ansible': '192.168.20.30',
}

LXC_CONTAINERS = {
    'pbs': ('192.168.20.22', 100),
    'docker-lxc-glance': ('192.168.20.22', 200),
    'pi-hole': ('192.168.20.20', 202),
    'homeassistant': ('192.168.20.22', 206),
}
```

### Safety Features

- **Skip self-update**: sentinel-bot container never updates itself
- **Timeout handling**: 10-minute timeout for apt operations
- **Error isolation**: Continues if one resource fails
- **Progress updates**: Real-time Discord embed updates
- **Approval required**: No updates without user confirmation

---

# Part 10: Custom APIs

| API | Host | Port | Purpose |
|-----|------|------|---------|
| **Life Progress** | 192.168.40.13 | 5051 | Dashboard progress bars |
| **Media Stats** | 192.168.40.12 | 5054 | Radarr/Sonarr statistics |
| **NBA Stats** | 192.168.40.12 | 5055 | Sports scores |
| **Docker Stats Exporter** | Multiple | 9417 | Container metrics |
| **SMART Health** | 192.168.20.22 | 9101 | Drive health monitoring |

---

# Part 11: Backup and Disaster Recovery

## 11.1 Backup Schedules

| Job | Schedule | Datastore | Retention |
|-----|----------|-----------|-----------|
| pbs-daily | Daily 2:00 AM | daily (NVMe) | 7 days |
| pbs-main | Sunday 3:00 AM | main (HDD) | 4 weekly + 2 monthly |

## 11.2 Recovery Procedures

### Restoring a VM

1. Open PBS Web UI: https://192.168.20.50:8007
2. Navigate to Datastore → Backups
3. Select backup snapshot
4. Click "Restore"
5. Choose target node and storage

## 11.3 Drive Health Monitoring

| Property | Value |
|----------|-------|
| API Endpoint | http://192.168.20.22:9101/health |
| Service | smart-health-api.service |
| Drives | Seagate 4TB HDD, Kingston 1TB NVMe |

---

# Part 12: Azure Cloud Integration

## 12.1 Azure Environment

| Property | Value |
|----------|-------|
| Subscription | FireGiants-Prod |
| Deployment VM | ubuntu-deploy-vm (10.90.10.5) |
| SIEM | Azure Sentinel (law-homelab-sentinel) |

## 12.2 Hybrid AD Lab

| Property | Value |
|----------|-------|
| Domain | hrmsmrflrii.xyz |
| NetBIOS | HRMSMRFLRII |

### Domain Controllers

| Server | IP | Role |
|--------|-----|------|
| AZDC01 | 10.10.4.4 | Primary DC |
| AZDC02 | 10.10.4.5 | Secondary DC |
| AZRODC01 | 10.10.4.6 | Read-Only DC |
| AZRODC02 | 10.10.4.7 | Read-Only DC |

## 12.3 Site-to-Site VPN

| Property | Value |
|----------|-------|
| On-Premises | OPNsense (192.168.91.30) |
| Azure VNet | 10.90.10.0/29 |
| Protocol | IPsec IKEv2 |

---

# Appendices

## Appendix A: Complete IP Address Map

### Infrastructure VLAN (192.168.20.0/24)

| IP Address | Hostname | Purpose |
|------------|----------|---------|
| 192.168.20.1 | gateway | VLAN Gateway |
| 192.168.20.20 | node01 | Proxmox Node 1 |
| 192.168.20.21 | node02 | Proxmox Node 2 |
| 192.168.20.22 | node03 | Proxmox Node 3 |
| 192.168.20.30 | ansible | Ansible Controller |
| 192.168.20.31 | synology | Synology NAS |
| 192.168.20.50 | pbs | Proxmox Backup Server |

### Production VLAN (192.168.40.0/24)

| IP Address | Hostname | Purpose |
|------------|----------|---------|
| 192.168.40.11 | docker-media | Media Stack |
| 192.168.40.12 | docker-glance | Glance Dashboard |
| 192.168.40.13 | docker-utils | Monitoring Stack |
| 192.168.40.20 | traefik | Reverse Proxy |
| 192.168.40.21 | authentik | SSO |
| 192.168.40.22 | immich | Photo Management |
| 192.168.40.23 | gitlab | GitLab |

## Appendix B: SSH Configuration

### SSH Config Example

```
# Proxmox Nodes
Host node01
    HostName 192.168.20.20
    User root
    IdentityFile ~/.ssh/homelab_ed25519

Host node02
    HostName 192.168.20.21
    User root
    IdentityFile ~/.ssh/homelab_ed25519

# Infrastructure VMs
Host ansible
    HostName 192.168.20.30
    User hermes-admin
    IdentityFile ~/.ssh/homelab_ed25519

# Docker Hosts
Host docker-utils
    HostName 192.168.40.13
    User hermes-admin
    IdentityFile ~/.ssh/homelab_ed25519
```

## Appendix C: Command Cheatsheet

### Proxmox Commands

| Task | Command |
|------|---------|
| Cluster status | `pvecm status` |
| List all VMs | `qm list` |
| List all containers | `pct list` |
| Start VM | `qm start <vmid>` |
| Stop VM | `qm shutdown <vmid>` |
| VM config | `qm config <vmid>` |
| Storage status | `pvesm status` |

### Docker Commands

| Task | Command |
|------|---------|
| List containers | `docker ps` |
| Container logs | `docker logs <container>` |
| Restart container | `docker restart <container>` |
| Pull updates | `docker compose pull` |
| Recreate | `docker compose up -d` |

### Ansible Commands

| Task | Command |
|------|---------|
| Run playbook | `ansible-playbook ansible/playbooks/<category>/<playbook>.yml` |
| Dry run | `ansible-playbook ansible/playbooks/<category>/<playbook>.yml --check` |
| With inventory | `ansible-playbook -i ansible/inventory/k8s.ini <playbook>` |
| Ping all | `ansible all -m ping` |

### Terraform Commands (from terraform/proxmox/)

| Task | Command |
|------|---------|
| Initialize | `terraform init` |
| Plan | `terraform plan` |
| Plan with env | `terraform plan -var-file=../env/prod.tfvars` |
| Apply | `terraform apply` |
| List resources | `terraform state list` |

---

## Related Documentation

- [NETWORKING.md](./NETWORKING.md) - Network configuration details
- [PROXMOX.md](./PROXMOX.md) - Proxmox cluster management
- [STORAGE.md](./STORAGE.md) - Storage architecture
- [TERRAFORM.md](./TERRAFORM.md) - Infrastructure as Code
- [ANSIBLE.md](./ANSIBLE.md) - Configuration management
- [SERVICES.md](./SERVICES.md) - Service deployment guides
- [OBSERVABILITY.md](./OBSERVABILITY.md) - Monitoring stack
- [DISCORD_BOTS.md](./DISCORD_BOTS.md) - Bot documentation
- [GLANCE.md](./GLANCE.md) - Dashboard configuration

---

**Document Information:**
- **Total Sections:** 12 Parts + 3 Appendices
- **Version:** 3.1
- **Last Updated:** January 13, 2026
- **Author:** Hermes Miraflor II with Claude Code

> **Note:** This is the public GitHub version. Credentials are stored separately in a private Obsidian vault.
