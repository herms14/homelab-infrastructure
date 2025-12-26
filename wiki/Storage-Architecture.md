# Storage Architecture

> **TL;DR**: Dedicated NFS exports for each content type prevent storage conflicts. VM disks on NAS, app data via bind mounts, media via manual NFS mounts.

## Storage Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Storage Architecture                            │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Synology NAS (192.168.20.31)                      │   │
│  │                                                                      │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │   │
│  │  │    VMDisks      │  │      ISOs       │  │      Media          │ │   │
│  │  │ /volume2/       │  │ /volume2/       │  │ /volume2/           │ │   │
│  │  │ ProxmoxCluster- │  │ ProxmoxCluster- │  │ Proxmox-Media       │ │   │
│  │  │ VMDisks         │  │ ISOs            │  │                     │ │   │
│  │  │                 │  │                 │  │ ├── Movies/         │ │   │
│  │  │ Content: Disk   │  │ Content: ISO    │  │ ├── Series/         │ │   │
│  │  │ images          │  │ images          │  │ └── Music/          │ │   │
│  │  │                 │  │                 │  │                     │ │   │
│  │  │ Managed by:     │  │ Managed by:     │  │ Mounted at:         │ │   │
│  │  │ Proxmox         │  │ Proxmox         │  │ /mnt/media (VMs)    │ │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐│   │
│  │  │                    Proxmox-LXCs                                  ││   │
│  │  │            /volume2/Proxmox-LXCs                                ││   │
│  │  │                                                                  ││   │
│  │  │  ├── traefik/     (bind mount → container /app/config)          ││   │
│  │  │  ├── authentik/   (bind mount → container /data)                ││   │
│  │  │  └── [service]/   (per-service directories)                     ││   │
│  │  │                                                                  ││   │
│  │  │  Mounted at: /mnt/nfs/lxcs (on Proxmox nodes)                   ││   │
│  │  └─────────────────────────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Local Storage (Each Node)                         │   │
│  │                                                                      │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                          │   │
│  │  │      local      │  │    local-lvm    │                          │   │
│  │  │ /var/lib/vz/    │  │ LVM thin pool   │                          │   │
│  │  │                 │  │                 │                          │   │
│  │  │ Content: ISO,   │  │ Content: LXC    │                          │   │
│  │  │ vztmpl, backup  │  │ rootfs          │                          │   │
│  │  └─────────────────┘  └─────────────────┘                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Design Principles

### One Export = One Storage Pool

Each NFS export maps to exactly one Proxmox storage pool with a single content type. This prevents:
- Storage state ambiguity (`?` icons in UI)
- Content type conflicts during cloning/migration
- Template detection failures

### Proxmox-Managed vs Manual Mounts

| Storage Type | Management | Use Case |
|--------------|------------|----------|
| **Proxmox Storage** | Automatic via API | VM disks, ISOs, templates |
| **Manual NFS Mount** | fstab entry | App configs, media files |

**Rationale**: Proxmox expects specific content types in its storage pools. Application data and media files don't fit Proxmox's storage model and cause scanning/permission issues if added as Proxmox storage.

---

## Synology NAS Configuration

### NAS Details

| Setting | Value |
|---------|-------|
| **Model** | Synology DS920+ |
| **IP Address** | 192.168.20.31 |
| **Protocol** | NFSv3/NFSv4 |
| **Volume** | /volume2 |

### NFS Exports

Configure in: **Control Panel → Shared Folder → [Folder] → NFS Permissions**

| Export Path | Proxmox Storage ID | Content Type | Squash | Permissions |
|-------------|-------------------|--------------|--------|-------------|
| `/volume2/ProxmoxCluster-VMDisks` | VMDisks | Disk image | no_root_squash | RW |
| `/volume2/ProxmoxCluster-ISOs` | ISOs | ISO image | no_root_squash | RW |
| `/volume2/Proxmox-LXCs` | (manual mount) | App configs | no_root_squash | RW |
| `/volume2/Proxmox-Media` | (manual mount) | Media files | all_squash | RW |

**NFS Permission Settings**:
```
Hostname/IP: 192.168.20.0/24
Privilege: Read/Write
Squash: Map all users to admin (for Media) or No mapping (for VMDisks)
Security: sys
Enable asynchronous: Yes
Allow connections from non-privileged ports: Yes
Allow users to access mounted subfolders: Yes
```

[Screenshot: Synology NFS permission settings]

---

## Proxmox Storage Configuration

### Adding NFS Storage to Proxmox

**Via Web UI**: Datacenter → Storage → Add → NFS

**VMDisks Storage**:
```
ID: VMDisks
Server: 192.168.20.31
Export: /volume2/ProxmoxCluster-VMDisks
Content: Disk image
Nodes: All
Enable: Yes
```

**ISOs Storage**:
```
ID: ISOs
Server: 192.168.20.31
Export: /volume2/ProxmoxCluster-ISOs
Content: ISO image
Nodes: All
Enable: Yes
```

**Via CLI** (on any Proxmox node):
```bash
# Add VMDisks storage
pvesm add nfs VMDisks \
    --server 192.168.20.31 \
    --export /volume2/ProxmoxCluster-VMDisks \
    --content images \
    --nodes node01,node02,node03

# Add ISOs storage
pvesm add nfs ISOs \
    --server 192.168.20.31 \
    --export /volume2/ProxmoxCluster-ISOs \
    --content iso \
    --nodes node01,node02,node03
```

**Parameter reference**:
- `--server`: NFS server IP/hostname
- `--export`: NFS export path
- `--content`: Content type (`images` = disk images, `iso` = ISO files, `vztmpl` = container templates)
- `--nodes`: Comma-separated list of nodes that can access this storage

### Verify Storage Configuration

```bash
# List all storage pools
pvesm status

# Expected output:
Name         Type     Status   Total      Used       Avail
VMDisks      nfs      active   7.2T       2.1T       5.1T
ISOs         nfs      active   7.2T       50G        7.1T
local        dir      active   460G       5G         455G
local-lvm    lvmthin  active   400G       120G       280G
```

```bash
# Show storage configuration
pvesm list VMDisks

# View storage details
cat /etc/pve/storage.cfg
```

---

## Manual NFS Mounts

### Configuring fstab on Proxmox Nodes

Execute on **all Proxmox nodes** (node01, node02, node03):

```bash
# Create mount points
mkdir -p /mnt/nfs/lxcs
mkdir -p /mnt/nfs/media

# Add fstab entries
cat >> /etc/fstab << 'EOF'
192.168.20.31:/volume2/Proxmox-LXCs   /mnt/nfs/lxcs   nfs  defaults,_netdev  0  0
192.168.20.31:/volume2/Proxmox-Media  /mnt/nfs/media  nfs  defaults,_netdev  0  0
EOF

# Mount all filesystems
mount -a

# Verify mounts
df -h | grep /mnt/nfs
```

**fstab options explained**:
- `defaults`: rw, suid, dev, exec, auto, nouser, async
- `_netdev`: Wait for network before mounting (prevents boot hangs)

### Configuring NFS on Docker VMs

Docker host VMs mount media directly for container access.

Execute on docker-vm-media01 (192.168.40.11):

```bash
# Install NFS client
apt update && apt install -y nfs-common

# Create mount point
mkdir -p /mnt/media

# Add fstab entry
echo "192.168.20.31:/volume2/Proxmox-Media  /mnt/media  nfs  defaults,_netdev  0  0" >> /etc/fstab

# Mount
mount -a

# Verify
ls -la /mnt/media/
# Should show: Movies/ Series/ Music/
```

---

## LXC Bind Mount Strategy

For LXC containers requiring persistent storage, use bind mounts from the manual NFS mount.

### Configuration Pattern

1. **Proxmox host** has `/mnt/nfs/lxcs` mounted via NFS
2. **Subdirectory** created for each service: `/mnt/nfs/lxcs/[service-name]/`
3. **Bind mount** configured in container config to map subdirectory into container

### Example: Traefik Container

**On Proxmox host**:
```bash
# Create service directory
mkdir -p /mnt/nfs/lxcs/traefik
```

**Container config** (`/etc/pve/lxc/100.conf`):
```
mp0: /mnt/nfs/lxcs/traefik,mp=/app/config
```

**Result**: Container sees `/app/config` which maps to NAS at `/volume2/Proxmox-LXCs/traefik/`

### Adding Bind Mount via CLI

```bash
# Add mount point to existing container
pct set 100 -mp0 /mnt/nfs/lxcs/traefik,mp=/app/config

# Verify configuration
pct config 100 | grep mp0
```

---

## Docker Volume Configuration

Docker services use bind mounts to host paths, which connect to NFS mounts.

### Arr Stack Example

**docker-compose.yml** excerpt:
```yaml
services:
  jellyfin:
    volumes:
      - /opt/arr-stack/jellyfin:/config        # Local: app config
      - /mnt/media/Movies:/movies:ro           # NFS: media files
      - /mnt/media/Series:/series:ro
      - /mnt/media/Music:/music:ro

  radarr:
    volumes:
      - /opt/arr-stack/radarr:/config          # Local: app config
      - /mnt/media/Movies:/movies              # NFS: read/write for downloads
      - /mnt/media/Downloads:/downloads
```

**Path mapping**:
```
Docker Container          →  Docker Host VM         →  NFS Server
/movies                   →  /mnt/media/Movies      →  192.168.20.31:/volume2/Proxmox-Media/Movies
/config                   →  /opt/arr-stack/[app]   →  Local disk
```

---

## Storage Performance Considerations

### NFS Tuning

For high-throughput scenarios (media streaming, VM disk I/O):

**Client-side mount options**:
```
192.168.20.31:/volume2/Proxmox-Media  /mnt/media  nfs  rsize=1048576,wsize=1048576,hard,intr,_netdev  0  0
```

**Option reference**:
- `rsize=1048576`: 1MB read block size
- `wsize=1048576`: 1MB write block size
- `hard`: Retry indefinitely on NFS timeout (prevents data corruption)
- `intr`: Allow interrupt of NFS operations (Ctrl+C)

### Storage Placement Guidelines

| Workload | Recommended Storage | Rationale |
|----------|---------------------|-----------|
| VM OS disks | VMDisks (NFS) | Enables live migration, snapshots |
| LXC rootfs | local-lvm | Lower latency for container operations |
| App configs (small, frequent writes) | local or NFS | Either works; NFS for persistence |
| Media files (large, sequential) | NFS | Centralized, shared access |
| Databases | local-lvm or dedicated storage | IOPS-sensitive workloads |

---

## Storage Operations

### Check NFS Mount Status

```bash
# View all NFS mounts
mount | grep nfs

# Show mount statistics
nfsstat -m

# Test NFS connectivity
showmount -e 192.168.20.31
```

### Troubleshooting Stale Mounts

```bash
# Force unmount stale NFS
umount -f /mnt/nfs/media

# Lazy unmount (completes when no longer in use)
umount -l /mnt/nfs/media

# Remount
mount -a
```

### Proxmox Storage Commands

```bash
# List content in storage pool
pvesm list VMDisks

# Show free space
pvesm status

# Scan storage for changes
pvesm scan nfs VMDisks

# Allocate disk for VM
pvesm alloc VMDisks 100 vm-100-disk-0.raw 20G
```

### Disk Operations

```bash
# List disks attached to VM
qm config 100 | grep -E "(scsi|virtio|ide|sata)"

# Resize VM disk
qm resize 100 scsi0 +10G

# Move disk between storages
qm move_disk 100 scsi0 VMDisks
```

---

## Backup Storage

### Proxmox Backup Configuration

Backups require storage with `backup` content type:

```bash
# Add backup storage (example: NFS)
pvesm add nfs Backups \
    --server 192.168.20.31 \
    --export /volume2/ProxmoxCluster-Backups \
    --content backup \
    --nodes node01,node02,node03
```

### Backup Commands

```bash
# Create VM backup
vzdump 100 --storage Backups --mode snapshot --compress zstd

# List backups
pvesm list Backups --content backup

# Restore VM from backup
qmrestore /mnt/pve/Backups/dump/vzdump-qemu-100-2025_12_19-02_00_00.vma.zst 100
```

---

## Troubleshooting

### Storage Shows Inactive

**Symptom**: Storage appears red/offline in Proxmox UI

**Diagnosis**:
```bash
# Check NFS server reachability
ping 192.168.20.31

# Test NFS export availability
showmount -e 192.168.20.31

# Check mount status
mount | grep VMDisks

# View Proxmox storage logs
journalctl -u pve-cluster | tail -50
```

**Resolution**:
```bash
# Remount NFS
umount /mnt/pve/VMDisks
mount -a

# Or restart storage daemon
systemctl restart pvedaemon
```

### Question Mark (?) on Storage

**Cause**: Proxmox can't determine content type, usually due to mixed content or permission issues

**Resolution**:
1. Ensure storage has single content type
2. Check NFS permissions (no_root_squash for VM disks)
3. Verify storage exists on all configured nodes

### Permission Denied on NFS

**Symptom**: `Permission denied` when accessing NFS files

**Diagnosis**:
```bash
# Check effective UID/GID
id

# Check NFS export permissions on server
# (via Synology UI or /etc/exports on Linux NFS server)
```

**Resolution**: Configure NFS squash settings appropriately:
- `no_root_squash`: Root access needed (VM disks)
- `all_squash`: Map all to single user (media files)

---

## Storage Reference

### Content Type Mapping

| Content Type | Description | File Types |
|--------------|-------------|------------|
| `images` | Disk images | .raw, .qcow2, .vmdk |
| `iso` | ISO images | .iso |
| `vztmpl` | Container templates | .tar.gz, .tar.xz |
| `backup` | Backup files | .vma, .tar |
| `rootdir` | Container root dirs | directories |

### Storage Path Reference

| Storage | Proxmox Mount Path |
|---------|-------------------|
| VMDisks | /mnt/pve/VMDisks |
| ISOs | /mnt/pve/ISOs |
| local | /var/lib/vz |
| local-lvm | (LVM thin pool, no direct path) |

---

## What's Next?

- **[DNS Configuration](DNS-Configuration)** - Internal DNS with OPNsense
- **[SSL Certificates](SSL-Certificates)** - Let's Encrypt automation
- **[Proxmox Cluster](Proxmox-Cluster)** - Cluster management

---

*Proper storage architecture prevents 90% of infrastructure headaches.*
