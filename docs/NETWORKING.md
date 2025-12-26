# Network Architecture

> Part of the [Proxmox Infrastructure Documentation](../CLAUDE.md)

## Physical Network Topology

```
                                    Internet
                                        │
                                        ▼
                              ┌─────────────────┐
                              │   ISP Router    │
                              │  192.168.100.1  │
                              │   (Converge)    │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │   Core Router   │
                              │   ER605 v2.20   │
                              │   192.168.0.1   │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │  Atreus Switch  │
                              │  ES20GP v1.0    │
                              │  192.168.90.51  │
                              │ (First Floor)   │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │   Core Switch   │
                              │  SG3210 v3.20   │
                              │  192.168.90.2   │
                              └────────┬────────┘
                                       │
          ┌────────────┬───────────────┼───────────────┬────────────┐
          │            │               │               │            │
          ▼            ▼               ▼               ▼            ▼
    ┌──────────┐ ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐
    │ Morpheus │ │ OPNsense │  │ Synology │  │  Wireless │  │  Other   │
    │  Switch  │ │ Firewall │  │   NAS    │  │    APs    │  │ Devices  │
    │ SG2210P  │ │  .91.30  │  │  .20.31  │  │ EAP225/   │  │          │
    │  .90.3   │ │          │  │          │  │ EAP610    │  │          │
    └────┬─────┘ └──────────┘  └──────────┘  └───────────┘  └──────────┘
         │
    ┌────┼────┬────┐
    │    │    │    │
    ▼    ▼    ▼    ▼
  Node01 Node02 NAS  EAP
  (.20) (.21) (.31) (.12)
```

**Physical Path**: ER605 Gateway → Atreus Switch → Core Switch (SG3210) → Morpheus Switch → Proxmox Nodes

### Network Hardware

| Device | Model | IP Address | Purpose |
|--------|-------|------------|---------|
| Core Router | ER605 v2.20 | 192.168.0.1 | Main gateway, inter-VLAN routing |
| Atreus Switch | ES20GP v1.0 | 192.168.90.51 | First floor distribution (router uplink) |
| Core Switch | SG3210 v3.20 | 192.168.90.2 | Primary L2 switch, VLAN trunking |
| Morpheus Switch | SG2210P v5.20 | 192.168.90.3 | Proxmox node connectivity (PoE) |
| Computer Room EAP | EAP225 v4.0 | 192.168.90.12 | WiFi AP |
| Living Room EAP | EAP610 v3.0 | 192.168.90.10 | WiFi AP (primary) |
| Outdoor EAP | EAP603-Outdoor v1.0 | 192.168.90.11 | Outdoor WiFi AP |

### Network Controller

- **Platform**: TP-Link Omada Cloud Controller (OC300)
- **Management**: Cloud-based SDN controller
- **Credentials**: Stored in `CREDENTIALS.md`

## VLAN Architecture

### Complete VLAN Configuration

| VLAN ID | Name | Network | Gateway | Purpose | DHCP Range |
|---------|------|---------|---------|---------|------------|
| 1 | Default | 192.168.0.0/24 | 192.168.0.1 | Management (temporary) | .100-.199 |
| 10 | Internal | 192.168.10.0/24 | 192.168.10.1 | Main LAN (workstations, NAS) | .50-.254 |
| **20** | **Homelab** | **192.168.20.0/24** | **192.168.20.1** | **Proxmox nodes, VMs** | .50-.254 |
| 30 | IoT | 192.168.30.0/24 | 192.168.30.1 | IoT WiFi devices | .50-.254 |
| **40** | **Production** | **192.168.40.0/24** | **192.168.40.1** | **Docker services, apps** | .50-.254 |
| 50 | Guest | 192.168.50.0/24 | 192.168.50.1 | Guest WiFi | .50-.254 |
| 60 | Sonos | 192.168.60.0/24 | 192.168.60.1 | Sonos speakers | .50-.100 |
| 90 | Management | 192.168.90.0/24 | 192.168.90.1 | Network device management | .50-.254 |
| 91 | Firewall | 192.168.91.0/24 | 192.168.91.1 | OPNsense firewall | - |

### Homelab VLANs (Primary)

The infrastructure uses two primary VLANs:

| VLAN | Network | Gateway | Purpose | Services |
|------|---------|---------|---------|----------|
| **VLAN 20** | 192.168.20.0/24 | 192.168.20.1 | Kubernetes Infrastructure | K8s control plane, worker nodes, Ansible |
| **VLAN 40** | 192.168.40.0/24 | 192.168.40.1 | Services & Management | Docker hosts, logging, automation |

## Switch Port Configuration

### Morpheus Switch (Proxmox Connectivity)

| Port | Device | Mode | Native VLAN | Tagged VLANs |
|------|--------|------|-------------|--------------|
| 1 | Core Switch Uplink | Trunk | VLAN 1 | All (1,10,20,30,40,50,90) |
| 2 | **Proxmox Node 01** | Trunk | VLAN 20 | 10, 40 |
| 5 | Computer Room EAP | Trunk | VLAN 1 | All SSIDs (10,20,30,40,50,90) |
| 6 | **Proxmox Node 02** | Trunk | VLAN 20 | 10, 40 |
| 7 | Synology NAS (eth0) | Access | VLAN 10 | - |
| 8 | Synology NAS (eth1) | Access | VLAN 20 | - |

### Core Switch (SG3210)

| Port | Device | Mode | Native VLAN | Tagged VLANs |
|------|--------|------|-------------|--------------|
| 1 | OC300 Controller | Trunk | VLAN 1 | All VLANs |
| 2 | OPNsense Port | Access | VLAN 90 | - |
| 5 | Zephyrus Port | Access | VLAN 10 | - |
| 6 | Morpheus Rack Uplink | Trunk | VLAN 1 | 10,20,30,40,50,90 |
| 7 | Kratos PC | Trunk | VLAN 10 | 20 (for Hyper-V) |
| 8 | Atreus Switch Uplink | Trunk | VLAN 1 | All VLANs |

## Network Bridge (Proxmox)

- **Bridge**: vmbr0 (all VMs and containers use this bridge)
- **VLAN Support**: Bridge must be VLAN-aware on all nodes
- **DNS Server**: 192.168.91.30 (OPNsense Unbound)

### Required `/etc/network/interfaces` Configuration

All Proxmox nodes **MUST** have VLAN-aware bridge configuration:

```bash
auto lo
iface lo inet loopback

# Physical interface
auto nic0
iface nic0 inet manual

auto vmbr0
iface vmbr0 inet static
    address 192.168.20.XX/24   # XX = node-specific IP
    gateway 192.168.20.1
    bridge-ports nic0
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes      # CRITICAL: Required for VLAN support
    bridge-vids 2-4094         # CRITICAL: Allowed VLAN range

source /etc/network/interfaces.d/*
```

### Verification

```bash
# Reload network configuration
ifreload -a

# Verify VLAN filtering (should show "vlan_filtering 1")
ip -d link show vmbr0 | grep vlan_filtering
```

## IP Address Allocation

### VLAN 20 (192.168.20.0/24) - Infrastructure

| Range | Purpose | Hosts |
|-------|---------|-------|
| 20-22 | Proxmox cluster nodes | node01, node02, node03 |
| 30 | Ansible automation | ansible-controller01 |
| 31 | Synology NAS | NFS storage |
| 32-34 | K8s control plane | k8s-controller01-03 |
| 40-45 | K8s worker nodes | k8s-worker01-06 |
| 46-99 | Reserved | Additional K8s nodes |
| 100-199 | Reserved | LXC containers |
| 200-254 | Reserved | Future VMs |

### VLAN 40 (192.168.40.0/24) - Services

| Range | Purpose | Hosts |
|-------|---------|-------|
| 5 | Logging | linux-syslog-server01 |
| 10-11 | Docker hosts | docker-vm-utilities01, docker-vm-media01 |
| 12-19 | Reserved | Additional Docker hosts |
| 20-29 | Application services | traefik, authentik, immich, gitlab |
| 30-39 | Reserved | Monitoring & additional services |
| 40-254 | Reserved | Future services |

## VLAN Configuration in Terraform

```hcl
# VLAN 20 (default, no tag needed on native VLAN)
vlan_tag    = null
gateway     = "192.168.20.1"
nameserver  = "192.168.91.30"
starting_ip = "192.168.20.x"

# VLAN 40 (explicit tag required)
vlan_tag    = 40
gateway     = "192.168.40.1"
nameserver  = "192.168.91.30"
starting_ip = "192.168.40.x"
```

## Domain & SSL Configuration

### Domain Setup

- **Domain**: `hrmsmrflrii.xyz` (GoDaddy + Cloudflare)
- **SSL Provider**: Let's Encrypt (wildcard via Cloudflare DNS-01)
- **Reverse Proxy**: Traefik v3.2 (192.168.40.20)
- **Internal DNS**: OPNsense (192.168.91.30) with host overrides

### SSL Certificate Configuration

Traefik automatically obtains and renews Let's Encrypt certificates:

- **Storage**: `/opt/traefik/certs/acme.json`
- **Email**: herms14@gmail.com
- **Challenge**: DNS-01 via Cloudflare API
- **Type**: Wildcard (*.hrmsmrflrii.xyz)

### DNS Configuration (OPNsense)

All `*.hrmsmrflrii.xyz` subdomains resolve to `192.168.40.20` (Traefik)

## WiFi SSIDs

| SSID | VLAN | Purpose |
|------|------|---------|
| NKD5380-Internal | 10 | Main LAN devices |
| NHN7476-Homelab | 20 | Homelab wireless access |
| WOC321-IoT | 30 | IoT devices |
| NAZ9229-Production | 40 | Production services |
| EAD6167-Guest | 50 | Guest access |
| NAZ9229-Sonos | 60 | Sonos speakers (2.4GHz preferred) |
| NCP5653-Management | 90 | Network management |

**WiFi Credentials**: Stored in `CREDENTIALS.md`

## Service URLs

### Infrastructure

| Service | URL | Backend |
|---------|-----|---------|
| Proxmox Cluster | https://proxmox.hrmsmrflrii.xyz | 192.168.20.21:8006 |
| Proxmox Node01 | https://node01.hrmsmrflrii.xyz | 192.168.20.20:8006 |
| Proxmox Node02 | https://node02.hrmsmrflrii.xyz | 192.168.20.21:8006 |
| Proxmox Node03 | https://node03.hrmsmrflrii.xyz | 192.168.20.22:8006 |
| Traefik Dashboard | https://traefik.hrmsmrflrii.xyz | localhost:8080 |

### Core Services

| Service | URL | Backend |
|---------|-----|---------|
| Authentik (SSO) | https://auth.hrmsmrflrii.xyz | 192.168.40.21:9000 |
| Immich (Photos) | https://photos.hrmsmrflrii.xyz | 192.168.40.22:2283 |
| GitLab | https://gitlab.hrmsmrflrii.xyz | 192.168.40.23:80 |

### Media Services (docker-vm-media01)

| Service | URL | Backend |
|---------|-----|---------|
| Jellyfin | https://jellyfin.hrmsmrflrii.xyz | 192.168.40.11:8096 |
| Radarr | https://radarr.hrmsmrflrii.xyz | 192.168.40.11:7878 |
| Sonarr | https://sonarr.hrmsmrflrii.xyz | 192.168.40.11:8989 |
| Lidarr | https://lidarr.hrmsmrflrii.xyz | 192.168.40.11:8686 |
| Prowlarr | https://prowlarr.hrmsmrflrii.xyz | 192.168.40.11:9696 |
| Bazarr | https://bazarr.hrmsmrflrii.xyz | 192.168.40.11:6767 |
| Overseerr | https://overseerr.hrmsmrflrii.xyz | 192.168.40.11:5055 |
| Jellyseerr | https://jellyseerr.hrmsmrflrii.xyz | 192.168.40.11:5056 |
| Tdarr | https://tdarr.hrmsmrflrii.xyz | 192.168.40.11:8265 |
| Autobrr | https://autobrr.hrmsmrflrii.xyz | 192.168.40.11:7474 |
| Deluge | https://deluge.hrmsmrflrii.xyz | 192.168.40.11:8112 |
| SABnzbd | https://sabnzbd.hrmsmrflrii.xyz | 192.168.40.11:8081 |

### Utility Services (docker-vm-utilities01)

| Service | URL | Backend |
|---------|-----|---------|
| Paperless-ngx | https://paperless.hrmsmrflrii.xyz | 192.168.40.10:8000 |
| Glance Dashboard | https://glance.hrmsmrflrii.xyz | 192.168.40.10:8080 |
| n8n Automation | https://n8n.hrmsmrflrii.xyz | 192.168.40.10:5678 |

### Monitoring & Observability (docker-vm-utilities01)

| Service | URL | Backend | Purpose |
|---------|-----|---------|---------|
| Uptime Kuma | https://uptime.hrmsmrflrii.xyz | 192.168.40.10:3001 | Service uptime monitoring |
| Prometheus | https://prometheus.hrmsmrflrii.xyz | 192.168.40.10:9090 | Metrics collection |
| Grafana | https://grafana.hrmsmrflrii.xyz | 192.168.40.10:3030 | Dashboards |
| Jaeger | https://jaeger.hrmsmrflrii.xyz | 192.168.40.10:16686 | Distributed tracing |
| Demo App | https://demo.hrmsmrflrii.xyz | 192.168.40.10:8080 | OTEL demo application |

### Internal Observability Endpoints (not externally exposed)

| Service | Endpoint | Purpose |
|---------|----------|---------|
| Traefik Metrics | 192.168.40.20:8082/metrics | Prometheus scrape target |
| OTEL Collector (gRPC) | 192.168.40.10:4317 | OTLP trace receiver |
| OTEL Collector (HTTP) | 192.168.40.10:4318 | OTLP trace receiver |
| OTEL Collector Metrics | 192.168.40.10:8888/metrics | Collector internal metrics |
| OTEL Pipeline Metrics | 192.168.40.10:8889/metrics | Pipeline exporter metrics |
| Jaeger Metrics | 192.168.40.10:14269/metrics | Jaeger internal metrics |

## Remote Access (Tailscale)

Tailscale provides secure remote access to the homelab from outside the local network. All Proxmox nodes have Tailscale installed, with node01 configured as a **subnet router** to enable access to all VMs and containers.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Tailscale Network                            │
│                                                                      │
│   ┌──────────────┐         ┌──────────────┐         ┌─────────────┐ │
│   │   MacBook    │◄───────►│   node01     │◄───────►│   node02    │ │
│   │ 100.90.207.58│  WireGuard│ 100.89.33.5 │         │100.96.195.27│ │
│   └──────────────┘         │ SUBNET ROUTER│         └─────────────┘ │
│                            └──────┬───────┘                         │
│                                   │                                  │
└───────────────────────────────────┼──────────────────────────────────┘
                                    │ Advertises Routes
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │192.168.20 │   │192.168.40 │   │192.168.91 │
            │  /24      │   │  /24      │   │  /24      │
            │ Infra     │   │ Services  │   │ Firewall  │
            └───────────┘   └───────────┘   └───────────┘
```

### Tailscale IP Mapping

| Device | Local IP | Tailscale IP | Role |
|--------|----------|--------------|------|
| node01 | 192.168.20.20 | 100.89.33.5 | **Subnet Router** |
| node02 | 192.168.20.21 | 100.96.195.27 | Peer |
| node03 | 192.168.20.22 | 100.76.81.39 | Peer |
| Synology NAS | 192.168.20.31 | 100.84.128.43 | Peer (inactive) |
| MacBook Pro | - | 100.90.207.58 | Client |

### Subnet Router Configuration

node01 is configured as a subnet router, advertising the following networks:

| Network | Purpose | Example Hosts |
|---------|---------|---------------|
| 192.168.20.0/24 | Infrastructure VLAN | Proxmox nodes, Ansible, K8s |
| 192.168.40.0/24 | Services VLAN | Docker hosts, applications |
| 192.168.91.0/24 | Firewall VLAN | OPNsense DNS (192.168.91.30) |

#### node01 Configuration

```bash
# IP forwarding (persisted in /etc/sysctl.d/99-tailscale.conf)
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1

# Tailscale subnet router command
tailscale up --advertise-routes=192.168.20.0/24,192.168.40.0/24,192.168.91.0/24 --accept-routes
```

#### Tailscale Admin Console Settings

Routes must be approved in https://login.tailscale.com/admin/machines:
1. Find node01 → Edit route settings
2. Enable all three subnets
3. Save changes

### Split DNS Configuration

DNS queries for `*.hrmsmrflrii.xyz` are routed to OPNsense Unbound:

| Setting | Value |
|---------|-------|
| Nameserver | 192.168.91.30 (OPNsense) |
| Restrict to domain | hrmsmrflrii.xyz |
| Override local DNS | Enabled |

Configure in Tailscale Admin Console → DNS tab.

### Client Configuration

#### macOS

```bash
# CLI path (not in PATH by default)
/Applications/Tailscale.app/Contents/MacOS/Tailscale

# Accept subnet routes
/Applications/Tailscale.app/Contents/MacOS/Tailscale up --accept-routes

# Optional: Add alias to ~/.zshrc
alias tailscale="/Applications/Tailscale.app/Contents/MacOS/Tailscale"
```

#### Linux/Windows

```bash
tailscale up --accept-routes
```

### Remote Access Commands

```bash
# Check Tailscale status
tailscale status

# SSH via local IPs (through subnet router)
ssh hermes-admin@192.168.20.30    # Ansible controller
ssh hermes-admin@192.168.40.10    # Docker utilities

# SSH via Tailscale IPs (direct)
ssh root@100.89.33.5              # node01
ssh root@100.96.195.27            # node02
ssh root@100.76.81.39             # node03

# Access services via domain (with split DNS)
curl https://grafana.hrmsmrflrii.xyz
curl https://glance.hrmsmrflrii.xyz
```

### What Works Remotely

| Access Type | Method | Example |
|-------------|--------|---------|
| SSH to any VM/container | Local IP via subnet router | `ssh 192.168.40.10` |
| Web services | Domain name via split DNS | `https://grafana.hrmsmrflrii.xyz` |
| Proxmox Web UI | Tailscale IP or local IP | `https://192.168.20.20:8006` |
| Direct container access | Local IP + port | `http://192.168.40.10:3030` |

### Troubleshooting

```bash
# Verify routes are accepted
tailscale status

# Test connectivity to subnets
ping 192.168.20.1    # VLAN 20 gateway
ping 192.168.40.1    # VLAN 40 gateway
ping 192.168.91.30   # OPNsense DNS

# Test DNS resolution
nslookup grafana.hrmsmrflrii.xyz 192.168.91.30

# Check Tailscale DNS status (macOS)
/Applications/Tailscale.app/Contents/MacOS/Tailscale dns status
```

### Security Notes

- **WireGuard encryption**: All traffic is encrypted end-to-end
- **ACL control**: Access controlled via Tailscale admin console
- **No port forwarding**: No inbound ports exposed to internet
- **Device authentication**: Only authorized devices can join the tailnet
- **Split DNS**: DNS queries stay within the encrypted tunnel

---

## Network Maintenance

### Omada Controller Backup

Configuration backed up to NAS via FTP:
- **Path**: `/OmadaConfigBackup`
- **Credentials**: Stored in `CREDENTIALS.md`

### Future Plans

- OPNsense migration as primary gateway/firewall and DNS resolver
- Additional network segmentation as needed

## Related Documentation

- [Proxmox Cluster](./PROXMOX.md) - Node configuration
- [Services](./SERVICES.md) - Deployed services details
- [Troubleshooting](./TROUBLESHOOTING.md) - Network issues
- [Storage](./STORAGE.md) - NFS and storage configuration
