# LXC Container Deployment Guide

## Overview

The LXC module allows you to deploy Linux containers on Proxmox with auto-incrementing hostnames and IP addresses, similar to the VM deployment.

**Note:** By default, VMs deploy to `node01` and LXC containers deploy to `node02`.

## Key Differences: LXC vs VMs

| Feature | LXC | VM |
|---------|-----|-----|
| Boot Time | Seconds | Minutes |
| Resource Usage | Lower | Higher |
| Overhead | Minimal | More |
| Isolation | Shared kernel | Full isolation |
| Use Case | Services, web apps | Full OS, Windows |

## Prerequisites

### 1. Download LXC Templates

First, download templates to your Proxmox node:

```bash
# SSH into your Proxmox node
pveam update
pveam available | grep ubuntu

# Download templates (examples)
pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
pveam download local debian-12-standard_12.2-1_amd64.tar.zst
```

### 2. Verify Template Path

Templates are stored in `/var/lib/vz/template/cache/` and referenced as:
```
local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst
```

## Basic Configuration

### Example 1: Simple Web Servers

```hcl
lxc_groups = {
  web = {
    count        = 3
    starting_ip  = "192.168.20.50"
    ostemplate   = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
    unprivileged = true
    cores        = 1
    memory       = 512
    swap         = 256
    disk_size    = "8G"
    storage      = "local-lvm"
    vlan_tag     = null
    gateway      = "192.168.20.1"
    nameserver   = "192.168.20.1"
    nesting      = false
  }
}
```

**Creates:**
- web01 → 192.168.20.50
- web02 → 192.168.20.51
- web03 → 192.168.20.52

### Example 2: Docker Hosts

**Important:** For Docker in LXC, you need:
- `unprivileged = false` (privileged container)
- `nesting = true` (enable container nesting)

```hcl
lxc_groups = {
  docker-host = {
    count        = 2
    starting_ip  = "192.168.20.60"
    ostemplate   = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
    unprivileged = false   # Required for Docker
    cores        = 2
    memory       = 2048
    swap         = 512
    disk_size    = "20G"
    storage      = "Synology-VMDisks"
    vlan_tag     = null
    gateway      = "192.168.20.1"
    nameserver   = "192.168.20.1"
    nesting      = true    # Required for Docker
  }
}
```

### Example 3: Database Containers

```hcl
lxc_groups = {
  postgres = {
    count        = 2
    starting_ip  = "192.168.40.50"
    ostemplate   = "local:vztmpl/debian-12-standard_12.2-1_amd64.tar.zst"
    unprivileged = true
    cores        = 2
    memory       = 4096
    swap         = 1024
    disk_size    = "50G"
    storage      = "Synology-VMDisks"
    vlan_tag     = 40
    gateway      = "192.168.40.1"
    nameserver   = "192.168.40.1"
    nesting      = false
  }
}
```

## Configuration Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `count` | Number of containers | `3` |
| `starting_ip` | First container's IP | `"192.168.20.50"` |
| `ostemplate` | Template path | `"local:vztmpl/ubuntu-22.04..."` |
| `unprivileged` | Unprivileged container | `true` |
| `cores` | CPU cores | `1` |
| `memory` | RAM in MB | `512` |
| `swap` | Swap in MB | `256` |
| `disk_size` | Root FS size | `"8G"` |
| `storage` | Storage pool | `"local-lvm"` |
| `vlan_tag` | VLAN tag | `20` or `null` |
| `gateway` | Network gateway | `"192.168.20.1"` |
| `nameserver` | DNS server | `"192.168.20.1"` |
| `nesting` | Enable nesting | `false` |

## Common Use Cases

### 1. Lightweight Services Stack

```hcl
lxc_groups = {
  nginx = {
    count = 2
    starting_ip = "192.168.20.70"
    cores = 1
    memory = 512
    # ... other config
  }

  nodejs = {
    count = 3
    starting_ip = "192.168.20.80"
    cores = 2
    memory = 1024
    # ... other config
  }

  redis = {
    count = 1
    starting_ip = "192.168.20.90"
    cores = 1
    memory = 512
    # ... other config
  }
}
```

### 2. Development Environments

```hcl
lxc_groups = {
  dev-env = {
    count = 5
    starting_ip = "192.168.20.100"
    ostemplate = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
    cores = 1
    memory = 1024
    disk_size = "10G"
    # ... other config
  }
}
```

### 3. Monitoring Stack

```hcl
lxc_groups = {
  prometheus = {
    count = 1
    starting_ip = "192.168.20.110"
    cores = 2
    memory = 2048
    disk_size = "20G"
    # ... other config
  }

  grafana = {
    count = 1
    starting_ip = "192.168.20.111"
    cores = 1
    memory = 1024
    # ... other config
  }
}
```

## Using the Configuration

### 1. Copy Example to Main Configuration

```bash
# Copy the lxc-example.tf content to a new file
cp lxc-example.tf lxc.tf

# Edit and uncomment the configuration
# Remove the /* and */ comment markers
```

### 2. Customize for Your Needs

Edit the `lxc_groups` block in `lxc.tf` with your desired containers.

### 3. Plan and Apply

```bash
terraform plan
terraform apply
```

### 4. View Created Containers

```bash
terraform output lxc_summary
terraform output lxc_ips
```

## Privileged vs Unprivileged Containers

### Unprivileged (Recommended)

- **Use for:** Most workloads
- **Pros:** More secure, better isolation
- **Cons:** Some features may not work
- **Set:** `unprivileged = true`

### Privileged

- **Use for:** Docker, systemd services, special features
- **Pros:** Full feature access
- **Cons:** Less secure
- **Set:** `unprivileged = false`

## Available Templates

Common templates you can download:

```bash
# Ubuntu
ubuntu-22.04-standard_22.04-1_amd64.tar.zst
ubuntu-20.04-standard_20.04-1_amd64.tar.zst

# Debian
debian-12-standard_12.2-1_amd64.tar.zst
debian-11-standard_11.7-1_amd64.tar.zst

# Alpine (very lightweight)
alpine-3.18-default_20230607_amd64.tar.xz

# CentOS/Rocky
rockylinux-9-default_20221109_amd64.tar.xz
```

## Storage Recommendations

| Storage Type | Use Case |
|--------------|----------|
| `local-lvm` | Fast, local containers |
| `Synology-VMDisks` | Shared storage, backups |
| `local` | Small containers, testing |

## Networking Tips

### VLAN Configuration

- **No VLAN (native):** `vlan_tag = null`
- **Specific VLAN:** `vlan_tag = 20`

### IP Ranges

Ensure your IP ranges don't overlap:
- VMs: 192.168.20.10-49
- LXCs: 192.168.20.50-99

## Post-Creation Steps

### Access Container

```bash
# From Proxmox host
pct enter <container-id>

# Via SSH
ssh hermes-admin@<container-ip>
```

### Install Docker (if nesting enabled)

```bash
pct enter <container-id>
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
```

## Troubleshooting

### Issue: Template Not Found

**Error:** `template 'local:vztmpl/...' does not exist`

**Solution:**
```bash
# SSH to Proxmox
pveam update
pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
```

### Issue: Cannot Start Container

**Error:** Container fails to start

**Solution:** Check if unprivileged is set correctly for your use case

### Issue: Docker Won't Run

**Solution:** Ensure:
- `unprivileged = false`
- `nesting = true`

## Combining VMs and LXCs

You can deploy both VMs and LXCs in the same configuration:

```hcl
# main.tf - VMs
locals {
  vm_groups = { ... }
}

# lxc.tf - Containers
locals {
  lxc_groups = { ... }
}
```

## Resource Sizing Guide

| Workload | Cores | Memory | Disk |
|----------|-------|--------|------|
| Web server | 1 | 512MB | 8G |
| App server | 2 | 1-2GB | 10-20G |
| Database | 2-4 | 2-4GB | 20-50G |
| Docker host | 2-4 | 2-4GB | 20-50G |
| Cache (Redis) | 1 | 512MB-1GB | 8G |

## Best Practices

1. **Use unprivileged containers** when possible for security
2. **Enable nesting** only when needed (Docker, systemd)
3. **Separate storage** for data and OS
4. **Use VLANs** to isolate different workloads
5. **Start small** with resources, scale up as needed
6. **Use shared storage** for containers that need backup/migration
