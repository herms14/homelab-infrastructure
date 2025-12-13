# Proxmox Terraform Infrastructure Documentation

## Overview

This repository contains Terraform infrastructure-as-code for deploying VMs and LXC containers on a Proxmox VE 9.1.2 cluster. The infrastructure is designed for a homelab environment with Kubernetes, Docker services, and supporting infrastructure.

## Infrastructure Architecture

### Proxmox Cluster Nodes

| Node | Purpose | Workload Type |
|------|---------|---------------|
| **node01** | VM Host | All virtual machines |
| **node02** | LXC Host | All LXC containers |

### Network Architecture

#### VLANs

| VLAN | Network | Gateway | Purpose | Services |
|------|---------|---------|---------|----------|
| **VLAN 20** | 192.168.20.0/24 | 192.168.20.1 | Kubernetes Infrastructure | K8s control plane, worker nodes, Traefik |
| **VLAN 40** | 192.168.40.0/24 | 192.168.40.1 | Services & Management | Docker hosts, logging, automation |

#### Network Bridge
- **Bridge**: vmbr0 (all VMs and containers use this bridge)

### Storage Configuration

| Storage Pool | Type | Usage |
|--------------|------|-------|
| **Synology-VMDisks** | Network Storage | Primary storage for all VMs and containers |
| **local-lvm** | Local LVM | Alternative storage option for LXC containers |
| **SynologyISOS** | ISO Storage | ISO images and templates |

## Deployed Infrastructure

### Virtual Machines (node01)

#### Kubernetes Cluster - VLAN 20

**Control Plane Nodes:**
| Hostname | IP Address | Cores | RAM | Disk | Purpose |
|----------|------------|-------|-----|------|---------|
| k8s-controlplane01 | 192.168.20.10 | 2 | 4GB | 50GB | K8s Control Plane |
| k8s-controlplane02 | 192.168.20.11 | 2 | 4GB | 50GB | K8s Control Plane |
| k8s-controlplane03 | 192.168.20.12 | 2 | 4GB | 50GB | K8s Control Plane |

**Worker Nodes:**
| Hostname | IP Address | Cores | RAM | Disk | Purpose |
|----------|------------|-------|-----|------|---------|
| k8s-workernode01 | 192.168.20.20 | 4 | 8GB | 100GB | K8s Worker |
| k8s-workernode02 | 192.168.20.21 | 4 | 8GB | 100GB | K8s Worker |
| k8s-workernode03 | 192.168.20.22 | 4 | 8GB | 100GB | K8s Worker |
| k8s-workernode04 | 192.168.20.23 | 4 | 8GB | 100GB | K8s Worker |
| k8s-workernode05 | 192.168.20.24 | 4 | 8GB | 100GB | K8s Worker |
| k8s-workernode06 | 192.168.20.25 | 4 | 8GB | 100GB | K8s Worker |

#### Services & Management - VLAN 40

| Hostname | IP Address | Cores | RAM | Disk | Purpose |
|----------|------------|-------|-----|------|---------|
| docker-media01 | 192.168.40.10 | 4 | 8GB | 100GB | Media services (Plex, etc.) |
| docker-utilities01 | 192.168.40.20 | 4 | 8GB | 100GB | Utility services |
| linux-syslogserver01 | 192.168.40.30 | 2 | 4GB | 50GB | Centralized logging |
| ansible-master01 | 192.168.40.40 | 2 | 4GB | 50GB | Ansible automation |

### LXC Containers (node02)

#### Reverse Proxy - VLAN 20

| Hostname | IP Address | Cores | RAM | Disk | Template | Purpose |
|----------|------------|-------|-----|------|----------|---------|
| traefik01 | 192.168.20.100 | 2 | 1GB | 10GB | Ubuntu 22.04 | Reverse proxy/Load balancer |

## IP Address Allocation

### VLAN 20 (192.168.20.0/24)
- **10-12**: Kubernetes Control Plane
- **20-25**: Kubernetes Worker Nodes
- **100-199**: LXC Containers (Traefik, future services)

### VLAN 40 (192.168.40.0/24)
- **10-19**: Docker Media Services
- **20-29**: Docker Utility Services
- **30-39**: Logging & Monitoring
- **40-49**: Automation & Management

## Authentication & Access

### SSH Access
- **User**: hermes-admin
- **SSH Key**: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAby7br+5MzyDus2fi2UFjUBZvGucN40Gxa29bgUTbfz hermes@homelab`
- **Access Method**: SSH key authentication only

### Proxmox API
- **API URL**: https://192.168.20.21:8006/api2/json
- **Authentication**: API Token (terraform-deployment-user@pve!tf)
- **TLS**: Self-signed certificate (insecure mode enabled)

## Terraform Configuration

### Provider
- **Provider**: telmate/proxmox v3.0.2-rc06
- **Reason for RC version**: Compatibility with Proxmox VE 9.x

### Module Structure

```
tf-proxmox/
├── main.tf                 # VM group definitions and orchestration
├── lxc.tf                  # LXC container definitions
├── variables.tf            # Global variables and defaults
├── outputs.tf              # Output definitions
├── terraform.tfvars        # Variable values (gitignored)
├── modules/
│   ├── linux-vm/          # VM deployment module
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── lxc/               # LXC deployment module
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── lxc-example.tf         # Example LXC configurations
├── LXC_GUIDE.md          # LXC deployment documentation
└── claude.md             # This file
```

### Key Features
- **Auto-incrementing hostnames**: Automatic sequential naming (e.g., k8s-workernode01, k8s-workernode02)
- **Auto-incrementing IPs**: Automatic IP assignment from starting_ip
- **Dynamic resource creation**: Uses Terraform for_each for scalable deployments
- **Cloud-init provisioning**: Automated VM configuration on first boot
- **Consistent configuration**: DRY principle through modules

## VM Configuration Standards

### All VMs Include:
- **Cloud-init**: For automated provisioning
- **QEMU Guest Agent**: Enabled for better integration
- **On Boot**: Auto-start enabled
- **CPU Type**: host (maximum performance)
- **SCSI Controller**: lsi
- **Network Model**: virtio
- **Template**: tpl-ubuntu-24.04-cloudinit-v3

## LXC Configuration Standards

### Container Types:
- **Unprivileged** (default): More secure, suitable for most services
- **Privileged**: Only when needed (e.g., Docker with nesting)

### Features:
- **Nesting**: Enabled only for Docker hosts
- **Auto-start**: Enabled for production services
- **SSH Keys**: Pre-configured for access

## Common Operations

### Deploy All Infrastructure
```bash
terraform init
terraform plan
terraform apply
```

### Deploy Only VMs
```bash
terraform apply -target=module.vms
```

### Deploy Only LXC Containers
```bash
terraform apply -target=module.lxc
```

### View Deployed Resources
```bash
# View all VMs
terraform output vm_summary

# View all LXC containers
terraform output lxc_summary

# View IP mappings
terraform output vm_ips
terraform output lxc_ips
```

### Add New VM Group
Edit `main.tf` and add to `vm_groups` local:
```hcl
new-service = {
  count       = 1
  starting_ip = "192.168.20.50"
  template    = "tpl-ubuntu-24.04-cloudinit-v3"
  cores       = 2
  sockets     = 1
  memory      = 4096
  disk_size   = "50G"
  storage     = "Synology-VMDisks"
  vlan_tag    = null  # or specific VLAN number
  gateway     = "192.168.20.1"
  nameserver  = "192.168.20.1"
}
```

### Add New LXC Container
Edit `lxc.tf` and add to `lxc_groups` local:
```hcl
new-container = {
  count        = 1
  starting_ip  = "192.168.20.101"
  ostemplate   = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
  unprivileged = true
  cores        = 1
  memory       = 512
  swap         = 256
  disk_size    = "8G"
  storage      = "Synology-VMDisks"
  vlan_tag     = null
  gateway      = "192.168.20.1"
  nameserver   = "192.168.20.1"
  nesting      = false
}
```

## LXC Template Management

### Download LXC Templates (on Proxmox nodes)
```bash
# Update template list
pveam update

# List available templates
pveam available

# Download Ubuntu 22.04 LXC template
pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst

# Download Debian 12 LXC template
pveam download local debian-12-standard_12.2-1_amd64.tar.zst
```

Templates are stored in: `/var/lib/vz/template/cache/`

## Resource Sizing Guidelines

### Kubernetes Nodes
- **Control Plane**: 2 cores, 4GB RAM minimum
- **Worker Nodes**: 4 cores, 8GB RAM (adjust based on workload)

### Docker Hosts
- **Media Services**: 4 cores, 8GB RAM (for transcoding)
- **General Services**: 2-4 cores, 4-8GB RAM

### LXC Containers
- **Reverse Proxy (Traefik)**: 1-2 cores, 1GB RAM
- **Web Servers**: 1 core, 512MB RAM
- **Docker in LXC**: 2-4 cores, 2-4GB RAM

## Troubleshooting

### Common Issues

#### Connection Refused Errors
- **Symptom**: `dial tcp 192.168.20.21:8006: connectex: No connection could be made`
- **Cause**: Proxmox API temporarily unavailable during heavy operations
- **Solution**: Wait and retry, or check Proxmox node status

#### Template Not Found (LXC)
- **Symptom**: `template 'local:vztmpl/...' does not exist`
- **Solution**: SSH to target node and download template with `pveam download`

#### Tainted Resources
- **Symptom**: Resources marked as tainted, requiring replacement
- **Solution**: Run `terraform apply` to recreate them properly

#### State Lock
- **Symptom**: Terraform state is locked
- **Solution**: Ensure no other terraform operations are running, or force unlock with caution

### Useful Commands

```bash
# Check Terraform state
terraform state list

# Show specific resource
terraform state show module.vms["k8s-controlplane01"].proxmox_vm_qemu.linux_vm

# Refresh state
terraform refresh

# Validate configuration
terraform validate

# Format configuration files
terraform fmt
```

## Security Considerations

1. **API Tokens**: Stored in `terraform.tfvars` (excluded from git)
2. **SSH Keys**: Public key only in configuration
3. **Unprivileged LXC**: Default for security
4. **Network Segmentation**: VLANs separate workloads
5. **Cloud-init**: Automated security updates possible

## Future Expansion

### Planned Services
- Additional LXC containers for lightweight services
- Monitoring stack (Prometheus, Grafana)
- GitLab or similar CI/CD
- Database containers (PostgreSQL, Redis)

### IP Reservation
Keep IP ranges available for future growth:
- VLAN 20: 192.168.20.101-199 (LXC containers)
- VLAN 40: 192.168.40.50-99 (Future services)

## Notes

- All VMs use Ubuntu 24.04 LTS cloud-init template
- LXC containers use Ubuntu 22.04 LTS or Debian 12
- VLAN 20 uses `vlan_tag = null` (default VLAN on vmbr0)
- VLAN 40 uses explicit `vlan_tag = 40`
- Auto-start enabled on all production infrastructure
- Proxmox node02 dedicated to containers for resource isolation
