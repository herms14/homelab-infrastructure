# Proxmox Terraform Deployments

Infrastructure as Code for deploying Linux and Windows VMs on Proxmox using Terraform.

## Structure

```
tf-proxmox/
├── modules/
│   ├── linux-vm/       # Reusable Linux VM module
│   └── windows-vm/     # Reusable Windows VM module
├── env/                # Environment-specific variable files
├── scripts/            # Helper scripts and cloud-init configurations
├── main.tf             # Main deployment configuration
├── variables.tf        # Variable definitions
├── terraform.tfvars    # Your variable values (DO NOT COMMIT)
├── providers.tf        # Provider configuration
└── outputs.tf          # Output definitions
```

## Prerequisites

1. **Terraform** >= 1.0
2. **Proxmox VE** cluster with API access
3. **Cloud-init templates** for Linux VMs (Ubuntu/Debian recommended)
4. **Windows templates** for Windows VMs (optional)

## Setup

### 1. Configure API Access

Edit `terraform.tfvars` and update:
- `proxmox_api_url`: Your Proxmox API URL (e.g., `https://192.168.1.100:8006/api2/json`)
- API token credentials are already configured

### 2. Customize the Test Deployment

Edit `main.tf` and update the following in the `test_linux_vm` module:
- `target_node`: Your Proxmox node name (default: "pve")
- `template_name`: Your cloud-init template name
- `storage`: Your storage pool (e.g., "local-lvm", "ceph-pool")
- `ip_address`: Desired IP in the 192.168.20.0/24 network
- `gateway`: Your gateway (typically 192.168.20.1)
- `nameserver`: Your DNS server
- `ssh_keys`: Your SSH public key for access

### 3. Initialize Terraform

```bash
terraform init
```

## Usage

### Deploy Test Linux VM

The test configuration deploys a Linux VM on VLAN 20 (192.168.20.0/24):

```bash
# Preview changes
terraform plan

# Deploy
terraform apply

# Show outputs
terraform output
```

### Deploy Custom Linux VM

Use the linux-vm module in your `main.tf`:

```hcl
module "my_linux_vm" {
  source = "./modules/linux-vm"

  vm_name       = "my-server"
  target_node   = "pve"
  template_name = "ubuntu-cloud-template"

  cores   = 4
  memory  = 8192
  storage = "local-lvm"

  vlan_tag    = 20
  ip_address  = "192.168.20.100"
  gateway     = "192.168.20.1"

  ci_user  = "admin"
  ssh_keys = "ssh-rsa AAAAB3..."
}
```

### Deploy Windows VM

Use the windows-vm module:

```hcl
module "my_windows_vm" {
  source = "./modules/windows-vm"

  vm_name       = "win-server"
  target_node   = "pve"
  template_name = "windows-2022-template"

  cores   = 4
  memory  = 16384
  storage = "local-lvm"

  vlan_tag  = 20
  use_dhcp  = true  # or set to false for static IP
}
```

## Module Parameters

### Linux VM Module

| Parameter | Description | Default |
|-----------|-------------|---------|
| `vm_name` | VM hostname | required |
| `target_node` | Proxmox node | required |
| `template_name` | Template to clone | required |
| `cores` | CPU cores | 2 |
| `memory` | RAM in MB | 2048 |
| `storage` | Storage pool | required |
| `disk_size` | Disk size | "20G" |
| `vlan_tag` | VLAN tag | -1 (no VLAN) |
| `ip_address` | Static IP | required |
| `gateway` | Default gateway | required |
| `ci_user` | Cloud-init username | "ubuntu" |
| `ssh_keys` | SSH public keys | "" |

### Windows VM Module

Similar to Linux, but with:
- `use_dhcp`: Enable DHCP (default: true)
- Higher default resources (4 cores, 8GB RAM, 100GB disk)
- Windows-specific OS type

## Network Configuration

The example is configured for VLAN 20 (192.168.20.0/24):
- VLAN Tag: 20
- Network: 192.168.20.0/24
- Gateway: 192.168.20.1
- Test VM IP: 192.168.20.10

## Cleanup

```bash
terraform destroy
```

## Security Notes

- `terraform.tfvars` contains sensitive credentials - ensure it's in `.gitignore`
- API tokens are already configured with proper permissions
- Use SSH keys instead of passwords for Linux VMs

## Requirements

- Terraform >= 1.0
- Proxmox VE with API access
