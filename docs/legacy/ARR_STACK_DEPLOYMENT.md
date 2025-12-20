# Arr Media Stack Deployment Guide

This document provides comprehensive documentation for deploying and managing the Arr media stack on docker-vm-media01 using Ansible automation.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Deployment Process](#deployment-process)
5. [Synology NAS Automation](#synology-nas-automation)
6. [Service Reference](#service-reference)
7. [Ansible Playbook Reference](#ansible-playbook-reference)
8. [Configuration Guide](#configuration-guide)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance Commands](#maintenance-commands)
11. [Lessons Learned](#lessons-learned)

---

## Overview

### What Was Deployed

The Arr media stack is a collection of applications for automated media management. This deployment includes:

| Service | Purpose | Port | Web UI |
|---------|---------|------|--------|
| **Jellyfin** | Media server for streaming | 8096 | http://192.168.40.11:8096 |
| **Radarr** | Movie management & automation | 7878 | http://192.168.40.11:7878 |
| **Sonarr** | TV series management & automation | 8989 | http://192.168.40.11:8989 |
| **Lidarr** | Music management & automation | 8686 | http://192.168.40.11:8686 |
| **Prowlarr** | Indexer manager for all *arr apps | 9696 | http://192.168.40.11:9696 |
| **Bazarr** | Subtitle management | 6767 | http://192.168.40.11:6767 |
| **Overseerr** | Media request management (Plex) | 5055 | http://192.168.40.11:5055 |
| **Jellyseerr** | Media request management (Jellyfin) | 5056 | http://192.168.40.11:5056 |
| **Tdarr** | Automated transcoding | 8265 | http://192.168.40.11:8265 |
| **Autobrr** | IRC announce/torrent automation | 7474 | http://192.168.40.11:7474 |

### Deployment Method

- **Infrastructure**: Docker containers via Docker Compose
- **Management**: Ansible automation from ansible-controller01 (192.168.20.30)
- **Target Host**: docker-vm-media01 (192.168.40.11)

---

## Architecture

### Network Diagram

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                   VLAN 40 (Services)                     │
                    │                                                          │
                    │  ┌─────────────────────────────────────────────────┐    │
                    │  │          docker-vm-media01 (192.168.40.11)      │    │
                    │  │                                                  │    │
                    │  │  ┌─────────────────────────────────────────┐    │    │
                    │  │  │         Docker Engine                    │    │    │
                    │  │  │                                          │    │    │
                    │  │  │  ┌──────────┐  ┌──────────┐ ┌────────┐  │    │    │
                    │  │  │  │ Jellyfin │  │ Radarr   │ │ Sonarr │  │    │    │
                    │  │  │  │  :8096   │  │  :7878   │ │ :8989  │  │    │    │
                    │  │  │  └──────────┘  └──────────┘ └────────┘  │    │    │
                    │  │  │                                          │    │    │
                    │  │  │  ┌──────────┐  ┌──────────┐ ┌────────┐  │    │    │
                    │  │  │  │ Prowlarr │  │ Bazarr   │ │ Lidarr │  │    │    │
                    │  │  │  │  :9696   │  │  :6767   │ │ :8686  │  │    │    │
                    │  │  │  └──────────┘  └──────────┘ └────────┘  │    │    │
                    │  │  │                                          │    │    │
                    │  │  │  ┌──────────┐  ┌──────────┐ ┌────────┐  │    │    │
                    │  │  │  │ Overseerr│  │Jellyseerr│ │ Tdarr  │  │    │    │
                    │  │  │  │  :5055   │  │  :5056   │ │ :8265  │  │    │    │
                    │  │  │  └──────────┘  └──────────┘ └────────┘  │    │    │
                    │  │  │                                          │    │    │
                    │  │  │  ┌──────────┐                           │    │    │
                    │  │  │  │ Autobrr  │                           │    │    │
                    │  │  │  │  :7474   │                           │    │    │
                    │  │  │  └──────────┘                           │    │    │
                    │  │  │                                          │    │    │
                    │  │  │  [arr-network - Docker Bridge]          │    │    │
                    │  │  └──────────────────────────────────────────┘    │    │
                    │  │                                                  │    │
                    │  │  Storage:                                        │    │
                    │  │  - /opt/arr-stack (configs)                      │    │
                    │  │  - /mnt/media (NFS mount - WORKING)              │    │
                    │  └─────────────────────────────────────────────────┘    │
                    └─────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────────────────────────┐
                    │                   VLAN 20 (Infrastructure)              │
                    │                                                          │
                    │  ansible-controller01 (192.168.20.30)                   │
                    │  - Manages deployments via Ansible                      │
                    │  - Playbooks in ~/ansible/docker/                       │
                    │                                                          │
                    │  Synology NAS (192.168.20.31)                           │
                    │  - NFS Share: /volume2/Proxmox-Media                    │
                    │  - /Movies, /Series, /Music                             │
                    └─────────────────────────────────────────────────────────┘
```

### Storage Layout

```
/opt/arr-stack/                     # Base configuration directory
├── docker-compose.yml              # Docker Compose configuration
├── jellyfin/
│   ├── config/                     # Jellyfin configuration & database
│   └── cache/                      # Transcoding cache
├── radarr/                         # Radarr config
├── sonarr/                         # Sonarr config
├── prowlarr/                       # Prowlarr config
├── bazarr/                         # Bazarr config
├── overseerr/                      # Overseerr config
├── jellyseerr/                     # Jellyseerr config
├── lidarr/                         # Lidarr config
├── tdarr/
│   ├── server/                     # Tdarr server data
│   ├── configs/                    # Tdarr configuration
│   ├── logs/                       # Tdarr logs
│   └── transcode_cache/            # Temporary transcoding space
├── autobrr/                        # Autobrr config
└── downloads/
    ├── complete/                   # Completed downloads
    ├── incomplete/                 # In-progress downloads
    └── torrents/                   # Torrent files

/mnt/media/                         # NFS mount point (192.168.20.31:/volume2/Proxmox-Media)
├── Movies/                         # Movie library
├── Series/                         # TV series library
├── Music/                          # Music library
└── YouTube Videos/                 # Additional media
```

---

## Prerequisites

### Required Infrastructure

1. **Ansible Controller** (192.168.20.30)
   - Ansible installed with `community.docker` collection
   - SSH access to target hosts

2. **Docker Host VM** (192.168.40.11)
   - Ubuntu 24.04 LTS
   - Docker CE and Docker Compose plugin
   - NFS client packages

3. **NAS Storage** (192.168.20.31)
   - Synology NAS with NFS share
   - Share: `/volume2/Proxmox-Media`
   - Directories: `/Movies`, `/Series`, `/Music`

### Ansible Collection Installation

```bash
# On ansible-controller01
ansible-galaxy collection install community.docker --force
```

**Why**: The `community.docker` collection provides the `docker_compose_v2` module used to manage Docker Compose deployments.

---

## Deployment Process

### Step 1: Install Docker on Target Host

```bash
# SSH to ansible-controller01
ssh hermes-admin@192.168.20.30

# Navigate to ansible directory
cd ~/ansible

# Run Docker installation playbook
ansible-playbook docker/install-docker.yml -l docker_media -v
```

**What this does**:
1. Updates apt cache to get latest package lists
2. Installs prerequisite packages (ca-certificates, curl, gnupg)
3. Adds Docker's official GPG key for package verification
4. Adds Docker APT repository for Ubuntu
5. Installs Docker CE, CLI, containerd, and Compose plugin
6. Starts Docker service and enables auto-start on boot
7. Adds the ansible user to docker group (allows running without sudo)

**Expected output**:
```
TASK [Display installed versions] **********************************************
ok: [docker-vm-media01] =>
  msg: |-
    Docker version: Docker version 29.1.3, build f52814d
    Compose version: Docker Compose version v5.0.0
```

### Step 2: Deploy Arr Stack

```bash
# Run arr stack deployment playbook
ansible-playbook docker/deploy-arr-stack.yml -l docker_media -v
```

**What this does**:
1. Installs NFS client packages (nfs-common, nfs4-acl-tools)
2. Creates directory structure under `/opt/arr-stack`
3. Creates NFS mount point at `/mnt/media`
4. Adds NFS mount to `/etc/fstab` for persistence
5. Attempts to mount NFS share (may fail if NAS not configured)
6. Deploys Docker Compose file
7. Pulls all container images
8. Starts all containers in the arr-network bridge

### Step 3: Configure NAS NFS Permissions (Automated)

The NFS mount requires Synology NAS permissions for VLAN 20 and VLAN 40. This is now **automated via Ansible**.

```bash
# Run the NFS permissions playbook
cd ~/ansible && ansible-playbook synology/configure-nfs-permissions.yml -v
```

This playbook automatically:
1. Backs up current `/etc/exports`
2. Adds subnet permissions (192.168.20.0/24 and 192.168.40.0/24)
3. Reloads NFS exports

See [Synology NAS Automation](#synology-nas-automation) section for full details.

**After running playbook, mount on media VM**:
```bash
# SSH to docker-vm-media01
ssh hermes-admin@192.168.40.11

# Mount the NFS share
sudo mount /mnt/media

# Verify mount
df -h /mnt/media
```

### Step 4: Verify Deployment

```bash
# Check all containers are running
ssh hermes-admin@192.168.40.11 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
```

**Expected output**:
```
NAMES        STATUS                        PORTS
bazarr       Up About a minute             0.0.0.0:6767->6767/tcp
tdarr        Up About a minute             0.0.0.0:8265-8266->8265-8266/tcp
sonarr       Up About a minute             0.0.0.0:8989->8989/tcp
autobrr      Up About a minute             0.0.0.0:7474->7474/tcp
lidarr       Up About a minute             0.0.0.0:8686->8686/tcp
overseerr    Up About a minute             0.0.0.0:5055->5055/tcp
radarr       Up About a minute             0.0.0.0:7878->7878/tcp
jellyseerr   Up About a minute             0.0.0.0:5056->5055/tcp
prowlarr     Up About a minute             0.0.0.0:9696->9696/tcp
jellyfin     Up About a minute (healthy)   0.0.0.0:8096->8096/tcp
```

---

## Synology NAS Automation

This section documents the Ansible automation for managing Synology NAS NFS permissions.

### Overview

The Synology NAS (192.168.20.31) provides NFS storage for the homelab infrastructure. Ansible automation allows managing NFS permissions without manual DSM configuration.

### Prerequisites Setup (One-Time)

Before using the NAS automation, the following was configured:

#### 1. SSH Key for Automation

A passphrase-less RSA key was generated on the Ansible controller for NAS automation:

```bash
# On ansible-controller01
ssh-keygen -t rsa -b 4096 -f ~/.ssh/nas_automation_key -N '' -C 'nas-automation'
```

**Why RSA instead of Ed25519**: Clearer naming convention to distinguish from other keys.

**Why no passphrase**: Ansible automation requires non-interactive SSH connections.

#### 2. SSH Key Added to NAS

The public key was added to the NAS:

```bash
# Copy key to NAS
ssh -p 14 hermes-admin@192.168.20.31 "cat >> ~/.ssh/authorized_keys" < ~/.ssh/nas_automation_key.pub
```

#### 3. Passwordless Sudo on NAS

Synology NAS management commands require root access:

```bash
# On Synology NAS
sudo sh -c 'echo "hermes-admin ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers'
```

#### 4. Ansible Inventory Entry

The NAS was added to the Ansible inventory (`~/ansible/inventory.ini`):

```ini
[synology_nas]
synology-nas01 ansible_host=192.168.20.31 ansible_port=14 ansible_ssh_private_key_file=~/.ssh/nas_automation_key
```

**Note**: Synology uses SSH port 14 (non-standard).

### NFS Permissions Playbook

**Location**: `~/ansible/synology/configure-nfs-permissions.yml`

**Purpose**: Automatically configure NFS export permissions for specified shares.

#### Usage

```bash
# Run the playbook
cd ~/ansible && ansible-playbook synology/configure-nfs-permissions.yml -v
```

#### What It Configures

| Share | Subnets Added |
|-------|---------------|
| /volume2/Proxmox-LXCs | 192.168.20.0/24, 192.168.40.0/24 |
| /volume2/Proxmox-Media | 192.168.20.0/24, 192.168.40.0/24 |
| /volume2/ProxmoxCluster-VMDisks | 192.168.20.0/24, 192.168.40.0/24 |
| /volume2/ProxmoxData | 192.168.20.0/24, 192.168.40.0/24 |

#### Playbook Tasks Explained

```yaml
- name: Backup current /etc/exports
  # Why: Always backup before modifying system files
  # Creates timestamped backup for rollback if needed
  copy:
    src: /etc/exports
    dest: "/etc/exports.backup.{{ ansible_date_time.iso8601_basic_short }}"
```

```yaml
- name: Update NFS exports with subnet permissions
  # Why: Add subnet-based access rules to each share
  # Uses blockinfile to manage our entries separately from Synology's
  blockinfile:
    path: /etc/exports
    marker: "# {mark} ANSIBLE MANAGED - {{ item }}"
    block: |
      {{ item }}    192.168.20.0/24(options...)    192.168.40.0/24(options...)
```

```yaml
- name: Reload NFS exports
  # Why: Apply the new export rules without restarting NFS service
  # exportfs -ra: Re-export all directories (sync /etc/exports with kernel)
  command: exportfs -ra
```

#### NFS Export Options

The playbook uses these NFS export options (matching Synology defaults):

| Option | Purpose |
|--------|---------|
| `rw` | Read-write access |
| `async` | Asynchronous writes (better performance) |
| `no_wdelay` | Don't delay writes |
| `crossmnt` | Allow crossing mount points |
| `insecure` | Allow connections from ports > 1024 |
| `all_squash` | Map all users to anonymous |
| `insecure_locks` | Don't require secure locking |
| `sec=sys` | Use standard UNIX auth |
| `anonuid=1024,anongid=100` | Anonymous user/group mapping |

### Verification

After running the playbook, verify from any client:

```bash
showmount -e 192.168.20.31
```

Expected output:
```
Export list for 192.168.20.31:
/volume2/Proxmox-Media          192.168.40.0/24,192.168.20.0/24
/volume2/Proxmox-LXCs           192.168.40.0/24,192.168.20.0/24
/volume2/ProxmoxCluster-VMDisks 192.168.40.0/24,192.168.20.0/24
/volume2/ProxmoxData            192.168.40.0/24,192.168.20.0/24
```

### Important Notes

1. **Synology DSM Regeneration**: Synology may regenerate `/etc/exports` during system updates. The Ansible-managed blocks are preserved, but you may need to re-run the playbook after major DSM updates.

2. **Backup Location**: Backups are created at `/etc/exports.backup.<timestamp>` on the NAS.

3. **Rollback**: To rollback, restore from backup:
   ```bash
   ssh -i ~/.ssh/nas_automation_key -p 14 hermes-admin@192.168.20.31 \
     "sudo cp /etc/exports.backup.<timestamp> /etc/exports && sudo exportfs -ra"
   ```

---

## Service Reference

### Jellyfin (Media Server)

**Purpose**: Stream media to devices, manage libraries, handle user access.

**URL**: http://192.168.40.11:8096

**Container Details**:
- Image: `jellyfin/jellyfin:latest`
- Ports: 8096 (Web UI), 8920 (HTTPS), 7359/udp (discovery), 1900/udp (DLNA)

**Configuration**:
- Config path: `/opt/arr-stack/jellyfin/config`
- Cache path: `/opt/arr-stack/jellyfin/cache`
- Media paths: `/mnt/media/Movies` (→ `/data/movies`), `/mnt/media/Series` (→ `/data/tvshows`)

**Initial Setup**:
1. Access http://192.168.40.11:8096
2. Create admin account
3. Add media libraries pointing to `/data/movies` and `/data/tvshows`
4. Configure transcoding settings

### Radarr (Movie Management)

**Purpose**: Automatically download and organize movies.

**URL**: http://192.168.40.11:7878

**Container Details**:
- Image: `lscr.io/linuxserver/radarr:latest`
- Port: 7878

**How it works**:
1. You add movies to a "wanted" list
2. Radarr searches configured indexers (via Prowlarr)
3. When found, sends to download client
4. Monitors download completion
5. Moves/renames file to media library
6. Updates Jellyfin library

**Configuration**:
- Config path: `/opt/arr-stack/radarr`
- Movies path: `/mnt/media/Movies` (→ `/movies` in container)
- Downloads path: `/opt/arr-stack/downloads`

### Sonarr (TV Series Management)

**Purpose**: Automatically download and organize TV shows.

**URL**: http://192.168.40.11:8989

**Container Details**:
- Image: `lscr.io/linuxserver/sonarr:latest`
- Port: 8989

**How it works**:
1. You add TV series to monitor
2. Sonarr tracks episode air dates
3. Searches indexers for new episodes
4. Downloads and organizes into season/episode structure

**Configuration**:
- Config path: `/opt/arr-stack/sonarr`
- TV path: `/mnt/media/Series` (→ `/tv` in container)
- Downloads path: `/opt/arr-stack/downloads`

### Lidarr (Music Management)

**Purpose**: Automatically download and organize music.

**URL**: http://192.168.40.11:8686

**Container Details**:
- Image: `lscr.io/linuxserver/lidarr:latest`
- Port: 8686

**Configuration**:
- Config path: `/opt/arr-stack/lidarr`
- Music path: `/mnt/media/Music` (→ `/music` in container)
- Downloads path: `/opt/arr-stack/downloads`

### Prowlarr (Indexer Manager)

**Purpose**: Central indexer management for all *arr apps.

**URL**: http://192.168.40.11:9696

**Container Details**:
- Image: `lscr.io/linuxserver/prowlarr:latest`
- Port: 9696

**How it works**:
1. You add indexers (torrent trackers, usenet) to Prowlarr
2. Configure sync to Radarr, Sonarr, Lidarr
3. Prowlarr automatically pushes indexer configs to all apps
4. Single point of management for all indexers

**Why use Prowlarr**:
- Single configuration point for indexers
- Automatic sync to all *arr apps
- Health monitoring for indexers
- Statistics and history

### Bazarr (Subtitle Management)

**Purpose**: Automatically download subtitles for movies and TV shows.

**URL**: http://192.168.40.11:6767

**Container Details**:
- Image: `lscr.io/linuxserver/bazarr:latest`
- Port: 6767

**Configuration**:
- Config path: `/opt/arr-stack/bazarr`
- Media paths: Shared with Radarr/Sonarr

**Setup**:
1. Connect to Radarr and Sonarr via API
2. Configure subtitle providers (OpenSubtitles, etc.)
3. Set language preferences
4. Bazarr automatically finds subtitles for your media

### Overseerr (Plex Request Management)

**Purpose**: User-friendly media request interface for Plex users.

**URL**: http://192.168.40.11:5055

**Container Details**:
- Image: `lscr.io/linuxserver/overseerr:latest`
- Port: 5055

**Note**: Primarily for Plex. If using Jellyfin, use Jellyseerr instead.

### Jellyseerr (Jellyfin Request Management)

**Purpose**: User-friendly media request interface for Jellyfin users.

**URL**: http://192.168.40.11:5056

**Container Details**:
- Image: `fallenbagel/jellyseerr:latest`
- Port: 5056 (mapped from internal 5055)

**How it works**:
1. Users browse and search for media
2. Submit requests through nice UI
3. Requests sent to Radarr/Sonarr
4. Automatic download and notification
5. Integrates with Jellyfin for library status

**Initial Setup**:
1. Access http://192.168.40.11:5056
2. Connect to Jellyfin server
3. Connect to Radarr and Sonarr
4. Configure user permissions

### Tdarr (Transcoding Automation)

**Purpose**: Automated media transcoding and health checking.

**URL**: http://192.168.40.11:8265

**Container Details**:
- Image: `ghcr.io/haveagitgat/tdarr:latest`
- Ports: 8265 (Web UI), 8266 (Server)

**Use cases**:
- Convert media to more efficient codecs (H.265/HEVC)
- Reduce storage requirements
- Ensure compatibility with devices
- Remove unwanted audio/subtitle tracks

**Configuration**:
- Server data: `/opt/arr-stack/tdarr/server`
- Config: `/opt/arr-stack/tdarr/configs`
- Logs: `/opt/arr-stack/tdarr/logs`
- Transcode cache: `/opt/arr-stack/tdarr/transcode_cache`

### Autobrr (Torrent Automation)

**Purpose**: IRC announce channel monitoring and filtering.

**URL**: http://192.168.40.11:7474

**Container Details**:
- Image: `ghcr.io/autobrr/autobrr:latest`
- Port: 7474

**How it works**:
1. Connects to IRC announce channels
2. Monitors for new releases in real-time
3. Applies filters (quality, release group, etc.)
4. Sends matching releases to download client
5. Much faster than RSS-based searching

**Configuration**:
- Config path: `/opt/arr-stack/autobrr`

---

## Ansible Playbook Reference

### install-docker.yml

**Location**: `~/ansible/docker/install-docker.yml` (on ansible-controller01)

**Purpose**: Installs Docker CE and Docker Compose on target hosts.

**Key Tasks Explained**:

```yaml
- name: Update apt cache
  # Why: Ensures we have the latest package lists before installing
  # This prevents "package not found" errors
  apt:
    update_cache: yes
    cache_valid_time: 3600  # Only update if cache older than 1 hour
```

```yaml
- name: Install prerequisite packages
  # Why: These packages are required for adding external repositories
  # - ca-certificates: SSL/TLS certificate handling
  # - curl: For downloading Docker GPG key
  # - gnupg: For GPG key management
  # - lsb-release: Provides distribution information
```

```yaml
- name: Add Docker official GPG key
  # Why: Verifies that Docker packages are authentic and unmodified
  # The GPG key signs all packages in the Docker repository
  # This prevents man-in-the-middle attacks on package downloads
```

```yaml
- name: Add Docker APT repository
  # Why: Adds Docker official repository for Ubuntu
  # Uses architecture detection for multi-arch support (amd64, arm64, etc.)
  # Ubuntu's default repos have older Docker versions
```

```yaml
- name: Add user to docker group
  # Why: Allows running docker commands without sudo
  # Security note: Users in docker group effectively have root access
  user:
    name: "{{ docker_user }}"
    groups: docker
    append: yes  # Don't remove from other groups
```

### deploy-arr-stack.yml

**Location**: `~/ansible/docker/deploy-arr-stack.yml` (on ansible-controller01)

**Purpose**: Deploys complete arr media stack using Docker Compose.

**Variables Explained**:

```yaml
puid: 1001  # User ID for container file permissions
pgid: 1001  # Group ID for container file permissions
# Why: Containers run as this UID/GID to match host user
# This ensures files created by containers are owned by hermes-admin
# Check with: id -u hermes-admin && id -g hermes-admin
```

```yaml
timezone: "America/New_York"
# Why: Containers use this for scheduling, logging timestamps
# Important for Radarr/Sonarr episode air date calculations
```

```yaml
arr_base_dir: /opt/arr-stack
# Why: Central location for all configuration files
# /opt is standard for optional/add-on software
# Easy to backup: tar -czvf arr-backup.tar.gz /opt/arr-stack
```

**Key Tasks Explained**:

```yaml
- name: Add NFS mount to fstab
  # Why: Ensures the NFS share mounts automatically on boot
  # Options explained:
  # - rw: Read-write access
  # - soft: Return error if server unavailable (vs hard which hangs)
  # - intr: Allow interruption of NFS operations
  # - timeo=300: Timeout in deciseconds (30 seconds)
  # - retrans=3: Number of retries before failing
  # - _netdev: Wait for network before mounting
  # - nofail: Don't fail boot if mount fails
  lineinfile:
    path: /etc/fstab
    line: "{{ nas_ip }}:{{ nas_media_share }} {{ media_mount_point }} nfs ..."
```

```yaml
- name: Start arr stack with Docker Compose
  community.docker.docker_compose_v2:
    project_src: "{{ arr_base_dir }}"  # Directory containing docker-compose.yml
    state: present                      # Ensure containers are running
    pull: always                        # Always check for newer images
  # Why: Uses Ansible's docker_compose_v2 module for idempotent deployment
  # This module handles image pulls, container creation, and network setup
```

---

## Configuration Guide

### Recommended Setup Order

1. **Prowlarr** (first - manages indexers)
   - Add your indexers (torrent trackers, usenet providers)
   - Configure API connections

2. **Radarr/Sonarr/Lidarr** (second - media managers)
   - Settings > Indexers > Add (connect to Prowlarr)
   - Settings > Download Clients > Add your download client
   - Settings > Media Management > Configure naming/organization

3. **Jellyfin** (third - media server)
   - Add libraries pointing to media directories
   - Configure users and access

4. **Jellyseerr** (fourth - request management)
   - Connect to Jellyfin
   - Connect to Radarr/Sonarr
   - Configure user permissions

5. **Bazarr** (fifth - subtitles)
   - Connect to Radarr/Sonarr
   - Configure subtitle providers

6. **Tdarr** (optional - transcoding)
   - Set up libraries pointing to media
   - Create transcoding plugins/flows

7. **Autobrr** (optional - IRC automation)
   - Configure IRC announce channels
   - Set up filters and rules

### Connecting Services

#### Configured Connections (API-Based - December 19, 2025)

The following connections have been configured via API:

| From | To | Connection Type | Status |
|------|-----|-----------------|--------|
| Prowlarr | Radarr | Full Sync (Movies) | ✅ Configured |
| Prowlarr | Sonarr | Full Sync (TV) | ✅ Configured |
| Prowlarr | Lidarr | Full Sync (Audio) | ✅ Configured |
| Bazarr | Radarr | API Connection | ✅ Configured |
| Bazarr | Sonarr | API Connection | ✅ Configured |
| Jellyseerr | Jellyfin | - | ⚠️ Needs Setup Wizard |
| Jellyseerr | Radarr/Sonarr | - | ⚠️ Needs Setup Wizard |

#### API Keys Reference

| Service | API Key | Config Location |
|---------|---------|-----------------|
| Radarr | `<your-api-key>` | `/opt/arr-stack/radarr/config.xml` |
| Sonarr | `<your-api-key>` | `/opt/arr-stack/sonarr/config.xml` |
| Lidarr | `<your-api-key>` | `/opt/arr-stack/lidarr/config.xml` |
| Prowlarr | `<your-api-key>` | `/opt/arr-stack/prowlarr/config.xml` |
| Bazarr | `<your-api-key>` | `/opt/arr-stack/bazarr/config/config.yaml` |

**Note**: API keys are auto-generated by each service. Access Settings > General > API Key in each application to retrieve yours.

#### Prowlarr Application Configuration

Prowlarr is configured to sync indexers automatically to all *arr apps:

```bash
# Verify Prowlarr applications
ssh hermes-admin@192.168.40.11 "curl -s http://localhost:9696/api/v1/applications \
  -H 'X-Api-Key: <your-prowlarr-api-key>' | python3 -c \"
import json,sys
apps=json.load(sys.stdin)
for a in apps:
    print(f'{a[\\\"name\\\"]}: {a[\\\"implementation\\\"]} - Enabled: {a[\\\"enable\\\"]}')
\""
```

**Expected Output:**
```
Radarr: Radarr - Enabled: True
Sonarr: Sonarr - Enabled: True
Lidarr: Lidarr - Enabled: True
```

#### Bazarr Configuration

Bazarr is configured to connect to Radarr and Sonarr using Docker container names:

```yaml
# /opt/arr-stack/bazarr/config/config.yaml (relevant sections)
general:
  use_radarr: true
  use_sonarr: true

radarr:
  ip: radarr              # Docker container name
  port: 7878
  apikey: <your-radarr-api-key>

sonarr:
  ip: sonarr              # Docker container name
  port: 8989
  apikey: <your-sonarr-api-key>
```

**Note:** Bazarr still needs a language profile configured via the web UI.

#### Services Requiring Manual Setup

**Jellyfin** (https://jellyfin.hrmsmrflrii.xyz):
1. Complete startup wizard (create admin account)
2. Add media libraries:
   - Movies: `/data/movies`
   - TV Shows: `/data/tvshows`
3. Generate API key: Dashboard → API Keys → Add

**Bazarr** (https://bazarr.hrmsmrflrii.xyz):
1. Create language profile: Settings → Languages → Add Profile
2. Select desired subtitle languages (e.g., English)
3. Assign profile to movies/series

**Jellyseerr** (https://jellyseerr.hrmsmrflrii.xyz):
1. Complete initial setup wizard
2. Connect to Jellyfin:
   - Hostname: `jellyfin`
   - Port: `8096`
   - Paste Jellyfin API key
3. Add Radarr: `radarr:7878`, API key from table above
4. Add Sonarr: `sonarr:8989`, API key from table above

#### Manual Connection Setup (Reference)

**Prowlarr to Radarr/Sonarr/Lidarr**:
1. In Prowlarr: Settings > Apps > Add
2. Select Radarr/Sonarr/Lidarr
3. Use container name as hostname (e.g., `radarr`, `sonarr`)
4. Get API key from target app: Settings > General > API Key

**Jellyseerr to Jellyfin**:
1. In Jellyseerr setup wizard
2. Jellyfin URL: `http://jellyfin:8096`
3. Enter Jellyfin admin credentials

**Bazarr to Radarr/Sonarr**:
1. Settings > Radarr/Sonarr
2. Use container names (e.g., `http://radarr:7878`)
3. Enter API keys

### Container Network Communication

All containers are on the `arr-network` Docker bridge network. They can reach each other by container name:

```
http://jellyfin:8096      # From any container to Jellyfin
http://radarr:7878        # From any container to Radarr
http://sonarr:8989        # From any container to Sonarr
http://lidarr:8686        # From any container to Lidarr
http://prowlarr:9696      # From any container to Prowlarr
http://bazarr:6767        # From any container to Bazarr
http://jellyseerr:5055    # From any container to Jellyseerr (internal port)
```

---

## Troubleshooting

### Issue: NFS Mount Access Denied

**Symptom**:
```
fatal: [docker-vm-media01]: FAILED! =>
  msg: Error mounting /mnt/media: mount.nfs: access denied by server
```

**Root Cause**: Synology NAS NFS permissions only allow Proxmox nodes (192.168.20.20-22), not VLAN 40 hosts.

**Resolution**:
1. Log into Synology DSM
2. Control Panel > Shared Folder > Proxmox-Media > Edit > NFS Permissions
3. Add rule for 192.168.40.11 (or 192.168.40.0/24)
4. Remount: `sudo mount /mnt/media`

**Verification**:
```bash
# Check what IPs can access NFS
ssh hermes-admin@192.168.40.11 "showmount -e 192.168.20.31"

# Should show your IP or subnet in the allowed list
```

### Issue: Container Won't Start

**Symptom**: Container shows as "Restarting" or exits immediately.

**Diagnosis**:
```bash
# Check container logs
ssh hermes-admin@192.168.40.11 "docker logs <container_name>"

# Check for permission issues
ssh hermes-admin@192.168.40.11 "ls -la /opt/arr-stack/<service_name>"
```

**Common causes**:
- Wrong PUID/PGID (file permission issues)
- Port already in use
- Volume mount path doesn't exist
- Insufficient memory

### Issue: Services Can't Communicate

**Symptom**: Radarr can't connect to Prowlarr, etc.

**Diagnosis**:
```bash
# Check if containers are on same network
ssh hermes-admin@192.168.40.11 "docker network inspect arr-stack_arr-network"

# Test connectivity from one container to another
ssh hermes-admin@192.168.40.11 "docker exec radarr ping prowlarr"
```

**Resolution**: Ensure all containers are on `arr-network` in docker-compose.yml.

### Issue: Ansible Playbook Fails

**Symptom**: Playbook fails with connection or permission errors.

**Common fixes**:
```bash
# Check SSH connectivity
ssh hermes-admin@192.168.40.11 "echo 'Connected'"

# Check become (sudo) works
ssh hermes-admin@192.168.40.11 "sudo whoami"

# Run with more verbosity
ansible-playbook docker/deploy-arr-stack.yml -l docker_media -vvv
```

---

## Maintenance Commands

### Container Management

```bash
# SSH to media VM
ssh hermes-admin@192.168.40.11

# View all containers
docker ps -a

# View container logs
docker logs <container_name>
docker logs -f <container_name>  # Follow/stream logs

# Restart a container
docker restart <container_name>

# Stop all arr stack containers
cd /opt/arr-stack && docker compose stop

# Start all arr stack containers
cd /opt/arr-stack && docker compose start

# Recreate containers (after config changes)
cd /opt/arr-stack && docker compose up -d

# Update all containers to latest images
cd /opt/arr-stack && docker compose pull && docker compose up -d

# View container resource usage
docker stats
```

### Backup and Restore

```bash
# Backup all configurations
sudo tar -czvf arr-stack-backup-$(date +%Y%m%d).tar.gz /opt/arr-stack

# Restore from backup
sudo tar -xzvf arr-stack-backup-20251218.tar.gz -C /

# Backup individual service
sudo tar -czvf radarr-backup.tar.gz /opt/arr-stack/radarr
```

### Re-run Ansible Playbook

```bash
# From ansible-controller01
cd ~/ansible

# Re-deploy entire stack (idempotent - safe to run multiple times)
ansible-playbook docker/deploy-arr-stack.yml -l docker_media -v

# Only run NFS-related tasks
ansible-playbook docker/deploy-arr-stack.yml -l docker_media --tags nfs

# Skip NFS tasks (if NAS not configured)
ansible-playbook docker/deploy-arr-stack.yml -l docker_media --skip-tags nfs
```

### Disk Space Management

```bash
# Check disk usage
df -h

# Check arr-stack size
du -sh /opt/arr-stack/*

# Clean up Docker resources
docker system prune -a  # Remove unused images, containers, networks

# Clean up Tdarr transcode cache
rm -rf /opt/arr-stack/tdarr/transcode_cache/*
```

---

## Lessons Learned

### 1. NFS Permissions Must Include VLAN 40

**Problem**: Initial deployment failed because Synology NAS only allowed Proxmox nodes.

**Lesson**: When adding VMs on different VLANs that need NAS access, update NFS permissions to include those subnets.

**Best Practice**: Use subnet-based rules (192.168.40.0/24) instead of individual IPs for easier management.

### 2. PUID/PGID Must Match Host User

**Problem**: Default PUID/PGID of 1000 didn't match hermes-admin's actual UID/GID of 1001.

**Lesson**: Always check actual user IDs with `id -u` and `id -g` before deploying.

**Best Practice**: Add a verification task to playbook that checks and displays PUID/PGID.

### 3. Docker Compose Version Attribute is Obsolete

**Warning**: Docker Compose warned that `version: "3.9"` is obsolete.

**Lesson**: Modern Docker Compose (v2.0+) doesn't require version specification.

**Best Practice**: Remove version attribute from docker-compose.yml files.

### 4. Ansible Collection Compatibility

**Warning**: `community.docker does not support Ansible version 2.16.3`

**Lesson**: Collection may work despite warnings, but should update Ansible for full compatibility.

**Best Practice**: Check Ansible and collection compatibility before deployments.

### 5. Use Container Names for Inter-Service Communication

**Lesson**: Services should connect to each other using container names (e.g., `http://radarr:7878`) not IP addresses.

**Why**: Container IPs can change on restart; container names resolve via Docker DNS.

---

## File Locations Summary

| Location | Purpose |
|----------|---------|
| **On Ansible Controller (192.168.20.30)** | |
| `~/ansible/docker/install-docker.yml` | Docker installation playbook |
| `~/ansible/docker/deploy-arr-stack.yml` | Arr stack deployment playbook |
| `~/ansible/inventory.ini` | Ansible inventory |
| `~/ansible/ansible.cfg` | Ansible configuration |
| **On Media VM (192.168.40.11)** | |
| `/opt/arr-stack/` | All arr stack configurations |
| `/opt/arr-stack/docker-compose.yml` | Docker Compose file |
| `/mnt/media/` | NFS mount point for media |
| `/etc/fstab` | NFS mount configuration |
| **On NAS (192.168.20.31)** | |
| `/volume2/Proxmox-Media/Movies/` | Movie library |
| `/volume2/Proxmox-Media/Series/` | TV series library |
| `/volume2/Proxmox-Media/Music/` | Music library |

---

## Quick Reference Card

### Service URLs

| Service | URL |
|---------|-----|
| Jellyfin | http://192.168.40.11:8096 |
| Radarr | http://192.168.40.11:7878 |
| Sonarr | http://192.168.40.11:8989 |
| Lidarr | http://192.168.40.11:8686 |
| Prowlarr | http://192.168.40.11:9696 |
| Bazarr | http://192.168.40.11:6767 |
| Overseerr | http://192.168.40.11:5055 |
| Jellyseerr | http://192.168.40.11:5056 |
| Tdarr | http://192.168.40.11:8265 |
| Autobrr | http://192.168.40.11:7474 |

### Common Commands

```bash
# Deploy arr stack
ssh hermes-admin@192.168.20.30 "cd ~/ansible && ansible-playbook docker/deploy-arr-stack.yml -l docker_media"

# Check container status
ssh hermes-admin@192.168.40.11 "docker ps"

# View container logs
ssh hermes-admin@192.168.40.11 "docker logs -f <container>"

# Update all containers
ssh hermes-admin@192.168.40.11 "cd /opt/arr-stack && docker compose pull && docker compose up -d"

# Mount NFS (after NAS configured)
ssh hermes-admin@192.168.40.11 "sudo mount /mnt/media"
```

---

*Document created: December 18, 2025*
*Last updated: December 19, 2025*
*Deployed by: Ansible automation from ansible-controller01*
*Inter-app connections configured via API: December 19, 2025*
