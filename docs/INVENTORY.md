# Deployed Infrastructure Inventory

> Part of the [Proxmox Infrastructure Documentation](../CLAUDE.md)

## Summary

**Cluster**: MorpheusCluster (2-node + Qdevice)

| Category | Count | vCPUs | RAM | Storage |
|----------|-------|-------|-----|---------|
| Ansible | 1 | 2 | 8GB | 20GB |
| Kubernetes | 9 | 18 | 72GB | 180GB |
| Services | 5 | 26 | 38GB | 130GB |
| LXC Containers | 7 | 16 | 25GB | 168GB |
| **Total** | **22** | **62** | **143GB** | **498GB** |

*Last updated: January 7, 2026*

## Synology NAS

| Hostname | IP | Services | Storage |
|----------|----|----------|---------|
| Synology NAS | 192.168.20.31 | DSM, NFS, SNMP, **Plex Media Server** | 6 drives (RAID) |

**Plex Media Server**: http://192.168.20.31:32400/web

---

## VLAN 20 - Infrastructure (192.168.20.0/24)

### Automation & Management

| Hostname | Node | IP | Cores | RAM | Disk | Purpose |
|----------|------|----|-------|-----|------|---------|
| ansible-controller01 | node01 | 192.168.20.30 | 2 | 8GB | 20GB | Ansible + Packer |

**Installed Tools:**
- **Ansible** - Configuration management (`~/ansible/`)
- **Packer v1.14.3** - VM template creation (`~/packer/`)
- **Omada Exporter** - Network metrics (port 9202)

### Kubernetes Cluster (9 nodes)

**Cluster Specifications**:
- **Version**: v1.28.15 (stable)
- **HA Control Plane**: 3 controllers with stacked etcd
- **Worker Nodes**: 6 workers for application workloads
- **Runtime**: containerd v1.7.28 (systemd cgroup)
- **CNI**: Calico v3.27.0
- **Pod Network**: 10.244.0.0/16
- **Status**: Fully operational (December 19, 2025)

#### Control Plane

| Hostname | Node | IP | Cores | RAM | Disk | Role |
|----------|------|----|-------|-----|------|------|
| k8s-controller01 | node01 | 192.168.20.32 | 2 | 8GB | 20GB | Primary |
| k8s-controller02 | node01 | 192.168.20.33 | 2 | 8GB | 20GB | HA |
| k8s-controller03 | node01 | 192.168.20.34 | 2 | 8GB | 20GB | HA |

#### Worker Nodes

| Hostname | Node | IP | Cores | RAM | Disk |
|----------|------|----|-------|-----|------|
| k8s-worker01 | node01 | 192.168.20.40 | 2 | 8GB | 20GB |
| k8s-worker02 | node01 | 192.168.20.41 | 2 | 8GB | 20GB |
| k8s-worker03 | node01 | 192.168.20.42 | 2 | 8GB | 20GB |
| k8s-worker04 | node01 | 192.168.20.43 | 2 | 8GB | 20GB |
| k8s-worker05 | node01 | 192.168.20.44 | 2 | 8GB | 20GB |
| k8s-worker06 | node01 | 192.168.20.45 | 2 | 8GB | 20GB |

## VLAN 40 - Services (192.168.40.0/24)

### Application Services

| Hostname | Node | VMID | IP | Cores | RAM | Disk | Purpose |
|----------|------|------|----|-------|-----|------|---------|
| linux-syslog-server01 | node02 | 109 | 192.168.40.5 | 8 | 8GB | 50GB | Centralized logging |
| docker-vm-core-utilities01 | node01 | 107 | 192.168.40.13 | 4 | 12GB | 40GB | Grafana, Prometheus, Uptime Kuma, Speedtest, n8n, Jaeger |
| immich-vm01 | node02 | 108 | 192.168.40.22 | 10 | 12GB | 20GB | Photo management |
| gitlab-vm01 | node02 | 106 | 192.168.40.23 | 2 | 8GB | 20GB | DevOps platform |
| gitlab-runner-vm01 | node02 | 121 | 192.168.40.24 | 2 | 2GB | 20GB | CI/CD job executor |

> **Note**: Traefik (VM 102), Authentik (VM 100), and docker-media (VM 111) were migrated to LXC containers on January 7, 2026. See [LXC Migration Plan](./LXC_MIGRATION_PLAN.md) for details.

## VLAN 90 - Management (192.168.90.0/24)

| Hostname | Node | VMID | IP | Cores | RAM | Disk | Purpose |
|----------|------|------|----|-------|-----|------|---------|
| pihole | node01 | 202 | 192.168.90.53 | 2 | 1GB | 8GB | DNS server (Pi-hole v6 + Unbound) |

## LXC Containers

| Hostname | Node | VMID | IP | Cores | RAM | Disk | Purpose |
|----------|------|------|----|-------|-----|------|---------|
| docker-lxc-glance | node01 | 200 | 192.168.40.12 | 2 | 4GB | 20GB | Glance, Media Stats API, Reddit Manager, NBA Stats API |
| docker-lxc-bots | node01 | 201 | 192.168.40.14 | 2 | 2GB | 8GB | Argus Bot, Chronos Bot |
| pihole | node01 | 202 | 192.168.90.53 | 2 | 1GB | 8GB | Pi-hole v6 + Unbound DNS |
| traefik-lxc | node02 | 203 | 192.168.40.20 | 2 | 2GB | 20GB | Traefik reverse proxy (migrated from VM 102) |
| authentik-lxc | node02 | 204 | 192.168.40.21 | 2 | 4GB | 30GB | Authentik SSO (migrated from VM 100) |
| docker-lxc-media | node01 | 205 | 192.168.40.11 | 4 | 8GB | 50GB | Arr media stack (migrated from VM 111) |
| homeassistant-lxc | node01 | 206 | 192.168.40.25 | 2 | 4GB | 32GB | Home Assistant smart home automation |

**Reserved IP Range**: 192.168.20.100-199

## Deployment Details

| Setting | Value |
|---------|-------|
| Deployment Method | Cloud-init template |
| Templates | tpl-ubuntu-shared-v1, tpl-ubuntuv24.04-v1 |
| Storage | VMDisks (NFS on Synology) |
| Network | vmbr0 (VLAN 20/40 tagged) |
| DNS | 192.168.90.53 (Pi-hole) |
| SSH User | hermes-admin |
| SSH Auth | Key-based only |
| Management | Ansible from ansible-controller01 |

## IP Reservations

### VLAN 20

| Range | Purpose |
|-------|---------|
| 46-99 | Additional Kubernetes nodes |
| 100-199 | LXC containers |
| 200-254 | Future VMs |

### VLAN 40

| Range | Purpose |
|-------|---------|
| 12-19 | Additional Docker hosts |
| 30-39 | Monitoring & additional services |
| 40-254 | Future services |

## Related Documentation

- [Proxmox](./PROXMOX.md) - Node configuration
- [Networking](./NETWORKING.md) - IP allocation details
- [Services](./SERVICES.md) - Service details
- [Terraform](./TERRAFORM.md) - Deployment configuration
- [CI/CD](./CICD.md) - GitLab automation pipeline
