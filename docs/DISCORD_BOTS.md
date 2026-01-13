# Discord Bots

This document describes the Discord bot deployed in the homelab for automation and notifications.

## Overview

| Bot | Host | Port | Purpose |
|-----|------|------|---------|
| **Sentinel** | docker-vm-core-utilities01 (192.168.40.13) | 5050 | Consolidated homelab management bot |

> **Note**: Sentinel consolidates the functionality of 4 previous bots (Argus, Chronos, Mnemosyne, Athena) into a single modular bot with channel routing.

---

## Sentinel - Unified Homelab Bot

**Location**: `/opt/sentinel-bot/`
**Container**: `sentinel-bot`
**Webhook Port**: 5050
**Status**: Deployed January 2026

### Features

- **Modular Cog Architecture**: 7 specialized cogs for different functionality
- **Channel Routing**: Automatic notification routing to appropriate channels
- **Progress Bars**: Live progress indicators for all long-running commands
- **Reaction-Based Approvals**: Thumbs up to approve container updates
- **REST API**: Task queue endpoints for Claude Code integration
- **Webhook Receiver**: Watchtower and Jellyseerr integration
- **SQLite Database**: Persistent storage for tasks, updates, and downloads

### Architecture

```
Discord Server (Hermes HomeLab)
│
├── #homelab-infrastructure ──► Sentinel (Homelab Cog)
│                                 ├── /homelab status, uptime
│                                 ├── /node, /vm, /lxc commands
│                                 └── SSH to Proxmox nodes (root)
│
├── #container-updates ────────► Sentinel (Updates Cog)
│                                 ├── /check, /update, /vmcheck
│                                 ├── Watchtower webhooks
│                                 └── Reaction-based approvals
│
├── #media-downloads ──────────► Sentinel (Media Cog)
│                                 ├── /downloads, /download, /search
│                                 ├── /library movies/shows/stats
│                                 ├── Radarr/Sonarr API integration
│                                 └── Download progress notifications
│
├── #project-management ───────► Sentinel (GitLab Cog)
│                                 ├── /todo, /issues, /close
│                                 ├── /quick (bulk create)
│                                 └── GitLab API integration
│
├── #claude-tasks ─────────────► Sentinel (Tasks Cog)
│                                 ├── /task, /queue, /status
│                                 ├── /done, /cancel, /taskstats
│                                 └── REST API for Claude instances
│
└── #new-service-onboarding ───► Sentinel (Onboarding Cog)
                                  ├── /onboard, /onboard-all
                                  ├── DNS, Traefik, SSL checks
                                  └── Daily 9am status report

Infrastructure:
┌─────────────────────────────────────────────────────────────────┐
│  VM 107: docker-vm-core-utilities01 (192.168.40.13)             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Sentinel Bot Container                                      ││
│  │   ├── Discord Gateway (discord.py 2.3+)                     ││
│  │   ├── Webhook Server (Quart/Hypercorn :5050)                ││
│  │   ├── SSH Manager (asyncssh)                                ││
│  │   ├── SQLite Database (/app/data/sentinel.db)               ││
│  │   └── 7 Cogs (homelab, updates, media, gitlab, tasks,       ││
│  │          onboarding, scheduler)                             ││
│  └─────────────────────────────────────────────────────────────┘│
│  8GB RAM | 4 vCPU | 50GB Disk                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Cog Modules

| Cog | File | Channel | Commands |
|-----|------|---------|----------|
| **Homelab** | `cogs/homelab.py` | #homelab-infrastructure | `/homelab`, `/node`, `/vm`, `/lxc` |
| **Updates** | `cogs/updates.py` | #container-updates | `/check`, `/update`, `/restart`, `/logs`, `/vmcheck`, `/updateall`, `/checknow`, `/updateschedule` |
| **Media** | `cogs/media.py` | #media-downloads | `/downloads`, `/download`, `/search`, `/library`, `/recent` |
| **GitLab** | `cogs/gitlab.py` | #project-management | `/todo`, `/issues`, `/close`, `/quick`, `/project` |
| **Tasks** | `cogs/tasks.py` | #claude-tasks | `/task`, `/queue`, `/status`, `/done`, `/cancel`, `/taskstats` |
| **Onboarding** | `cogs/onboarding.py` | #new-service-onboarding | `/onboard`, `/onboard-all`, `/onboard-services` |
| **Power** | `cogs/power.py` | #homelab-infrastructure | `/shutdownall`, `/shutdown-nodns`, `/startall` |
| **Scheduler** | `cogs/scheduler.py` | Various | Background tasks (7pm updates, download monitoring) |

---

## Commands Reference

### Infrastructure Commands (#homelab-infrastructure)

| Command | Description |
|---------|-------------|
| `/help` | Show all Sentinel commands in a formatted embed |
| `/insight` | Health check: memory, errors, storage, failed downloads |
| `/homelab status` | Cluster overview (CPU, RAM, uptime per node) |
| `/homelab uptime` | Uptime for all Proxmox nodes and Docker hosts |
| `/node <name> status` | Detailed status for a Proxmox node |
| `/node <name> vms` | List VMs on a node with status |
| `/node <name> lxc` | List LXC containers on a node |
| `/node <name> restart` | Restart a Proxmox node (with confirmation) |
| `/vm <id> status` | Get VM status |
| `/vm <id> start/stop/restart` | Control a VM |
| `/lxc <id> status` | Get LXC container status |
| `/lxc <id> start/stop/restart` | Control an LXC container |

### Power Management Commands (#homelab-infrastructure)

| Command | Description |
|---------|-------------|
| `/shutdownall` | Gracefully shutdown ALL VMs, LXCs, and Proxmox nodes |
| `/shutdown-nodns` | Shutdown all except Pi-hole (LXC 202) and node01 (DNS stays online) |
| `/startall` | Wake all nodes via Wake-on-LAN and start all VMs/LXCs |

**Power Management System** (Added January 2026):

Safe cluster-wide power management with confirmation prompts and progress tracking.

**Shutdown Order (Safety-Critical)**:
1. Stop all VMs (gracefully, per node)
2. Stop all LXC containers
3. Shutdown Proxmox nodes (node03 → node02 → node01)

**Startup Order**:
1. Send Wake-on-LAN to all nodes
2. Wait for nodes to come online (5-min timeout each)
3. Start LXCs (Pi-hole first for DNS)
4. Start all VMs

**Wake-on-LAN Configuration**:
| Node | MAC Address |
|------|-------------|
| node01 | `38:05:25:32:82:76` |
| node02 | `84:47:09:4d:7a:ca` |
| node03 | `d8:43:ae:a8:4c:a7` |

**Confirmation Flow**:
```
/shutdownall
    │
    ▼
Show summary (VMs, LXCs, nodes to shutdown)
    │
    ▼
Wait for ⚠️ reaction to confirm (or ❌ to cancel)
    │
    ▼
Execute shutdown phases with progress updates
    │
    ▼
Send completion report
```

**Important Notes**:
- `/shutdown-nodns` keeps Pi-hole (LXC 202) and node01 running for DNS availability
- Sentinel Bot runs on node02, so `/shutdownall` will shut down the bot itself (final report sent before node02 shutdown)
- All commands require reaction-based confirmation within 60 seconds

### Container Updates (#container-updates)

| Command | Description |
|---------|-------------|
| `/check` | Scan all containers for available updates |
| `/update <container>` | Update a specific container |
| `/restart <container>` | Restart a container |
| `/containers` | List all monitored containers |
| `/logs <container> [lines]` | View container logs (default 50 lines) |
| `/vmcheck` | Check all VMs for apt package updates |
| `/updateall` | **Check and update ALL VMs, containers, and LXCs** (with approval) |
| `/checknow` | Manually trigger scheduled update check |
| `/updateschedule` | Show automatic update check schedule |

**Automated Infrastructure Update System** (Added January 2026):

The `/updateall` command provides comprehensive infrastructure updates:
1. **VMs**: apt upgrade on all service VMs (8 hosts)
2. **Docker Containers**: Pull latest images and restart (35+ containers)
3. **LXC Containers**: apt upgrade inside LXC containers (4 LXCs)

**Workflow**:
```
/updateall
    │
    ▼
Phase 1: Check all resources
    │
    ▼
Show summary with update counts
    │
    ▼
Wait for 👍 approval
    │
    ▼
Apply updates (VMs → Containers → LXCs)
    │
    ▼
Send completion report
```

**Scheduled Automatic Checks**:
- Bot automatically checks for updates at **6:00 AM** and **6:00 PM UTC** daily
- If updates found, sends notification to #container-updates with thumbs up reaction
- Updates only applied after user approval

**Reaction-Based Approval Flow**:
1. Bot posts update notification with container list
2. React with :thumbsup: to approve ALL updates
3. React with 1️⃣, 2️⃣, etc. to approve individual updates
4. Bot executes approved updates and reports status

### Media Commands (#media-downloads)

| Command | Description |
|---------|-------------|
| `/downloads` | Show current download queues with visual progress bars |
| `/download <title> [type]` | Request a movie or TV show via Jellyseerr |
| `/search <query> [type]` | Search media without downloading |
| `/library movies [limit]` | List movies in Radarr library |
| `/library shows [limit]` | List TV shows in Sonarr library |
| `/library stats` | Library statistics (counts, sizes) |
| `/recent [type]` | Recently added media |

**`/downloads` Output Format** (Updated January 2026):
```
📥 Download Queue

🎬 Movies (2)
`[████████░░]`  80.5% | Interstellar.2014.2160p.UHD
`[██░░░░░░░░]`  20.0% | The.Matrix.1999.4K

📺 TV Shows (54)
`[██████████]` 100.0% | House.of.the.Dragon.S02E05
`[█████░░░░░]`  50.0% | The.Sandman.S02E01
...
```

**Automatic Notifications**:
- Download completion notifications (100% only to reduce spam)
- Completion notifications with Jellyfin links
- Poster images embedded
- **Failed download alerts** with reaction-based removal (react with 🗑️ to remove)

### GitLab Commands (#project-management)

| Command | Description |
|---------|-------------|
| `/todo <description> [priority]` | Create a new GitLab issue |
| `/issues [limit]` | List open issues |
| `/close <id>` | Close an issue |
| `/quick <tasks>` | Bulk create issues (semicolon-separated) |
| `/project` | Show GitLab project info |

**Priority Options**: high, medium (default), low

### Claude Task Commands (#claude-tasks)

| Command | Description |
|---------|-------------|
| `/task <description> [priority]` | Submit a new task for Claude |
| `/queue [limit]` | View pending tasks |
| `/status` | Claude instance status |
| `/done [limit]` | View completed tasks |
| `/cancel <id>` | Cancel a pending task |
| `/taskstats` | Queue statistics |

### Onboarding Commands (#new-service-onboarding)

| Command | Description |
|---------|-------------|
| `/onboard <service>` | Check single service (DNS, Traefik, SSL, Authentik, Docs) |
| `/onboard-all` | Check all 27 tracked services (parallel checks, table format) |
| `/onboard-services` | List known services by category |

**Checks Performed**:
- **DNS**: Resolves `service.hrmsmrflrii.xyz` via Pi-hole (192.168.90.53)
- **Traefik**: Route exists in `/opt/traefik/config/dynamic/`
- **SSL**: Valid certificate (openssl verify)
- **Authentik**: Provider exists (optional)
- **Docs**: Mentioned in `docs/` directory (optional)

**Table Format Output** (as of January 2026):
```
Service          DNS TRF SSL
grafana          🟢  🟢  🟢
prometheus       🟢  🟢  🟢
uptime-kuma      🟢  🟢  🟢
...
```
- 🟢 = Configured/passing
- 🔴 = Missing/failing
- Parallel checks for speed (~10 seconds for all 27 services)
- Color-coded embed border (green=all good, yellow=few issues, red=many issues)

---

## REST API Endpoints

Base URL: `http://192.168.40.13:5050`

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |

### Task Queue (Claude Integration)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tasks` | GET | List pending tasks |
| `/api/tasks` | POST | Create new task |
| `/api/tasks/<id>/claim` | POST | Claim a task for processing |
| `/api/tasks/<id>/complete` | POST | Mark task as completed |

### Webhooks

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook/watchtower` | POST | Container update notifications |
| `/webhook/jellyseerr` | POST | Media request notifications |

---

## Scheduled Tasks

| Task | Schedule | Channel |
|------|----------|---------|
| **Infrastructure Update Check** | 6:00 AM & 6:00 PM UTC daily | #container-updates |
| Container Update Report | 7:00 PM daily | #container-updates |
| Download Progress Check | Every 60 seconds | #media-downloads |
| Failed Download Check | Every 5 minutes | #media-downloads |
| Onboarding Status Report | 9:00 AM daily | #new-service-onboarding |
| Stale Task Cleanup | Every 30 minutes | (internal) |

**Infrastructure Update Check Details**:
- Checks all VMs for apt package updates
- Checks all LXC containers for apt package updates
- If updates found, sends notification with approval reaction
- User approves with thumbs up to apply updates
- Comprehensive report sent after completion

---

## Database Schema

SQLite database at `/app/data/sentinel.db`

```sql
-- Claude Tasks
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending, in_progress, completed, cancelled
    priority TEXT DEFAULT 'medium', -- high, medium, low
    instance_id TEXT,
    instance_name TEXT,
    created_at TIMESTAMP,
    claimed_at TIMESTAMP,
    completed_at TIMESTAMP,
    notes TEXT,
    submitted_by TEXT
);

-- Task Audit Log
CREATE TABLE task_logs (
    id INTEGER PRIMARY KEY,
    task_id INTEGER REFERENCES tasks(id),
    action TEXT NOT NULL,
    details TEXT,
    instance_id TEXT,
    timestamp TIMESTAMP
);

-- Claude Instance Registry
CREATE TABLE instances (
    id TEXT PRIMARY KEY,
    name TEXT,
    last_seen TIMESTAMP,
    current_task_id INTEGER,
    status TEXT DEFAULT 'idle'
);

-- Container Update History
CREATE TABLE update_history (
    id INTEGER PRIMARY KEY,
    container_name TEXT NOT NULL,
    host_ip TEXT NOT NULL,
    old_image TEXT,
    new_image TEXT,
    update_status TEXT,
    updated_by TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Download Tracking (milestone notifications)
CREATE TABLE download_tracking (
    id TEXT PRIMARY KEY,
    media_type TEXT NOT NULL,
    title TEXT NOT NULL,
    poster_url TEXT,
    size_bytes INTEGER,
    started_at TIMESTAMP,
    notified_milestones TEXT DEFAULT '[]',  -- JSON array [50, 80, 100]
    completed_at TIMESTAMP
);

-- Service Onboarding Cache
CREATE TABLE onboarding_cache (
    service_name TEXT PRIMARY KEY,
    terraform_ok INTEGER DEFAULT 0,
    ansible_ok INTEGER DEFAULT 0,
    dns_ok INTEGER DEFAULT 0,
    traefik_ok INTEGER DEFAULT 0,
    ssl_ok INTEGER DEFAULT 0,
    authentik_ok INTEGER,
    docs_ok INTEGER DEFAULT 0,
    last_checked TIMESTAMP
);
```

---

## Configuration

### Environment Variables

```bash
# Discord
DISCORD_TOKEN=your_bot_token
DISCORD_GUILD_ID=optional_guild_id

# Channels
CHANNEL_CONTAINER_UPDATES=container-updates
CHANNEL_MEDIA_DOWNLOADS=media-downloads
CHANNEL_ONBOARDING=new-service-onboarding-workflow
CHANNEL_ARGUS=homelab-infrastructure
CHANNEL_PROJECT_MANAGEMENT=project-management
CHANNEL_CLAUDE_TASKS=claude-tasks
CHANNEL_ANNOUNCEMENTS=announcements

# Radarr
RADARR_URL=http://192.168.40.11:7878
RADARR_API_KEY=your_key

# Sonarr
SONARR_URL=http://192.168.40.11:8989
SONARR_API_KEY=your_key

# Jellyseerr
JELLYSEERR_URL=http://192.168.40.11:5056

# GitLab
GITLAB_URL=https://gitlab.hrmsmrflrii.xyz
GITLAB_TOKEN=your_pat
GITLAB_PROJECT_ID=2

# Authentik
AUTHENTIK_URL=http://192.168.40.21:9000
AUTHENTIK_TOKEN=your_token

# Prometheus
PROMETHEUS_URL=http://192.168.40.13:9090

# SSH
SSH_KEY_PATH=/app/.ssh/homelab_ed25519

# Webhook Server
WEBHOOK_PORT=5050
API_KEY=sentinel-secret-key

# Domain
DOMAIN=hrmsmrflrii.xyz
```

### SSH Host Configuration

Container hosts for SSH operations:

```python
CONTAINER_HOSTS = {
    'grafana': '192.168.40.13',
    'prometheus': '192.168.40.13',
    'uptime-kuma': '192.168.40.13',
    'n8n': '192.168.40.13',
    'jellyfin': '192.168.40.11',
    'radarr': '192.168.40.11',
    'sonarr': '192.168.40.11',
    # ... 35+ monitored containers
}

VM_HOSTS = {
    'docker-utilities': '192.168.40.13',
    'docker-media': '192.168.40.11',
    'traefik': '192.168.40.20',
    'authentik': '192.168.40.21',
    'immich': '192.168.40.22',
    'gitlab': '192.168.40.23',
    'gitlab-runner': '192.168.40.24',
    'ansible': '192.168.20.30',
}

# LXC containers for apt updates (added January 2026)
# Format: name -> (proxmox_node_ip, ctid)
LXC_CONTAINERS = {
    'pbs': ('192.168.20.22', 100),              # node03 - Proxmox Backup Server
    'docker-lxc-glance': ('192.168.20.22', 200), # node03 - Glance dashboard
    'pi-hole': ('192.168.20.20', 202),          # node01 - DNS server
    'homeassistant': ('192.168.20.22', 206),    # node03 - Home Assistant
}
```

---

## File Structure

```
/opt/sentinel-bot/
├── sentinel.py              # Main entry point
├── config.py                # Configuration loader
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container build
├── docker-compose.yml       # Deployment config
├── .env                     # Environment variables (not in git)
│
├── core/
│   ├── __init__.py
│   ├── bot.py               # SentinelBot class
│   ├── database.py          # Async SQLite wrapper
│   ├── ssh_manager.py       # Async SSH (asyncssh)
│   ├── channel_router.py    # Notification routing
│   └── progress.py          # Progress bar utilities
│
├── cogs/
│   ├── __init__.py
│   ├── homelab.py           # /homelab, /node, /vm
│   ├── updates.py           # /check, /update, /vmcheck
│   ├── media.py             # /downloads, /library
│   ├── gitlab.py            # /todo, /issues
│   ├── tasks.py             # /task, /queue
│   ├── onboarding.py        # /onboard, /onboard-all
│   └── scheduler.py         # Background tasks
│
├── webhooks/
│   ├── __init__.py
│   └── server.py            # Quart async HTTP server
│
└── data/
    └── sentinel.db          # SQLite database
```

---

## Deployment

### Prerequisites

- Docker and Docker Compose on host
- SSH key for infrastructure access
- Discord bot token with proper intents

### Deploy via Ansible

```bash
# From Ansible controller (192.168.20.30)
cd ~/ansible
ansible-playbook sentinel-bot/deploy-sentinel-bot.yml
```

### Manual Deployment

```bash
# SSH to utilities host
ssh docker-vm-core-utilities01

# Navigate to bot directory
cd /opt/sentinel-bot

# Copy SSH key (required for infrastructure commands)
mkdir -p /opt/sentinel-bot/.ssh
cp ~/.ssh/homelab_ed25519 /opt/sentinel-bot/.ssh/

# Create .env file with tokens
nano .env

# Build and start
sudo docker compose up -d --build

# Check logs
sudo docker compose logs -f
```

### Update Bot Code

```bash
# Copy updated files from local
scp -i ~/.ssh/homelab_ed25519 cogs/*.py hermes-admin@192.168.40.13:/opt/sentinel-bot/cogs/

# Restart container
ssh docker-vm-core-utilities01 "cd /opt/sentinel-bot && sudo docker compose restart"

# Check logs
ssh docker-vm-core-utilities01 "cd /opt/sentinel-bot && sudo docker compose logs --tail 30"
```

---

## Troubleshooting

### Bot not responding

1. Check container is running:
   ```bash
   ssh docker-vm-core-utilities01 "docker ps | grep sentinel"
   ```
2. Check logs for errors:
   ```bash
   ssh docker-vm-core-utilities01 "docker logs sentinel-bot --tail 100"
   ```
3. Verify bot is connected:
   ```
   Look for: "Sentinel Bot online as Sentinel#XXXX"
   ```

### Commands not appearing

Discord slash commands can take up to 1 hour to propagate globally. Command sync is now **skipped by default** on restart to avoid rate limits. To force sync:

1. Set environment variable: `SYNC_COMMANDS=true`
2. Restart the container
3. Check logs for "Commands synced to guild"

```bash
# Force command sync
ssh docker-vm-core-utilities01 "cd /opt/sentinel-bot && sudo docker compose down && sudo SYNC_COMMANDS=true docker compose up -d"
```

If commands still don't appear, re-invite bot with `applications.commands` scope.

### Token issues

If you see "Improper token" errors:
1. Go to Discord Developer Portal
2. Reset bot token
3. Update `/opt/sentinel-bot/.env`
4. Recreate container: `docker compose down && docker compose up -d`

### SSH connection failures

1. Verify SSH key exists and has correct ownership:
   ```bash
   docker exec sentinel-bot ls -la /home/sentinel/.ssh/
   ```
   Key should be owned by `sentinel:sentinel` (UID 1000).

2. Fix key ownership on host (if owned by root):
   ```bash
   sudo chown 1000:1000 /opt/sentinel-bot/ssh/homelab_ed25519
   sudo chown 1000:1000 /opt/sentinel-bot/ssh/known_hosts
   ```

3. Test SSH from container:
   ```bash
   docker exec sentinel-bot ssh -i /home/sentinel/.ssh/homelab_ed25519 -o StrictHostKeyChecking=no hermes-admin@192.168.40.13 "echo ok"
   ```

4. Restart container to clear cached connections:
   ```bash
   cd /opt/sentinel-bot && sudo docker compose restart
   ```

### Download notifications spam

**Fixed January 2026**: The scheduler now uses an in-memory cache instead of database tracking, and only notifies on 100% completion (not 50%, 80% milestones).

If issues persist:
1. Restart the bot to clear the in-memory cache:
   ```bash
   cd /opt/sentinel-bot && sudo docker compose restart
   ```
2. The `_download_cache` is cleared when bot restarts, preventing duplicate notifications.

### Webhook not receiving updates

1. Test webhook endpoint:
   ```bash
   curl http://192.168.40.13:5050/health
   ```
2. Check firewall allows port 5050
3. Verify Watchtower configuration on source hosts

---

## Migration from Legacy Bots

Sentinel replaced the following bots:

| Old Bot | Channel | Migrated To |
|---------|---------|-------------|
| **Argus** | #container-updates | Sentinel (Updates Cog) |
| **Chronos** | #project-management | Sentinel (GitLab Cog) |
| **Mnemosyne** | #media-downloads | Sentinel (Media Cog) |
| **Athena** | #claude-tasks | Sentinel (Tasks Cog) |

The legacy bots on LXC 201 (192.168.40.14) have been deprecated. Their containers can be removed:

```bash
# On LXC 201 (if still running)
docker stop argus-bot chronos-bot
docker rm argus-bot chronos-bot
```

---

## Related Documentation

- **[DISCORD_BOT_DEPLOYMENT_TUTORIAL.md](./DISCORD_BOT_DEPLOYMENT_TUTORIAL.md)** - Complete tutorial on creating Discord bots
- **[SERVICES.md](./SERVICES.md)** - All deployed services
- **[CICD.md](./CICD.md)** - GitLab automation pipeline

---

*Last Updated: January 2026*
*Bot: Sentinel*
*Deployment: docker-vm-core-utilities01 (192.168.40.13)*
