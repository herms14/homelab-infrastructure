# VM Deployment

> **TL;DR**: Define VM groups in `main.tf`, each group uses the `linux-vm` module to clone from cloud-init templates with auto-incrementing hostnames and IPs.

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VM Deployment Flow                                 │
│                                                                              │
│   main.tf                    modules/linux-vm/           Proxmox             │
│   ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐   │
│   │ local.vm_groups │       │                 │       │                 │   │
│   │                 │       │ proxmox_vm_qemu │       │  Clone from     │   │
│   │ k8s-workers = { │──────▶│                 │──────▶│  Template       │   │
│   │   count = 6     │       │ • Configure HW  │       │                 │   │
│   │   starting_ip   │       │ • Set network   │       │  Apply cloud-   │   │
│   │   ...           │       │ • Cloud-init    │       │  init on boot   │   │
│   │ }               │       │                 │       │                 │   │
│   └─────────────────┘       └─────────────────┘       └─────────────────┘   │
│                                                                              │
│   for_each expands:                                                          │
│   k8s-worker01, k8s-worker02, k8s-worker03...                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## VM Groups Configuration

### Structure

**File**: `main.tf`

```hcl
locals {
  vm_groups = {
    # Ansible Automation
    ansible-controller = {
      count         = 1
      starting_ip   = "192.168.20.30"
      starting_node = "node01"
      template      = "tpl-ubuntuv24.04-v1"
      cores         = 2
      sockets       = 1
      memory        = 4096
      disk_size     = "20G"
      storage       = "VMDisks"
      vlan_tag      = null
      gateway       = "192.168.20.1"
      nameserver    = "192.168.91.30"
    }

    # Kubernetes Control Plane
    k8s-controller = {
      count         = 3
      starting_ip   = "192.168.20.32"
      starting_node = "node03"
      template      = "tpl-ubuntu-shared-v1"
      cores         = 2
      sockets       = 1
      memory        = 4096
      disk_size     = "20G"
      storage       = "VMDisks"
      vlan_tag      = null
      gateway       = "192.168.20.1"
      nameserver    = "192.168.91.30"
    }

    # Kubernetes Workers
    k8s-worker = {
      count         = 6
      starting_ip   = "192.168.20.40"
      starting_node = "node03"
      template      = "tpl-ubuntu-shared-v1"
      cores         = 2
      sockets       = 1
      memory        = 4096
      disk_size     = "20G"
      storage       = "VMDisks"
      vlan_tag      = null
      gateway       = "192.168.20.1"
      nameserver    = "192.168.91.30"
    }

    # Docker Hosts (VLAN 40)
    docker-vm-utilities = {
      count         = 1
      starting_ip   = "192.168.40.10"
      starting_node = "node02"
      template      = "tpl-ubuntu-shared-v1"
      cores         = 2
      sockets       = 1
      memory        = 4096
      disk_size     = "20G"
      storage       = "VMDisks"
      vlan_tag      = 40
      gateway       = "192.168.40.1"
      nameserver    = "192.168.91.30"
    }

    docker-vm-media = {
      count         = 1
      starting_ip   = "192.168.40.11"
      starting_node = "node02"
      template      = "tpl-ubuntu-shared-v1"
      cores         = 2
      sockets       = 1
      memory        = 4096
      disk_size     = "20G"
      storage       = "VMDisks"
      vlan_tag      = 40
      gateway       = "192.168.40.1"
      nameserver    = "192.168.91.30"
    }
  }
}
```

### Parameter Reference

| Parameter | Type | Description |
|-----------|------|-------------|
| `count` | number | Number of VMs in this group |
| `starting_ip` | string | First IP address (auto-increments) |
| `starting_node` | string | Target Proxmox node |
| `template` | string | Cloud-init template name |
| `cores` | number | vCPU cores per VM |
| `sockets` | number | CPU sockets |
| `memory` | number | RAM in MB |
| `disk_size` | string | OS disk size (e.g., "20G") |
| `storage` | string | Proxmox storage pool |
| `vlan_tag` | number/null | VLAN ID (null for native VLAN) |
| `gateway` | string | Network gateway |
| `nameserver` | string | DNS server |

---

## Expanding VM Groups

### Flat Map Transformation

The VM groups are expanded into individual VMs:

```hcl
locals {
  # Expand groups into flat list of VMs
  all_vms = flatten([
    for group_name, group in local.vm_groups : [
      for i in range(group.count) : {
        key         = format("%s%02d", group_name, i + 1)  # k8s-worker01
        hostname    = format("%s%02d", group_name, i + 1)
        ip_address  = cidrhost("${group.starting_ip}/24", i)
        target_node = group.starting_node
        template    = group.template
        cores       = group.cores
        sockets     = group.sockets
        memory      = group.memory
        disk_size   = group.disk_size
        storage     = group.storage
        vlan_tag    = group.vlan_tag
        gateway     = group.gateway
        nameserver  = group.nameserver
      }
    ]
  ])

  # Convert to map for for_each
  vms_map = {
    for vm in local.all_vms : vm.key => vm
  }
}
```

**Transformation example**:
```
Input: k8s-worker { count = 3, starting_ip = "192.168.20.40" }

Output:
  k8s-worker01 → 192.168.20.40
  k8s-worker02 → 192.168.20.41
  k8s-worker03 → 192.168.20.42
```

---

## Module Invocation

### Module Call

```hcl
module "vms" {
  source   = "./modules/linux-vm"
  for_each = local.vms_map

  hostname      = each.value.hostname
  ip_address    = each.value.ip_address
  target_node   = each.value.target_node
  template      = each.value.template
  cores         = each.value.cores
  sockets       = each.value.sockets
  memory        = each.value.memory
  disk_size     = each.value.disk_size
  storage       = each.value.storage
  vlan_tag      = each.value.vlan_tag
  gateway       = each.value.gateway
  nameserver    = each.value.nameserver
  ssh_public_key = var.ssh_public_key
  ci_user       = var.ci_user
}
```

---

## Linux VM Module

### Module Structure

```
modules/linux-vm/
├── main.tf          # Resource definition
├── variables.tf     # Input variables
└── outputs.tf       # Output values
```

### Main Resource

**File**: `modules/linux-vm/main.tf`

```hcl
resource "proxmox_vm_qemu" "linux_vm" {
  name        = var.hostname
  target_node = var.target_node
  clone       = var.template

  # Hardware
  cores   = var.cores
  sockets = var.sockets
  memory  = var.memory
  cpu     = "host"
  numa    = false

  # UEFI Boot Configuration
  bios    = "ovmf"
  machine = "q35"

  # EFI Disk (required for UEFI)
  efidisk {
    storage           = var.storage
    efitype           = "4m"
    pre_enrolled_keys = true
  }

  # SCSI Controller
  scsihw = "virtio-scsi-single"

  # OS Disk
  disks {
    scsi {
      scsi0 {
        disk {
          storage = var.storage
          size    = var.disk_size
        }
      }
    }
  }

  # Network
  network {
    bridge = "vmbr0"
    model  = "virtio"
    tag    = var.vlan_tag
  }

  # Cloud-init Configuration
  os_type   = "cloud-init"
  ipconfig0 = "ip=${var.ip_address}/24,gw=${var.gateway}"
  ciuser    = var.ci_user
  sshkeys   = var.ssh_public_key
  nameserver = var.nameserver

  # VM Behavior
  agent       = 1
  onboot      = true
  boot        = "order=scsi0"
  full_clone  = true

  # Lifecycle
  lifecycle {
    ignore_changes = [
      network,
    ]
  }
}
```

### Module Variables

**File**: `modules/linux-vm/variables.tf`

```hcl
variable "hostname" {
  type        = string
  description = "VM hostname"
}

variable "target_node" {
  type        = string
  description = "Proxmox node to deploy on"
}

variable "template" {
  type        = string
  description = "Cloud-init template to clone"
}

variable "ip_address" {
  type        = string
  description = "Static IP address"
}

variable "cores" {
  type        = number
  default     = 4
  description = "Number of CPU cores"
}

variable "sockets" {
  type        = number
  default     = 1
  description = "Number of CPU sockets"
}

variable "memory" {
  type        = number
  default     = 8192
  description = "RAM in MB"
}

variable "disk_size" {
  type        = string
  default     = "20G"
  description = "OS disk size"
}

variable "storage" {
  type        = string
  default     = "VMDisks"
  description = "Proxmox storage pool"
}

variable "vlan_tag" {
  type        = number
  default     = null
  description = "VLAN tag (null for untagged)"
}

variable "gateway" {
  type        = string
  description = "Network gateway"
}

variable "nameserver" {
  type        = string
  description = "DNS server"
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key for access"
}

variable "ci_user" {
  type        = string
  default     = "hermes-admin"
  description = "Cloud-init username"
}
```

### Module Outputs

**File**: `modules/linux-vm/outputs.tf`

```hcl
output "vm_id" {
  value       = proxmox_vm_qemu.linux_vm.vmid
  description = "Proxmox VM ID"
}

output "vm_name" {
  value       = proxmox_vm_qemu.linux_vm.name
  description = "VM hostname"
}

output "ip_address" {
  value       = var.ip_address
  description = "VM IP address"
}

output "mac_address" {
  value       = proxmox_vm_qemu.linux_vm.network[0].macaddr
  description = "Network MAC address"
}
```

---

## Root Outputs

**File**: `outputs.tf`

```hcl
output "vm_summary" {
  value = {
    for k, v in module.vms : k => {
      vmid       = v.vm_id
      hostname   = v.vm_name
      ip_address = v.ip_address
    }
  }
  description = "Summary of all deployed VMs"
}

output "vm_ips" {
  value = {
    for k, v in module.vms : k => v.ip_address
  }
  description = "IP addresses of all VMs"
}

output "ansible_controller_ip" {
  value       = module.vms["ansible-controller01"].ip_address
  description = "Ansible controller IP for quick access"
}

output "k8s_controller_ips" {
  value = [
    for k, v in module.vms : v.ip_address
    if can(regex("^k8s-controller", k))
  ]
  description = "Kubernetes control plane IPs"
}

output "k8s_worker_ips" {
  value = [
    for k, v in module.vms : v.ip_address
    if can(regex("^k8s-worker", k))
  ]
  description = "Kubernetes worker IPs"
}
```

---

## Deployment Commands

### Full Deployment

```bash
# Initialize providers
terraform init

# Preview all changes
terraform plan

# Apply all changes
terraform apply
```

### Partial Deployment

```bash
# Deploy only Kubernetes workers
terraform apply -target='module.vms["k8s-worker01"]' \
                -target='module.vms["k8s-worker02"]' \
                -target='module.vms["k8s-worker03"]'

# Deploy all VMs matching pattern (use shell loop)
for i in 01 02 03 04 05 06; do
  terraform apply -target="module.vms[\"k8s-worker${i}\"]" -auto-approve
done
```

### View Deployment

```bash
# Show all VM IPs
terraform output vm_ips

# Show specific VM
terraform output -json vm_summary | jq '.["ansible-controller01"]'

# Show K8s controller IPs
terraform output k8s_controller_ips
```

---

## Adding New VM Groups

### Step 1: Add Group Definition

Add to `local.vm_groups` in `main.tf`:

```hcl
# New monitoring stack
monitoring = {
  count         = 1
  starting_ip   = "192.168.40.30"
  starting_node = "node02"
  template      = "tpl-ubuntu-shared-v1"
  cores         = 4
  sockets       = 1
  memory        = 8192
  disk_size     = "50G"
  storage       = "VMDisks"
  vlan_tag      = 40
  gateway       = "192.168.40.1"
  nameserver    = "192.168.91.30"
}
```

### Step 2: Preview Changes

```bash
terraform plan
```

Expected output:
```
module.vms["monitoring01"].proxmox_vm_qemu.linux_vm: Plan to create

Plan: 1 to add, 0 to change, 0 to destroy.
```

### Step 3: Apply

```bash
terraform apply
```

---

## Scaling VM Groups

### Increase Count

Change `count` in vm_groups:

```hcl
k8s-worker = {
  count = 8  # Changed from 6 to 8
  # ...
}
```

```bash
terraform plan
# Shows: 2 to add

terraform apply
# Creates k8s-worker07 and k8s-worker08
```

### Decrease Count

```hcl
k8s-worker = {
  count = 4  # Changed from 6 to 4
  # ...
}
```

```bash
terraform plan
# Shows: 2 to destroy (k8s-worker05, k8s-worker06)

terraform apply
```

**Warning**: Decreasing count destroys highest-numbered VMs. Ensure no critical workloads before reducing.

---

## VLAN Configuration

### VLAN 20 (Infrastructure)

```hcl
vlan_tag   = null           # No tag (native VLAN)
gateway    = "192.168.20.1"
starting_ip = "192.168.20.x"
```

### VLAN 40 (Services)

```hcl
vlan_tag   = 40             # Explicit tag
gateway    = "192.168.40.1"
starting_ip = "192.168.40.x"
```

---

## VM Configuration Details

### UEFI Boot (OVMF)

Required for modern Ubuntu cloud images:

```hcl
bios    = "ovmf"    # UEFI firmware
machine = "q35"     # Modern chipset

efidisk {
  storage           = var.storage
  efitype           = "4m"
  pre_enrolled_keys = true
}
```

### Cloud-init Integration

```hcl
os_type    = "cloud-init"
ipconfig0  = "ip=${var.ip_address}/24,gw=${var.gateway}"
ciuser     = var.ci_user
sshkeys    = var.ssh_public_key
nameserver = var.nameserver
```

**What cloud-init configures**:
- Network (static IP, gateway, DNS)
- User account (ciuser)
- SSH authorized keys
- Hostname (from VM name)

---

## Troubleshooting

### VM Won't Boot

**Symptom**: VM starts but hangs before cloud-init

**Cause**: UEFI/BIOS mismatch between template and Terraform config

**Fix**: Ensure template and Terraform both use OVMF:
```hcl
bios = "ovmf"
```

### Clone Failed

**Symptom**: `clone operation failed`

**Causes**:
- Template doesn't exist on target node
- Insufficient storage space
- Template locked

**Diagnosis**:
```bash
# Verify template exists
ssh root@node03 "qm list | grep template"

# Check storage space
ssh root@node03 "pvesm status"
```

### Network Unreachable

**Symptom**: VM boots but can't ping gateway

**Causes**:
- Wrong VLAN tag
- Bridge not VLAN-aware
- Wrong gateway IP

**Diagnosis**:
```bash
# Check VM network config in Proxmox
qm config <vmid> | grep net

# Verify cloud-init config
qm cloudinit dump <vmid> network
```

### IP Already in Use

**Symptom**: `duplicate IP detected`

**Fix**: Check IP allocation and update `starting_ip` or existing infrastructure

---

## What's Next?

- **[Cloud-Init Templates](Cloud-Init-Templates)** - Create templates
- **[LXC Containers](LXC-Containers)** - Container deployment
- **[Ansible-Basics](Ansible-Basics)** - Post-deployment configuration

---

*Terraform makes 17 VMs as easy to manage as one.*
