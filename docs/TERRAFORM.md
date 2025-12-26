# Terraform Configuration

> Part of the [Proxmox Infrastructure Documentation](../CLAUDE.md)

## Provider

- **Provider**: telmate/proxmox v3.0.2-rc06
- **RC Reason**: Required for Proxmox VE 9.x compatibility

## Repository Structure

```
tf-proxmox/
├── main.tf                 # VM group definitions (cloud-init)
├── lxc.tf                  # LXC container definitions
├── variables.tf            # Global variables and defaults
├── outputs.tf              # Output definitions
├── terraform.tfvars        # Variable values (gitignored)
├── modules/
│   ├── linux-vm/           # VM deployment module
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── lxc/                # LXC deployment module
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── ansible-playbooks/      # Ansible playbooks
├── docs/                   # Documentation
└── CLAUDE.md               # Main documentation
```

## Key Features

- **Auto-incrementing hostnames**: Sequential naming (k8s-controller01, k8s-worker01...)
- **Auto-incrementing IPs**: Automatic IP assignment from starting_ip
- **Dynamic resource creation**: Terraform for_each for scalable deployments
- **Cloud-init automation**: Fully automated VM provisioning
- **Ansible integration**: Centralized config from ansible-controller01
- **DRY configuration**: Consistent settings through modules

## Deployment Methodology

### Cloud-init Deployment

All VMs use cloud-init templates for consistent, automated provisioning.

**Workflow**:
1. Terraform clones from cloud-init template
2. Cloud-init configures network, users, SSH keys on first boot
3. VM boots fully configured and accessible
4. Ansible manages post-deployment configuration

**Requirements**:
- Cloud-init compatible template on target node
- UEFI boot mode must match template configuration
- Working network configuration at boot time
- VLAN-aware bridge properly configured

**Templates Used**:
- `tpl-ubuntuv24.04-v1`: Ansible controller (Ubuntu 24.04, UEFI)
- `tpl-ubuntu-shared-v1`: All other VMs (Ubuntu, UEFI)

## Common Operations

### Deploy All Infrastructure

```bash
terraform init
terraform plan
terraform apply
```

### Deploy VMs Only

```bash
terraform apply -target=module.vms
```

### Deploy LXC Only

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

### State Management

```bash
# List all resources
terraform state list

# Show specific resource
terraform state show module.vms["k8s-controlplane01"].proxmox_vm_qemu.linux_vm

# Refresh state
terraform refresh

# Validate configuration
terraform validate

# Format files
terraform fmt
```

## Adding New VM Group

Edit `main.tf` and add to `vm_groups` local:

```hcl
new-service = {
  count         = 1
  starting_ip   = "192.168.20.50"
  starting_node = "node01"  # Optional: auto-increment nodes
  template      = "ubuntu-24.04-cloudinit-template"
  cores         = 4         # Default: 4 cores
  sockets       = 1         # Default: 1 socket
  memory        = 8192      # Default: 8GB
  disk_size     = "20G"     # Default: 20GB
  storage       = "VMDisks"
  vlan_tag      = null      # null for VLAN 20, 40 for VLAN 40
  gateway       = "192.168.20.1"
  nameserver    = "192.168.91.30"
}
```

### VLAN Configuration Examples

**VLAN 20** (Infrastructure):
```hcl
vlan_tag    = null
gateway     = "192.168.20.1"
nameserver  = "192.168.91.30"
starting_ip = "192.168.20.x"
```

**VLAN 40** (Services):
```hcl
vlan_tag    = 40
gateway     = "192.168.40.1"
nameserver  = "192.168.91.30"
starting_ip = "192.168.40.x"
```

## Adding New LXC Container

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
  storage      = "local-lvm"  # LXC rootfs on local storage
  vlan_tag     = null
  gateway      = "192.168.20.1"
  nameserver   = "192.168.91.30"
  nesting      = false
}
```

**Note**: LXC containers use `local-lvm` for rootfs. Bind mount application data from `/mnt/nfs/lxcs`:

```
# In /etc/pve/lxc/<vmid>.conf
mp0: /mnt/nfs/lxcs/new-container,mp=/app/config
```

## Security Considerations

1. **API Tokens**: Stored in `terraform.tfvars` (excluded from git)
2. **SSH Keys**: Public key only in configuration
3. **Unprivileged LXC**: Default for security
4. **Network Segmentation**: VLANs separate workloads
5. **Cloud-init**: Automated security updates possible

## UEFI Boot Configuration

VMs must match template boot mode. Current templates use UEFI:

```hcl
# In modules/linux-vm/main.tf
bios    = "ovmf"
machine = "q35"

efidisk {
  storage           = var.storage
  efitype           = "4m"
  pre_enrolled_keys = true
}

scsihw = "virtio-scsi-single"
```

## Troubleshooting

### Connection Refused

- **Symptom**: `dial tcp 192.168.20.21:8006: connectex: No connection could be made`
- **Cause**: Proxmox API temporarily unavailable
- **Solution**: Wait and retry, check node status

### Template Not Found (LXC)

- **Symptom**: `template 'local:vztmpl/...' does not exist`
- **Solution**: Download with `pveam download` on target node

### Tainted Resources

- **Symptom**: Resources marked as tainted
- **Solution**: Run `terraform apply` to recreate

### State Lock

- **Symptom**: Terraform state is locked
- **Solution**: Ensure no other operations running, or force unlock

## Related Documentation

- [Proxmox](./PROXMOX.md) - Cluster and VM configuration
- [Storage](./STORAGE.md) - Storage configuration
- [Networking](./NETWORKING.md) - VLAN and IP configuration
- [Inventory](./INVENTORY.md) - Deployed resources
- [Troubleshooting](./TROUBLESHOOTING.md) - Detailed issue resolution
