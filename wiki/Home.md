# Proxmox Homelab Infrastructure Wiki

Welcome to the comprehensive documentation for a production-grade homelab running on Proxmox VE.

## What is This?

This wiki documents a complete homelab infrastructure including:
- A 3-node Proxmox virtualization cluster
- 17 virtual machines running various services
- 22 containerized applications with HTTPS
- A 9-node Kubernetes cluster
- Automated deployment with Terraform and Ansible

Whether you're setting up your first homelab or looking for inspiration, this documentation explains every component in beginner-friendly terms.

---

## Quick Reference (Modular Docs)

For developers and advanced users, we maintain modular documentation in the repository:

| Resource | Link | Description |
|----------|------|-------------|
| **Network** | [docs/NETWORKING.md](../docs/NETWORKING.md) | VLANs, IPs, DNS, SSL |
| **Compute** | [docs/PROXMOX.md](../docs/PROXMOX.md) | Cluster nodes, VM/LXC standards |
| **Storage** | [docs/STORAGE.md](../docs/STORAGE.md) | NFS, Synology, storage pools |
| **Terraform** | [docs/TERRAFORM.md](../docs/TERRAFORM.md) | Modules, deployment |
| **Services** | [docs/SERVICES.md](../docs/SERVICES.md) | Docker services |
| **Ansible** | [docs/ANSIBLE.md](../docs/ANSIBLE.md) | Automation, playbooks |
| **Inventory** | [docs/INVENTORY.md](../docs/INVENTORY.md) | Deployed infrastructure |
| **Troubleshooting** | [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) | Common issues |

---

## Quick Navigation

### Getting Started

1. **[Introduction](Introduction)** - What this project is and who it's for
2. **[Prerequisites](Prerequisites)** - What you need before starting
3. **[Architecture Overview](Architecture-Overview)** - See the big picture
4. **[Quick Start](Quick-Start)** - Deploy your first VM in 15 minutes

### Infrastructure Guides

- **[Proxmox Cluster](Proxmox-Cluster)** - Setting up the virtualization platform
- **[Network Architecture](Network-Architecture)** - VLANs, IPs, and routing
- **[Storage Architecture](Storage-Architecture)** - NFS, NAS, and storage pools
- **[DNS Configuration](DNS-Configuration)** - Internal DNS with OPNsense
- **[SSL Certificates](SSL-Certificates)** - Let's Encrypt with Cloudflare

### Deployment Tools

- **[Terraform Basics](Terraform-Basics)** - Infrastructure as Code fundamentals
- **[Ansible Basics](Ansible-Basics)** - Configuration management fundamentals
- **[VM Deployment](VM-Deployment)** - Creating virtual machines
- **[Cloud-Init Templates](Cloud-Init-Templates)** - Automated VM provisioning

### Services

- **[Services Overview](Services-Overview)** - All services at a glance
- **[Traefik](Traefik)** - Reverse proxy and SSL termination
- **[Arr Stack](Arr-Stack)** - Media automation (Jellyfin, Radarr, Sonarr, etc.)

### Kubernetes

- **[Kubernetes Overview](Kubernetes)** - Container orchestration basics

### Reference

- **[IP Address Map](IP-Address-Map)** - Complete IP allocation table
- **[Command Cheatsheet](Command-Cheatsheet)** - Quick reference commands

---

## Infrastructure Overview

```
+---------------------------------------------------------------+
|                     PROXMOX CLUSTER                              |
+-----------------+-----------------+-----------------------------+
|    node01       |     node02      |         node03              |
|  192.168.20.20  |  192.168.20.21  |      192.168.20.22          |
|    (VMs)        |    (LXC)        |      (Kubernetes)           |
+--------+--------+--------+--------+------------+----------------+
         |                 |                      |
         v                 v                      v
+---------------------------------------------------------------+
|                    VLAN 20 - Infrastructure                      |
|  * Ansible Controller (192.168.20.30)                           |
|  * Kubernetes: 3 Controllers + 6 Workers (192.168.20.32-45)     |
+---------------------------------------------------------------+
         |
         v
+---------------------------------------------------------------+
|                    VLAN 40 - Services                            |
|  * Traefik Reverse Proxy (192.168.40.20)                        |
|  * Authentik SSO (192.168.40.21)                                |
|  * Immich Photos (192.168.40.22)                                |
|  * GitLab (192.168.40.23)                                       |
|  * Docker Hosts (192.168.40.10-11) - Arr Stack, Paperless, n8n  |
+---------------------------------------------------------------+
         |
         v
+---------------------------------------------------------------+
|                    Storage (Synology NAS)                        |
|  * VM Disks: /volume2/ProxmoxCluster-VMDisks                    |
|  * Media: /volume2/Proxmox-Media                                |
|  * ISOs: /volume2/ProxmoxCluster-ISOs                           |
+---------------------------------------------------------------+
```

---

## Stats

| Metric | Value |
|--------|-------|
| Proxmox Nodes | 3 |
| Virtual Machines | 17 |
| Docker Containers | 22+ |
| Kubernetes Nodes | 9 |
| Total vCPUs | 36 |
| Total RAM | 72 GB |
| Storage | 370 GB (NFS) |
| Services with HTTPS | 22 |

---

## Getting Help

- **Issues**: If something doesn't work, check [Troubleshooting Guide](../docs/TROUBLESHOOTING.md)
- **Questions**: Open an issue on [GitHub](https://github.com/herms14/Proxmox-TerraformDeployments/issues)
- **Credentials**: Sensitive values are in `CREDENTIALS.md` (not in git)

---

*This wiki is maintained alongside the infrastructure. Last updated: December 2025*
