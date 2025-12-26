# Cloud-Init Templates

> **TL;DR**: Cloud-init templates enable instant VM provisioning by pre-configuring OS images with cloud-init support, allowing network and user configuration at first boot.

## Cloud-Init Overview

Cloud-init is an industry-standard tool for cloud instance initialization. When a VM boots from a cloud-init enabled image:

1. Reads configuration from a mounted drive or metadata service
2. Configures network (IP, gateway, DNS)
3. Creates users and SSH keys
4. Sets hostname
5. Runs custom scripts

---

## Template Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Template to VM Flow                                   │
│                                                                              │
│   1. Download Cloud Image                                                    │
│          │                                                                   │
│          ▼                                                                   │
│   ┌─────────────────┐                                                       │
│   │ ubuntu-24.04-   │                                                       │
│   │ cloudimg.img    │                                                       │
│   └────────┬────────┘                                                       │
│            │                                                                 │
│            ▼                                                                 │
│   2. Create VM from Image                                                    │
│          │                                                                   │
│          ▼                                                                   │
│   ┌─────────────────┐                                                       │
│   │ Template VM     │  Configure: UEFI, cloud-init drive, hardware         │
│   │ (VMID: 9000)    │                                                       │
│   └────────┬────────┘                                                       │
│            │                                                                 │
│            ▼                                                                 │
│   3. Convert to Template                                                     │
│          │                                                                   │
│          ▼                                                                   │
│   ┌─────────────────┐                                                       │
│   │ tpl-ubuntu-     │  Locked, read-only, clone source                     │
│   │ shared-v1       │                                                       │
│   └────────┬────────┘                                                       │
│            │                                                                 │
│            ▼                                                                 │
│   4. Terraform Clones Template                                               │
│          │                                                                   │
│          ▼                                                                   │
│   ┌─────────────────┐                                                       │
│   │ Production VM   │  Boots with cloud-init config:                       │
│   │ (k8s-worker01)  │  IP, user, SSH keys, hostname                        │
│   └─────────────────┘                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Creating Templates

### Prerequisites

- Proxmox node with sufficient storage
- Internet access for downloading cloud images
- Target storage pool configured (VMDisks)

### Step 1: Download Cloud Image

```bash
# SSH to Proxmox node
ssh root@192.168.20.21

# Create working directory
mkdir -p /tmp/cloud-images && cd /tmp/cloud-images

# Download Ubuntu 24.04 cloud image
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
```

**Image sources**:

| Distribution | URL |
|--------------|-----|
| Ubuntu 24.04 | https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img |
| Ubuntu 22.04 | https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img |
| Debian 12 | https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-amd64.qcow2 |
| Rocky Linux 9 | https://download.rockylinux.org/pub/rocky/9/images/x86_64/Rocky-9-GenericCloud.latest.x86_64.qcow2 |

### Step 2: Create VM

```bash
# Set variables
VMID=9000
TEMPLATE_NAME="tpl-ubuntuv24.04-v1"
STORAGE="VMDisks"
IMAGE="/tmp/cloud-images/noble-server-cloudimg-amd64.img"

# Create VM with UEFI support
qm create $VMID \
  --name $TEMPLATE_NAME \
  --memory 2048 \
  --cores 2 \
  --cpu host \
  --net0 virtio,bridge=vmbr0 \
  --bios ovmf \
  --machine q35 \
  --scsihw virtio-scsi-single \
  --efidisk0 $STORAGE:1,efitype=4m,pre-enrolled-keys=1 \
  --agent enabled=1
```

**Parameter explanation**:

| Parameter | Purpose |
|-----------|---------|
| `--bios ovmf` | UEFI firmware (required for modern cloud images) |
| `--machine q35` | Modern chipset with PCIe support |
| `--scsihw virtio-scsi-single` | High-performance SCSI controller |
| `--efidisk0` | EFI System Partition storage |
| `--agent enabled=1` | Enable QEMU guest agent |

### Step 3: Import Disk

```bash
# Import cloud image as disk
qm importdisk $VMID $IMAGE $STORAGE
```

Output:
```
importing disk 'noble-server-cloudimg-amd64.img' to VM 9000 ...
Successfully imported disk as 'unused0:VMDisks:9000/vm-9000-disk-0.raw'
```

### Step 4: Attach Disk

```bash
# Attach imported disk as scsi0
qm set $VMID --scsi0 $STORAGE:$VMID/vm-$VMID-disk-0.raw

# Resize disk to desired size
qm resize $VMID scsi0 20G
```

### Step 5: Configure Boot Order

```bash
# Set boot order to scsi0
qm set $VMID --boot order=scsi0
```

### Step 6: Add Cloud-Init Drive

```bash
# Add cloud-init CD-ROM drive
qm set $VMID --ide2 $STORAGE:cloudinit

# Configure serial console for cloud-init
qm set $VMID --serial0 socket --vga serial0
```

### Step 7: Convert to Template

```bash
# Convert VM to template
qm template $VMID
```

**Verification**:
```bash
# List templates
qm list | grep template

# Show template config
qm config $VMID
```

---

## Complete Template Script

```bash
#!/bin/bash
# create-ubuntu-template.sh

set -e

# Configuration
VMID="${1:-9000}"
TEMPLATE_NAME="${2:-tpl-ubuntuv24.04-v1}"
STORAGE="${3:-VMDisks}"
NODE="${4:-node01}"

IMAGE_URL="https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
IMAGE_FILE="/tmp/noble-server-cloudimg-amd64.img"

echo "Creating template: $TEMPLATE_NAME (VMID: $VMID)"

# Download image if not exists
if [ ! -f "$IMAGE_FILE" ]; then
    echo "Downloading cloud image..."
    wget -O "$IMAGE_FILE" "$IMAGE_URL"
fi

# Remove existing VM if present
if qm status $VMID &>/dev/null; then
    echo "Removing existing VM $VMID..."
    qm destroy $VMID --purge
fi

# Create VM
echo "Creating VM..."
qm create $VMID \
    --name "$TEMPLATE_NAME" \
    --memory 2048 \
    --cores 2 \
    --cpu host \
    --net0 virtio,bridge=vmbr0 \
    --bios ovmf \
    --machine q35 \
    --scsihw virtio-scsi-single \
    --efidisk0 "$STORAGE:1,efitype=4m,pre-enrolled-keys=1" \
    --agent enabled=1

# Import and attach disk
echo "Importing disk..."
qm importdisk $VMID "$IMAGE_FILE" "$STORAGE"
qm set $VMID --scsi0 "$STORAGE:$VMID/vm-$VMID-disk-0.raw"
qm resize $VMID scsi0 20G

# Configure boot and cloud-init
echo "Configuring boot and cloud-init..."
qm set $VMID --boot order=scsi0
qm set $VMID --ide2 "$STORAGE:cloudinit"
qm set $VMID --serial0 socket --vga serial0

# Convert to template
echo "Converting to template..."
qm template $VMID

echo "Template $TEMPLATE_NAME created successfully!"
qm config $VMID
```

**Usage**:
```bash
chmod +x create-ubuntu-template.sh
./create-ubuntu-template.sh 9000 tpl-ubuntuv24.04-v1 VMDisks
```

---

## Current Templates

| Template Name | VMID | Node | OS | Purpose |
|---------------|------|------|-----|---------|
| `tpl-ubuntuv24.04-v1` | 9000 | node01 | Ubuntu 24.04 | Ansible controller |
| `tpl-ubuntu-shared-v1` | 9001 | All | Ubuntu 24.04 | General VMs |

---

## Template Placement

### Single Node Template

Template exists on one node only:

```hcl
# main.tf - VMs must deploy to same node as template
ansible-controller = {
  starting_node = "node01"      # Template on node01
  template      = "tpl-ubuntuv24.04-v1"
}
```

### Shared Template (All Nodes)

Copy template to all nodes for flexibility:

```bash
# On source node
qm clone 9000 9001 --full --storage VMDisks --name tpl-ubuntu-shared-v1

# Copy to other nodes (via Proxmox HA migration)
# Or manually recreate on each node
```

**Alternative**: Use NFS-backed storage (VMDisks) which is accessible from all nodes.

---

## Cloud-Init Configuration

### Proxmox Cloud-Init Settings

Configure in Terraform (or via Web UI: VM → Cloud-Init):

| Setting | Terraform Parameter | Purpose |
|---------|---------------------|---------|
| User | `ciuser` | Default username |
| Password | `cipassword` | User password (optional) |
| SSH Keys | `sshkeys` | Public keys for SSH access |
| IP Config | `ipconfig0` | Network configuration |
| DNS Server | `nameserver` | DNS server IP |
| DNS Domain | `searchdomain` | Search domain |

### Terraform Cloud-Init Example

```hcl
resource "proxmox_vm_qemu" "linux_vm" {
  # ...

  # Cloud-init configuration
  os_type    = "cloud-init"
  ipconfig0  = "ip=192.168.20.30/24,gw=192.168.20.1"
  ciuser     = "hermes-admin"
  sshkeys    = <<-EOF
    ssh-ed25519 AAAAC3... user@host
  EOF
  nameserver = "192.168.91.30"
}
```

### Generated Cloud-Init Config

View what Proxmox generates:

```bash
# Network configuration
qm cloudinit dump 100 network

# User configuration
qm cloudinit dump 100 user

# Meta configuration
qm cloudinit dump 100 meta
```

**Example network output**:
```yaml
version: 1
config:
  - type: physical
    name: eth0
    mac_address: '02:00:00:00:00:01'
    subnets:
      - type: static
        address: '192.168.20.30'
        netmask: '255.255.255.0'
        gateway: '192.168.20.1'
  - type: nameserver
    address:
      - '192.168.91.30'
```

---

## Customizing Templates

### Pre-Install Packages

Before converting to template, boot the VM and install packages:

```bash
# Start VM temporarily
qm start 9000

# SSH in (may need to set temporary cloud-init config first)
# Or use console

# Install packages
apt update && apt install -y qemu-guest-agent cloud-init

# Clean up
apt clean
cloud-init clean
truncate -s 0 /etc/machine-id
rm -f /var/lib/dbus/machine-id

# Shutdown
poweroff
```

### Custom Cloud-Init Scripts

Add to `/etc/cloud/cloud.cfg.d/` before templating:

**99-custom.cfg**:
```yaml
#cloud-config
package_update: true
package_upgrade: true
packages:
  - curl
  - wget
  - htop
  - vim

runcmd:
  - echo "Custom initialization complete" >> /var/log/cloud-init-custom.log
```

---

## Template Maintenance

### Update Template

1. Clone template to temporary VM
2. Boot and apply updates
3. Clean up (machine-id, cloud-init state)
4. Create new template with incremented version

```bash
# Clone template
qm clone 9000 9999 --full --name temp-update

# Start and update
qm start 9999
ssh user@temp-ip "sudo apt update && sudo apt upgrade -y"
ssh user@temp-ip "sudo cloud-init clean && sudo truncate -s 0 /etc/machine-id"
ssh user@temp-ip "sudo poweroff"

# Create new template
qm template 9999
qm set 9999 --name tpl-ubuntuv24.04-v2
```

### Delete Old Template

```bash
# Remove template (ensure no VMs referencing it)
qm destroy 9000 --purge
```

---

## Troubleshooting

### VM Boots to UEFI Shell

**Symptom**: VM shows UEFI shell instead of booting OS

**Cause**: Boot order incorrect or disk not properly attached

**Fix**:
```bash
# Verify disk attached
qm config <vmid> | grep scsi0

# Set boot order
qm set <vmid> --boot order=scsi0
```

### Cloud-Init Not Running

**Symptom**: VM boots but no network/user configuration

**Cause**: cloud-init drive not attached or cloud-init not installed in image

**Fix**:
```bash
# Verify cloud-init drive
qm config <vmid> | grep ide2

# Should show: ide2: VMDisks:cloudinit
```

### Network Not Configured

**Symptom**: VM boots but can't get IP

**Cause**: cloud-init network config issues

**Diagnosis**:
```bash
# View cloud-init logs
cat /var/log/cloud-init.log

# Check network config
cat /etc/netplan/*.yaml
```

### Template Clone Fails

**Symptom**: Terraform fails to clone template

**Causes**:
- Template on different node than target
- Template doesn't exist
- Storage not accessible

**Fix**:
```bash
# Verify template exists
qm list | grep tpl

# Verify storage accessible from target node
pvesm status
```

---

## Best Practices

### Naming Convention

```
tpl-<distro>v<version>-v<template-version>
```

Examples:
- `tpl-ubuntuv24.04-v1`
- `tpl-debian12-v2`
- `tpl-rocky9-v1`

### Template VMID Reservation

| VMID Range | Purpose |
|------------|---------|
| 9000-9099 | Templates |
| 100-999 | Production VMs |
| 1000+ | Test/Dev |

### Documentation

Document each template:
- Source image URL
- Creation date
- Pre-installed packages
- Known limitations

---

## What's Next?

- **[VM Deployment](VM-Deployment)** - Deploy VMs from templates
- **[LXC Containers](LXC-Containers)** - Container deployment
- **[Ansible-Basics](Ansible-Basics)** - Configure deployed VMs

---

*Good templates are the foundation of consistent infrastructure.*
