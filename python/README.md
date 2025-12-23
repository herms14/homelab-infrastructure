# Python Applications

Python applications for APIs, Discord bots, and exporters.

## Directory Structure

```
python/
├── apis/
│   ├── media-stats-api/      # Media statistics API
│   ├── life-progress-api/    # Life progress tracker
│   └── reddit-manager/       # Reddit subreddit manager
├── discord-bots/
│   ├── sysadmin-bot/         # Argus SysAdmin bot
│   ├── download-monitor/     # Media download notifications
│   └── update-manager/       # Container update manager
├── exporters/
│   └── docker-stats-exporter/  # Docker metrics exporter
└── ci-cd/                    # GitLab CI/CD scripts
```

## APIs

### Media Stats API
- **Port**: 5050
- **Purpose**: Aggregate media statistics from Radarr/Sonarr/Jellyfin
- **Endpoint**: `GET /api/stats`

### Life Progress API
- **Port**: 5051
- **Purpose**: Calculate life progress metrics for Glance dashboard
- **Endpoint**: `GET /api/feed`

### Reddit Manager
- **Port**: 5052
- **Purpose**: Manage subreddit lists for Glance RSS feeds
- **Endpoints**: `GET/POST /api/subreddits`

## Discord Bots

### Argus SysAdmin Bot
- **Channel**: #argus-assistant
- **Features**:
  - VM start/stop/restart
  - Container management
  - Service status checks
  - System health monitoring

### Download Monitor
- **Channel**: #media-downloads
- **Features**:
  - Radarr/Sonarr webhook receiver
  - Download notifications
  - Media library updates

### Update Manager
- **Channel**: #update-manager
- **Features**:
  - Container update detection
  - Interactive update approval
  - Service onboarding checker

## Deployment

Each application includes:
- `Dockerfile` - Container build
- `docker-compose.yml` - Service definition
- `.env.example` - Environment template
- `requirements.txt` - Python dependencies

### Example Deployment

```bash
cd python/discord-bots/sysadmin-bot
cp .env.example .env
# Edit .env with your values
docker compose up -d
```

## Environment Variables

See `.env.example` in each application directory for required variables.
