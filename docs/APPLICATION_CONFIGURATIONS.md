# Application Configurations

> Part of the [Proxmox Infrastructure Documentation](../CLAUDE.md)

This document provides detailed configuration guides for applications in the homelab, including step-by-step setup instructions, command explanations, and troubleshooting notes.

---

## Table of Contents

- [Arr Stack Path Configuration](#arr-stack-path-configuration)
  - [Why Unified Paths](#why-unified-paths)
  - [Path Structure](#path-structure)
  - [App Configuration](#arr-stack-app-configuration)
  - [Troubleshooting](#arr-stack-troubleshooting)
- [Immich Photo Management](#immich-photo-management)
  - [Architecture Overview](#architecture-overview)
  - [Storage Configuration](#storage-configuration)
  - [NFS Mount Setup](#nfs-mount-setup)
  - [Docker Volume Mappings](#docker-volume-mappings)
  - [External Library Setup](#external-library-setup)
  - [Troubleshooting](#immich-troubleshooting)
- [Life Progress Widget (Glance)](#life-progress-widget-glance)
  - [Overview](#life-progress-overview)
  - [Architecture](#life-progress-architecture)
  - [API Service Setup](#api-service-setup)
  - [Glance Widget Configuration](#glance-widget-configuration)
  - [Customization](#life-progress-customization)
  - [Maintenance](#life-progress-maintenance)
- [Glance Dashboard Theming](#glance-dashboard-theming)
  - [Theme Overview](#theme-overview)
  - [How Theming Works](#how-theming-works)
  - [Using the Theme Picker](#using-the-theme-picker)
  - [Custom CSS Enhancements](#custom-css-enhancements)
  - [Adding a New Theme](#adding-a-new-theme)
  - [Theme Design Reference](#theme-design-reference)
- [Authentik SSO Configuration](#authentik-sso-configuration)
  - [Overview](#authentik-overview)
  - [GitLab OIDC Integration](#gitlab-oidc-integration)
  - [OAuth Sources](#oauth-sources)
  - [Application Dashboard Organization](#application-dashboard-organization)
  - [Troubleshooting](#authentik-troubleshooting)

---

## Arr Stack Path Configuration

**Host**: docker-vm-media01 (192.168.40.11)
**Configured**: December 23, 2025

### Why Unified Paths

The *arr stack (Radarr, Sonarr, Lidarr) and download clients (Deluge, SABnzbd) must share a common filesystem view for two critical reasons:

1. **Hardlinks**: When Radarr/Sonarr imports a completed download, it can create a hardlink instead of copying. This saves disk space and is instant.

2. **Atomic Moves**: Files can be moved instantly within the same filesystem instead of copy+delete operations.

**The Problem (Before Fix)**:

```
Download clients used:  /mnt/media/Completed → /downloads/completed
Radarr/Sonarr used:     /opt/arr-stack/downloads → /downloads
```

These were different host paths, so Radarr/Sonarr couldn't see completed downloads.

**The Solution (After Fix)**:

```
All services use:       /mnt/media → /data
```

Now all services share the same filesystem view and hardlinks work.

### Path Structure

**Host Directory Layout** (`/mnt/media/` on docker-vm-media01):

```
/mnt/media/                    # NFS mount from Synology NAS
├── Completed/                 # Download clients put finished files here
├── Downloading/               # Active downloads
├── Incomplete/                # Partial downloads
├── Movies/                    # Radarr organizes movies here
├── Series/                    # Sonarr organizes TV here
├── Music/                     # Lidarr organizes music here
└── downloads/                 # Legacy folder (unused)
```

**Container Volume Mappings**:

| Service | Volume Mount | Container View |
|---------|--------------|----------------|
| Radarr | `/mnt/media:/data` | `/data/Movies`, `/data/Completed` |
| Sonarr | `/mnt/media:/data` | `/data/Series`, `/data/Completed` |
| Lidarr | `/mnt/media:/data` | `/data/Music`, `/data/Completed` |
| Bazarr | `/mnt/media:/data` | `/data/Movies`, `/data/Series` |
| Deluge | `/mnt/media:/data` | `/data/Completed`, `/data/Downloading` |
| SABnzbd | `/mnt/media:/data` | `/data/Completed`, `/data/Downloading` |
| Jellyfin | `/mnt/media/Movies:/data/movies:ro`<br>`/mnt/media/Series:/data/tvshows:ro` | Read-only media access |

### Arr Stack App Configuration

After deploying with unified paths, configure each app:

#### Radarr Configuration

1. **Settings → Media Management → Root Folders**
   - Delete old root folder if exists
   - Add: `/data/Movies`

2. **Settings → Download Clients → Deluge/SABnzbd**
   - Remote Path Mapping: NOT needed (same paths)

3. **Settings → Download Clients → Category**
   - Set category to `radarr`

#### Sonarr Configuration

1. **Settings → Media Management → Root Folders**
   - Delete old root folder if exists
   - Add: `/data/Series`

2. **Settings → Download Clients**
   - Configure Deluge/SABnzbd with no remote path mapping

3. **Settings → Download Clients → Category**
   - Set category to `sonarr`

#### Lidarr Configuration

1. **Settings → Media Management → Root Folders**
   - Add: `/data/Music`

2. **Settings → Download Clients**
   - Configure with category `lidarr`

#### Deluge Configuration

1. **Preferences → Downloads**
   - Download to: `/data/Downloading`
   - Move completed to: `/data/Completed`

2. **Enable Label Plugin**
   - Used for category-based organization

#### SABnzbd Configuration

1. **Config → Folders**
   - Temporary Download Folder: `/data/Incomplete`
   - Completed Download Folder: `/data/Completed`

2. **Config → Categories**
   - Add categories: `radarr`, `sonarr`, `lidarr`
   - Each pointing to `/data/Completed`

### Arr Stack Troubleshooting

#### Issue: Jellyfin Shows No Movies/TV Shows

**Resolved**: December 23, 2025

**Symptoms**:
- Jellyfin web UI loads but shows "Library folder is inaccessible or empty"
- Media files exist in `/mnt/media/Completed/` but not in `/mnt/media/Movies/`

**Root Cause**: Path mismatch between download clients and *arr apps. Download clients put files in `/mnt/media/Completed` but Radarr/Sonarr were configured to look at `/opt/arr-stack/downloads` (a different host path).

**Diagnosis**:
```bash
# Check Jellyfin logs
ssh hermes-admin@192.168.40.11 "docker logs jellyfin 2>&1 | grep -i 'inaccessible\|empty'"

# Check where downloads are
ssh hermes-admin@192.168.40.11 "ls -la /mnt/media/"

# Check Radarr/Sonarr container mounts
ssh hermes-admin@192.168.40.11 "docker inspect radarr --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'"
```

**Fix**:

1. Update `/opt/arr-stack/docker-compose.yml` to use unified paths:
   ```yaml
   radarr:
     volumes:
       - /opt/arr-stack/radarr:/config
       - /mnt/media:/data

   sonarr:
     volumes:
       - /opt/arr-stack/sonarr:/config
       - /mnt/media:/data

   deluge:
     volumes:
       - /opt/arr-stack/deluge:/config
       - /mnt/media:/data
   ```

2. Recreate containers:
   ```bash
   ssh hermes-admin@192.168.40.11 "cd /opt/arr-stack && sudo docker compose down && sudo docker compose up -d"
   ```

3. Reconfigure each app with new paths (see App Configuration above)

4. Trigger manual import in Radarr/Sonarr for existing downloads

**Verification**:
```bash
# Check Radarr can see completed downloads
ssh hermes-admin@192.168.40.11 "docker exec radarr ls /data/Completed/"

# Check Jellyfin can see movies
ssh hermes-admin@192.168.40.11 "docker exec jellyfin ls /data/movies/"
```

**Prevention**: Always use unified `/data` mount for all *arr stack services. Never use separate mount paths for download clients vs media managers.

---

#### Issue: Hardlinks Not Working (Copy Instead of Instant Move)

**Symptoms**:
- Import takes a long time (copying instead of instant)
- Disk usage doubles during import
- Radarr/Sonarr logs show "copy" instead of "hardlink"

**Root Cause**: Source and destination are on different filesystems (different mount points).

**Diagnosis**:
```bash
# Check if paths are on same filesystem
ssh hermes-admin@192.168.40.11 "df /mnt/media/Completed /mnt/media/Movies"
# Should show SAME filesystem for both

# Check Radarr logs for copy vs hardlink
ssh hermes-admin@192.168.40.11 "docker logs radarr 2>&1 | grep -i 'hardlink\|copy'"
```

**Fix**: Ensure all paths use the same NFS mount (`/mnt/media`). The unified `/data` configuration solves this.

---

## Immich Photo Management

**Host**: immich-vm01 (192.168.40.22)
**Configured**: December 21, 2025

### Architecture Overview

Immich is configured with a dual-storage architecture:

| Storage Zone | Purpose | Access | Location |
|--------------|---------|--------|----------|
| Legacy Photos | Historical archive from Synology Photos | Read-Only | `/volume2/homes/hermes-admin/Photos` |
| Active Uploads | New photos from Immich mobile/web | Read-Write | `/volume2/Immich Photos` |

**Design Rationale**:
- Legacy photos remain immutable (protected from accidental modification)
- New uploads have dedicated storage managed exclusively by Immich
- Synology provides durability via snapshots and RAID
- Clear separation of concerns between archive and active data

### Storage Configuration

#### Synology NAS Setup

**NAS IP**: 192.168.20.31
**DSM Address**: https://192.168.20.31:5001

Two NFS exports configured in DSM Control Panel > Shared Folder > NFS Permissions:

| Shared Folder | NFS Path | Client IP | Privilege | Squash |
|---------------|----------|-----------|-----------|--------|
| homes | `/volume2/homes` | 192.168.40.22 | Read-only | Map all users to admin |
| Immich Photos | `/volume2/Immich Photos` | 192.168.40.22 | Read/Write | Map all users to admin |

**Why "Map all users to admin"**: Docker containers run as various UIDs. Squashing all users to admin ensures consistent write access regardless of container user mapping.

#### VM Mount Points

Three mount points configured on immich-vm01:

| Mount Point | Type | Source | Purpose |
|-------------|------|--------|---------|
| `/mnt/synology-root` | NFS4 | `192.168.20.31:/volume2/homes` | Base NFS mount (RO) |
| `/mnt/synology-photos` | Bind | `/mnt/synology-root/hermes-admin/Photos` | Legacy photos (RO) |
| `/mnt/immich-uploads` | NFS4 | `192.168.20.31:/volume2/Immich Photos` | Active uploads (RW) |

**Why a bind mount for legacy photos**: The Synology homes share contains multiple user directories. A bind mount isolates just the Photos subdirectory, providing a clean path for Immich without exposing other home directory contents.

### NFS Mount Setup

#### Step 1: Install NFS Client

```bash
ssh hermes-admin@192.168.40.22 "sudo apt install -y nfs-common nfs4-acl-tools"
```

**What this does**:
- `nfs-common`: Core NFS client utilities for mounting NFS shares
- `nfs4-acl-tools`: NFSv4 ACL management tools for permission handling

#### Step 2: Create Mount Point Directories

```bash
ssh hermes-admin@192.168.40.22 "sudo mkdir -p /mnt/synology-root /mnt/synology-photos /mnt/immich-uploads"
```

**What this does**: Creates the local directories where NFS shares will be mounted. The `-p` flag creates parent directories if they don't exist.

#### Step 3: Configure /etc/fstab

The following entries are added to `/etc/fstab` for persistent mounts:

```fstab
# Synology homes export (RO) - base mount for legacy photos access
192.168.20.31:/volume2/homes  /mnt/synology-root  nfs4  ro,vers=4,_netdev,nofail  0  0

# Legacy photos bind mount (RO) - isolated path to Photos directory
/mnt/synology-root/hermes-admin/Photos  /mnt/synology-photos  none  bind,ro  0  0

# Immich active uploads (RW) - dedicated share for new photos
192.168.20.31:/volume2/Immich\040Photos  /mnt/immich-uploads  nfs4  rw,vers=4,_netdev,nofail  0  0
```

**Mount Options Explained**:

| Option | Purpose |
|--------|---------|
| `ro` | Read-only mount - prevents writes |
| `rw` | Read-write mount - allows writes |
| `vers=4` | Use NFSv4 protocol (more secure, better performance) |
| `_netdev` | Wait for network before mounting (prevents boot failures) |
| `nofail` | Don't fail boot if mount fails (prevents boot hang) |
| `bind` | Creates a bind mount (mirror of existing path) |
| `\040` | Escaped space character for "Immich Photos" share name |

#### Step 4: Mount the Shares

```bash
ssh hermes-admin@192.168.40.22 "sudo mount -a"
```

**What this does**: Mounts all filesystems defined in `/etc/fstab` that aren't already mounted.

#### Step 5: Verify Mounts

```bash
ssh hermes-admin@192.168.40.22 "mount | grep -E 'synology|immich'"
```

**Expected output**:
```
192.168.20.31:/volume2/homes on /mnt/synology-root type nfs4 (ro,...)
192.168.20.31:/volume2/homes/hermes-admin/Photos on /mnt/synology-photos type nfs4 (ro,...)
192.168.20.31:/volume2/Immich Photos on /mnt/immich-uploads type nfs4 (rw,...)
```

#### Step 6: Test Permissions

```bash
# Verify legacy photos are readable but not writable
ssh hermes-admin@192.168.40.22 "ls /mnt/synology-photos/ | head -3"
ssh hermes-admin@192.168.40.22 "touch /mnt/synology-photos/test 2>&1 || echo 'RO verified'"

# Verify uploads are writable
ssh hermes-admin@192.168.40.22 "touch /mnt/immich-uploads/test && rm /mnt/immich-uploads/test && echo 'RW verified'"
```

### Docker Volume Mappings

#### Immich Server Container Volumes

The docker-compose.yml at `/opt/immich/docker-compose.yml` maps host directories to container paths:

```yaml
services:
  immich-server:
    volumes:
      # Active uploads on Synology (RW)
      - /mnt/immich-uploads:/usr/src/app/upload
      # Legacy photos from Synology (RO external library)
      - /mnt/synology-photos:/usr/src/app/external/synology:ro
      - /etc/localtime:/etc/localtime:ro
```

**Volume Mapping Explained**:

| Host Path | Container Path | Mode | Purpose |
|-----------|----------------|------|---------|
| `/mnt/immich-uploads` | `/usr/src/app/upload` | RW | Where Immich stores all new uploads, thumbnails, encoded videos |
| `/mnt/synology-photos` | `/usr/src/app/external/synology` | RO | External library path for legacy photos |
| `/etc/localtime` | `/etc/localtime` | RO | Sync container timezone with host |

**The `:ro` suffix**: Explicitly marks the volume as read-only inside the container, providing defense-in-depth even if the host mount were accidentally changed to RW.

#### Immich Upload Directory Structure

Immich requires specific subdirectories with marker files for integrity checks:

```
/mnt/immich-uploads/
├── thumbs/          # Thumbnail cache
│   └── .immich      # Integrity marker
├── upload/          # Original uploads
│   └── .immich
├── library/         # Organized library
│   └── .immich
├── encoded-video/   # Transcoded videos
│   └── .immich
├── profile/         # User profile images
│   └── .immich
└── backups/         # Database backups
    └── .immich
```

**Create directories and markers**:
```bash
ssh hermes-admin@192.168.40.22 "for dir in thumbs upload backups library profile encoded-video; do \
  sudo mkdir -p /mnt/immich-uploads/\$dir && \
  sudo touch /mnt/immich-uploads/\$dir/.immich; \
done"
```

**Why marker files**: Immich performs "system integrity checks" on startup. It verifies each required directory exists and contains a `.immich` marker file to confirm the mount is correct and not an empty local directory.

#### Redeploy Immich

After updating docker-compose.yml:

```bash
ssh hermes-admin@192.168.40.22 "cd /opt/immich && sudo docker compose down && sudo docker compose up -d"
```

**What this does**:
- `docker compose down`: Stops and removes containers, networks (but preserves volumes)
- `docker compose up -d`: Creates and starts containers in detached mode with new configuration

#### Verify Container Access

```bash
# Check external library is accessible
ssh hermes-admin@192.168.40.22 "sudo docker exec immich-server ls /usr/src/app/external/synology/ | head -5"

# Check upload directory structure
ssh hermes-admin@192.168.40.22 "sudo docker exec immich-server ls /usr/src/app/upload/"

# Verify read-only on external library
ssh hermes-admin@192.168.40.22 "sudo docker exec immich-server touch /usr/src/app/external/synology/test 2>&1"
# Expected: "touch: cannot touch '/usr/src/app/external/synology/test': Read-only file system"

# Verify read-write on uploads
ssh hermes-admin@192.168.40.22 "sudo docker exec immich-server touch /usr/src/app/upload/test && \
  sudo docker exec immich-server rm /usr/src/app/upload/test && echo 'RW OK'"
```

### External Library Setup

After infrastructure is configured, add the external library in Immich UI:

1. **Navigate to**: https://photos.hrmsmrflrii.xyz (or http://192.168.40.22:2283)
2. **Go to**: Administration > External Libraries
3. **Click**: Create Library
4. **Configure**:
   - Name: `Synology Legacy Photos`
   - Path: `/usr/src/app/external/synology`
   - Owner: Select your user account
5. **Click**: Create
6. **Click**: Scan Library (three-dot menu)
7. **Monitor**: Administration > Jobs to track import progress

**Important Notes**:
- External libraries are read-only in Immich UI (cannot delete/modify photos)
- Face detection and object recognition will process external library photos
- Original files remain on Synology, Immich creates thumbnails locally

### Immich Troubleshooting

#### Issue: Container Restart Loop - Missing Directory Structure

**Resolved**: December 21, 2025

**Symptoms**:
- Container status shows "Restarting"
- Logs show: `Failed to read: "<UPLOAD_LOCATION>/encoded-video/.immich"`

**Root Cause**: When pointing Immich to a new empty NFS share, the required directory structure with `.immich` marker files doesn't exist.

**Diagnosis**:
```bash
ssh hermes-admin@192.168.40.22 "sudo docker logs immich-server --tail 30 2>&1 | grep -i error"
```

**Thought Process**: The error message indicates Immich performs startup checks for specific directories. Looking at the Immich documentation and source code, it verifies mount integrity by checking for marker files. A new empty NFS share won't have these, causing the startup check to fail.

**Fix**:
```bash
ssh hermes-admin@192.168.40.22 "for dir in thumbs upload backups library profile encoded-video; do \
  sudo mkdir -p /mnt/immich-uploads/\$dir && \
  sudo touch /mnt/immich-uploads/\$dir/.immich; \
done"

ssh hermes-admin@192.168.40.22 "cd /opt/immich && sudo docker compose restart immich-server"
```

**Verification**:
```bash
ssh hermes-admin@192.168.40.22 "sudo docker ps --filter name=immich-server --format '{{.Status}}'"
# Should show "Up X seconds (healthy)" after ~30 seconds
```

**Prevention**: The Ansible playbook (`ansible/immich/deploy-immich.yml`) now includes tasks to create the directory structure automatically on deployment.

---

#### Issue: Bind Mount Not Active After Reboot

**Resolved**: December 21, 2025

**Symptoms**:
- `/mnt/synology-photos/` directory exists but is empty
- Legacy photos not accessible in Immich

**Diagnosis**:
```bash
# Check if mount is active
ssh hermes-admin@192.168.40.22 "mount | grep synology-photos"

# Check fstab entry
ssh hermes-admin@192.168.40.22 "grep synology-photos /etc/fstab"

# Check if source exists
ssh hermes-admin@192.168.40.22 "ls /mnt/synology-root/hermes-admin/Photos/ | head -3"
```

**Root Cause**: Bind mounts depend on their source mount being available first. If the NFS mount order isn't guaranteed, the bind mount may fail silently.

**Thought Process**: The fstab entry exists and the source directory has content, but the bind mount shows empty. This is a mount order dependency issue - the bind mount runs before the NFS mount completes.

**Fix**:
```bash
# Manually mount to restore access
ssh hermes-admin@192.168.40.22 "sudo mount --bind /mnt/synology-root/hermes-admin/Photos /mnt/synology-photos"
ssh hermes-admin@192.168.40.22 "sudo mount -o remount,ro /mnt/synology-photos"
```

**Permanent Fix**: The fstab entries use `_netdev` to ensure network is available. For boot order issues, consider using systemd mount units instead of fstab.

**Verification**:
```bash
ssh hermes-admin@192.168.40.22 "ls /mnt/synology-photos/ | head -3"
# Should show photo files
```

---

#### Issue: Immich Shows "Click to upload your first photo"

**Resolved**: December 21, 2025

**Symptoms**:
- Immich web UI works but shows no photos
- External library not configured or not scanning

**Diagnosis**:
```bash
# Verify container can see external library
ssh hermes-admin@192.168.40.22 "sudo docker exec immich-server ls /usr/src/app/external/synology/ | wc -l"

# Check Immich logs for library scanning
ssh hermes-admin@192.168.40.22 "sudo docker logs immich-server 2>&1 | grep -i library"
```

**Thought Process**: The message appears when no photos are in Immich's library. If the NFS mounts are working but Immich shows no photos, either:
1. The Docker volume mappings are missing
2. The external library hasn't been configured in the UI
3. A library scan hasn't been triggered

**Root Cause**: Docker Compose file didn't have volume mappings for the Synology mounts.

**Fix**:
1. Update `/opt/immich/docker-compose.yml` with correct volume mappings
2. Restart Immich: `cd /opt/immich && sudo docker compose down && sudo docker compose up -d`
3. Add external library in Immich UI with path `/usr/src/app/external/synology`
4. Trigger library scan

**Verification**:
```bash
# Verify Immich API is healthy
ssh hermes-admin@192.168.40.22 "curl -s http://localhost:2283/api/server/ping"
# Expected: {"res":"pong"}
```

---

## Ansible Playbook Reference

The Immich Ansible playbook at `ansible/immich/deploy-immich.yml` automates the entire configuration:

### Key Variables

```yaml
# Synology NAS connection
nas_ip: "192.168.20.31"

# Mount points
synology_homes_share: "/volume2/homes"
synology_homes_mount: "/mnt/synology-root"
legacy_photos_source: "{{ synology_homes_mount }}/hermes-admin/Photos"
legacy_photos_mount: "/mnt/synology-photos"
immich_uploads_share: "/volume2/Immich Photos"
immich_uploads_mount: "/mnt/immich-uploads"

# Local directories
immich_local_dir: "/opt/immich"
```

### Playbook Tasks Summary

1. Install NFS client packages
2. Create mount point directories
3. Mount Synology homes (RO)
4. Create bind mount for legacy photos (RO)
5. Mount Immich uploads share (RW)
6. Create local directories for PostgreSQL and ML models
7. Create upload directory structure with marker files
8. Deploy Docker Compose configuration
9. Start Immich stack
10. Verify health

### Run Playbook

```bash
cd ~/ansible
ansible-playbook immich/deploy-immich.yml -l immich-vm01 -v
```

---

## Life Progress Widget (Glance)

**Host**: docker-vm-utilities01 (192.168.40.10)
**API Port**: 5051
**Configured**: December 22, 2025

### Life Progress Overview

The Life Progress widget displays visual progress bars showing how much of the current year, month, day, and life has passed. It includes daily motivational quotes about time and mortality to encourage mindful living.

**Features**:
- Horizontal progress bars with percentage display
- Year progress (red gradient)
- Month progress (yellow gradient)
- Day progress (green gradient)
- Life progress based on target age (green gradient)
- Daily rotating motivational quotes
- Updates every hour (configurable cache)

### Life Progress Architecture

The widget consists of two components:

| Component | Purpose | Location |
|-----------|---------|----------|
| Flask API | Calculates progress percentages and serves quotes | docker-vm-utilities01:5051 |
| Glance Widget | Renders HTML progress bars using API data | Glance dashboard |

**Data Flow**:
1. Glance dashboard requests `/progress` endpoint from Flask API
2. API calculates current progress for year/month/day/life
3. API selects quote based on day of year (consistent daily)
4. Glance renders HTML template with progress bar styling

### API Service Setup

#### Step 1: Create Service Directory

```bash
ssh hermes-admin@192.168.40.10 "sudo mkdir -p /opt/life-progress"
```

#### Step 2: Create Flask Application

Create `/opt/life-progress/app.py`:

```python
from flask import Flask, jsonify
from datetime import datetime, date
import calendar

app = Flask(__name__)

# Configuration - MODIFY THESE VALUES TO CUSTOMIZE
BIRTH_DATE = date(1989, 2, 14)  # Your birth date (YYYY, MM, DD)
TARGET_AGE = 75                  # Target lifespan in years

# Motivational quotes about time and mortality
QUOTES = [
    "Time is the most valuable thing a man can spend. - Theophrastus",
    "Lost time is never found again. - Benjamin Franklin",
    "The trouble is, you think you have time. - Buddha",
    "Your time is limited, don't waste it living someone else's life. - Steve Jobs",
    "Time flies over us, but leaves its shadow behind. - Nathaniel Hawthorne",
    "The way we spend our time defines who we are. - Jonathan Estrin",
    "Time is what we want most, but what we use worst. - William Penn",
    "Don't count the days, make the days count. - Muhammad Ali",
    "The only way to do great work is to love what you do. - Steve Jobs",
    "Life is what happens when you're busy making other plans. - John Lennon",
    "In the end, it's not the years in your life that count. It's the life in your years. - Abraham Lincoln",
    "Time is the coin of your life. Only you can determine how it will be spent. - Carl Sandburg",
    "Yesterday is gone. Tomorrow has not yet come. We have only today. - Mother Teresa",
    "The future is something which everyone reaches at the rate of 60 minutes an hour. - C.S. Lewis",
    "Time is a created thing. To say 'I don't have time' is to say 'I don't want to.' - Lao Tzu",
    "You may delay, but time will not. - Benjamin Franklin",
    "Time flies. It's up to you to be the navigator. - Robert Orben",
    "Better three hours too soon than a minute too late. - William Shakespeare",
    "The key is in not spending time, but in investing it. - Stephen R. Covey",
    "Time is the wisest counselor of all. - Pericles",
    "We must use time wisely and forever realize that the time is always ripe to do right. - Nelson Mandela",
    "Time waits for no one. - Folklore",
    "The two most powerful warriors are patience and time. - Leo Tolstoy",
    "How did it get so late so soon? - Dr. Seuss",
    "Time is a game played beautifully by children. - Heraclitus",
    "Forever is composed of nows. - Emily Dickinson",
    "Time and tide wait for no man. - Geoffrey Chaucer",
    "They always say time changes things, but you actually have to change them yourself. - Andy Warhol",
    "The bad news is time flies. The good news is you're the pilot. - Michael Altshuler",
    "Enjoy life. There's plenty of time to be dead. - Hans Christian Andersen"
]

def get_daily_quote():
    """Get a consistent quote for the day based on date"""
    today = date.today()
    day_of_year = today.timetuple().tm_yday
    return QUOTES[day_of_year % len(QUOTES)]

def calculate_progress():
    now = datetime.now()
    today = date.today()

    # Year progress (0-100)
    year_start = datetime(now.year, 1, 1)
    year_end = datetime(now.year + 1, 1, 1)
    year_progress = ((now - year_start).total_seconds() / (year_end - year_start).total_seconds()) * 100

    # Month progress (0-100)
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    month_progress = ((now.day - 1 + now.hour/24 + now.minute/1440) / days_in_month) * 100

    # Day progress (0-100)
    day_progress = ((now.hour * 3600 + now.minute * 60 + now.second) / 86400) * 100

    # Life progress (0-100)
    target_date = date(BIRTH_DATE.year + TARGET_AGE, BIRTH_DATE.month, BIRTH_DATE.day)
    total_life_days = (target_date - BIRTH_DATE).days
    days_lived = (today - BIRTH_DATE).days
    life_progress = (days_lived / total_life_days) * 100

    return {
        "year": round(year_progress, 1),
        "month": round(month_progress, 1),
        "day": round(day_progress, 1),
        "life": round(life_progress, 1),
        "age": round(days_lived / 365.25, 1),
        "remaining_years": round((total_life_days - days_lived) / 365.25, 1),
        "remaining_days": total_life_days - days_lived,
        "quote": get_daily_quote(),
        "target_age": TARGET_AGE
    }

@app.route('/progress')
def progress():
    return jsonify(calculate_progress())

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051)
```

**Configuration Variables**:

| Variable | Description | How to Change |
|----------|-------------|---------------|
| `BIRTH_DATE` | Your birth date | Edit `date(YYYY, MM, DD)` format |
| `TARGET_AGE` | Target lifespan for life progress | Change integer value |
| `QUOTES` | List of daily motivational quotes | Add/remove/modify strings |

#### Step 3: Create Dockerfile

Create `/opt/life-progress/Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install flask gunicorn
COPY app.py .
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5051", "app:app"]
```

#### Step 4: Create Docker Compose

Create `/opt/life-progress/docker-compose.yml`:

```yaml
services:
  life-progress:
    build: .
    container_name: life-progress
    restart: unless-stopped
    ports:
      - "5051:5051"
    environment:
      - TZ=Asia/Manila
```

#### Step 5: Deploy the Service

```bash
ssh hermes-admin@192.168.40.10 "cd /opt/life-progress && sudo docker compose up -d --build"
```

#### Step 6: Verify API

```bash
# Test the API endpoint
curl http://192.168.40.10:5051/progress
```

**Expected Response**:
```json
{
  "year": 98.3,
  "month": 70.5,
  "day": 45.2,
  "life": 47.8,
  "age": 35.9,
  "remaining_years": 39.1,
  "remaining_days": 14289,
  "quote": "Time is the most valuable thing a man can spend. - Theophrastus",
  "target_age": 75
}
```

### Glance Widget Configuration

The widget is configured in `/opt/glance/config/glance.yml` on docker-vm-utilities01.

**Widget Configuration**:

```yaml
- type: custom-api
  title: Life Progress
  cache: 1h
  url: http://192.168.40.10:5051/progress
  template: |
    <div style="font-family: sans-serif; padding: 10px;">
      <div style="display: flex; align-items: center; margin-bottom: 12px;">
        <span style="width: 60px; font-weight: bold; color: #fff;">Year</span>
        <div style="flex: 1; height: 24px; background: #444; border-radius: 4px; position: relative; margin: 0 15px;">
          <div style="width: {{ .JSON.Float "year" }}%; height: 100%; background: linear-gradient(90deg, #ff4444, #ff6666); border-radius: 4px;"></div>
          <span style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #fff; font-weight: bold; text-shadow: 1px 1px 2px #000;">{{ .JSON.Float "year" | printf "%.1f" }}%</span>
        </div>
      </div>
      <div style="display: flex; align-items: center; margin-bottom: 12px;">
        <span style="width: 60px; font-weight: bold; color: #fff;">Month</span>
        <div style="flex: 1; height: 24px; background: #444; border-radius: 4px; position: relative; margin: 0 15px;">
          <div style="width: {{ .JSON.Float "month" }}%; height: 100%; background: linear-gradient(90deg, #ffaa00, #ffcc44); border-radius: 4px;"></div>
          <span style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #fff; font-weight: bold; text-shadow: 1px 1px 2px #000;">{{ .JSON.Float "month" | printf "%.1f" }}%</span>
        </div>
      </div>
      <div style="display: flex; align-items: center; margin-bottom: 12px;">
        <span style="width: 60px; font-weight: bold; color: #fff;">Day</span>
        <div style="flex: 1; height: 24px; background: #444; border-radius: 4px; position: relative; margin: 0 15px;">
          <div style="width: {{ .JSON.Float "day" }}%; height: 100%; background: linear-gradient(90deg, #44aa44, #66cc66); border-radius: 4px;"></div>
          <span style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #fff; font-weight: bold; text-shadow: 1px 1px 2px #000;">{{ .JSON.Float "day" | printf "%.1f" }}%</span>
        </div>
      </div>
      <div style="display: flex; align-items: center; margin-bottom: 12px;">
        <span style="width: 60px; font-weight: bold; color: #fff;">Life</span>
        <div style="flex: 1; height: 24px; background: #444; border-radius: 4px; position: relative; margin: 0 15px;">
          <div style="width: {{ .JSON.Float "life" }}%; height: 100%; background: linear-gradient(90deg, #44aa44, #66cc66); border-radius: 4px;"></div>
          <span style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #fff; font-weight: bold; text-shadow: 1px 1px 2px #000;">{{ .JSON.Float "life" | printf "%.1f" }}%</span>
        </div>
      </div>
      <div style="text-align: center; margin-top: 15px; padding: 10px; background: rgba(255,255,255,0.1); border-radius: 8px;">
        <em style="color: #aaa; font-size: 14px;">"{{ .JSON.String "quote" }}"</em>
      </div>
    </div>
```

**Template Syntax Notes**:

| Syntax | Purpose |
|--------|---------|
| `{{ .JSON.Float "field" }}` | Access float/number fields from JSON |
| `{{ .JSON.String "field" }}` | Access string fields from JSON |
| `{{ .JSON.Int "field" }}` | Access integer fields from JSON |
| `| printf "%.1f"` | Format number to 1 decimal place |

### Life Progress Customization

#### Changing Birth Date

Edit `/opt/life-progress/app.py` line 9:

```python
BIRTH_DATE = date(1989, 2, 14)  # Change to your birth date (YYYY, MM, DD)
```

Then rebuild the container:

```bash
ssh hermes-admin@192.168.40.10 "cd /opt/life-progress && sudo docker compose up -d --build"
```

#### Changing Target Age

Edit `/opt/life-progress/app.py` line 10:

```python
TARGET_AGE = 75  # Change to your target age
```

Then rebuild the container.

#### Adding or Modifying Quotes

Edit the `QUOTES` list in `/opt/life-progress/app.py`. The quote is selected based on the day of year using `day_of_year % len(QUOTES)`, so each day consistently shows the same quote.

To add a quote, append to the list:

```python
QUOTES = [
    # ... existing quotes ...
    "Your new quote here. - Author",
]
```

#### Changing Colors

Edit the Glance widget template in `/opt/glance/config/glance.yml`:

| Progress Bar | Gradient Colors |
|--------------|-----------------|
| Year | `#ff4444` to `#ff6666` (red) |
| Month | `#ffaa00` to `#ffcc44` (yellow/orange) |
| Day | `#44aa44` to `#66cc66` (green) |
| Life | `#44aa44` to `#66cc66` (green) |

Modify the `background: linear-gradient(...)` values to change colors.

#### Changing Cache Duration

Edit the `cache` value in the widget configuration:

```yaml
- type: custom-api
  cache: 1h  # Options: 30s, 1m, 5m, 1h, etc.
```

### Life Progress Maintenance

#### Rebuild Container After Changes

```bash
ssh hermes-admin@192.168.40.10 "cd /opt/life-progress && sudo docker compose up -d --build"
```

#### View Logs

```bash
ssh hermes-admin@192.168.40.10 "sudo docker logs life-progress"
```

#### Restart Service

```bash
ssh hermes-admin@192.168.40.10 "sudo docker restart life-progress"
```

#### Test API

```bash
curl http://192.168.40.10:5051/progress | jq
```

---

## Glance Dashboard Theming

**Host**: docker-vm-utilities01 (192.168.40.10)
**Configured**: December 22, 2025

### Theme Overview

Glance dashboard supports multiple color themes with a built-in theme picker. Users can switch between themes using the palette icon in the top-right corner of the dashboard.

**Available Themes**:

| Theme | Description | Primary Color |
|-------|-------------|---------------|
| Catppuccin Mocha | Soft pastel dark theme (default) | Purple/Pink |
| Midnight Blue | Deep blue professional | Blue |
| Nord | Arctic, cool blue-gray palette | Cyan |
| Dracula | Popular purple-based dark theme | Purple |
| Monokai | Classic code editor theme | Pink/Magenta |
| Gruvbox Dark | Warm retro theme | Yellow/Orange |
| Solarized Dark | Ethan Schoonover's classic | Blue |
| Tokyo Night | VSCode-inspired Japanese theme | Blue/Purple |
| Cyberpunk | Neon futuristic theme | Magenta/Neon |
| Classic Dark | Original minimal dark theme | Gold |

### How Theming Works

Glance uses HSL (Hue, Saturation, Lightness) color format for theme definitions:

```yaml
theme:
  background-color: 240 21 15      # HSL values: Hue Saturation Lightness
  primary-color: 267 84 81         # Purple accent
  positive-color: 115 54 76        # Green for success states
  negative-color: 343 81 75        # Red for error states
  contrast-multiplier: 1.2         # Text contrast adjustment
```

**Theme Properties Explained**:

| Property | Purpose | Format |
|----------|---------|--------|
| `background-color` | Page and widget background | H S L (space-separated) |
| `primary-color` | Main accent color | H S L |
| `positive-color` | Online/success status indicators | H S L |
| `negative-color` | Error/offline status indicators | H S L |
| `contrast-multiplier` | Text visibility adjustment (1.0-1.5) | Decimal |

### Using the Theme Picker

1. **Access**: Click the palette icon (🎨) in the top-right corner of any Glance page
2. **Select**: Click on any theme swatch to apply it instantly
3. **Persist**: Theme selection is stored in browser localStorage and persists across sessions

### Custom CSS Enhancements

Additional styling is provided via `/opt/glance/assets/custom-themes.css`:

**Features**:
- Smooth color transitions when switching themes (0.3s ease)
- Rounded widget corners (12px border-radius)
- Subtle hover effects on widgets
- Glassmorphism effects (backdrop-filter: blur)
- Fade-in animations for widgets
- Custom scrollbar styling
- Enhanced theme picker dropdown styling

### Configuration Files

| File | Purpose |
|------|---------|
| `/opt/glance/config/glance.yml` | Theme presets and widget configuration |
| `/opt/glance/assets/custom-themes.css` | Additional CSS styling |

### Adding a New Theme

To add a custom theme preset, edit `/opt/glance/config/glance.yml`:

```yaml
theme:
  presets:
    your-theme-name:
      background-color: H S L    # Background color in HSL
      primary-color: H S L       # Accent color
      positive-color: H S L      # Success/online color
      negative-color: H S L      # Error/offline color
      contrast-multiplier: 1.2   # Text contrast (1.0-1.5)
```

**Converting Colors to HSL**:

1. Use a tool like [HSL Color Picker](https://hslpicker.com/)
2. Enter your hex color (e.g., `#282a36`)
3. Note the HSL values (e.g., `231° 15% 18%`)
4. Format as space-separated: `231 15 18`

**Example - Creating "Ocean" Theme**:

```yaml
ocean:
  background-color: 200 50 10    # Deep ocean blue
  primary-color: 180 80 50      # Teal accent
  positive-color: 140 60 45     # Sea green
  negative-color: 0 70 60       # Coral red
  contrast-multiplier: 1.2
```

After editing, restart Glance:

```bash
ssh hermes-admin@192.168.40.10 "cd /opt/glance && sudo docker compose restart"
```

### Theme Design Reference

**Popular Theme Color Sources**:

| Theme | Source/Inspiration |
|-------|-------------------|
| Nord | [nordtheme.com](https://www.nordtheme.com/) |
| Dracula | [draculatheme.com](https://draculatheme.com/) |
| Catppuccin | [catppuccin.com](https://catppuccin.com/) |
| Gruvbox | [github.com/morhetz/gruvbox](https://github.com/morhetz/gruvbox) |
| Solarized | [ethanschoonover.com/solarized](https://ethanschoonover.com/solarized/) |
| Tokyo Night | [github.com/enkia/tokyo-night-vscode-theme](https://github.com/enkia/tokyo-night-vscode-theme) |

### Deployment via Ansible

The themes are deployed using the Glance Ansible playbook:

```bash
cd ~/ansible
ansible-playbook glance/deploy-glance-dashboard.yml
```

This playbook:
1. Creates the config directory structure
2. Deploys `custom-themes.css` to the assets folder
3. Deploys `glance.yml` with all theme presets
4. Restarts the Glance container

---

## Authentik SSO Configuration

**Host**: authentik-vm01 (192.168.40.21)
**External URL**: https://auth.hrmsmrflrii.xyz
**Version**: 2025.10.3
**Configured**: December 24, 2025

### Authentik Overview

Authentik is deployed as the central identity provider for the homelab. It provides:

- **Single Sign-On (SSO)**: One login for all services
- **OAuth2/OpenID Connect**: Industry-standard protocols for application integration
- **Forward Authentication**: Proxy-based auth for legacy services via Traefik
- **Social Login**: External identity providers (Google, GitHub, Discord, etc.)
- **Application Dashboard**: Centralized application launcher

**Architecture**:

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Traefik (Reverse Proxy)                     │
│                   traefik.hrmsmrflrii.xyz                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐    ┌──────────────────┐    ┌────────────────────┐
│  Authentik    │    │   Applications   │    │   Forward Auth     │
│ (IdP Server)  │◄───┤  (OIDC Clients)  │    │   Protected Apps   │
│               │    │                  │    │                    │
│ - OAuth2      │    │ - GitLab         │    │ - Traefik Dash     │
│ - OIDC        │    │ - Portainer      │    │ - Proxmox          │
│ - SAML        │    │ - (future apps)  │    │ - Grafana          │
└───────────────┘    └──────────────────┘    └────────────────────┘
```

### GitLab OIDC Integration

GitLab is configured to use Authentik as an OpenID Connect (OIDC) provider, enabling users to log in with their Authentik credentials.

#### How It Works

1. User clicks "Sign in with Authentik" on GitLab login page
2. GitLab redirects to Authentik authorization endpoint
3. User authenticates with Authentik (password or social login)
4. Authentik issues authorization code and redirects back to GitLab
5. GitLab exchanges code for tokens and creates/links user account

#### Authentik Configuration

**OAuth2/OIDC Provider Settings**:

| Setting | Value |
|---------|-------|
| Name | `gitlab-oidc-provider` |
| Client ID | `gitlab` |
| Client Type | Confidential |
| Authorization Flow | default-provider-authorization-implicit-consent |
| Redirect URI | `https://gitlab.hrmsmrflrii.xyz/users/auth/openid_connect/callback` |
| Sub Mode | Hashed User ID |
| Include Claims in ID Token | Yes |
| Issuer Mode | Per Provider |

**Application Settings**:

| Setting | Value |
|---------|-------|
| Name | GitLab |
| Slug | `gitlab` |
| Group | DevOps |
| Launch URL | https://gitlab.hrmsmrflrii.xyz |
| Icon | application-icons/gitlab.png |
| Provider | gitlab-oidc-provider |

**OIDC Endpoints**:

| Endpoint | URL |
|----------|-----|
| Discovery | `https://auth.hrmsmrflrii.xyz/application/o/gitlab/.well-known/openid-configuration` |
| Authorization | `https://auth.hrmsmrflrii.xyz/application/o/authorize/` |
| Token | `https://auth.hrmsmrflrii.xyz/application/o/token/` |
| Userinfo | `https://auth.hrmsmrflrii.xyz/application/o/userinfo/` |

#### GitLab Configuration

The GitLab docker-compose includes OmniAuth OIDC configuration:

```yaml
# In GITLAB_OMNIBUS_CONFIG environment variable
gitlab_rails['omniauth_enabled'] = true
gitlab_rails['omniauth_allow_single_sign_on'] = ['openid_connect']
gitlab_rails['omniauth_block_auto_created_users'] = false
gitlab_rails['omniauth_auto_link_user'] = ['openid_connect']
gitlab_rails['omniauth_sync_email_from_provider'] = 'openid_connect'
gitlab_rails['omniauth_sync_profile_from_provider'] = ['openid_connect']
gitlab_rails['omniauth_sync_profile_attributes'] = ['email', 'name']

gitlab_rails['omniauth_providers'] = [
  {
    name: "openid_connect",
    label: "Authentik",
    icon: "https://auth.hrmsmrflrii.xyz/static/dist/assets/icons/icon.png",
    args: {
      name: "openid_connect",
      scope: ["openid", "profile", "email"],
      response_type: "code",
      issuer: "https://auth.hrmsmrflrii.xyz/application/o/gitlab/",
      discovery: true,
      client_auth_method: "basic",
      uid_field: "sub",
      pkce: true,
      client_options: {
        identifier: "gitlab",
        secret: "YOUR_CLIENT_SECRET",
        redirect_uri: "https://gitlab.hrmsmrflrii.xyz/users/auth/openid_connect/callback"
      }
    }
  }
]
```

**User Behavior**:

| Scenario | Behavior |
|----------|----------|
| New User (no GitLab account) | Auto-created on first SSO login |
| Existing User (matching email) | Linked by email address |
| Profile Changes in Authentik | Synced to GitLab (email, name) |

#### Ansible Automation

Deploy GitLab SSO integration using the Ansible playbook:

```bash
# Set Authentik API token
export AUTHENTIK_TOKEN="your-token-here"

# Run the playbook
cd ~/ansible
ansible-playbook authentik/configure-gitlab-sso.yml
```

The playbook (`ansible-playbooks/authentik/configure-gitlab-sso.yml`):
1. Creates OAuth2/OIDC provider in Authentik
2. Creates Application linked to provider
3. Updates GitLab docker-compose with OmniAuth config
4. Restarts and reconfigures GitLab

### OAuth Sources

OAuth sources allow users to authenticate to Authentik using external identity providers (social login).

#### Configured Sources

| Provider | Status | Notes |
|----------|--------|-------|
| Google | ✅ Active | Primary social login |
| GitHub | ⏳ Ready | Requires credentials |
| Discord | ⏳ Ready | Requires credentials |
| Reddit | ⏳ Ready | Requires credentials |
| Apple | ⏳ Ready | Requires credentials |
| Facebook | ⏳ Ready | Requires credentials |
| Telegram | ⏳ Ready | Requires bot token |

#### Setting Up OAuth Sources

Each OAuth source requires creating a developer application on the provider platform:

**GitHub**:
1. Go to https://github.com/settings/developers
2. Create new OAuth App
3. Callback URL: `https://auth.hrmsmrflrii.xyz/source/oauth/callback/github/`
4. Get Client ID and Client Secret

**Discord**:
1. Go to https://discord.com/developers/applications
2. Create new application
3. OAuth2 > Add Redirect: `https://auth.hrmsmrflrii.xyz/source/oauth/callback/discord/`
4. Get Client ID and Client Secret

**Reddit**:
1. Go to https://www.reddit.com/prefs/apps
2. Create new "web app"
3. Redirect URI: `https://auth.hrmsmrflrii.xyz/source/oauth/callback/reddit/`
4. Get Client ID (under app name) and Secret

**Facebook**:
1. Go to https://developers.facebook.com/apps
2. Create new app (Consumer type)
3. Add Facebook Login product
4. Valid OAuth Redirect: `https://auth.hrmsmrflrii.xyz/source/oauth/callback/facebook/`
5. Get App ID and App Secret

**Apple**:
1. Go to https://developer.apple.com/account/resources/identifiers/list
2. Create Services ID with Sign In with Apple
3. Return URL: `https://auth.hrmsmrflrii.xyz/source/oauth/callback/apple/`
4. Generate Key for Client Secret

**Telegram**:
1. Message @BotFather on Telegram
2. Create new bot with `/newbot`
3. Get bot token
4. Set domain with `/setdomain` to `auth.hrmsmrflrii.xyz`

#### Ansible Playbook for OAuth Sources

Use the OAuth sources playbook to configure multiple providers:

```bash
# Set credentials as environment variables
export GITHUB_CLIENT_ID="your-github-client-id"
export GITHUB_CLIENT_SECRET="your-github-client-secret"
export DISCORD_CLIENT_ID="your-discord-client-id"
export DISCORD_CLIENT_SECRET="your-discord-client-secret"
# ... etc

# Run playbook
ansible-playbook authentik/configure-oauth-sources.yml
```

The playbook (`ansible-playbooks/authentik/configure-oauth-sources.yml`) creates sources for all configured providers.

### Application Dashboard Organization

Authentik's application dashboard organizes apps into groups for easy access.

#### Current Groups

| Group | Applications |
|-------|-------------|
| DevOps | GitLab |
| Dashboards | Glance, Portainer |
| Download Clients | Deluge, SABnzbd |
| Media | Jellyfin, Radarr, Sonarr, Lidarr, Prowlarr, Bazarr, Jellyseerr, Tdarr |
| Monitoring & Observability | Uptime Kuma, Grafana, Prometheus, Jaeger |

#### Setting Application Groups

Via Authentik Admin UI:
1. Go to Applications > Applications
2. Click on the application
3. In "UI settings", set the Group field
4. Click Update

Via API:
```bash
curl -X PATCH "http://192.168.40.21:9000/api/v3/core/applications/APP_SLUG/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"meta_group": "DevOps"}'
```

#### Setting Application Icons

Icons are stored in `/opt/authentik/media/application-icons/`:

```bash
# Download icon
ssh hermes-admin@192.168.40.21 "sudo curl -o /opt/authentik/media/application-icons/gitlab.png https://about.gitlab.com/images/press/logo/png/gitlab-icon-rgb.png"

# Set permissions
ssh hermes-admin@192.168.40.21 "sudo chmod 644 /opt/authentik/media/application-icons/gitlab.png"

# Update application via database
ssh hermes-admin@192.168.40.21 "sudo docker exec authentik-postgres psql -U authentik -d authentik -c \"UPDATE authentik_core_application SET meta_icon = 'application-icons/gitlab.png' WHERE slug = 'gitlab';\""
```

### Authentik Troubleshooting

#### Issue: GitLab SSO Redirect Loop

**Symptoms**:
- Clicking "Sign in with Authentik" redirects back to login page
- No error message displayed

**Root Cause**: Redirect URI mismatch between GitLab config and Authentik provider.

**Diagnosis**:
```bash
# Check GitLab logs
ssh hermes-admin@192.168.40.23 "docker logs gitlab 2>&1 | grep -i oauth"

# Verify Authentik provider redirect URI
curl -s -H "Authorization: Bearer TOKEN" \
  "http://192.168.40.21:9000/api/v3/providers/oauth2/?name=gitlab-oidc-provider" | jq '.results[0].redirect_uris'
```

**Fix**: Ensure redirect URIs match exactly:
- Authentik: `https://gitlab.hrmsmrflrii.xyz/users/auth/openid_connect/callback`
- GitLab: Same URI in `redirect_uri` client option

---

#### Issue: Application Not Showing on Dashboard

**Symptoms**:
- Application created but not visible on user dashboard
- Can access application directly via URL

**Root Cause**: Application not assigned to outpost or user doesn't have access.

**Diagnosis**:
```bash
# Check if application exists
curl -s -H "Authorization: Bearer TOKEN" \
  "http://192.168.40.21:9000/api/v3/core/applications/" | jq '.results[] | {name, slug}'

# Check outpost bindings
curl -s -H "Authorization: Bearer TOKEN" \
  "http://192.168.40.21:9000/api/v3/outposts/instances/" | jq '.results[] | {name, providers}'
```

**Fix**:
1. Ensure provider is assigned to Embedded Outpost
2. Check application policy allows user access
3. Verify application has a linked provider

---

#### Issue: OAuth Source Login Fails

**Symptoms**:
- "Invalid request" or "redirect_uri_mismatch" error
- Login button does nothing

**Root Cause**: Callback URL mismatch in OAuth provider configuration.

**Fix**: Verify callback URL format for each provider:
- Must be HTTPS
- Must match exactly: `https://auth.hrmsmrflrii.xyz/source/oauth/callback/PROVIDER_SLUG/`
- Trailing slash is required

---

## Related Documentation

- [Services](./SERVICES.md) - Service overview and ports
- [Storage](./STORAGE.md) - NFS and storage configuration
- [Networking](./NETWORKING.md) - Service URLs and DNS
- [Ansible](./ANSIBLE.md) - Deployment automation
- [Troubleshooting](./TROUBLESHOOTING.md) - Common issues
