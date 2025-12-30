# Deployed Infrastructure Inventory

> Part of the [Proxmox Infrastructure Documentation](../CLAUDE.md)

## Summary

**Cluster**: MorpheusCluster (2-node + Qdevice)

| Category | Count | vCPUs | RAM | Storage |
|----------|-------|-------|-----|---------|
| Ansible | 1 | 2 | 8GB | 20GB |
| Kubernetes | 9 | 18 | 72GB | 180GB |
| Services | 8 | 18 | 58GB | 190GB |
| LXC Containers | 3 | 6 | 7GB | 36GB |
| **Total** | **21** | **44** | **145GB** | **426GB** |

*Last updated: December 30, 2025*

> **Note**: node03 was removed from cluster on 2025-12-30. All workloads now run on node01/node02.

## VLAN 20 - Infrastructure (192.168.20.0/24)

### Automation & Management

| Hostname | Node | IP | Cores | RAM | Disk | Purpose |
|----------|------|----|-------|-----|------|---------|
| ansible-controller01 | node01 | 192.168.20.30 | 2 | 8GB | 20GB | Ansible automation |

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
| docker-vm-media01 | node01 | 111 | 192.168.40.11 | 2 | 12GB | 100GB | Arr media stack, Mnemosyne Bot |
| docker-vm-core-utilities01 | node01 | 107 | 192.168.40.13 | 4 | 12GB | 40GB | Grafana, Prometheus, Uptime Kuma, Speedtest, n8n, Jaeger |
| traefik-vm01 | node02 | 102 | 192.168.40.20 | 2 | 8GB | 20GB | Reverse proxy |
| authentik-vm01 | node02 | 100 | 192.168.40.21 | 2 | 8GB | 20GB | Identity/SSO |
| immich-vm01 | node02 | 108 | 192.168.40.22 | 10 | 12GB | 20GB | Photo management |
| gitlab-vm01 | node02 | 106 | 192.168.40.23 | 2 | 8GB | 20GB | DevOps platform |
| gitlab-runner-vm01 | node02 | 121 | 192.168.40.24 | 2 | 2GB | 20GB | CI/CD job executor |

> **Note**: docker-vm-utilities01 (192.168.40.10) was decommissioned. Services moved to LXC 200 and VM 107.

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
