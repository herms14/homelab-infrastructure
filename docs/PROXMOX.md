# Proxmox Cluster Configuration

> Part of the [Proxmox Infrastructure Documentation](../CLAUDE.md)

## Cluster Nodes

| Node | IP Address | Purpose | Workload Type |
|------|------------|---------|---------------|
| **node01** | 192.168.20.20 | VM Host | Virtual machines |
| **node02** | 192.168.20.21 | LXC Host | LXC containers, Service VMs |
| **node03** | 192.168.20.22 | General Purpose | Mixed workloads, Kubernetes |

## Proxmox Version

- **Version**: Proxmox VE 9.1.2
- **Terraform Provider**: telmate/proxmox v3.0.2-rc06 (RC for PVE 9.x compatibility)

## API Access

- **API URL**: https://192.168.20.21:8006/api2/json
- **Authentication**: API Token (`terraform-deployment-user@pve!tf`)
- **TLS**: Self-signed certificate (insecure mode enabled for Terraform)

## VM Configuration Standards

### Default Specifications

| Setting | Value |
|---------|-------|
| CPU | 1 socket, 4 cores |
| Memory | 8GB (8192 MB) |
| Disk | 20GB |
| Storage | VMDisks (NFS) |
| Cloud-init User | hermes-admin |
| SSH Auth | Key only (password disabled) |

### SSH Key

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAby7br+5MzyDus2fi2UFjUBZvGucN40Gxa29bgUTbfz hermes@homelab
```

### Standard VM Features

| Feature | Configuration |
|---------|---------------|
| Cloud-init | Enabled for automated provisioning |
| QEMU Guest Agent | Enabled |
| Auto-start | On Boot enabled |
| CPU Type | host (maximum performance) |
| SCSI Controller | virtio-scsi-single |
| Network Model | virtio |
| BIOS | UEFI (ovmf) |
| Machine | q35 |

### Templates

| Template | OS | Boot Mode | Used For |
|----------|-----|-----------|----------|
| `tpl-ubuntuv24.04-v1` | Ubuntu 24.04 | UEFI | Ansible controller |
| `tpl-ubuntu-shared-v1` | Ubuntu | UEFI | All other VMs |

## LXC Configuration Standards

### Container Types

| Type | Security | Use Case |
|------|----------|----------|
| **Unprivileged** (default) | More secure | Most services |
| **Privileged** | Less secure | Docker with nesting |

### Standard Features

| Feature | Configuration |
|---------|---------------|
| Nesting | Only for Docker hosts |
| Auto-start | Enabled for production |
| SSH Keys | Pre-configured |

### LXC Templates

Download templates on Proxmox nodes:

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

Templates stored in: `/var/lib/vz/template/cache/`

## Resource Sizing Guidelines

### Kubernetes Nodes

| Role | Cores | RAM | Notes |
|------|-------|-----|-------|
| Control Plane | 2 | 4GB | Minimum recommended |
| Worker Nodes | 4 | 8GB | Adjust based on workload |

### Docker Hosts

| Workload | Cores | RAM | Notes |
|----------|-------|-----|-------|
| Media Services | 4 | 8GB | For transcoding |
| General Services | 2-4 | 4-8GB | Standard services |

### LXC Containers

| Service Type | Cores | RAM |
|--------------|-------|-----|
| Reverse Proxy | 1-2 | 1GB |
| Web Servers | 1 | 512MB |
| Docker in LXC | 2-4 | 2-4GB |

## UEFI Boot Configuration

All VMs use UEFI boot mode. Template must match:

```hcl
# modules/linux-vm/main.tf
bios    = "ovmf"
machine = "q35"

efidisk {
  storage           = var.storage
  efitype           = "4m"
  pre_enrolled_keys = true
}

scsihw = "virtio-scsi-single"
```

**Key Lesson**: Always verify template boot mode with `qm config <vmid>` before deploying.

## Useful Commands

### Check Node Status

```bash
# Cluster status
pvecm status

# Node resources
pvesh get /cluster/resources --type node

# Corosync membership
corosync-cmapctl runtime.votequorum.quorate
```

### Template Management

```bash
# List VM templates
qm list | grep template

# Check template config
qm config <vmid>

# Clone from template
qm clone <template_vmid> <new_vmid> --name <hostname>
```

### Node Health

```bash
# Service status
systemctl status pve-cluster corosync

# Cluster logs
journalctl -u corosync -n 50

# Restart cluster services (if needed)
systemctl restart pve-cluster && systemctl restart corosync
```

## Related Documentation

- [Storage](./STORAGE.md) - Storage configuration
- [Networking](./NETWORKING.md) - Network configuration
- [Terraform](./TERRAFORM.md) - Deployment automation
- [Inventory](./INVENTORY.md) - Deployed VMs and containers
- [Troubleshooting](./TROUBLESHOOTING.md) - Common issues
