# Proxmox Cluster

> **TL;DR**: Three physical servers running Proxmox VE 9.1.2 form a high-availability cluster for hosting all VMs and containers.

## What is Proxmox?

**Proxmox VE** (Virtual Environment) is a free, open-source platform for running virtual machines and containers. Think of it as the foundation layer - it turns your physical servers into hosts that can run many "virtual computers" inside them.

### Why Proxmox?

| Feature | Benefit |
|---------|---------|
| **Free & Open Source** | No licensing costs, even for enterprise features |
| **Web Interface** | Manage everything from a browser |
| **Clustering** | Multiple nodes work together as one system |
| **High Availability** | VMs automatically restart on another node if one fails |
| **KVM & LXC** | Run full VMs and lightweight containers |
| **ZFS Support** | Built-in enterprise storage features |

---

## Our Cluster Configuration

### Physical Nodes

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Proxmox VE Cluster                            │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │     node01       │  │     node02       │  │     node03       │  │
│  │  192.168.20.20   │  │  192.168.20.21   │  │  192.168.20.22   │  │
│  │                  │  │                  │  │                  │  │
│  │  Primary Host    │  │  App Services    │  │  Kubernetes      │  │
│  │  Ansible Ctrl    │  │  Docker VMs      │  │  9 K8s Nodes     │  │
│  │                  │  │  Traefik         │  │                  │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                      │
│                    ┌──────────────────────┐                         │
│                    │    Synology NAS      │                         │
│                    │   192.168.20.31      │                         │
│                    │   Shared Storage     │                         │
│                    └──────────────────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Node Specifications

| Node | CPU | RAM | Local Storage | Role |
|------|-----|-----|---------------|------|
| **node01** | 8 cores | 32 GB | 500 GB NVMe | Primary VM host, Ansible |
| **node02** | 8 cores | 32 GB | 500 GB NVMe | Application services |
| **node03** | 8 cores | 32 GB | 500 GB NVMe | Kubernetes cluster |

### Cluster Resources Summary

| Resource | Total | Used | Available |
|----------|-------|------|-----------|
| **CPU Cores** | 24 physical | ~36 vCPU allocated | Overcommit OK |
| **RAM** | 96 GB | ~72 GB allocated | 24 GB buffer |
| **Local Storage** | 1.5 TB | Varies | OS + cache |
| **NAS Storage** | 8 TB | Growing | Media + VMs |

---

## Accessing the Cluster

### Web Interface

Each node has its own web interface:

| Node | URL | Notes |
|------|-----|-------|
| node01 | https://192.168.20.20:8006 | Direct access |
| node02 | https://192.168.20.21:8006 | Direct access |
| node03 | https://192.168.20.22:8006 | Direct access |
| Cluster | https://proxmox.hrmsmrflrii.xyz | Via Traefik (recommended) |

**Login credentials**: Use your Proxmox root account or PAM authentication.

[Screenshot: Proxmox login page]

### SSH Access

```bash
# Connect to any node
ssh root@192.168.20.20    # node01
ssh root@192.168.20.21    # node02
ssh root@192.168.20.22    # node03
```

---

## Understanding the Web Interface

### Dashboard Overview

When you log in, you'll see:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Datacenter                                                           │
│ ├── node01                                                          │
│ │   ├── 100 (ansible-controller01)                                  │
│ │   └── Templates                                                   │
│ ├── node02                                                          │
│ │   ├── 101 (traefik-vm01)                                         │
│ │   ├── 102 (authentik-vm01)                                       │
│ │   └── ...more VMs                                                 │
│ └── node03                                                          │
│     ├── 200 (k8s-controller01)                                      │
│     ├── 201 (k8s-controller02)                                      │
│     └── ...more K8s nodes                                           │
└─────────────────────────────────────────────────────────────────────┘
```

**Key sections**:
- **Datacenter**: Cluster-wide settings (storage, users, HA)
- **Node**: Individual server settings and local resources
- **VM/CT**: Virtual machine or container settings

[Screenshot: Proxmox dashboard with node tree]

### Important Menus

| Location | What It Shows |
|----------|---------------|
| **Datacenter → Summary** | Cluster health, resource usage |
| **Datacenter → Storage** | All storage pools |
| **Datacenter → Permissions** | Users and API tokens |
| **Node → System → Network** | Network interface configuration |
| **VM → Summary** | VM status, resource usage |
| **VM → Console** | Direct access to VM screen |

---

## Cluster Health Checks

### Check Cluster Status

```bash
# SSH to any node and run:
pvecm status
```

**Healthy output**:
```
Cluster information
-------------------
Name:             proxmox-cluster
Config Version:   3
Transport:        knet
Secure auth:      on

Quorum information
------------------
Date:             Thu Dec 19 2025
Quorum provider:  corosync_votequorum
Nodes:            3
Node ID:          0x00000001
Ring ID:          1.15
Quorate:          Yes      ← All nodes agree

Votequorum information
----------------------
Expected votes:   3
Highest expected: 3
Total votes:      3
Quorum:           2
Flags:            Quorate

Membership information
----------------------
    Nodeid      Votes Name
0x00000001          1 192.168.20.20 (local)
0x00000002          1 192.168.20.21
0x00000003          1 192.168.20.22
```

**What to look for**:
- `Quorate: Yes` - Cluster has majority agreement
- All 3 nodes listed in Membership
- No `NR` (Not Ready) flags

### Check Node Resources

```bash
# View all nodes and their status
pvesh get /cluster/resources --type node
```

**Expected output**:
```
┌────────┬────────────────┬─────────┬───────┬────────┐
│ node   │ status         │ cpu     │ mem   │ uptime │
├────────┼────────────────┼─────────┼───────┼────────┤
│ node01 │ online         │ 0.15    │ 45%   │ 5d 3h  │
│ node02 │ online         │ 0.32    │ 67%   │ 5d 3h  │
│ node03 │ online         │ 0.28    │ 52%   │ 5d 3h  │
└────────┴────────────────┴─────────┴───────┴────────┘
```

### Check Running VMs

```bash
# List all VMs across cluster
qm list
```

---

## Network Configuration

### VLAN-Aware Bridge Setup

**Critical**: All nodes must have VLAN-aware bridge configuration for VMs to work.

**Configuration file**: `/etc/network/interfaces`

```bash
auto lo
iface lo inet loopback

auto nic0
iface nic0 inet manual

auto vmbr0
iface vmbr0 inet static
    address 192.168.20.XX/24    # XX = 20, 21, or 22
    gateway 192.168.20.1
    bridge-ports nic0
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes       # CRITICAL: Enables VLAN tagging
    bridge-vids 2-4094          # CRITICAL: Allowed VLAN range
```

**What each line means**:
- `bridge-ports nic0` - Physical NIC connected to bridge
- `bridge-vlan-aware yes` - Enables VLAN filtering (required!)
- `bridge-vids 2-4094` - Which VLAN IDs are allowed

### Verify VLAN Configuration

```bash
# Check VLAN filtering is active
ip -d link show vmbr0 | grep vlan_filtering
```

**Expected output**:
```
vlan_filtering 1
```

If you see `vlan_filtering 0`, the bridge is NOT VLAN-aware and VMs on VLANs will fail.

### Apply Network Changes

```bash
# Reload network configuration
ifreload -a

# Or reboot for clean state
reboot
```

---

## Storage Configuration

### Proxmox Storage Pools

| Storage ID | Type | Location | Content | Purpose |
|------------|------|----------|---------|---------|
| **VMDisks** | NFS | Synology NAS | Disk images | VM virtual disks |
| **ISOs** | NFS | Synology NAS | ISO images | Installation media |
| **local** | Directory | Each node | ISO, vztmpl | Local templates |
| **local-lvm** | LVM | Each node | Disk images | LXC rootfs |

### View Storage in CLI

```bash
# List all storage pools
pvesm status
```

**Output**:
```
Name         Type     Status   Total      Used       Avail
VMDisks      nfs      active   7.2T       2.1T       5.1T
ISOs         nfs      active   7.2T       50G        7.1T
local        dir      active   460G       5G         455G
local-lvm    lvmthin  active   400G       120G       280G
```

See [Storage Architecture](Storage-Architecture) for detailed storage documentation.

---

## Creating VMs (Manual Method)

While we use Terraform for automation, here's how to create a VM manually:

### Step 1: Upload ISO (if needed)

1. Navigate to: **Datacenter → Storage → ISOs → ISO Images**
2. Click **Upload** or **Download from URL**
3. Select your ISO file

[Screenshot: ISO upload dialog]

### Step 2: Create VM

1. Click **Create VM** button (top right)
2. Fill in the wizard:

**General tab**:
- **Node**: Which server to create VM on
- **VM ID**: Unique number (e.g., 100)
- **Name**: Descriptive name (e.g., `test-vm01`)

**OS tab**:
- **ISO Image**: Select uploaded ISO
- **Type**: Linux or Windows

**System tab**:
- **BIOS**: OVMF (UEFI) for modern OSes
- **Machine**: q35

**Disks tab**:
- **Storage**: VMDisks (NFS)
- **Disk size**: 20 GB minimum

**CPU tab**:
- **Sockets**: 1
- **Cores**: 2-4

**Memory tab**:
- **Memory**: 2048-8192 MB

**Network tab**:
- **Bridge**: vmbr0
- **VLAN Tag**: Leave empty for VLAN 20, enter `40` for VLAN 40

3. Click **Finish**

[Screenshot: Create VM wizard]

### Step 3: Start and Install

1. Select your VM in the tree
2. Click **Start**
3. Click **Console** to see the screen
4. Follow OS installation wizard

---

## Using Cloud-Init Templates

Instead of manual installation, we use **cloud-init templates** for instant VM deployment.

### What is Cloud-Init?

Cloud-init automatically configures VMs on first boot:
- Sets hostname
- Creates user accounts
- Adds SSH keys
- Configures network
- Runs initial commands

### Our Templates

| Template Name | OS | Used For |
|--------------|-----|----------|
| `tpl-ubuntuv24.04-v1` | Ubuntu 24.04 | Ansible controller |
| `tpl-ubuntu-shared-v1` | Ubuntu 24.04 | All other VMs |

### Clone from Template (CLI)

```bash
# Clone template to new VM
qm clone 9000 150 --name my-new-vm --full
```

**What each part means**:
- `qm clone` - QEMU machine clone command
- `9000` - Template VM ID
- `150` - New VM ID
- `--name my-new-vm` - New VM name
- `--full` - Full clone (independent copy)

See [Cloud-Init Templates](Cloud-Init-Templates) for creating templates.

---

## Common Operations

### Start/Stop VMs

```bash
# Start a VM
qm start 100

# Stop a VM (graceful shutdown)
qm shutdown 100

# Force stop (like pulling power)
qm stop 100

# Reboot
qm reboot 100
```

### VM Console Access

```bash
# Open terminal console
qm terminal 100

# Or use noVNC via web interface
```

### View VM Configuration

```bash
# Show VM config
qm config 100
```

### Migrate VM to Another Node

```bash
# Live migration (VM stays running)
qm migrate 100 node02 --online

# Offline migration
qm migrate 100 node02
```

---

## Troubleshooting

### Node Shows Question Mark (?)

**Symptom**: Node appears with `?` icon in web UI

**Cause**: Node lost connection to cluster

**Fix**:
```bash
# Check if node is running
ping 192.168.20.XX

# SSH and check cluster status
ssh root@192.168.20.XX
pvecm status

# Restart cluster services
systemctl restart pve-cluster corosync
```

### VM Won't Start

**Symptom**: `QEMU exited with code 1`

**Common causes**:
1. **VLAN not configured**: Check `bridge-vlan-aware yes` in network config
2. **Storage unavailable**: Verify NFS mount is active
3. **Template mismatch**: UEFI VM with BIOS template

**Diagnosis**:
```bash
# Check VM configuration
qm config 100

# View QEMU errors
journalctl -u pve-qemu-server -n 50
```

### Storage Shows Inactive

**Symptom**: Storage pool shows red/inactive

**Fix**:
```bash
# Check NFS mount
df -h | grep VMDisks

# Remount if needed
mount -a

# Verify Proxmox sees it
pvesm status
```

---

## Backup & High Availability

### Scheduled Backups

Configure in: **Datacenter → Backup**

**Recommended settings**:
- **Schedule**: Daily at 2:00 AM
- **Storage**: Backup-capable storage
- **Mode**: Snapshot (no downtime)
- **Retention**: Keep last 7

### High Availability (HA)

HA automatically restarts VMs on another node if one fails.

**Enable HA**:
1. Go to **Datacenter → HA → Resources**
2. Click **Add**
3. Select VM
4. Set priority and group

**Requirements**:
- 3+ nodes (for quorum)
- Shared storage (NFS/Ceph)
- Fencing configured

---

## Command Reference

| Task | Command |
|------|---------|
| Cluster status | `pvecm status` |
| List all VMs | `qm list` |
| List all containers | `pct list` |
| Start VM | `qm start <vmid>` |
| Stop VM | `qm shutdown <vmid>` |
| VM config | `qm config <vmid>` |
| Storage status | `pvesm status` |
| Node resources | `pvesh get /cluster/resources --type node` |
| Network reload | `ifreload -a` |

---

## What's Next?

- **[Network Architecture](Network-Architecture)** - VLAN setup details
- **[Storage Architecture](Storage-Architecture)** - NFS and storage pools
- **[Cloud-Init Templates](Cloud-Init-Templates)** - Creating templates

---

*Proxmox is the foundation. Everything else runs on top of it.*
