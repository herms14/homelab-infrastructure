# Quick Start Guide

## Before You Begin

You need:
1. A Proxmox server accessible via network
2. A cloud-init Linux template created in Proxmox
3. Your SSH public key

## Step-by-Step Setup

### 1. Update Proxmox Connection

Edit `terraform.tfvars`:
```hcl
proxmox_api_url = "https://YOUR-PROXMOX-IP:8006/api2/json"
```

### 2. Update VM Configuration

Edit `main.tf` and change:

```hcl
module "test_linux_vm" {
  # ...existing config...

  target_node   = "YOUR-NODE-NAME"      # Run 'pvesh get /nodes' to see nodes
  template_name = "YOUR-TEMPLATE-NAME"   # Your cloud-init template
  storage       = "YOUR-STORAGE"         # e.g., "local-lvm"

  # Network - VLAN 20 (192.168.20.0/24)
  ip_address = "192.168.20.10"
  gateway    = "192.168.20.1"
  nameserver = "192.168.20.1"           # Your DNS server

  # SSH Access
  ssh_keys = <<-EOT
    ssh-rsa AAAAB3NzaC1yc2EAAAADA... your-email@example.com
  EOT
}
```

### 3. Initialize and Deploy

```bash
# Download provider plugins
terraform init

# Preview what will be created
terraform plan

# Deploy the VM
terraform apply

# View VM details
terraform output
```

### 4. Access Your VM

```bash
ssh admin@192.168.20.10
```

## What Gets Created

A single Linux VM with:
- **Name**: test-ubuntu-vm
- **Resources**: 2 cores, 4GB RAM, 32GB disk
- **Network**: VLAN 20, IP 192.168.20.10/24
- **Access**: SSH with your public key

## Common Issues

### "template not found"
Create a cloud-init template in Proxmox first. Example:
```bash
# On Proxmox host
qm create 9000 --name ubuntu-cloud-template --memory 2048 --net0 virtio,bridge=vmbr0
qm importdisk 9000 ubuntu-22.04-server-cloudimg-amd64.img local-lvm
qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0
qm set 9000 --ide2 local-lvm:cloudinit
qm set 9000 --boot c --bootdisk scsi0
qm set 9000 --serial0 socket --vga serial0
qm template 9000
```

### "storage not found"
List available storage: `pvesm status`

### "node not found"
List nodes: `pvesh get /nodes`

## Next Steps

1. Test the VM deployment
2. Customize for your needs
3. Add more VMs by copying the module block
4. Deploy Windows VMs using the windows-vm module

## Cleaning Up

```bash
terraform destroy
```
