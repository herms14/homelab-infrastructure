# Services Overview

> **TL;DR**: 22 services running across Docker hosts and dedicated VMs, all accessible via HTTPS through Traefik reverse proxy.

## Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Service Architecture                               │
│                                                                              │
│                        User Request (HTTPS)                                  │
│                              │                                               │
│                              ▼                                               │
│                    ┌─────────────────┐                                      │
│                    │    OPNsense     │  DNS: *.hrmsmrflrii.xyz              │
│                    │   DNS Server    │  → 192.168.40.20                     │
│                    └────────┬────────┘                                      │
│                             │                                                │
│                             ▼                                                │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    Traefik (192.168.40.20)                           │   │
│   │                                                                      │   │
│   │  • SSL Termination (Let's Encrypt)                                  │   │
│   │  • Host-based routing                                                │   │
│   │  • Load balancing                                                    │   │
│   │  • Middleware (headers, auth)                                        │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                             │                                                │
│         ┌───────────────────┼───────────────────┐                           │
│         │                   │                   │                           │
│         ▼                   ▼                   ▼                           │
│   ┌───────────┐       ┌───────────┐       ┌───────────┐                    │
│   │ Docker    │       │ Docker    │       │ Dedicated │                    │
│   │ Utilities │       │ Media     │       │ VMs       │                    │
│   │ .40.10    │       │ .40.11    │       │           │                    │
│   │           │       │           │       │ Authentik │                    │
│   │ Paperless │       │ Jellyfin  │       │ Immich    │                    │
│   │ Glance    │       │ Radarr    │       │ GitLab    │                    │
│   │ n8n       │       │ Sonarr    │       │           │                    │
│   └───────────┘       │ ...       │       └───────────┘                    │
│                       └───────────┘                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Service Catalog

### Infrastructure Services

| Service | Host | Port | URL | Purpose |
|---------|------|------|-----|---------|
| **Traefik** | 192.168.40.20 | 80, 443, 8080 | https://traefik.hrmsmrflrii.xyz | Reverse proxy, SSL |
| **Authentik** | 192.168.40.21 | 9000 | https://auth.hrmsmrflrii.xyz | SSO, Identity provider |

### Media Services (docker-vm-media01)

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| **Jellyfin** | 8096 | https://jellyfin.hrmsmrflrii.xyz | Media server |
| **Radarr** | 7878 | https://radarr.hrmsmrflrii.xyz | Movie management |
| **Sonarr** | 8989 | https://sonarr.hrmsmrflrii.xyz | TV series management |
| **Lidarr** | 8686 | https://lidarr.hrmsmrflrii.xyz | Music management |
| **Prowlarr** | 9696 | https://prowlarr.hrmsmrflrii.xyz | Indexer manager |
| **Bazarr** | 6767 | https://bazarr.hrmsmrflrii.xyz | Subtitle management |
| **Overseerr** | 5055 | https://overseerr.hrmsmrflrii.xyz | Media requests (Plex) |
| **Jellyseerr** | 5056 | https://jellyseerr.hrmsmrflrii.xyz | Media requests (Jellyfin) |
| **Tdarr** | 8265 | https://tdarr.hrmsmrflrii.xyz | Transcoding automation |
| **Autobrr** | 7474 | https://autobrr.hrmsmrflrii.xyz | Torrent automation |

### Utility Services (docker-vm-utilities01)

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| **Paperless-ngx** | 8000 | https://paperless.hrmsmrflrii.xyz | Document management |
| **Glance** | 8080 | https://glance.hrmsmrflrii.xyz | Dashboard |
| **n8n** | 5678 | https://n8n.hrmsmrflrii.xyz | Workflow automation |

### Application Services

| Service | Host | Port | URL | Purpose |
|---------|------|------|-----|---------|
| **Immich** | 192.168.40.22 | 2283 | https://photos.hrmsmrflrii.xyz | Photo management |
| **GitLab** | 192.168.40.23 | 80, 443 | https://gitlab.hrmsmrflrii.xyz | DevOps platform |

### Management Interfaces

| Service | URL | Purpose |
|---------|-----|---------|
| **Proxmox (Cluster)** | https://proxmox.hrmsmrflrii.xyz | Cluster management |
| **Proxmox (node01)** | https://node01.hrmsmrflrii.xyz | Node 01 direct |
| **Proxmox (node02)** | https://node02.hrmsmrflrii.xyz | Node 02 direct |
| **Proxmox (node03)** | https://node03.hrmsmrflrii.xyz | Node 03 direct |
| **Synology NAS** | https://192.168.20.31:5001 | NAS management |

---

## Service Deployment Status

| Service | Status | Deployment Method | Documentation |
|---------|--------|-------------------|---------------|
| Traefik | Deployed | Docker Compose | [Traefik](Traefik) |
| Authentik | Deployed | Docker Compose | [Authentik](Authentik) |
| Jellyfin | Deployed | Arr Stack | [Arr-Stack](Arr-Stack) |
| Radarr | Deployed | Arr Stack | [Arr-Stack](Arr-Stack) |
| Sonarr | Deployed | Arr Stack | [Arr-Stack](Arr-Stack) |
| Lidarr | Deployed | Arr Stack | [Arr-Stack](Arr-Stack) |
| Prowlarr | Deployed | Arr Stack | [Arr-Stack](Arr-Stack) |
| Bazarr | Deployed | Arr Stack | [Arr-Stack](Arr-Stack) |
| Overseerr | Deployed | Arr Stack | [Arr-Stack](Arr-Stack) |
| Jellyseerr | Deployed | Arr Stack | [Arr-Stack](Arr-Stack) |
| Tdarr | Deployed | Arr Stack | [Arr-Stack](Arr-Stack) |
| Autobrr | Deployed | Arr Stack | [Arr-Stack](Arr-Stack) |
| Paperless | Deployed | Docker Compose | [Paperless](Paperless) |
| Glance | Deployed | Docker Compose | [Glance](Glance) |
| n8n | Deployed | Docker Compose | [n8n](n8n) |
| Immich | Deployed | Docker Compose | [Immich](Immich) |
| GitLab | Deployed | Docker Compose | [GitLab](GitLab) |

---

## Network Configuration

### Service to Traefik Routing

All services are accessed through Traefik:

1. **DNS Resolution**: `service.hrmsmrflrii.xyz` → `192.168.40.20`
2. **Traefik Receives**: HTTPS request on port 443
3. **SSL Termination**: Traefik handles TLS with Let's Encrypt cert
4. **Routing**: Based on `Host` header, routes to backend
5. **Backend**: HTTP connection to actual service

### Direct Access (Bypass Traefik)

For debugging or when Traefik is down:

| Service | Direct URL |
|---------|------------|
| Jellyfin | http://192.168.40.11:8096 |
| Authentik | http://192.168.40.21:9000 |
| Immich | http://192.168.40.22:2283 |

---

## Docker Host Details

### docker-vm-utilities01 (192.168.40.10)

**Purpose**: General utility services

**Docker Compose Projects**:
```
/opt/
├── paperless/
│   └── docker-compose.yml
├── glance/
│   └── docker-compose.yml
└── n8n/
    └── docker-compose.yml
```

**Management**:
```bash
# SSH to host
ssh hermes-admin@192.168.40.10

# View running containers
docker ps

# View logs
docker logs paperless-webserver -f
```

### docker-vm-media01 (192.168.40.11)

**Purpose**: Media automation stack

**Docker Compose Projects**:
```
/opt/
└── arr-stack/
    └── docker-compose.yml    # All 10 services
```

**NFS Mounts**:
```
192.168.20.31:/volume2/Proxmox-Media → /mnt/media
├── Movies/
├── Series/
├── Music/
└── Downloads/
```

**Management**:
```bash
# SSH to host
ssh hermes-admin@192.168.40.11

# View all Arr stack containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Restart specific service
docker restart radarr

# View logs
docker logs -f jellyfin
```

---

## Service Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Service Dependencies                                  │
│                                                                              │
│  ┌─────────────┐                                                            │
│  │   Traefik   │ ◄── All services depend on for external access            │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│  ┌──────▼──────┐                                                            │
│  │  Authentik  │ ◄── SSO provider for protected services                   │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│  ┌──────┴───────────────────────────────────────────┐                      │
│  │                                                   │                      │
│  ▼                                                   ▼                      │
│  ┌─────────────┐                              ┌─────────────┐              │
│  │   Prowlarr  │ ◄── Indexer source for:     │   Jellyfin  │              │
│  └──────┬──────┘                              └──────▲──────┘              │
│         │                                            │                      │
│  ┌──────┼────────────┬────────────┐                 │                      │
│  │      │            │            │                 │                      │
│  ▼      ▼            ▼            ▼                 │                      │
│  Radarr  Sonarr    Lidarr    Overseerr              │                      │
│  (Movies) (TV)    (Music)   (Requests)──────────────┘                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Common Operations

### Check Service Status

```bash
# Via SSH to Docker host
ssh hermes-admin@192.168.40.11 "docker ps"

# Via Ansible
ansible docker_hosts -a "docker ps --format 'table {{.Names}}\t{{.Status}}'"

# Check specific service
curl -s https://photos.hrmsmrflrii.xyz/api/server-info | jq
```

### Restart Service

```bash
# Single container
ssh hermes-admin@192.168.40.11 "docker restart jellyfin"

# Full stack
ssh hermes-admin@192.168.40.11 "cd /opt/arr-stack && docker compose restart"
```

### View Logs

```bash
# Follow logs
ssh hermes-admin@192.168.40.11 "docker logs -f radarr"

# Last 100 lines
ssh hermes-admin@192.168.40.11 "docker logs --tail 100 radarr"
```

### Update Services

```bash
# Pull latest images
ssh hermes-admin@192.168.40.11 "cd /opt/arr-stack && docker compose pull"

# Recreate containers with new images
ssh hermes-admin@192.168.40.11 "cd /opt/arr-stack && docker compose up -d"
```

---

## Adding New Services

### Process

1. **Choose host**: docker-vm-utilities01 or docker-vm-media01
2. **Create directory**: `/opt/<service-name>/`
3. **Create docker-compose.yml**: Define service
4. **Add DNS record**: Via OPNsense or Ansible
5. **Add Traefik route**: In dynamic configuration
6. **Deploy**: `docker compose up -d`
7. **Document**: Add to this wiki

### Example: Adding New Service

```bash
# 1. Create directory
ssh hermes-admin@192.168.40.10 "sudo mkdir -p /opt/newservice"

# 2. Create compose file
ssh hermes-admin@192.168.40.10 "cat > /opt/newservice/docker-compose.yml << 'EOF'
version: '3.8'
services:
  newservice:
    image: newservice/newservice:latest
    container_name: newservice
    ports:
      - '8080:8080'
    restart: unless-stopped
EOF"

# 3. Add DNS record
ansible-playbook opnsense/add-dns-record.yml -e "dns_hostname=newservice"

# 4. Add Traefik route (in dynamic.yml)
# 5. Start service
ssh hermes-admin@192.168.40.10 "cd /opt/newservice && docker compose up -d"
```

---

## Service Documentation Index

### Infrastructure
- **[Traefik](Traefik)** - Reverse proxy and SSL
- **[Authentik](Authentik)** - Identity and SSO

### Media
- **[Arr-Stack](Arr-Stack)** - Complete media automation

### Applications
- **[Immich](Immich)** - Photo management
- **[GitLab](GitLab)** - DevOps platform
- **[Paperless](Paperless)** - Document management
- **[n8n](n8n)** - Workflow automation
- **[Glance](Glance)** - Dashboard

---

## What's Next?

- **[Traefik](Traefik)** - Reverse proxy configuration
- **[Arr-Stack](Arr-Stack)** - Media services setup
- **[Authentik](Authentik)** - SSO configuration

---

*Services are the payload. Infrastructure exists to run them reliably.*
