# Homelab Services Deployment Guide

This guide provides comprehensive documentation for all deployed Docker services in the homelab infrastructure. Each service includes architecture details, configuration explanations, and learning resources.

## Table of Contents

1. [Service Overview](#service-overview)
2. [Traefik Reverse Proxy](#traefik-reverse-proxy)
3. [Authentik Identity Provider](#authentik-identity-provider)
4. [Immich Photo Management](#immich-photo-management)
5. [GitLab CE DevOps Platform](#gitlab-ce-devops-platform)
6. [Arr Media Stack](#arr-media-stack)
7. [Integration Guide](#integration-guide)

---

## Service Overview

| Service | VM | IP Address | Port(s) | Purpose |
|---------|-----|------------|---------|---------|
| **Traefik** | traefik-vm01 | 192.168.40.20 | 80, 443, 8080 | Reverse proxy & load balancer |
| **Authentik** | authentik-vm01 | 192.168.40.21 | 9000, 9443 | SSO & Identity management |
| **Immich** | immich-vm01 | 192.168.40.22 | 2283 | Photo/video backup |
| **GitLab** | gitlab-vm01 | 192.168.40.23 | 80, 443, 2222 | DevOps platform |
| **Arr Stack** | docker-vm-media01 | 192.168.40.11 | Various | Media automation |

---

## Traefik Reverse Proxy

### What is Traefik?

Traefik is a modern, cloud-native reverse proxy and load balancer. It automatically discovers services and configures routing rules, making it ideal for dynamic container environments.

### Why Use Traefik?

- **Automatic Service Discovery**: Detects new services via Docker labels or file configuration
- **Built-in HTTPS**: Automatic TLS certificate management with Let's Encrypt
- **Dashboard**: Web UI for monitoring routes and services
- **Middleware**: Add authentication, rate limiting, headers to any route
- **Modern Protocols**: HTTP/2, WebSocket support out of the box

### Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │              Traefik (192.168.40.20)        │
                    │  ┌─────────────────────────────────────────┤
Internet/LAN  ──────┤  │ Port 80 (HTTP) ─────> Redirect to 443  │
                    │  │ Port 443 (HTTPS) ───> Route to services │
                    │  │ Port 8080 ──────────> Dashboard         │
                    │  └─────────────────────────────────────────┤
                    └─────────────────────────────────────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
              ▼                         ▼                         ▼
    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
    │    Authentik    │     │     Immich      │     │     GitLab      │
    │  192.168.40.21  │     │  192.168.40.22  │     │  192.168.40.23  │
    └─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Configuration Files Explained

#### Static Configuration (`/opt/traefik/config/traefik.yml`)

```yaml
# Global settings - disable telemetry
global:
  checkNewVersion: false
  sendAnonymousUsage: false

# API and Dashboard - enables web UI
api:
  dashboard: true
  insecure: true  # Allows access on port 8080 without auth

# Entrypoints - where Traefik listens
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure      # Redirect HTTP to HTTPS
          scheme: https
          permanent: true
  websecure:
    address: ":443"

# Providers - how Traefik discovers services
providers:
  docker:                    # Auto-discover Docker containers
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false  # Require explicit labels
  file:                      # Manual configuration files
    directory: /etc/traefik/dynamic
    watch: true              # Hot reload on changes
```

#### Dynamic Configuration (`/opt/traefik/config/dynamic/services.yml`)

```yaml
http:
  # Routers - match requests and route to services
  routers:
    authentik:
      rule: "Host(`auth.homelab.local`)"  # Match hostname
      service: authentik                   # Route to this service
      entryPoints:
        - websecure                        # Only HTTPS
      tls: {}                              # Enable TLS

  # Services - define backend servers
  services:
    authentik:
      loadBalancer:
        servers:
          - url: "http://192.168.40.21:9000"  # Backend URL
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Entrypoint** | Network port where Traefik listens (80, 443, 8080) |
| **Router** | Rules to match incoming requests (Host, Path, Headers) |
| **Service** | Backend server(s) to forward requests to |
| **Middleware** | Modify requests/responses (auth, headers, rate limit) |
| **Provider** | Source of configuration (Docker, File, Kubernetes) |

### Access Information

| Interface | URL |
|-----------|-----|
| Dashboard | http://192.168.40.20:8080 |
| HTTP Endpoint | http://192.168.40.20 (redirects to HTTPS) |
| HTTPS Endpoint | https://192.168.40.20 |

### Adding New Services

Edit `/opt/traefik/config/dynamic/services.yml`:

```yaml
http:
  routers:
    my-service:
      rule: "Host(`myservice.homelab.local`)"
      service: my-service
      entryPoints:
        - websecure
      tls: {}

  services:
    my-service:
      loadBalancer:
        servers:
          - url: "http://192.168.40.XX:PORT"
```

Changes are applied automatically (file watcher enabled).

### Learning Resources

- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [Traefik Quick Start](https://doc.traefik.io/traefik/getting-started/quick-start/)
- [Routing & Load Balancing](https://doc.traefik.io/traefik/routing/overview/)

---

## Authentik Identity Provider

### What is Authentik?

Authentik is an open-source Identity Provider (IdP) focused on flexibility and versatility. It provides Single Sign-On (SSO), user management, and application access control.

### Why Use Authentik?

- **Single Sign-On**: Login once, access all applications
- **Multiple Protocols**: OAuth2, SAML, LDAP, Proxy authentication
- **Self-Service**: Users can manage their own profiles, passwords, MFA
- **Customizable Flows**: Define login, enrollment, recovery processes
- **Audit Logging**: Track all authentication events

### Architecture

```
┌────────────────────────────────────────────────────────────┐
│                  Authentik (192.168.40.21)                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  authentik-server (Port 9000/9443)                   │  │
│  │  - Web UI and API                                    │  │
│  │  - OAuth2/OIDC Provider                              │  │
│  │  - SAML Provider                                     │  │
│  │  - LDAP Provider                                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  authentik-worker                                    │  │
│  │  - Background tasks (emails, cleanup)                │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│  ┌────────────────┐  ┌────────────────┐                   │
│  │   PostgreSQL   │  │     Redis      │                   │
│  │   (Database)   │  │    (Cache)     │                   │
│  └────────────────┘  └────────────────┘                   │
└────────────────────────────────────────────────────────────┘
```

### Components Explained

| Component | Purpose |
|-----------|---------|
| **authentik-server** | Main application - handles web UI, API, authentication |
| **authentik-worker** | Background task processor (emails, scheduled tasks) |
| **PostgreSQL** | Database for users, applications, policies |
| **Redis** | Cache and message broker for background tasks |

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Provider** | How applications authenticate (OAuth2, SAML, Proxy, LDAP) |
| **Application** | A service that uses Authentik for authentication |
| **Flow** | Step-by-step process for authentication, enrollment, recovery |
| **Stage** | Individual step in a flow (password, MFA, consent) |
| **Policy** | Rules that control access and flow progression |
| **Source** | External identity providers (Google, GitHub, Azure AD) |

### Access Information

| Interface | URL |
|-----------|-----|
| Web Interface | http://192.168.40.21:9000 |
| Secure Interface | https://192.168.40.21:9443 |
| Initial Setup | http://192.168.40.21:9000/if/flow/initial-setup/ |

### Initial Setup Steps

1. Navigate to http://192.168.40.21:9000/if/flow/initial-setup/
2. Create admin account (default username: `akadmin`)
3. Set a strong password
4. Complete the setup wizard

### Integrating Applications

#### OAuth2/OIDC (Most Modern Apps)

1. Admin Interface → Applications → Create
2. Provider: Create OAuth2/OpenID Provider
3. Configure redirect URIs for your application
4. Use Client ID/Secret in your application

#### SAML (Enterprise Apps)

1. Admin Interface → Applications → Create
2. Provider: Create SAML Provider
3. Download SAML metadata
4. Configure your application with metadata

#### Proxy Authentication (Legacy Apps)

1. Admin Interface → Outposts → Create
2. Type: Proxy Outpost
3. Deploy proxy in front of your application

### Learning Resources

- [Authentik Documentation](https://goauthentik.io/docs/)
- [Getting Started Guide](https://goauthentik.io/docs/installation/docker-compose)
- [Provider Documentation](https://goauthentik.io/docs/providers/)

---

## Immich Photo Management

### What is Immich?

Immich is a self-hosted photo and video backup solution with a mobile app. It's designed as a Google Photos alternative with machine learning features.

### Why Use Immich?

- **Mobile Backup**: Automatic photo/video backup from iOS and Android
- **Face Recognition**: AI-powered face detection and grouping
- **Object Detection**: Smart search by objects and scenes
- **Timeline View**: Browse photos by date with map integration
- **Sharing**: Create shared albums with family/friends

### Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   Immich (192.168.40.22)                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  immich-server (Port 2283)                           │  │
│  │  - Web UI and API                                    │  │
│  │  - Photo/video processing                            │  │
│  │  - Mobile app backend                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  immich-machine-learning                             │  │
│  │  - Face recognition                                  │  │
│  │  - Object/scene detection                            │  │
│  │  - CLIP embeddings for search                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│  ┌────────────────┐  ┌────────────────┐                   │
│  │   PostgreSQL   │  │     Redis      │                   │
│  │  + pgvecto-rs  │  │   (Job Queue)  │                   │
│  └────────────────┘  └────────────────┘                   │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   NFS Storage (NAS)    │
              │  /mnt/appdata/immich   │
              │  - 7TB available       │
              └────────────────────────┘
```

### Components Explained

| Component | Purpose |
|-----------|---------|
| **immich-server** | Main application - web UI, API, media processing |
| **immich-ml** | Machine learning service for AI features |
| **PostgreSQL + pgvecto-rs** | Database with vector extension for ML embeddings |
| **Redis** | Job queue for background processing |

### Storage Layout

| Location | Purpose | Type |
|----------|---------|------|
| `/opt/immich/` | Application config, database | Local |
| `/opt/immich/postgres/` | PostgreSQL data | Local |
| `/opt/immich/model-cache/` | ML model cache | Local |
| `/mnt/appdata/immich/upload/` | Photo/video storage | NFS |

### Access Information

| Interface | URL |
|-----------|-----|
| Web Interface | http://192.168.40.22:2283 |
| Mobile App Server | http://192.168.40.22:2283/api |

### Initial Setup Steps

1. Navigate to http://192.168.40.22:2283
2. Create admin account
3. Download Immich mobile app (iOS/Android)
4. In app settings, set server URL: `http://192.168.40.22:2283/api`
5. Login and enable backup

### Mobile App Setup

1. Download "Immich" from App Store or Play Store
2. Open app and tap "Change Server URL"
3. Enter: `http://192.168.40.22:2283/api`
4. Login with your credentials
5. Go to Settings → Backup
6. Enable "Auto Backup"
7. Select which albums to backup

### Learning Resources

- [Immich Documentation](https://immich.app/docs/overview/introduction)
- [Mobile App Guide](https://immich.app/docs/features/mobile-app)
- [FAQ](https://immich.app/docs/FAQ)

---

## GitLab CE DevOps Platform

### What is GitLab?

GitLab is a complete DevOps platform delivered as a single application. It covers the entire software development lifecycle from project planning through CI/CD to monitoring.

### Why Use GitLab?

- **Git Repository**: Host unlimited private repositories
- **CI/CD Pipelines**: Automated build, test, and deployment
- **Issue Tracking**: Project management with boards and milestones
- **Wiki**: Documentation for your projects
- **Container Registry**: Store Docker images (can be enabled)
- **Code Review**: Merge requests with diff views

### Architecture

```
┌────────────────────────────────────────────────────────────┐
│                  GitLab CE (192.168.40.23)                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  gitlab (all-in-one container)                       │  │
│  │                                                      │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │  │
│  │  │   Nginx     │ │    Puma     │ │  Sidekiq    │    │  │
│  │  │  (Reverse   │ │   (Rails    │ │ (Background │    │  │
│  │  │   Proxy)    │ │    App)     │ │   Jobs)     │    │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘    │  │
│  │                                                      │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │  │
│  │  │ PostgreSQL  │ │    Redis    │ │  Gitaly     │    │  │
│  │  │ (Database)  │ │   (Cache)   │ │ (Git RPC)   │    │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  Ports: 80 (HTTP), 443 (HTTPS), 2222 (SSH)                │
└────────────────────────────────────────────────────────────┘
```

### Components Explained

| Component | Purpose |
|-----------|---------|
| **Nginx** | Web server and reverse proxy |
| **Puma** | Ruby on Rails application server |
| **Sidekiq** | Background job processor |
| **PostgreSQL** | Main database |
| **Redis** | Caching and Sidekiq job queue |
| **Gitaly** | Git repository access service |

### Access Information

| Interface | URL/Port |
|-----------|----------|
| Web Interface | http://192.168.40.23 |
| Git SSH | ssh://git@192.168.40.23:2222 |

### Initial Setup Steps

1. **Wait for initialization** (3-5 minutes after container start)
2. **Get initial root password**:
   ```bash
   ssh hermes-admin@192.168.40.23 "sudo docker exec gitlab grep 'Password:' /etc/gitlab/initial_root_password"
   ```
3. Navigate to http://192.168.40.23
4. Login with username `root` and the initial password
5. **Change password immediately** (Settings → Password)

**Important**: The initial password file is automatically deleted after 24 hours!

### Common Operations

#### Clone a Repository

```bash
# HTTPS
git clone http://192.168.40.23/username/project.git

# SSH (requires SSH key setup)
git clone ssh://git@192.168.40.23:2222/username/project.git
```

#### Add SSH Key

1. Generate key: `ssh-keygen -t ed25519 -C "your_email@example.com"`
2. Copy public key: `cat ~/.ssh/id_ed25519.pub`
3. GitLab → User Settings → SSH Keys → Add Key

#### Check GitLab Status

```bash
ssh hermes-admin@192.168.40.23 "sudo docker exec gitlab gitlab-ctl status"
```

### Configuration

GitLab configuration is managed via environment variables in Docker Compose:

```yaml
GITLAB_OMNIBUS_CONFIG: |
  external_url 'http://192.168.40.23'
  gitlab_rails['gitlab_shell_ssh_port'] = 2222

  # Resource optimization for homelab
  puma['worker_processes'] = 2
  sidekiq['max_concurrency'] = 10
  postgresql['shared_buffers'] = "256MB"
```

### Learning Resources

- [GitLab Documentation](https://docs.gitlab.com/)
- [Git Basics](https://docs.gitlab.com/ee/topics/git/)
- [CI/CD Quick Start](https://docs.gitlab.com/ee/ci/quick_start/)
- [GitLab Runner](https://docs.gitlab.com/runner/)

---

## Arr Media Stack

The Arr Stack is documented in [ARR_STACK_DEPLOYMENT.md](./ARR_STACK_DEPLOYMENT.md).

### Quick Reference

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| Jellyfin | 8096 | https://jellyfin.hrmsmrflrii.xyz | Media server |
| Radarr | 7878 | https://radarr.hrmsmrflrii.xyz | Movie management |
| Sonarr | 8989 | https://sonarr.hrmsmrflrii.xyz | TV series management |
| Lidarr | 8686 | https://lidarr.hrmsmrflrii.xyz | Music management |
| Prowlarr | 9696 | https://prowlarr.hrmsmrflrii.xyz | Indexer management |
| Bazarr | 6767 | https://bazarr.hrmsmrflrii.xyz | Subtitle management |
| Jellyseerr | 5056 | https://jellyseerr.hrmsmrflrii.xyz | Media requests |

### Configured Connections (December 19, 2025)

| Connection | Status |
|------------|--------|
| Prowlarr → Radarr | ✅ Full Sync |
| Prowlarr → Sonarr | ✅ Full Sync |
| Prowlarr → Lidarr | ✅ Full Sync |
| Bazarr → Radarr | ✅ Connected |
| Bazarr → Sonarr | ✅ Connected |
| Jellyseerr → Jellyfin | ⚠️ Needs Setup |

### API Keys

| Service | API Key |
|---------|---------|
| Radarr | `21f807cf286941158e11ba6477853821` |
| Sonarr | `50c598d01b294f929e5ecf36ae42ad2e` |
| Lidarr | `13fe89b5dbdb45d48418e0879781ff3b` |
| Prowlarr | `e5f64c69e6c04bd8ba5eb8952ed25dbc` |
| Bazarr | `6c0037b075a3ee20f9818c14a3c35e7d` |

---

## Integration Guide

### Setting Up DNS

For the hostname-based routing to work (e.g., `auth.homelab.local`), you need local DNS:

**Option 1: Router DNS (Recommended)**
Add entries in your router's DNS settings.

**Option 2: Local hosts file**
Edit `/etc/hosts` (Linux/Mac) or `C:\Windows\System32\drivers\etc\hosts` (Windows):

```
192.168.40.20  traefik.homelab.local
192.168.40.20  auth.homelab.local
192.168.40.20  photos.homelab.local
192.168.40.20  gitlab.homelab.local
192.168.40.20  media.homelab.local
```

**Option 3: Pi-hole or AdGuard Home**
Add local DNS records in your DNS server.

### Integrating Authentik with Services

#### GitLab with Authentik SSO

1. In Authentik, create OAuth2 provider for GitLab
2. In GitLab, configure OmniAuth:
   ```ruby
   gitlab_rails['omniauth_providers'] = [
     {
       name: "oauth2_generic",
       app_id: "CLIENT_ID",
       app_secret: "CLIENT_SECRET",
       args: {
         client_options: {
           site: "https://auth.homelab.local",
           ...
         }
       }
     }
   ]
   ```

#### Traefik with Authentik Forward Auth

Add to Traefik dynamic config for protected routes:
```yaml
middlewares:
  authentik:
    forwardAuth:
      address: "http://192.168.40.21:9000/outpost.goauthentik.io/auth/traefik"
      trustForwardHeader: true
      authResponseHeaders:
        - X-authentik-username
```

### Service Dependencies

```
                    ┌──────────────┐
                    │   Traefik    │
                    │ (Entry Point)│
                    └──────┬───────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
  ┌────────────┐   ┌────────────┐   ┌────────────┐
  │  Authentik │   │   Immich   │   │   GitLab   │
  │  (Auth)    │   │  (Photos)  │   │   (Code)   │
  └────────────┘   └────────────┘   └────────────┘
         │
         ▼
  ┌────────────────────────────────────────────┐
  │         Protected Services                  │
  │  (Any service using Authentik for auth)    │
  └────────────────────────────────────────────┘
```

---

## Quick Reference

### Service URLs

| Service | Direct URL | Via Traefik |
|---------|------------|-------------|
| Traefik Dashboard | http://192.168.40.20:8080 | - |
| Authentik | http://192.168.40.21:9000 | https://auth.homelab.local |
| Immich | http://192.168.40.22:2283 | https://photos.homelab.local |
| GitLab | http://192.168.40.23 | https://gitlab.homelab.local |
| Jellyfin | http://192.168.40.11:8096 | https://media.homelab.local |

### Common Commands

```bash
# View service logs
ssh hermes-admin@<IP> "cd /opt/<service> && sudo docker compose logs -f"

# Restart service
ssh hermes-admin@<IP> "cd /opt/<service> && sudo docker compose restart"

# Update service
ssh hermes-admin@<IP> "cd /opt/<service> && sudo docker compose pull && sudo docker compose up -d"

# Check container status
ssh hermes-admin@<IP> "docker ps"
```

### Useful Ansible Commands

```bash
# From ansible-controller01
cd ~/ansible

# Deploy Traefik
ansible-playbook traefik/deploy-traefik.yml -l traefik-vm01 -v

# Deploy Authentik
ansible-playbook authentik/deploy-authentik.yml -l authentik-vm01 -v

# Deploy Immich
ansible-playbook immich/deploy-immich.yml -l immich-vm01 -v

# Deploy GitLab
ansible-playbook gitlab/deploy-gitlab.yml -l gitlab-vm01 -v
```
