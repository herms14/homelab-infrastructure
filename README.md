# Proxmox Terraform Deployments

Infrastructure-as-code for deploying virtual machines and LXC containers on a Proxmox VE cluster using Terraform.

## Overview

This repository contains Terraform configurations for managing a 3-node Proxmox VE 9.1.2 cluster with automated VM and container deployments. The infrastructure uses a production-grade NFS storage architecture backed by Synology NAS, with support for auto-incrementing hostnames, IP addresses, and multi-node deployment.

## Features

- **Auto-incrementing deployments**: Automatic sequential naming and IP allocation
- **Multi-node support**: Deploy VMs across different Proxmox nodes automatically
- **Production storage architecture**: Dedicated NFS exports for VM disks, ISOs, and application data
- **Dynamic resource creation**: Terraform `for_each` for scalable infrastructure
- **Cloud-init provisioning**: ✅ Fully operational automated VM configuration (UEFI boot support added Dec 2025)
- **UEFI boot support**: Native UEFI template compatibility for modern cloud-init images
- **Ansible automation**: Centralized configuration management with production-grade playbooks
- **LXC container support**: Lightweight containers with persistent storage via NFS bind mounts

## Current Infrastructure

**Production Deployment (17 VMs):**
- ✅ **Kubernetes Cluster**: 9 nodes (3 control plane + 6 workers) - Infrastructure deployed, pending initialization
- ✅ **Ansible Automation**: 1 controller managing all infrastructure
- ✅ **Application Services**: 7 VMs (logging, Docker hosts, Traefik, Authentik, Immich, GitLab)

**Resources:**
- **Total VMs**: 17 across 2 VLANs
- **Total vCPUs**: 36 cores
- **Total RAM**: 72GB
- **Storage**: 370GB on NFS (Synology NAS)

See [CLAUDE.md](./CLAUDE.md) for detailed infrastructure inventory.

## Architecture

### Proxmox Cluster

| Node | IP Address | Purpose |
|------|------------|---------|
| node01 | 192.168.20.20 | VM Host |
| node02 | 192.168.20.21 | LXC Host |
| node03 | 192.168.20.22 | General Purpose |

### Storage Architecture

The cluster uses a dedicated NFS export strategy:

```
Synology NAS (192.168.20.31)
├── /volume2/ProxmoxCluster-VMDisks → Proxmox-managed VM disks
├── /volume2/ProxmoxCluster-ISOs    → Proxmox-managed ISO storage
├── /volume2/Proxmox-LXCs           → Manual mount for LXC app configs
└── /volume2/Proxmox-Media          → Manual mount for media files
```

**Key Principle**: One NFS export = One Proxmox storage pool

See [CLAUDE.md](./CLAUDE.md) for detailed storage architecture documentation.

### Network

- **VLAN 20** (192.168.20.0/24): Infrastructure and management
- **VLAN 40** (192.168.40.0/24): Services and applications
- **Bridge**: vmbr0 (all VMs and containers)

## Repository Structure

```
tf-proxmox/
├── main.tf                 # VM group definitions and orchestration
├── lxc.tf                  # LXC container definitions
├── variables.tf            # Global variables
├── outputs.tf              # Output definitions
├── terraform.tfvars        # Variable values (gitignored)
├── modules/
│   ├── linux-vm/          # VM deployment module
│   └── lxc/               # LXC deployment module
├── CLAUDE.md              # Comprehensive infrastructure documentation
└── README.md              # This file
```

## Quick Start

### Prerequisites

- Proxmox VE 9.x cluster
- Terraform >= 1.0
- Synology NAS with NFS configured
- VM template with cloud-init support

### 1. Clone and Configure

```bash
git clone https://github.com/herms14/Proxmox-TerraformDeployments.git
cd Proxmox-TerraformDeployments
```

### 2. Create `terraform.tfvars`

```hcl
# Proxmox API Configuration
proxmox_api_url          = "https://192.168.20.21:8006/api2/json"
proxmox_api_token_id     = "terraform-deployment-user@pve!tf"
proxmox_api_token_secret = "your-api-token-secret"
proxmox_tls_insecure     = true

# Infrastructure Defaults
default_storage    = "VMDisks"
default_node       = "node01"
default_vlan       = 20
default_gateway    = "192.168.20.1"
default_nameserver = "192.168.20.1"

# SSH Configuration
ssh_public_key = "ssh-ed25519 AAAA... user@host"
```

### 3. Initialize and Deploy

```bash
terraform init
terraform plan
terraform apply
```

## Usage Examples

### Deploy VMs Across Multiple Nodes

```hcl
# main.tf
locals {
  vm_groups = {
    ansible-control = {
      count         = 2
      starting_ip   = "192.168.20.50"
      starting_node = "node02"  # node02, node03
      template      = "ubuntu-24.04-cloudinit-template"
      cores         = 4
      sockets       = 1
      memory        = 8192
      disk_size     = "20G"
      storage       = "VMDisks"
      vlan_tag      = null
      gateway       = "192.168.20.1"
      nameserver    = "192.168.20.1"
    }
  }
}
```

This creates:
- `ansible-control01` on node02 at 192.168.20.50 (4 cores, 8GB RAM, 20GB disk)
- `ansible-control02` on node03 at 192.168.20.51 (4 cores, 8GB RAM, 20GB disk)

### Deploy LXC Container with Persistent Storage

```hcl
# lxc.tf
locals {
  lxc_groups = {
    traefik = {
      count        = 1
      starting_ip  = "192.168.20.100"
      ostemplate   = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
      cores        = 2
      memory       = 1024
      disk_size    = "10G"
      storage      = "local-lvm"
      vlan_tag     = null
      gateway      = "192.168.20.1"
      nameserver   = "192.168.20.1"
      nesting      = false
    }
  }
}
```

**Bind mount app config** (add to `/etc/pve/lxc/100.conf`):
```
mp0: /mnt/nfs/lxcs/traefik,mp=/app/config
```

## Storage Setup

### Proxmox Configuration

**Add NFS storages** (Datacenter → Storage):

1. **VMDisks**:
   - Server: 192.168.20.31
   - Export: `/volume2/ProxmoxCluster-VMDisks`
   - Content: Disk image

2. **ISOs**:
   - Server: 192.168.20.31
   - Export: `/volume2/ProxmoxCluster-ISOs`
   - Content: ISO image

### Manual Mounts

**On all Proxmox nodes**, add to `/etc/fstab`:

```bash
192.168.20.31:/volume2/Proxmox-LXCs   /mnt/nfs/lxcs   nfs  defaults,_netdev  0  0
192.168.20.31:/volume2/Proxmox-Media  /mnt/nfs/media  nfs  defaults,_netdev  0  0
```

Then mount:
```bash
mkdir -p /mnt/nfs/lxcs /mnt/nfs/media
mount -a
```

## Common Operations

### View Deployed Resources

```bash
# All VMs
terraform output vm_summary

# All LXC containers
terraform output lxc_summary

# IP mappings
terraform output vm_ips
terraform output lxc_ips
```

### Deploy Only VMs

```bash
terraform apply -target=module.vms
```

### Deploy Only LXC Containers

```bash
terraform apply -target=module.lxc
```

### Format Configuration

```bash
terraform fmt
```

### Validate Configuration

```bash
terraform validate
```

## Key Configuration Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `proxmox_api_url` | Proxmox API endpoint | - |
| `proxmox_api_token_id` | API token ID | - |
| `proxmox_api_token_secret` | API token secret | - |
| `default_storage` | Default VM storage | `local-lvm` |
| `default_node` | Default Proxmox node | `node01` |
| `ssh_public_key` | SSH public key for access | - |

## VM Configuration Standards

All VMs include:
- **Cloud-init**: Automated provisioning
- **QEMU Guest Agent**: Enhanced integration
- **Auto-start**: Start on boot
- **CPU Type**: host (maximum performance)
- **Network**: virtio model on vmbr0

## LXC Configuration Standards

- **Default**: Unprivileged containers
- **Storage**: local-lvm for rootfs
- **App Data**: Bind-mounted from `/mnt/nfs/lxcs`
- **Auto-start**: Enabled for production services

## Troubleshooting

For detailed troubleshooting guides, see **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)**.

### Common Issues

#### QEMU Exit Code 1 - Missing VLAN Configuration

**Problem**: VMs fail to start with `QEMU exited with code 1`

**Cause**: Proxmox node bridge (`vmbr0`) not configured as VLAN-aware

**Solution**: Update `/etc/network/interfaces` on affected node:
```bash
auto vmbr0
iface vmbr0 inet static
	address 192.168.20.XX/24
	gateway 192.168.20.1
	bridge-ports nic0
	bridge-stp off
	bridge-fd 0
	bridge-vlan-aware yes      # Required!
	bridge-vids 2-4094         # Required!
```

Then reload: `ifreload -a` or `reboot`

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for the complete resolution process.

#### Cloud-init VM Boot Failure - UEFI/BIOS Mismatch

**Problem**: VMs create successfully but hang during boot, never reaching login prompt

**Symptoms**:
- Console stops at: `Btrfs loaded, zoned=yes, fsverity=yes`
- VM unreachable via SSH/ping
- Boot process hangs before cloud-init initialization

**Root Cause**: Template uses UEFI boot (`bios: ovmf`) but Terraform configured VM with legacy BIOS mode

**Solution**: Verify template boot mode and match in Terraform module:

```bash
# Check template configuration
ssh root@<node-ip> "qm config <template-vmid> | grep -E 'bios:|efidisk'"
```

If template uses UEFI (`bios: ovmf`), ensure `modules/linux-vm/main.tf` includes:
```hcl
bios    = "ovmf"
machine = "q35"

efidisk {
  storage           = var.storage
  efitype           = "4m"
  pre_enrolled_keys = true
}

scsihw = "virtio-scsi-single"
```

**Status**: ✅ Fixed December 15, 2025. Cloud-init deployments fully operational with UEFI support.

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for detailed troubleshooting steps.

#### Node Showing Question Mark / Unhealthy Status

**Problem**: Node appears with `?` icon in Proxmox UI and shows "NR" (Not Ready) status

**Symptoms**:
- Question mark icon in Proxmox web UI cluster view
- "NR" status in cluster membership (`pvecm status`)
- Node may be unreachable or shutting down

**Common Causes**:
- Node in shutdown state (intentional or unexpected)
- Network connectivity issues
- Corosync cluster communication failure

**Quick Diagnosis**:
```bash
# Check if node is reachable
ping <node-ip>

# Check cluster status
ssh root@<node-ip> "pvecm status"

# Check for shutdown messages
ssh root@<node-ip> "dmesg | tail -50"
```

**Resolution**:
1. If node shutdown: Power on via physical access, IPMI, or WOL
2. If network issue: Verify network configuration and corosync services
3. If cluster communication issue: Restart cluster services

See [CLAUDE.md](./CLAUDE.md#node-showing-question-mark--unhealthy-status-resolved---december-16-2025) for detailed troubleshooting steps.

**Status**: ✅ Documented December 16, 2025 after successful node03 recovery incident.

#### Storage Issues

**Problem**: Storage marked as inactive or showing `?` icons

**Solution**: Ensure NFS exports are configured correctly:
```bash
# On NAS, verify exports
showmount -e 192.168.20.31

# On Proxmox nodes, verify mounts
df -h | grep 192.168.20.31
```

#### Template Not Found

**Problem**: VM template doesn't exist on target node

**Solution**: Ensure template exists on all nodes or use `starting_node` to target specific nodes with the template.

#### Connection Refused

**Problem**: Terraform can't connect to Proxmox API

**Solution**:
- Verify Proxmox node is online
- Check API token is valid
- Confirm firewall allows connections

## Documentation

- **[CLAUDE.md](./CLAUDE.md)**: Comprehensive infrastructure documentation including:
  - Storage architecture deep-dive
  - Network configuration and requirements
  - Node setup requirements (VLAN-aware bridges)
  - Deployed infrastructure inventory (17 VMs across 2 VLANs)
  - Terraform usage guide

- **[Kubernetes_Setup.md](./Kubernetes_Setup.md)**: Complete Kubernetes deployment guide:
  - Production-grade 9-node HA cluster (3 controllers + 6 workers)
  - Ansible playbook documentation with detailed explanations
  - Every command explained with rationale
  - Comprehensive troubleshooting section
  - Post-installation tasks and verification

- **[ANSIBLE_SETUP.md](./ANSIBLE_SETUP.md)**: Ansible automation documentation:
  - Inventory organization and host groups
  - SSH key configuration
  - Common playbooks and commands
  - Managed hosts status (9 VMs active, 5 offline K8s nodes)

- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)**: Detailed troubleshooting guide covering:
  - Cloud-init VM UEFI/BIOS boot mismatch resolution
  - Node03 QEMU deployment failure resolution
  - Network bridge VLAN configuration
  - Step-by-step diagnostic process
  - Prevention strategies for new nodes

## Security Considerations

- API tokens stored in `terraform.tfvars` (excluded from git)
- SSH key authentication only
- Unprivileged LXC containers by default
- Network segmentation via VLANs
- TLS for Proxmox API (self-signed certificate accepted)

## Contributing

This is a personal homelab infrastructure repository. Feel free to fork and adapt for your own use.

## License

MIT License - See LICENSE file for details

## Author

Hermes - Homelab Infrastructure

## Acknowledgments

- Telmate Proxmox Terraform Provider
- Proxmox VE Team
- Synology NAS Platform
