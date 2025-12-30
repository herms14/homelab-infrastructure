# Packer - Image Builder

HashiCorp Packer is used to create VM templates and images for the Proxmox cluster.

## Overview

| Item | Details |
|------|---------|
| **Location** | Ansible Controller (192.168.20.30) |
| **Version** | 1.14.3 |
| **Working Directory** | `/home/hermes-admin/packer/` |
| **Purpose** | Create Proxmox VM templates with cloud-init |

## Why Packer?

Packer automates the creation of VM templates, ensuring:
- **Consistency** - Same base image for all VMs
- **Reproducibility** - Templates can be rebuilt from code
- **Integration** - Works with Terraform and Ansible
- **Cloud-Init Ready** - Templates support cloud-init for dynamic configuration

## Directory Structure

```
/home/hermes-admin/packer/
├── proxmox-ubuntu-template.pkr.hcl    # Main template definition
├── credentials.pkrvars.hcl.example    # Credentials template
├── credentials.pkrvars.hcl            # Actual credentials (not in git)
└── http/                              # Autoinstall files (for Ubuntu)
    └── user-data                      # Cloud-init user data
```

## Quick Start

### 1. SSH to Ansible Controller

```bash
ssh ansible
cd ~/packer
```

### 2. Configure Credentials

```bash
# Copy example and edit
cp credentials.pkrvars.hcl.example credentials.pkrvars.hcl
nano credentials.pkrvars.hcl

# Add your Proxmox API token secret
# proxmox_api_token_secret = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### 3. Initialize Packer Plugins

```bash
packer init proxmox-ubuntu-template.pkr.hcl
```

### 4. Validate Template

```bash
packer validate -var-file=credentials.pkrvars.hcl proxmox-ubuntu-template.pkr.hcl
```

### 5. Build Template

```bash
packer build -var-file=credentials.pkrvars.hcl proxmox-ubuntu-template.pkr.hcl
```

## Available Templates

### Ubuntu 24.04 Server Template

| Setting | Value |
|---------|-------|
| **VM ID** | 9000 |
| **Name** | ubuntu-2404-template |
| **CPU** | 2 cores (host type) |
| **Memory** | 2048 MB |
| **Disk** | 20 GB (local-lvm) |
| **Network** | VLAN 20 (Infrastructure) |
| **Cloud-Init** | Enabled |

**Features:**
- QEMU Guest Agent installed
- Cloud-init configured
- SSH enabled
- Ready for Terraform cloning

## Integration with Terraform

After Packer creates a template, Terraform can clone it:

```hcl
# In Terraform
resource "proxmox_vm_qemu" "my_vm" {
  name        = "my-new-vm"
  target_node = "node02"
  clone       = "ubuntu-2404-template"  # Packer-created template

  # Cloud-init configuration
  ipconfig0 = "ip=192.168.20.100/24,gw=192.168.20.1"
  ciuser    = "hermes-admin"
  sshkeys   = file("~/.ssh/homelab_ed25519.pub")
}
```

## Integration with Ansible

Packer can run Ansible playbooks during image creation:

```hcl
build {
  sources = ["source.proxmox-iso.ubuntu"]

  # Run Ansible after base install
  provisioner "ansible" {
    playbook_file = "../ansible/base-config.yml"
    user          = "hermes-admin"
  }
}
```

## Common Commands

| Command | Purpose |
|---------|---------|
| `packer version` | Check Packer version |
| `packer init <file>` | Download required plugins |
| `packer validate <file>` | Validate template syntax |
| `packer build <file>` | Build the image |
| `packer build -debug <file>` | Build with debug output |
| `packer build -on-error=ask <file>` | Pause on error for debugging |

## Proxmox API Requirements

The Packer Proxmox builder needs these API permissions:

| Permission | Required For |
|------------|--------------|
| `VM.Allocate` | Create new VMs |
| `VM.Clone` | Clone existing templates |
| `VM.Config.*` | Configure VM settings |
| `VM.PowerMgmt` | Start/stop VMs |
| `VM.Console` | Access VM console |
| `Datastore.AllocateSpace` | Create disks |
| `Datastore.AllocateTemplate` | Create templates |
| `Sys.Modify` | Modify system settings |

The existing `terraform-deployment-user@pve!tf` API token has these permissions.

## Troubleshooting

### SSH Connection Timeout

```bash
# Increase timeout in template
ssh_timeout  = "30m"

# Or use SSH agent forwarding
ssh_agent_auth = true
```

### ISO Not Found

```bash
# List available ISOs
pvesh get /nodes/node02/storage/local/content --content iso

# Upload ISO via web UI or:
# Datacenter > node02 > local > ISO Images > Upload
```

### Template Already Exists

```bash
# Delete existing template first
qm destroy 9000

# Or use a different VM ID
vm_id = 9001
```

### Cloud-Init Drive Issues

```bash
# Check cloud-init storage pool exists
pvesm status

# Ensure local-lvm has space
lvs
```

## Best Practices

1. **Version Control** - Keep Packer templates in git (without credentials)
2. **Variables** - Use variables for all configurable values
3. **Credentials** - Store secrets in `.pkrvars.hcl` files (gitignored)
4. **Validation** - Always validate before building
5. **Naming** - Use descriptive template names with version/date
6. **Testing** - Test templates before using in production

## Related Documentation

- [Terraform](./TERRAFORM.md) - Infrastructure provisioning
- [Ansible](./ANSIBLE.md) - Configuration management
- [Proxmox](./PROXMOX.md) - Hypervisor documentation
- [Cloud-Init Templates](./scripts/cloud-init/) - Cloud-init examples
