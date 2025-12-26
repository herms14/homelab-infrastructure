# Architecture Overview

> **TL;DR**: 3 Proxmox nodes running 17 VMs, with Traefik routing all traffic to 22 services, all backed by Synology NAS storage.

## The Big Picture

This diagram shows how all the pieces fit together:

```
                              ┌─────────────────┐
                              │    Internet     │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │  Router/Modem   │
                              │  (Your ISP)     │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │    OPNsense     │
                              │   Firewall      │
                              │ 192.168.91.30   │
                              │                 │
                              │ • DNS Server    │
                              │ • DHCP          │
                              │ • Firewall      │
                              └────────┬────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            │                          │                          │
   ┌────────▼────────┐       ┌────────▼────────┐       ┌────────▼────────┐
   │    Proxmox      │       │    Proxmox      │       │    Proxmox      │
   │    node01       │       │    node02       │       │    node03       │
   │ 192.168.20.20   │       │ 192.168.20.21   │       │ 192.168.20.22   │
   │                 │       │                 │       │                 │
   │ • Primary       │       │ • Application   │       │ • Kubernetes    │
   │ • Ansible       │       │   Services      │       │   Cluster       │
   └────────┬────────┘       └────────┬────────┘       └────────┬────────┘
            │                          │                          │
            └──────────────────────────┼──────────────────────────┘
                                       │
                              ┌────────▼────────┐
                              │   Synology NAS  │
                              │ 192.168.20.31   │
                              │                 │
                              │ • VM Storage    │
                              │ • Media Files   │
                              │ • Backups       │
                              └─────────────────┘
```

---

## Layer by Layer

### Layer 1: Physical Hardware

Three physical servers form the Proxmox cluster:

| Server | IP Address | Primary Role | VMs Running |
|--------|------------|--------------|-------------|
| **node01** | 192.168.20.20 | VM Host | Ansible controller |
| **node02** | 192.168.20.21 | App Host | Application services (7 VMs) |
| **node03** | 192.168.20.22 | K8s Host | Kubernetes cluster (9 VMs) |

**Why three nodes?**
- **High availability**: If one node fails, VMs can migrate to others
- **Load distribution**: Spread workloads across hardware
- **Isolation**: Keep Kubernetes separate from regular services

### Layer 2: Network Segmentation (VLANs)

Traffic is separated into two networks:

```
┌─────────────────────────────────────────────────────────────┐
│                    VLAN 20 (Infrastructure)                  │
│                    192.168.20.0/24                          │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Proxmox    │  │  Ansible    │  │    Kubernetes       │ │
│  │  Nodes      │  │  Controller │  │    Cluster          │ │
│  │  .20-.22    │  │  .30        │  │    .32-.45          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    VLAN 40 (Services)                        │
│                    192.168.40.0/24                          │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Traefik    │  │  Docker     │  │    Application      │ │
│  │  Proxy      │  │  Hosts      │  │    Services         │ │
│  │  .20        │  │  .10-.11    │  │    .21-.23          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Why VLANs?**
- **Security**: Services can't directly access infrastructure
- **Organization**: Easy to understand what's where
- **Traffic management**: Control who talks to whom

### Layer 3: Virtual Machines

17 VMs distributed across the cluster:

#### VLAN 20 - Infrastructure (10 VMs)

| VM Name | IP Address | Purpose |
|---------|------------|---------|
| ansible-controller01 | 192.168.20.30 | Automation hub |
| k8s-controller01 | 192.168.20.32 | K8s control plane (primary) |
| k8s-controller02 | 192.168.20.33 | K8s control plane (HA) |
| k8s-controller03 | 192.168.20.34 | K8s control plane (HA) |
| k8s-worker01-06 | 192.168.20.40-45 | K8s worker nodes |

#### VLAN 40 - Services (7 VMs)

| VM Name | IP Address | Purpose |
|---------|------------|---------|
| linux-syslog-server01 | 192.168.40.5 | Centralized logging |
| docker-vm-utilities01 | 192.168.40.10 | Paperless, Glance, n8n |
| docker-vm-media01 | 192.168.40.11 | Arr stack (Jellyfin, etc.) |
| traefik-vm01 | 192.168.40.20 | Reverse proxy |
| authentik-vm01 | 192.168.40.21 | SSO/Identity |
| immich-vm01 | 192.168.40.22 | Photo management |
| gitlab-vm01 | 192.168.40.23 | DevOps platform |

### Layer 4: Containers & Services

Services run as Docker containers inside VMs:

```
┌─────────────────────────────────────────────────────────────┐
│              docker-vm-media01 (192.168.40.11)              │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Jellyfin │ │  Radarr  │ │  Sonarr  │ │  Lidarr  │      │
│  │  :8096   │ │  :7878   │ │  :8989   │ │  :8686   │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Prowlarr │ │  Bazarr  │ │Overseerr │ │Jellyseerr│      │
│  │  :9696   │ │  :6767   │ │  :5055   │ │  :5056   │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  ┌──────────┐ ┌──────────┐                                 │
│  │  Tdarr   │ │ Autobrr  │                                 │
│  │  :8265   │ │  :7474   │                                 │
│  └──────────┘ └──────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

### Layer 5: Traffic Flow (Traefik)

All web traffic flows through Traefik:

```
User Request
     │
     │  https://photos.hrmsmrflrii.xyz
     │
     ▼
┌─────────────────┐
│    OPNsense     │
│  DNS Lookup     │  → Returns 192.168.40.20 (Traefik)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Traefik      │
│  192.168.40.20  │
│                 │
│  • SSL Termination (Let's Encrypt)
│  • Route matching (Host header)
│  • Load balancing
└────────┬────────┘
         │
         │  Host: photos.hrmsmrflrii.xyz → Immich (192.168.40.22:2283)
         │
         ▼
┌─────────────────┐
│    Immich       │
│  192.168.40.22  │
└─────────────────┘
```

---

## Storage Architecture

All persistent data lives on the Synology NAS:

```
Synology NAS (192.168.20.31)
│
├── /volume2/ProxmoxCluster-VMDisks
│   │   Virtual machine disk images
│   │   Managed by Proxmox
│   │
│   └── VM-100-disk-0.raw
│       VM-101-disk-0.raw
│       ...
│
├── /volume2/ProxmoxCluster-ISOs
│   │   Installation media
│   │
│   └── ubuntu-24.04-live-server-amd64.iso
│       ...
│
├── /volume2/Proxmox-Media
│   │   Movies, TV shows, Music
│   │   Used by Jellyfin, Radarr, Sonarr
│   │
│   ├── Movies/
│   ├── Series/
│   └── Music/
│
└── /volume2/Proxmox-LXCs
        LXC container app configs
```

**Key principle**: Proxmox storages for Proxmox things, manual mounts for app data.

---

## DNS & SSL Flow

How `https://photos.hrmsmrflrii.xyz` becomes a secure connection:

```
1. User types: https://photos.hrmsmrflrii.xyz
                        │
                        ▼
2. DNS Query:   OPNsense (192.168.91.30)
                "What IP is photos.hrmsmrflrii.xyz?"
                        │
                        ▼
3. DNS Response: 192.168.40.20 (Traefik)
                        │
                        ▼
4. HTTPS Connection: Browser connects to Traefik
                        │
                        ▼
5. SSL Certificate: Traefik presents Let's Encrypt cert
                    (Obtained via Cloudflare DNS challenge)
                        │
                        ▼
6. Routing:     Traefik checks Host header
                Routes to Immich (192.168.40.22:2283)
                        │
                        ▼
7. Response:    Immich responds
                Traefik forwards to user
```

---

## Management Flow

How changes get deployed:

```
┌─────────────────┐
│  Your Machine   │
│  (Workstation)  │
│                 │
│  • Terraform    │────────────────────────────┐
│  • Git          │                            │
└────────┬────────┘                            │
         │                                     │
         │ 1. terraform apply                  │
         │    (Creates/modifies VMs)           │
         │                                     │
         ▼                                     │
┌─────────────────┐                            │
│    Proxmox      │                            │
│    Cluster      │                            │
│                 │                            │
│  Creates VMs    │                            │
└────────┬────────┘                            │
         │                                     │
         │ 2. VMs boot with cloud-init         │
         │    (Network, SSH keys, hostname)    │
         │                                     │
         ▼                                     │
┌─────────────────┐                            │
│    Ansible      │◄───────────────────────────┘
│    Controller   │  3. ansible-playbook
│  192.168.20.30  │     (Configures services)
│                 │
│  • Inventory    │
│  • Playbooks    │
└────────┬────────┘
         │
         │ SSH to target VMs
         │
         ▼
┌─────────────────────────────────────────────┐
│              Target VMs                      │
│                                             │
│  • Install Docker                           │
│  • Deploy containers                        │
│  • Configure services                       │
└─────────────────────────────────────────────┘
```

---

## What's Next?

- **[Network Architecture](Network-Architecture)** - Deep dive into networking
- **[Storage Architecture](Storage-Architecture)** - How storage is organized
- **[Quick Start](Quick-Start)** - Deploy your first VM

---

*This architecture evolved over time. Start simple, add complexity as needed.*
