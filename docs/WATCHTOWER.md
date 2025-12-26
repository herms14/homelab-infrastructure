# Watchtower - Interactive Container Updates

> Part of the [Proxmox Infrastructure Documentation](../CLAUDE.md)

Watchtower monitors Docker containers for updates and sends interactive Discord notifications for approval before updating. This provides controlled, user-approved container updates across the entire homelab infrastructure.

## Overview

| Setting | Value |
|---------|-------|
| Check Schedule | Daily at 3:00 AM (America/New_York) |
| Mode | Monitor-only (requires approval) |
| Notifications | Discord bot with reaction-based approval |
| Auto-cleanup | Old images removed after update |
| Webhook Endpoint | http://192.168.40.10:5050/webhook |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Watchtower Update System                                │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Docker Hosts with Watchtower                      │    │
│  │                                                                      │    │
│  │   192.168.40.10     192.168.40.11     192.168.40.20                 │    │
│  │   (utilities)       (media)           (traefik)                     │    │
│  │        │                 │                 │                        │    │
│  │   192.168.40.21     192.168.40.22     192.168.40.23                 │    │
│  │   (authentik)       (immich)          (gitlab)                      │    │
│  └─────────┬───────────────┴─────────────────┴─────────────────────────┘    │
│            │                                                                 │
│            │ Shoutrrr Webhook (generic+http://)                             │
│            ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │              Update Manager (192.168.40.10:5050)                    │    │
│  │                                                                      │    │
│  │   ┌──────────────┐              ┌──────────────────┐                │    │
│  │   │ Flask Server │◄─────────────│  Discord.py Bot  │                │    │
│  │   │ (Webhook)    │              │  (Interactions)  │                │    │
│  │   └──────┬───────┘              └────────┬─────────┘                │    │
│  │          │                               │                          │    │
│  │          └───────────┬───────────────────┘                          │    │
│  │                      │                                              │    │
│  │                      ▼                                              │    │
│  │              ┌───────────────┐                                      │    │
│  │              │  SSH to Host  │──────► docker compose pull/up        │    │
│  │              └───────────────┘                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│                                 │                                            │
│                                 ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Discord Channel                              │    │
│  │                                                                      │    │
│  │   "Hey Hermes! There is a new update for sonarr..."                 │    │
│  │                                                                      │    │
│  │   👍 → Update proceeds → "sonarr has been updated!"                 │    │
│  │   👎 → Update skipped  → "Skipping update for sonarr"               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## How It Works

1. **Watchtower monitors** containers on each Docker host daily at 3 AM
2. **Updates detected** trigger a webhook to the Update Manager
3. **Discord notification** sent with update details and reaction options
4. **User approves/rejects** via 👍 or 👎 emoji reaction
5. **Update executes** via SSH to the container's host
6. **Completion notification** confirms success or reports errors

## Discord Bot Features

### Commands

| Command | Aliases | Description |
|---------|---------|-------------|
| `check versions` | `check version`, `check updates`, `status` | Scan all services for available updates |
| `update all` | - | Update all services with pending updates |
| `update <service>` | - | Update a specific service (e.g., `update sonarr`) |
| `help` | `commands`, `?` | Show available commands |

### Notification Format

**Update Available:**
```
👋 Hey Hermes!

🆕 There is a new update available for **sonarr**
📦 Current: `current`
🚀 New: `lscr.io/linuxserver/sonarr (sha256:abc1...)`

React with 👍 to update or 👎 to skip!
```

**Update Approved:**
```
🔄 Updating **sonarr**... Please wait, Master Hermes!
✅ **sonarr** has been updated to **lscr.io/linuxserver/sonarr:latest**, Master Hermes! 🎉
```

**Check Versions Output:**
```
🔍 Checking all services for updates, Master Hermes... This may take a minute.

Service              Current Image                  Status
-------------------- ------------------------------ ---------------
authentik-server     ghcr.io/goauthentik/server     Up to date
bazarr               lscr.io/linuxserver/bazarr     Up to date
sonarr               lscr.io/linuxserver/sonarr     UPDATE AVAILABLE
radarr               lscr.io/linuxserver/radarr     Up to date
...

📦 **1 updates available:** sonarr
Type `update all` to update all, or wait for individual notifications.
```

## Components

### Watchtower (All 6 Docker Hosts)

| Host | IP | Config Location | Purpose |
|------|----|-----------------|---------|
| docker-vm-utilities01 | 192.168.40.10 | `/opt/watchtower/docker-compose.yml` | Utilities, monitoring |
| docker-vm-media01 | 192.168.40.11 | `/opt/watchtower/docker-compose.yml` | Arr stack, Jellyfin |
| traefik-vm01 | 192.168.40.20 | `/opt/watchtower/docker-compose.yml` | Reverse proxy |
| authentik-vm01 | 192.168.40.21 | `/opt/watchtower/docker-compose.yml` | SSO/Identity |
| immich-vm01 | 192.168.40.22 | `/opt/watchtower/docker-compose.yml` | Photo management |
| gitlab-vm01 | 192.168.40.23 | `/opt/watchtower/docker-compose.yml` | DevOps platform |

### Update Manager (192.168.40.10)

| Component | Location |
|-----------|----------|
| Service Directory | `/opt/update-manager/` |
| Python Application | `/opt/update-manager/update_manager.py` |
| Docker Compose | `/opt/update-manager/docker-compose.yml` |
| Dockerfile | `/opt/update-manager/Dockerfile` |
| Requirements | `/opt/update-manager/requirements.txt` |
| Credentials | `/opt/update-manager/.env` |

### Container to Host Mapping

The Update Manager maintains a mapping of containers to their host IPs:

```python
CONTAINER_HOSTS = {
    # Utilities (192.168.40.10)
    "uptime-kuma": "192.168.40.10",
    "prometheus": "192.168.40.10",
    "grafana": "192.168.40.10",
    "glance": "192.168.40.10",
    "n8n": "192.168.40.10",
    "paperless-ngx": "192.168.40.10",
    "openspeedtest": "192.168.40.10",

    # Media (192.168.40.11)
    "jellyfin": "192.168.40.11",
    "radarr": "192.168.40.11",
    "sonarr": "192.168.40.11",
    "lidarr": "192.168.40.11",
    "prowlarr": "192.168.40.11",
    "bazarr": "192.168.40.11",
    "overseerr": "192.168.40.11",
    "jellyseerr": "192.168.40.11",
    "tdarr": "192.168.40.11",
    "autobrr": "192.168.40.11",

    # Infrastructure
    "traefik": "192.168.40.20",
    "authentik-server": "192.168.40.21",
    "authentik-worker": "192.168.40.21",
    "immich-server": "192.168.40.22",
    "immich-ml": "192.168.40.22",
    "gitlab": "192.168.40.23",
}
```

## Configuration

### Watchtower (Monitor-Only Mode)

Deploy on each Docker host at `/opt/watchtower/docker-compose.yml`:

```yaml
name: watchtower

services:
  watchtower:
    image: containrrr/watchtower:latest
    container_name: watchtower
    restart: unless-stopped
    environment:
      DOCKER_API_VERSION: "1.44"
      WATCHTOWER_SCHEDULE: "0 0 3 * * *"
      WATCHTOWER_CLEANUP: "true"
      WATCHTOWER_INCLUDE_STOPPED: "false"
      WATCHTOWER_MONITOR_ONLY: "true"
      WATCHTOWER_NOTIFICATIONS: "shoutrrr"
      WATCHTOWER_NOTIFICATION_URL: "generic+http://192.168.40.10:5050/webhook"
      TZ: "America/New_York"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
```

**Key Settings:**
- `WATCHTOWER_MONITOR_ONLY: "true"` - Does NOT auto-update, only notifies
- `WATCHTOWER_NOTIFICATIONS: "shoutrrr"` - Uses Shoutrrr notification system
- `WATCHTOWER_NOTIFICATION_URL: "generic+http://..."` - MUST use `generic+http://` (not `generic://`)
- `WATCHTOWER_CLEANUP: "true"` - Removes old images after update

### Update Manager

**Docker Compose** (`/opt/update-manager/docker-compose.yml`):

```yaml
name: update-manager

services:
  update-manager:
    build: .
    container_name: update-manager
    restart: unless-stopped
    ports:
      - "5050:5000"
    environment:
      - DISCORD_TOKEN=${DISCORD_TOKEN}
      - DISCORD_CHANNEL_ID=${DISCORD_CHANNEL_ID}
      - SSH_KEY_PATH=/root/.ssh/homelab_ed25519
      - WEBHOOK_PORT=5000
      - TZ=America/New_York
    volumes:
      - /home/hermes-admin/.ssh:/root/.ssh:ro
    networks:
      - update-manager-network

networks:
  update-manager-network:
    name: update-manager-network
    driver: bridge
```

**Dockerfile** (`/opt/update-manager/Dockerfile`):

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install SSH client
RUN apt-get update && apt-get install -y openssh-client && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY update_manager.py .

CMD ["python", "update_manager.py"]
```

**Requirements** (`/opt/update-manager/requirements.txt`):

```
flask>=2.3.0
discord.py>=2.3.0
```

**Environment File** (`/opt/update-manager/.env`):

```bash
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here
```

## Discord Bot Setup

### 1. Create Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" → Name it "Hermes Update Manager"
3. Go to "Bot" section → Click "Add Bot"
4. Enable these Privileged Gateway Intents:
   - MESSAGE CONTENT INTENT
   - SERVER MEMBERS INTENT (optional)
5. Copy the Bot Token

### 2. Invite Bot to Server

1. Go to OAuth2 → URL Generator
2. Select Scopes: `bot`
3. Select Bot Permissions:
   - Send Messages
   - Read Message History
   - Add Reactions
   - Use External Emojis
4. Copy the generated URL and open it to invite the bot

### 3. Get Channel ID

1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
2. Right-click the channel → "Copy ID"

### 4. Configure Update Manager

```bash
# SSH to utilities host
ssh hermes-admin@192.168.40.10

# Create .env file
cat > /opt/update-manager/.env << 'EOF'
DISCORD_TOKEN=your_bot_token_here
DISCORD_CHANNEL_ID=your_channel_id_here
EOF

# Set permissions
chmod 600 /opt/update-manager/.env
```

## Deployment

### Initial Setup

```bash
# 1. Deploy Watchtower to all hosts
for ip in 192.168.40.10 192.168.40.11 192.168.40.20 192.168.40.21 192.168.40.22 192.168.40.23; do
  ssh hermes-admin@$ip "sudo mkdir -p /opt/watchtower"
  scp watchtower-compose.yml hermes-admin@$ip:/opt/watchtower/docker-compose.yml
  ssh hermes-admin@$ip "cd /opt/watchtower && sudo docker compose up -d"
done

# 2. Deploy Update Manager
ssh hermes-admin@192.168.40.10
cd /opt/update-manager
sudo docker compose up -d --build
```

### SSH Key Setup

The Update Manager container needs SSH access to all Docker hosts:

```bash
# Copy SSH key to utilities host (if not already present)
scp ~/.ssh/homelab_ed25519 hermes-admin@192.168.40.10:/home/hermes-admin/.ssh/

# Set correct permissions
ssh hermes-admin@192.168.40.10 "chmod 600 /home/hermes-admin/.ssh/homelab_ed25519"
```

## Commands

### Check Status

```bash
# Update Manager status
ssh hermes-admin@192.168.40.10 "docker ps --filter name=update-manager --format '{{.Status}}'"

# Watchtower on all hosts
for ip in 192.168.40.10 192.168.40.11 192.168.40.20 192.168.40.21 192.168.40.22 192.168.40.23; do
  echo -n "$ip: "
  ssh hermes-admin@$ip "docker ps --filter name=watchtower --format '{{.Status}}'"
done
```

### Trigger Immediate Update Check

```bash
# On specific host
ssh hermes-admin@192.168.40.11 "docker exec watchtower /watchtower --run-once"

# On all hosts
for ip in 192.168.40.10 192.168.40.11 192.168.40.20 192.168.40.21 192.168.40.22 192.168.40.23; do
  echo "Checking $ip..."
  ssh hermes-admin@$ip "docker exec watchtower /watchtower --run-once" &
done
wait
```

### View Logs

```bash
# Update Manager logs
ssh hermes-admin@192.168.40.10 "docker logs update-manager --tail 50"

# Watchtower logs (specific host)
ssh hermes-admin@192.168.40.11 "docker logs watchtower --tail 50"

# Check for logged-in status
ssh hermes-admin@192.168.40.10 "docker logs update-manager 2>&1 | grep 'logged in'"
```

### Restart Services

```bash
# Update Manager
ssh hermes-admin@192.168.40.10 "cd /opt/update-manager && sudo docker compose restart"

# Watchtower (all hosts)
for ip in 192.168.40.10 192.168.40.11 192.168.40.20 192.168.40.21 192.168.40.22 192.168.40.23; do
  ssh hermes-admin@$ip "cd /opt/watchtower && sudo docker compose restart"
done

# Full rebuild (after code changes)
ssh hermes-admin@192.168.40.10 "cd /opt/update-manager && sudo docker compose down && sudo docker compose build --no-cache && sudo docker compose up -d"
```

### Test Notification

```bash
# Send test webhook
curl -X POST -d 'Found new lscr.io/linuxserver/sonarr image (sha256:test123)' \
  http://192.168.40.10:5050/webhook

# Check health endpoint
curl http://192.168.40.10:5050/health

# Test notification endpoint
curl http://192.168.40.10:5050/test
```

## Excluding Containers from Updates

Add this label to any container's compose file to exclude it from Watchtower monitoring:

```yaml
labels:
  - "com.centurylinklabs.watchtower.enable=false"
```

## Adding New Containers

1. Add the container to `CONTAINER_HOSTS` in `/opt/update-manager/update_manager.py`:

```python
CONTAINER_HOSTS = {
    "new-container": "192.168.40.XX",
    # ... existing containers
}
```

2. Rebuild the Update Manager:

```bash
ssh hermes-admin@192.168.40.10 "cd /opt/update-manager && sudo docker compose build --no-cache && sudo docker compose up -d"
```

3. Ensure Watchtower is running on the new container's host.

## Troubleshooting

### Discord Bot Not Responding

**Symptoms**: Commands typed in Discord channel get no response.

**Diagnosis**:
```bash
# Check bot is running and logged in
ssh hermes-admin@192.168.40.10 "docker logs update-manager 2>&1 | grep 'logged in'"

# Expected output:
# Discord bot logged in as Hermes Update Manager#2521

# Check for errors
ssh hermes-admin@192.168.40.10 "docker logs update-manager --tail 20"
```

**Fixes**:
1. Verify bot token is correct in `.env`
2. Verify channel ID matches the channel you're typing in
3. Ensure bot has MESSAGE CONTENT INTENT enabled in Discord Developer Portal
4. Check bot has permissions in the Discord server

### Watchtower TLS Handshake Error

**Symptoms**: Watchtower logs show `tls: first record does not look like a TLS handshake`.

**Root Cause**: Using `generic://` instead of `generic+http://` in the webhook URL causes Watchtower to attempt HTTPS connection to an HTTP endpoint.

**Fix**: Update `WATCHTOWER_NOTIFICATION_URL` in docker-compose.yml:
```yaml
# Wrong
WATCHTOWER_NOTIFICATION_URL: "generic://192.168.40.10:5050/webhook"

# Correct
WATCHTOWER_NOTIFICATION_URL: "generic+http://192.168.40.10:5050/webhook"
```

Then restart Watchtower:
```bash
ssh hermes-admin@192.168.40.11 "cd /opt/watchtower && sudo docker compose restart"
```

### Update Fails - "Could not find compose directory"

**Symptoms**: After approving an update, Discord shows `❌ Update failed for sonarr: Could not find compose directory`.

**Root Cause**: The Update Manager container cannot SSH to the target host, usually because:
1. SSH key not mounted correctly
2. SSH key missing from the utilities host
3. Host key verification failing

**Diagnosis**:
```bash
# Test SSH from container
ssh hermes-admin@192.168.40.10 "docker exec update-manager ssh -i /root/.ssh/homelab_ed25519 -o StrictHostKeyChecking=no hermes-admin@192.168.40.11 hostname"

# Check if SSH key exists in container
ssh hermes-admin@192.168.40.10 "docker exec update-manager ls -la /root/.ssh/"
```

**Fixes**:
```bash
# 1. Ensure SSH key exists on host
ls -la /home/hermes-admin/.ssh/homelab_ed25519

# 2. If missing, copy from local machine
scp ~/.ssh/homelab_ed25519 hermes-admin@192.168.40.10:/home/hermes-admin/.ssh/
ssh hermes-admin@192.168.40.10 "chmod 600 /home/hermes-admin/.ssh/homelab_ed25519"

# 3. Restart container to remount volume
ssh hermes-admin@192.168.40.10 "cd /opt/update-manager && sudo docker compose restart"
```

### Container Not in Host Mapping

**Symptoms**: `❌ Service not found` when trying to update a container.

**Fix**: Add the container to `CONTAINER_HOSTS` in `update_manager.py` and rebuild:
```bash
ssh hermes-admin@192.168.40.10 "cd /opt/update-manager && sudo docker compose build --no-cache && sudo docker compose up -d"
```

### Changes Not Taking Effect After Rebuild

**Symptoms**: Code changes don't appear in bot behavior after rebuild.

**Root Cause**: Docker caching old layers or container not properly recreated.

**Fix**: Force full rebuild with no cache:
```bash
ssh hermes-admin@192.168.40.10 "cd /opt/update-manager && sudo docker compose down && sudo docker compose build --no-cache && sudo docker compose up -d"
```

### Webhook Not Received

**Symptoms**: Watchtower finds updates but no Discord notification appears.

**Diagnosis**:
```bash
# Check Watchtower logs for notification attempts
ssh hermes-admin@192.168.40.11 "docker logs watchtower 2>&1 | grep -i notification"

# Check Update Manager received webhook
ssh hermes-admin@192.168.40.10 "docker logs update-manager 2>&1 | grep -i webhook"

# Test webhook manually
curl -X POST -d 'Found new test/image image (sha256:test123)' http://192.168.40.10:5050/webhook
```

**Fixes**:
1. Ensure port 5050 is open on utilities host
2. Verify webhook URL format uses `generic+http://`
3. Check Update Manager is running

## Schedule Options

Change `WATCHTOWER_SCHEDULE` in Watchtower's docker-compose.yml:

| Schedule | Cron Expression |
|----------|-----------------|
| Daily 3 AM | `0 0 3 * * *` |
| Every 6 hours | `0 0 */6 * * *` |
| Sunday 2 AM | `0 0 2 * * 0` |
| Every hour | `0 0 * * * *` |
| Twice daily (3 AM, 3 PM) | `0 0 3,15 * * *` |

**Note**: Watchtower uses 6-field cron (with seconds): `seconds minutes hours day month weekday`

## Related Documentation

- [Services](./SERVICES.md) - Service deployment details
- [Ansible](./ANSIBLE.md) - Automation playbooks
- [Troubleshooting](./TROUBLESHOOTING.md) - General troubleshooting guide
