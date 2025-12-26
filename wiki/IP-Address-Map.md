# IP Address Map

> **TL;DR**: Complete reference of all IP addresses in the homelab infrastructure.

## Network Overview

| Network | VLAN | Range | Purpose |
|---------|------|-------|---------|
| Infrastructure | VLAN 20 | 192.168.20.0/24 | Proxmox, Kubernetes, Management |
| Services | VLAN 40 | 192.168.40.0/24 | Applications, Docker hosts |
| Firewall/DNS | N/A | 192.168.91.0/24 | OPNsense management |

---

## VLAN 20 - Infrastructure (192.168.20.0/24)

### Proxmox Cluster Nodes

| IP Address | Hostname | Role | Notes |
|------------|----------|------|-------|
| 192.168.20.20 | node01 | Primary VM Host | Proxmox VE 9.1.2 |
| 192.168.20.21 | node02 | Secondary Host | Application services |
| 192.168.20.22 | node03 | Kubernetes Host | K8s cluster |

### Management Infrastructure

| IP Address | Hostname | Role | Access |
|------------|----------|------|--------|
| 192.168.20.30 | ansible-controller01 | Ansible Controller | SSH: `ssh hermes-admin@192.168.20.30` |
| 192.168.20.31 | synology-nas | NAS Storage | Web: `https://192.168.20.31:5001` |

### Kubernetes Control Plane

| IP Address | Hostname | Role | Notes |
|------------|----------|------|-------|
| 192.168.20.32 | k8s-controller01 | Control Plane (Primary) | etcd, API server |
| 192.168.20.33 | k8s-controller02 | Control Plane (HA) | etcd, API server |
| 192.168.20.34 | k8s-controller03 | Control Plane (HA) | etcd, API server |

### Kubernetes Worker Nodes

| IP Address | Hostname | Role | Notes |
|------------|----------|------|-------|
| 192.168.20.40 | k8s-worker01 | Worker Node | Container workloads |
| 192.168.20.41 | k8s-worker02 | Worker Node | Container workloads |
| 192.168.20.42 | k8s-worker03 | Worker Node | Container workloads |
| 192.168.20.43 | k8s-worker04 | Worker Node | Container workloads |
| 192.168.20.44 | k8s-worker05 | Worker Node | Container workloads |
| 192.168.20.45 | k8s-worker06 | Worker Node | Container workloads |

### Reserved Ranges (VLAN 20)

| Range | Purpose |
|-------|---------|
| 192.168.20.1-19 | Network equipment, reserved |
| 192.168.20.20-22 | Proxmox nodes |
| 192.168.20.23-29 | Future Proxmox nodes |
| 192.168.20.30-31 | Management (Ansible, NAS) |
| 192.168.20.32-39 | Kubernetes control plane |
| 192.168.20.40-99 | Kubernetes workers |
| 192.168.20.100-199 | LXC containers |
| 192.168.20.200-254 | Future VMs |

---

## VLAN 40 - Services (192.168.40.0/24)

### Infrastructure Services

| IP Address | Hostname | Service | Ports | HTTPS URL |
|------------|----------|---------|-------|-----------|
| 192.168.40.5 | linux-syslog-server01 | Syslog Server | 514/udp | N/A |
| 192.168.40.20 | traefik-vm01 | Traefik Reverse Proxy | 80, 443, 8080 | https://traefik.hrmsmrflrii.xyz |

### Docker Hosts

| IP Address | Hostname | Services Running | Notes |
|------------|----------|------------------|-------|
| 192.168.40.10 | docker-vm-utilities01 | Paperless, Glance, n8n | Utility services |
| 192.168.40.11 | docker-vm-media01 | Arr Stack (10 services) | Media automation |

### Application Services

| IP Address | Hostname | Service | Port | HTTPS URL |
|------------|----------|---------|------|-----------|
| 192.168.40.21 | authentik-vm01 | Authentik SSO | 9000 | https://auth.hrmsmrflrii.xyz |
| 192.168.40.22 | immich-vm01 | Immich Photos | 2283 | https://photos.hrmsmrflrii.xyz |
| 192.168.40.23 | gitlab-vm01 | GitLab CE | 80, 443 | https://gitlab.hrmsmrflrii.xyz |

### Reserved Ranges (VLAN 40)

| Range | Purpose |
|-------|---------|
| 192.168.40.1-4 | Network equipment |
| 192.168.40.5-9 | Logging/monitoring |
| 192.168.40.10-19 | Docker hosts |
| 192.168.40.20-39 | Application services |
| 192.168.40.40-99 | Future services |
| 192.168.40.100-199 | Dynamic/DHCP |
| 192.168.40.200-254 | Reserved |

---

## Other Networks

### Firewall/Management (192.168.91.0/24)

| IP Address | Hostname | Role | Notes |
|------------|----------|------|-------|
| 192.168.91.30 | opnsense | Firewall/DNS | Internal DNS server |

---

## Service Endpoints (via Traefik)

All services are accessible through Traefik at 192.168.40.20:

| Service | HTTPS URL | Backend IP:Port |
|---------|-----------|-----------------|
| **Infrastructure** | | |
| Traefik Dashboard | https://traefik.hrmsmrflrii.xyz | 192.168.40.20:8080 |
| Proxmox Cluster | https://proxmox.hrmsmrflrii.xyz | 192.168.20.21:8006 |
| Proxmox Node 01 | https://node01.hrmsmrflrii.xyz | 192.168.20.20:8006 |
| Proxmox Node 02 | https://node02.hrmsmrflrii.xyz | 192.168.20.21:8006 |
| Proxmox Node 03 | https://node03.hrmsmrflrii.xyz | 192.168.20.22:8006 |
| **Core Services** | | |
| Authentik | https://auth.hrmsmrflrii.xyz | 192.168.40.21:9000 |
| Immich | https://photos.hrmsmrflrii.xyz | 192.168.40.22:2283 |
| GitLab | https://gitlab.hrmsmrflrii.xyz | 192.168.40.23:80 |
| **Media Services** | | |
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
| **Utility Services** | | |
| Paperless | https://paperless.hrmsmrflrii.xyz | 192.168.40.10:8000 |
| Glance | https://glance.hrmsmrflrii.xyz | 192.168.40.10:8080 |
| n8n | https://n8n.hrmsmrflrii.xyz | 192.168.40.10:5678 |

---

## Quick Reference Commands

### Find IP of a service

```bash
# Using nslookup with OPNsense DNS
nslookup jellyfin.hrmsmrflrii.xyz 192.168.91.30
```

### Scan network for devices

```bash
# Find all active IPs on VLAN 40
nmap -sn 192.168.40.0/24
```

### Check if port is open

```bash
# Test if Jellyfin is responding
nc -zv 192.168.40.11 8096
```

---

## Updating This Document

When adding new services:
1. Assign IP from the appropriate reserved range
2. Add entry to this page
3. Add DNS record in OPNsense
4. Add Traefik route if HTTPS needed

---

*Last updated: December 2025*
