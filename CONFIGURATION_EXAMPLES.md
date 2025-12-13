# Configuration Examples

## Overview

This guide shows how to configure VMs with different storage pools and VLAN configurations.

## Available Storage Pools

- `local-lvm` - Local LVM storage (fast, local to node)
- `Synology-VMDisks` - Synology NAS storage (shared, network storage)

## Available VLANs

Configure in `terraform.tfvars`:
- VLAN 20 (default): 192.168.20.0/24
- VLAN 30: 192.168.30.0/24 (example)
- No VLAN (-1): Untagged traffic

---

## Quick Examples

### Example 1: Local Storage + Default VLAN

```hcl
module "web_server" {
  source = "./modules/linux-vm"

  vm_name       = "web-server-01"
  target_node   = var.default_node
  template_name = "ubuntu-cloud-template"

  cores     = 2
  memory    = 4096
  disk_size = "32G"

  # Storage
  storage = "local-lvm"

  # Network - Uses default VLAN 20
  network_bridge = "vmbr0"
  vlan_tag       = var.default_vlan
  ip_address     = "192.168.20.10"
  subnet_mask    = 24
  gateway        = var.default_gateway
  nameserver     = var.default_nameserver

  ci_user     = "admin"
  ci_password = "SecurePass123!"
  ssh_keys    = ""

  onboot             = true
  qemu_agent_enabled = true
}
```

### Example 2: Synology Storage + Default VLAN

```hcl
module "database_server" {
  source = "./modules/linux-vm"

  vm_name       = "db-server-01"
  target_node   = var.default_node
  template_name = "ubuntu-cloud-template"

  cores     = 4
  memory    = 8192
  disk_size = "100G"

  # Storage - Using Synology NAS
  storage = "Synology-VMDisks"

  # Network - VLAN 20
  network_bridge = "vmbr0"
  vlan_tag       = 20
  ip_address     = "192.168.20.20"
  subnet_mask    = 24
  gateway        = var.default_gateway
  nameserver     = var.default_nameserver

  ci_user     = "admin"
  ci_password = "SecurePass123!"
  ssh_keys    = ""

  onboot             = true
  qemu_agent_enabled = true
}
```

### Example 3: Local Storage + Custom VLAN

```hcl
module "app_server" {
  source = "./modules/linux-vm"

  vm_name       = "app-server-01"
  target_node   = var.default_node
  template_name = "ubuntu-cloud-template"

  cores     = 2
  memory    = 4096
  disk_size = "50G"

  # Storage
  storage = "local-lvm"

  # Network - Custom VLAN 30
  network_bridge = "vmbr0"
  vlan_tag       = 30
  ip_address     = "192.168.30.10"
  subnet_mask    = 24
  gateway        = "192.168.30.1"
  nameserver     = "192.168.30.1"

  ci_user     = "admin"
  ci_password = "SecurePass123!"
  ssh_keys    = ""

  onboot             = true
  qemu_agent_enabled = true
}
```

### Example 4: Synology Storage + No VLAN

```hcl
module "management_vm" {
  source = "./modules/linux-vm"

  vm_name       = "mgmt-vm-01"
  target_node   = var.default_node
  template_name = "ubuntu-cloud-template"

  cores     = 1
  memory    = 2048
  disk_size = "20G"

  # Storage - Synology
  storage = "Synology-VMDisks"

  # Network - No VLAN (untagged)
  network_bridge = "vmbr0"
  vlan_tag       = -1
  ip_address     = "192.168.1.100"
  subnet_mask    = 24
  gateway        = "192.168.1.1"
  nameserver     = "192.168.1.1"

  ci_user     = "admin"
  ci_password = "SecurePass123!"
  ssh_keys    = ""

  onboot             = true
  qemu_agent_enabled = true
}
```

---

## Configuration Matrix

| Storage       | VLAN | Use Case                    | Network       |
|---------------|------|-----------------------------|---------------|
| local-lvm     | 20   | Fast local VMs              | 192.168.20.x  |
| Synology-VMDisks | 20   | Shared storage VMs          | 192.168.20.x  |
| local-lvm     | 30   | Isolated app servers        | 192.168.30.x  |
| Synology-VMDisks | 30   | Shared isolated VMs         | 192.168.30.x  |
| local-lvm     | -1   | Management/untagged         | 192.168.1.x   |
| Synology-VMDisks | -1   | Shared management           | 192.168.1.x   |

---

## Default Values

Edit `terraform.tfvars` to change defaults:

```hcl
# Infrastructure Defaults
default_storage    = "local-lvm"        # or "Synology-VMDisks"
default_node       = "node01"
default_vlan       = 20                 # -1 for no VLAN
default_gateway    = "192.168.20.1"
default_nameserver = "192.168.20.1"
```

---

## Common Patterns

### Pattern 1: Multiple VMs on Same VLAN

```hcl
# Web servers on VLAN 20
module "web1" {
  source = "./modules/linux-vm"
  vm_name    = "web-01"
  storage    = "local-lvm"
  vlan_tag   = 20
  ip_address = "192.168.20.10"
  # ... other config
}

module "web2" {
  source = "./modules/linux-vm"
  vm_name    = "web-02"
  storage    = "local-lvm"
  vlan_tag   = 20
  ip_address = "192.168.20.11"
  # ... other config
}
```

### Pattern 2: Mix of Storage Types

```hcl
# Fast local storage for web tier
module "web" {
  source  = "./modules/linux-vm"
  vm_name = "web-01"
  storage = "local-lvm"
  # ... config
}

# Synology for database (redundancy)
module "db" {
  source  = "./modules/linux-vm"
  vm_name = "db-01"
  storage = "Synology-VMDisks"
  # ... config
}
```

### Pattern 3: Multi-Tier Application

```hcl
# Web tier - VLAN 20 (DMZ)
module "web" {
  source  = "./modules/linux-vm"
  vm_name = "web-01"
  storage = "local-lvm"
  vlan_tag   = 20
  ip_address = "192.168.20.10"
  # ... config
}

# App tier - VLAN 30 (Application)
module "app" {
  source  = "./modules/linux-vm"
  vm_name = "app-01"
  storage = "local-lvm"
  vlan_tag   = 30
  ip_address = "192.168.30.10"
  # ... config
}

# DB tier - VLAN 40 (Database)
module "db" {
  source  = "./modules/linux-vm"
  vm_name = "db-01"
  storage = "Synology-VMDisks"
  vlan_tag   = 40
  ip_address = "192.168.40.10"
  # ... config
}
```

---

## Troubleshooting

### Storage Not Found
```
Error: storage 'Synology-VMDisks' does not exist
```
**Solution:** Check storage name in Proxmox UI → Datacenter → Storage

### VLAN Issues
```
VM has no network connectivity
```
**Solution:**
- Verify VLAN is configured on your switch
- Check VLAN tag matches network configuration
- Ensure vmbr0 is VLAN-aware in Proxmox

### IP Conflicts
```
VM gets IP but can't communicate
```
**Solution:**
- Check IP isn't already in use
- Verify gateway is correct
- Ensure subnet mask matches your network
