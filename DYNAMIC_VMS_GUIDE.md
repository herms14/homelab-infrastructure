# Dynamic VM Deployment Guide

## Overview

The configuration now supports creating multiple VMs with auto-incrementing hostnames and IP addresses.

## How It Works

### Example Configuration

```hcl
vm_groups = {
  aks-masternode = {
    count       = 3
    starting_ip = "192.168.20.10"
    # ... other settings
  }
}
```

**Creates:**
- `aks-masternode01` → 192.168.20.10
- `aks-masternode02` → 192.168.20.11
- `aks-masternode03` → 192.168.20.12

## Adding VM Groups

Edit `main.tf` and modify the `vm_groups` block:

```hcl
locals {
  vm_groups = {
    # Group 1: AKS Master Nodes
    aks-masternode = {
      count         = 3
      starting_ip   = "192.168.20.10"
      template      = "tpl-ubuntu-24.04-cloudinit-v3"
      cores         = 2
      sockets       = 1
      memory        = 4096
      disk_size     = "50G"
      storage       = "local-lvm"
      vlan_tag      = null  # null = no VLAN
    }

    # Group 2: AKS Worker Nodes
    aks-workernode = {
      count         = 5
      starting_ip   = "192.168.20.20"
      template      = "tpl-ubuntu-24.04-cloudinit-v3"
      cores         = 4
      sockets       = 1
      memory        = 8192
      disk_size     = "100G"
      storage       = "Synology-VMDisks"
      vlan_tag      = 20  # VLAN 20
    }

    # Group 3: Database Servers
    db-server = {
      count         = 2
      starting_ip   = "192.168.20.30"
      template      = "tpl-ubuntu-24.04-cloudinit-v3"
      cores         = 4
      sockets       = 1
      memory        = 16384
      disk_size     = "200G"
      storage       = "Synology-VMDisks"
      vlan_tag      = 30
    }
  }
}
```

## Configuration Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `count` | Number of VMs to create | `3` |
| `starting_ip` | First VM's IP address | `"192.168.20.10"` |
| `template` | Template name in Proxmox | `"tpl-ubuntu-24.04-cloudinit-v3"` |
| `cores` | CPU cores per VM | `2` |
| `sockets` | CPU sockets per VM | `1` |
| `memory` | RAM in MB | `4096` (4GB) |
| `disk_size` | Disk size | `"50G"` |
| `storage` | Storage pool | `"local-lvm"` or `"Synology-VMDisks"` |
| `vlan_tag` | VLAN tag | `20` or `null` for no VLAN |

## Examples

### Example 1: Kubernetes Cluster

```hcl
vm_groups = {
  k8s-master = {
    count       = 3
    starting_ip = "192.168.20.10"
    cores       = 2
    memory      = 4096
    disk_size   = "50G"
    storage     = "local-lvm"
    template    = "tpl-ubuntu-24.04-cloudinit-v3"
    vlan_tag    = 20
  }

  k8s-worker = {
    count       = 5
    starting_ip = "192.168.20.20"
    cores       = 4
    memory      = 8192
    disk_size   = "100G"
    storage     = "Synology-VMDisks"
    template    = "tpl-ubuntu-24.04-cloudinit-v3"
    vlan_tag    = 20
  }
}
```

**Creates:**
- k8s-master01 (192.168.20.10)
- k8s-master02 (192.168.20.11)
- k8s-master03 (192.168.20.12)
- k8s-worker01 (192.168.20.20)
- k8s-worker02 (192.168.20.21)
- k8s-worker03 (192.168.20.22)
- k8s-worker04 (192.168.20.23)
- k8s-worker05 (192.168.20.24)

### Example 2: Docker Swarm

```hcl
vm_groups = {
  swarm-manager = {
    count       = 3
    starting_ip = "192.168.20.50"
    cores       = 2
    memory      = 4096
    disk_size   = "40G"
    storage     = "local-lvm"
    template    = "tpl-ubuntu-24.04-cloudinit-v3"
    vlan_tag    = null
  }

  swarm-worker = {
    count       = 7
    starting_ip = "192.168.20.60"
    cores       = 4
    memory      = 8192
    disk_size   = "80G"
    storage     = "local-lvm"
    template    = "tpl-ubuntu-24.04-cloudinit-v3"
    vlan_tag    = null
  }
}
```

### Example 3: Web Application Stack

```hcl
vm_groups = {
  web = {
    count       = 3
    starting_ip = "192.168.20.10"
    cores       = 2
    memory      = 4096
    disk_size   = "30G"
    storage     = "local-lvm"
    template    = "tpl-ubuntu-24.04-cloudinit-v3"
    vlan_tag    = 20  # DMZ
  }

  app = {
    count       = 3
    starting_ip = "192.168.30.10"
    cores       = 4
    memory      = 8192
    disk_size   = "50G"
    storage     = "local-lvm"
    template    = "tpl-ubuntu-24.04-cloudinit-v3"
    vlan_tag    = 30  # Application tier
  }

  db = {
    count       = 2
    starting_ip = "192.168.40.10"
    cores       = 4
    memory      = 16384
    disk_size   = "200G"
    storage     = "Synology-VMDisks"
    template    = "tpl-ubuntu-24.04-cloudinit-v3"
    vlan_tag    = 40  # Database tier
  }
}
```

## Viewing Created VMs

After deploying, check the outputs:

```bash
terraform output vm_summary
terraform output vm_ips
```

Example output:
```
vm_ips = {
  "aks-masternode01" = "192.168.20.10"
  "aks-masternode02" = "192.168.20.11"
  "aks-masternode03" = "192.168.20.12"
}
```

## Naming Convention

- VM names are automatically padded with zeros: `01`, `02`, `03`, etc.
- Format: `{prefix}{number}`
- Examples:
  - 1 VM: `web01`
  - 10 VMs: `web01` to `web10`
  - 100 VMs: `web001` to `web100`

## IP Address Calculation

IPs are automatically calculated from `starting_ip`:
- `starting_ip = "192.168.20.10"`
- VM 1: 192.168.20.10
- VM 2: 192.168.20.11
- VM 3: 192.168.20.12
- etc.

**Note:** Make sure your starting IP leaves enough room for all VMs!

## Tips

### Tip 1: Plan Before Applying
```bash
terraform plan
```
Review what will be created before deploying.

### Tip 2: Deploy One Group at a Time
Comment out other groups initially, test one group, then add more:

```hcl
vm_groups = {
  test-vm = {
    count = 1
    # ... config
  }
  # other-vm = {  # Commented out for now
  #   count = 3
  #   # ... config
  # }
}
```

### Tip 3: Use Different Storage for Different Tiers
- Fast local storage for app servers
- Shared storage (Synology) for databases

### Tip 4: Group by Function
Group VMs by their role:
- `k8s-master`, `k8s-worker`
- `web`, `app`, `db`
- `docker-manager`, `docker-worker`

## Modifying Existing Deployments

### Adding More VMs to a Group

Change `count`:
```hcl
aks-masternode = {
  count = 5  # Was 3, now 5
  # ... rest of config
}
```

Terraform will add `aks-masternode04` and `aks-masternode05`.

### Removing VMs

Decrease `count`:
```hcl
aks-masternode = {
  count = 2  # Was 3
  # ... rest of config
}
```

**Warning:** Terraform will destroy the highest numbered VMs!

### Destroying Specific Group

Comment out the group:
```hcl
# aks-masternode = {
#   count = 3
#   # ... config
# }
```

Then run `terraform apply` - it will destroy those VMs.

## Common Patterns

### Pattern 1: HA Cluster (3 masters)
```hcl
cluster-master = { count = 3, ... }
```

### Pattern 2: Scaling Workers
```hcl
cluster-worker = { count = 10, ... }  # Easy to change to 15, 20, etc.
```

### Pattern 3: Testing Environment
```hcl
dev-web = { count = 1, memory = 2048, ... }
dev-db  = { count = 1, memory = 4096, ... }
```

### Pattern 4: Production Environment
```hcl
prod-web = { count = 3, memory = 8192, ... }
prod-app = { count = 5, memory = 16384, ... }
prod-db  = { count = 2, memory = 32768, ... }
```

## Troubleshooting

### Issue: IP Conflict
**Problem:** Starting IP overlaps with existing VMs

**Solution:** Choose a different starting IP range
```hcl
starting_ip = "192.168.20.100"  # Start from .100 instead
```

### Issue: Not Enough IPs
**Problem:** Count too high for subnet

**Solution:** Use a lower count or different subnet
```hcl
count = 10  # Make sure .10 to .19 are free
```

### Issue: Template Not Found
**Problem:** Template name doesn't exist

**Solution:** Check template name in Proxmox or create it
```hcl
template = "tpl-ubuntu-24.04-cloudinit-v3"  # Verify this exists
```
