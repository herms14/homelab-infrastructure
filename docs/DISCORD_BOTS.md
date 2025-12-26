# Discord Bots

This document describes the Discord bots deployed in the homelab for automation and notifications.

## Overview

| Bot | Channel | Host | Purpose |
|-----|---------|------|---------|
| **Argus** | `#container-updates` | docker-utilities (192.168.40.10) | Container update management |
| **Mnemosyne** | `#media-downloads` | docker-media (192.168.40.11) | Media download tracking |
| **Chronos** | `#project-management` | docker-utilities (192.168.40.10) | GitLab task management |

Each bot is channel-restricted and will only respond to commands in its designated channel.

---

## Argus - Container Update Guardian

**Location**: `/opt/argus-bot/`
**Container**: `argus-bot`
**Webhook Port**: 5050

### Features
- Watchtower webhook integration for update notifications
- Button-based update approvals
- SSH-based container management
- Real-time container status monitoring

### Commands

| Command | Description |
|---------|-------------|
| `/check` | Scan all containers for available updates |
| `/update` | Update a specific container (dropdown selection) |
| `/updateall` | Update all containers with pending updates |
| `/containers` | List all monitored containers |
| `/status` | Show bot and system status |
| `/argus` | Display help and bot info |

### Watchtower Integration

Configure Watchtower on each host to send notifications:

```yaml
# In docker-compose.yml for Watchtower
environment:
  - WATCHTOWER_NOTIFICATION_URL=generic+http://192.168.40.10:5050/webhook
```

### Deployment

```bash
# Set environment variable
export ARGUS_DISCORD_TOKEN=your_token

# Deploy via Ansible
cd ~/ansible
ansible-playbook container-updates/deploy-argus-bot.yml
```

---

## Mnemosyne - Media Guardian

**Location**: `/opt/mnemosyne-bot/`
**Container**: `mnemosyne-bot`

### Features
- Real-time download notifications (50%, 80%, 100% progress)
- Radarr/Sonarr API integration
- Library browsing and statistics
- Media search and request functionality

### Commands

| Command | Description |
|---------|-------------|
| `/downloads` | Show current download queue |
| `/search` | Search for movies or TV shows |
| `/request` | Add media to Radarr/Sonarr |
| `/availablemovies` | List downloaded movies in library |
| `/availableseries` | List downloaded TV series |
| `/showlist` | Quick compact list of all media |
| `/stats` | Library statistics |
| `/recent` | Recently added media |
| `/quality` | View quality profiles |
| `/mnemosyne` | Display help and bot info |

### Automatic Notifications

Mnemosyne monitors download queues and sends notifications:
- **Download Started**: When a new download begins
- **Progress Updates**: At 50%, 80%, and 100% completion
- **Download Complete**: With link to Jellyfin

### Deployment

```bash
# Set environment variables
export MNEMOSYNE_DISCORD_TOKEN=your_token
export RADARR_API_KEY=your_key  # Optional, has default
export SONARR_API_KEY=your_key  # Optional, has default

# Deploy via Ansible
cd ~/ansible
ansible-playbook media-downloads/deploy-mnemosyne-bot.yml
```

---

## Chronos - Project Management

**Location**: `/opt/chronos-bot/`
**Container**: `chronos-bot`

### Features
- GitLab Boards integration for task management
- Create and manage issues via slash commands
- Priority labels support
- Bulk task creation

### Commands

| Command | Description |
|---------|-------------|
| `/todo <task>` | Create a new task with optional priority |
| `/tasks` | List all open tasks |
| `/done` | List completed tasks |
| `/close` | Close a task (dropdown selection) |
| `/board` | Show board overview with task counts |
| `/quick <tasks>` | Bulk add tasks (comma or newline separated) |
| `/chronos` | Display help and bot info |

### Priority Labels

When creating tasks with `/todo`, you can set priority:
- `priority::high` - High priority (red label)
- `priority::medium` - Medium priority (yellow label)
- `priority::low` - Low priority (green label)

### GitLab Setup

1. Create a GitLab project for tasks (e.g., `homelab/tasks`)
2. Create labels: `todo`, `priority::high`, `priority::medium`, `priority::low`
3. Optionally create a board with lists for workflow

### Deployment

```bash
# Set environment variables
export CHRONOS_DISCORD_TOKEN=your_token
export GITLAB_TOKEN=your_gitlab_pat
export GITLAB_PROJECT_ID=homelab/tasks  # Optional

# Deploy via Ansible
cd ~/ansible
ansible-playbook project-management/deploy-chronos-bot.yml
```

---

## Architecture

```
Discord Server
├── #container-updates ──► Argus (192.168.40.10:5050)
│                              └── Watchtower webhooks
├── #media-downloads ───► Mnemosyne (192.168.40.11)
│                              ├── Radarr API (localhost:7878)
│                              └── Sonarr API (localhost:8989)
└── #project-management ► Chronos (192.168.40.10)
                               └── GitLab API (gitlab.hrmsmrflrii.xyz)
```

## File Locations

```
ansible-playbooks/
├── container-updates/
│   ├── argus-bot.py
│   └── deploy-argus-bot.yml
├── media-downloads/
│   ├── mnemosyne-bot.py
│   ├── deploy-mnemosyne-bot.yml
│   ├── Dockerfile
│   └── requirements.txt
└── project-management/
    ├── chronos-bot.py
    └── deploy-chronos-bot.yml
```

## Troubleshooting

### Bot not responding
1. Check container is running: `docker ps | grep bot-name`
2. Check logs: `docker logs bot-name --tail 50`
3. Verify channel restriction matches your channel name

### Commands not syncing
Discord slash commands can take up to 1 hour to propagate globally. For immediate sync:
1. Restart the bot container
2. Check logs for "Slash commands synced" message

### Token issues
If you see "Improper token" errors:
1. Regenerate token in Discord Developer Portal
2. Update docker-compose.yml with new token
3. Restart container: `docker compose up -d`

### Webhook not receiving updates (Argus)
1. Verify Watchtower is configured with correct URL
2. Test webhook: `curl http://192.168.40.10:5050/health`
3. Check firewall allows port 5050

---

*Created: December 26, 2025*
*Bots: Argus, Mnemosyne, Chronos*
