# LXC Containers

> **TL;DR**: LXC containers provide lightweight OS-level virtualization. Use for services that don't need full VM overhead. Deploy via Terraform or Proxmox CLI.

## LXC vs VM

| Aspect | LXC Container | Virtual Machine |
|--------|---------------|-----------------|
| **Kernel** | Shares host kernel | Own kernel |
| **Boot time** | Seconds | 30-60 seconds |
| **Memory overhead** | Minimal | ~256MB+ per VM |
| **Isolation** | Process/namespace | Full hardware |
| **Disk usage** | Smaller | Larger |
| **Use case** | Single-purpose services | Complex/multi-service |

### When to Use LXC

- Single-service deployments (Traefik, nginx, databases)
- Memory-constrained environments
- Fast startup requirements
- Services not requiring custom kernels

### When to Use VM

- Docker/Kubernetes hosts
- Services requiring kernel modules
- Security-critical workloads
- Windows or non-Linux OS

---

## LXC Terraform Configuration

### lxc.tf Structure

```hcl
locals {
  lxc_groups = {
    traefik-lxc = {
      count        = 1
      starting_ip  = "192.168.20.100"
      ostemplate   = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
      unprivileged = true
      cores        = 2
      memory       = 1024
      swap         = 256
      disk_size    = "8G"
      storage      = "local-lvm"
      vlan_tag     = null
      gateway      = "192.168.20.1"
      nameserver   = "192.168.91.30"
      nesting      = false
    }

    docker-lxc = {
      count        = 1
      starting_ip  = "192.168.40.100"
      ostemplate   = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
      unprivileged = false    # Privileged for Docker
      cores        = 4
      memory       = 4096
      swap         = 512
      disk_size    = "20G"
      storage      = "local-lvm"
      vlan_tag     = 40
      gateway      = "192.168.40.1"
      nameserver   = "192.168.91.30"
      nesting      = true     # Required for Docker
    }
  }
}
```

### Parameter Reference

| Parameter | Type | Description |
|-----------|------|-------------|
| `count` | number | Number of containers |
| `starting_ip` | string | First IP (auto-increments) |
| `ostemplate` | string | Container template path |
| `unprivileged` | bool | Run as unprivileged (more secure) |
| `cores` | number | CPU cores |
| `memory` | number | RAM in MB |
| `swap` | number | Swap in MB |
| `disk_size` | string | Root filesystem size |
| `storage` | string | Storage pool |
| `vlan_tag` | number/null | VLAN ID |
| `nesting` | bool | Allow nested containers (Docker) |

---

## LXC Module

### Module Structure

```
modules/lxc/
├── main.tf
├── variables.tf
└── outputs.tf
```

### Main Resource

**File**: `modules/lxc/main.tf`

```hcl
resource "proxmox_lxc" "container" {
  hostname     = var.hostname
  target_node  = var.target_node
  ostemplate   = var.ostemplate
  unprivileged = var.unprivileged
  vmid         = var.vmid

  # Resources
  cores  = var.cores
  memory = var.memory
  swap   = var.swap

  # Root filesystem
  rootfs {
    storage = var.storage
    size    = var.disk_size
  }

  # Network
  network {
    name   = "eth0"
    bridge = "vmbr0"
    ip     = "${var.ip_address}/24"
    gw     = var.gateway
    tag    = var.vlan_tag
  }

  # SSH Keys
  ssh_public_keys = var.ssh_public_keys

  # DNS
  nameserver = var.nameserver

  # Features
  features {
    nesting = var.nesting
    keyctl  = var.nesting  # Required with nesting
  }

  # Startup
  onboot = true
  start  = true
}
```

### Module Variables

**File**: `modules/lxc/variables.tf`

```hcl
variable "hostname" {
  type = string
}

variable "target_node" {
  type = string
}

variable "vmid" {
  type    = number
  default = null
}

variable "ostemplate" {
  type = string
}

variable "unprivileged" {
  type    = bool
  default = true
}

variable "cores" {
  type    = number
  default = 1
}

variable "memory" {
  type    = number
  default = 512
}

variable "swap" {
  type    = number
  default = 256
}

variable "disk_size" {
  type    = string
  default = "8G"
}

variable "storage" {
  type    = string
  default = "local-lvm"
}

variable "ip_address" {
  type = string
}

variable "gateway" {
  type = string
}

variable "vlan_tag" {
  type    = number
  default = null
}

variable "nameserver" {
  type = string
}

variable "ssh_public_keys" {
  type = string
}

variable "nesting" {
  type    = bool
  default = false
}
```

---

## LXC Templates

### Download Templates

```bash
# SSH to Proxmox node
ssh root@192.168.20.21

# Update template list
pveam update

# List available templates
pveam available | grep ubuntu

# Download Ubuntu 22.04
pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst

# Download Debian 12
pveam download local debian-12-standard_12.2-1_amd64.tar.zst
```

### Verify Templates

```bash
# List downloaded templates
pveam list local

# Output:
local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst
local:vztmpl/debian-12-standard_12.2-1_amd64.tar.zst
```

### Template Reference

Terraform uses format: `storage:vztmpl/template-filename`

| Template | Terraform Value |
|----------|-----------------|
| Ubuntu 22.04 | `local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst` |
| Debian 12 | `local:vztmpl/debian-12-standard_12.2-1_amd64.tar.zst` |

---

## Bind Mounts

### NFS Data via Bind Mount

Containers access NFS data through bind mounts from the host.

**Host prerequisite** (on Proxmox node):
```bash
# NFS mount must exist on host
mount | grep /mnt/nfs/lxcs
# 192.168.20.31:/volume2/Proxmox-LXCs on /mnt/nfs/lxcs type nfs
```

**Container configuration** (`/etc/pve/lxc/<vmid>.conf`):
```
mp0: /mnt/nfs/lxcs/traefik,mp=/app/config
```

### Terraform Bind Mount

```hcl
resource "proxmox_lxc" "container" {
  # ...

  mountpoint {
    key     = "0"
    slot    = 0
    storage = "/mnt/nfs/lxcs/traefik"
    mp      = "/app/config"
    size    = "0"
  }
}
```

### Manual Bind Mount

```bash
# Add mount point to existing container
pct set 100 -mp0 /mnt/nfs/lxcs/traefik,mp=/app/config

# Verify
pct config 100 | grep mp0
```

---

## Container Operations

### Create Container (CLI)

```bash
# Create unprivileged container
pct create 100 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname traefik-lxc01 \
  --storage local-lvm \
  --rootfs local-lvm:8 \
  --cores 2 \
  --memory 1024 \
  --swap 256 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.20.100/24,gw=192.168.20.1 \
  --nameserver 192.168.91.30 \
  --unprivileged 1 \
  --ssh-public-keys /root/.ssh/authorized_keys \
  --onboot 1 \
  --start 1
```

### Start/Stop Container

```bash
# Start
pct start 100

# Stop (graceful)
pct shutdown 100

# Stop (force)
pct stop 100

# Reboot
pct reboot 100
```

### Access Container

```bash
# Enter container shell (as root)
pct enter 100

# Execute command
pct exec 100 -- apt update

# SSH (if configured)
ssh root@192.168.20.100
```

### View Configuration

```bash
# Show container config
pct config 100

# List all containers
pct list
```

---

## Privileged vs Unprivileged

### Unprivileged (Default)

```hcl
unprivileged = true
```

- UID/GID remapped (0 → 100000)
- More secure
- Some operations restricted
- Recommended for most services

### Privileged

```hcl
unprivileged = false
```

- UID 0 is real root
- Less secure
- Required for:
  - Docker (with nesting)
  - NFS server inside container
  - Some mount operations

---

## Docker in LXC

### Configuration Requirements

```hcl
docker-lxc = {
  unprivileged = false    # Must be privileged
  nesting      = true     # Enable container nesting
  # ...
}
```

**Container features** (`/etc/pve/lxc/<vmid>.conf`):
```
features: nesting=1,keyctl=1
```

### Post-Creation Setup

```bash
# Enter container
pct enter 100

# Install Docker
apt update
apt install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verify
docker run hello-world
```

---

## Terraform Deployment

### Deploy LXC Containers

```bash
# Plan LXC deployment
terraform plan -target=module.lxc

# Apply
terraform apply -target=module.lxc
```

### Output Configuration

**outputs.tf**:
```hcl
output "lxc_summary" {
  value = {
    for k, v in module.lxc : k => {
      vmid       = v.vmid
      hostname   = v.hostname
      ip_address = v.ip_address
    }
  }
}

output "lxc_ips" {
  value = {
    for k, v in module.lxc : k => v.ip_address
  }
}
```

---

## Troubleshooting

### Container Won't Start

**Error**: `container failed to start`

**Diagnosis**:
```bash
# Check logs
journalctl -u pve-container@100 -n 50

# Check container status
pct status 100
```

### Permission Denied (Unprivileged)

**Symptom**: File operations fail with permission denied

**Cause**: UID remapping in unprivileged containers

**Fix**: Use privileged container or adjust permissions:
```bash
# On host, shift ownership
chown -R 100000:100000 /mnt/nfs/lxcs/app
```

### Network Not Working

**Symptom**: Container can't reach network

**Diagnosis**:
```bash
# Inside container
ip addr show
ip route show

# Check bridge on host
brctl show vmbr0
```

### Template Not Found

**Error**: `template 'local:vztmpl/...' does not exist`

**Fix**:
```bash
# Download template
pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst

# Verify
pveam list local
```

---

## Best Practices

### Resource Allocation

| Service Type | Cores | Memory | Disk |
|--------------|-------|--------|------|
| Reverse proxy | 1-2 | 512MB-1GB | 4-8GB |
| Database | 2-4 | 2-4GB | 20-50GB |
| Web server | 1-2 | 512MB-1GB | 8GB |
| Docker host | 4+ | 4GB+ | 20GB+ |

### Security

- Use unprivileged containers when possible
- Minimize bind mounts
- Keep containers updated
- Use separate containers per service

### Naming Convention

```
<service>-lxc<number>
```

Examples:
- `traefik-lxc01`
- `nginx-lxc01`
- `postgres-lxc01`

---

## Migration: LXC to VM

If a service outgrows LXC:

1. Backup container configuration
2. Export container data
3. Create VM from template
4. Restore data
5. Reconfigure service

```bash
# Backup container
vzdump 100 --compress zstd --storage Backups

# Note: Full migration requires manual process
# LXC backup cannot be directly restored as VM
```

---

## What's Next?

- **[Ansible-Basics](Ansible-Basics)** - Configure containers with Ansible
- **[Storage Architecture](Storage-Architecture)** - Bind mount setup
- **[Services Overview](Services-Overview)** - Service deployment

---

*LXC: VM functionality with container efficiency.*
