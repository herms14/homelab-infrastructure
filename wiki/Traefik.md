# Traefik

> **TL;DR**: Traefik is the single entry point for all services. It handles SSL termination, host-based routing, and automatic certificate management via Let's Encrypt.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Traefik Architecture                                 │
│                                                                              │
│   Internet/LAN                                                               │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    traefik-vm01 (192.168.40.20)                      │   │
│   │                                                                      │   │
│   │  ┌─────────────────────────────────────────────────────────────┐   │   │
│   │  │                     Traefik v3.0                             │   │   │
│   │  │                                                              │   │   │
│   │  │  Entrypoints:                                               │   │   │
│   │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐            │   │   │
│   │  │  │ :80 (web)  │  │:443 (https)│  │:8080 (api) │            │   │   │
│   │  │  │ Redirect→  │  │ TLS term   │  │ Dashboard  │            │   │   │
│   │  │  └────────────┘  └────────────┘  └────────────┘            │   │   │
│   │  │                        │                                    │   │   │
│   │  │  ┌─────────────────────▼─────────────────────┐             │   │   │
│   │  │  │              Routers                       │             │   │   │
│   │  │  │                                            │             │   │   │
│   │  │  │  Host(`photos.*`) → immich-service        │             │   │   │
│   │  │  │  Host(`jellyfin.*`) → jellyfin-service    │             │   │   │
│   │  │  │  Host(`auth.*`) → authentik-service       │             │   │   │
│   │  │  │  ...                                       │             │   │   │
│   │  │  └────────────────────────────────────────────┘             │   │   │
│   │  │                        │                                    │   │   │
│   │  │  ┌─────────────────────▼─────────────────────┐             │   │   │
│   │  │  │              Services                      │             │   │   │
│   │  │  │                                            │             │   │   │
│   │  │  │  immich → http://192.168.40.22:2283       │             │   │   │
│   │  │  │  jellyfin → http://192.168.40.11:8096     │             │   │   │
│   │  │  │  authentik → http://192.168.40.21:9000    │             │   │   │
│   │  │  └────────────────────────────────────────────┘             │   │   │
│   │  └──────────────────────────────────────────────────────────────┘   │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment

### Directory Structure

```
/opt/traefik/
├── docker-compose.yml
├── traefik.yml           # Static configuration
├── config/
│   └── dynamic.yml       # Dynamic configuration (routers, services)
├── acme.json             # Certificate storage
└── .env                  # Cloudflare credentials
```

### docker-compose.yml

```yaml
version: "3.8"

services:
  traefik:
    image: traefik:v3.0
    container_name: traefik
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    environment:
      - CLOUDFLARE_EMAIL=${CLOUDFLARE_EMAIL}
      - CLOUDFLARE_DNS_API_TOKEN=${CLOUDFLARE_DNS_API_TOKEN}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/etc/traefik/traefik.yml:ro
      - ./config:/etc/traefik/config:ro
      - ./acme.json:/etc/traefik/acme.json
    networks:
      - traefik

networks:
  traefik:
    external: true
```

### traefik.yml (Static Configuration)

```yaml
# API and Dashboard
api:
  dashboard: true
  insecure: false

# Logging
log:
  level: INFO

accessLog:
  filePath: "/var/log/traefik/access.log"
  bufferingSize: 100

# Entrypoints
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
          permanent: true

  websecure:
    address: ":443"
    http:
      tls:
        certResolver: cloudflare
        domains:
          - main: "hrmsmrflrii.xyz"
            sans:
              - "*.hrmsmrflrii.xyz"

  traefik:
    address: ":8080"

# Certificate Resolvers
certificatesResolvers:
  cloudflare:
    acme:
      email: admin@example.com
      storage: /etc/traefik/acme.json
      dnsChallenge:
        provider: cloudflare
        resolvers:
          - "1.1.1.1:53"
          - "8.8.8.8:53"
        delayBeforeCheck: 10

# Providers
providers:
  file:
    directory: /etc/traefik/config
    watch: true

# Global settings
global:
  checkNewVersion: false
  sendAnonymousUsage: false
```

---

## Dynamic Configuration

### config/dynamic.yml

```yaml
http:
  # ==========================================================================
  # ROUTERS
  # ==========================================================================

  routers:
    # Dashboard
    traefik-dashboard:
      rule: "Host(`traefik.hrmsmrflrii.xyz`)"
      service: api@internal
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare
      middlewares:
        - secure-headers

    # Proxmox Cluster
    proxmox:
      rule: "Host(`proxmox.hrmsmrflrii.xyz`)"
      service: proxmox
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    # Proxmox Nodes
    node01:
      rule: "Host(`node01.hrmsmrflrii.xyz`)"
      service: node01
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    node02:
      rule: "Host(`node02.hrmsmrflrii.xyz`)"
      service: node02
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    node03:
      rule: "Host(`node03.hrmsmrflrii.xyz`)"
      service: node03
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    # Core Services
    authentik:
      rule: "Host(`auth.hrmsmrflrii.xyz`)"
      service: authentik
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    immich:
      rule: "Host(`photos.hrmsmrflrii.xyz`)"
      service: immich
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    gitlab:
      rule: "Host(`gitlab.hrmsmrflrii.xyz`)"
      service: gitlab
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    # Media Services
    jellyfin:
      rule: "Host(`jellyfin.hrmsmrflrii.xyz`)"
      service: jellyfin
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    radarr:
      rule: "Host(`radarr.hrmsmrflrii.xyz`)"
      service: radarr
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    sonarr:
      rule: "Host(`sonarr.hrmsmrflrii.xyz`)"
      service: sonarr
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    lidarr:
      rule: "Host(`lidarr.hrmsmrflrii.xyz`)"
      service: lidarr
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    prowlarr:
      rule: "Host(`prowlarr.hrmsmrflrii.xyz`)"
      service: prowlarr
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    bazarr:
      rule: "Host(`bazarr.hrmsmrflrii.xyz`)"
      service: bazarr
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    overseerr:
      rule: "Host(`overseerr.hrmsmrflrii.xyz`)"
      service: overseerr
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    jellyseerr:
      rule: "Host(`jellyseerr.hrmsmrflrii.xyz`)"
      service: jellyseerr
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    tdarr:
      rule: "Host(`tdarr.hrmsmrflrii.xyz`)"
      service: tdarr
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    autobrr:
      rule: "Host(`autobrr.hrmsmrflrii.xyz`)"
      service: autobrr
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    # Utility Services
    paperless:
      rule: "Host(`paperless.hrmsmrflrii.xyz`)"
      service: paperless
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    glance:
      rule: "Host(`glance.hrmsmrflrii.xyz`)"
      service: glance
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

    n8n:
      rule: "Host(`n8n.hrmsmrflrii.xyz`)"
      service: n8n
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

  # ==========================================================================
  # SERVICES
  # ==========================================================================

  services:
    # Proxmox
    proxmox:
      loadBalancer:
        servers:
          - url: "https://192.168.20.21:8006"
        serversTransport: insecure-transport

    node01:
      loadBalancer:
        servers:
          - url: "https://192.168.20.20:8006"
        serversTransport: insecure-transport

    node02:
      loadBalancer:
        servers:
          - url: "https://192.168.20.21:8006"
        serversTransport: insecure-transport

    node03:
      loadBalancer:
        servers:
          - url: "https://192.168.20.22:8006"
        serversTransport: insecure-transport

    # Core Services
    authentik:
      loadBalancer:
        servers:
          - url: "http://192.168.40.21:9000"

    immich:
      loadBalancer:
        servers:
          - url: "http://192.168.40.22:2283"

    gitlab:
      loadBalancer:
        servers:
          - url: "http://192.168.40.23:80"

    # Media Services (docker-vm-media01)
    jellyfin:
      loadBalancer:
        servers:
          - url: "http://192.168.40.11:8096"

    radarr:
      loadBalancer:
        servers:
          - url: "http://192.168.40.11:7878"

    sonarr:
      loadBalancer:
        servers:
          - url: "http://192.168.40.11:8989"

    lidarr:
      loadBalancer:
        servers:
          - url: "http://192.168.40.11:8686"

    prowlarr:
      loadBalancer:
        servers:
          - url: "http://192.168.40.11:9696"

    bazarr:
      loadBalancer:
        servers:
          - url: "http://192.168.40.11:6767"

    overseerr:
      loadBalancer:
        servers:
          - url: "http://192.168.40.11:5055"

    jellyseerr:
      loadBalancer:
        servers:
          - url: "http://192.168.40.11:5056"

    tdarr:
      loadBalancer:
        servers:
          - url: "http://192.168.40.11:8265"

    autobrr:
      loadBalancer:
        servers:
          - url: "http://192.168.40.11:7474"

    # Utility Services (docker-vm-utilities01)
    paperless:
      loadBalancer:
        servers:
          - url: "http://192.168.40.10:8000"

    glance:
      loadBalancer:
        servers:
          - url: "http://192.168.40.10:8080"

    n8n:
      loadBalancer:
        servers:
          - url: "http://192.168.40.10:5678"

  # ==========================================================================
  # MIDDLEWARES
  # ==========================================================================

  middlewares:
    secure-headers:
      headers:
        stsSeconds: 31536000
        stsIncludeSubdomains: true
        stsPreload: true
        forceSTSHeader: true
        contentTypeNosniff: true
        browserXssFilter: true
        referrerPolicy: "strict-origin-when-cross-origin"

    rate-limit:
      rateLimit:
        average: 100
        burst: 50

  # ==========================================================================
  # TRANSPORTS
  # ==========================================================================

  serversTransports:
    insecure-transport:
      insecureSkipVerify: true

# TLS Configuration
tls:
  options:
    default:
      minVersion: VersionTLS12
      sniStrict: true
```

---

## Deployment

### Via Ansible

```bash
ansible-playbook traefik/deploy-traefik.yml
```

### Manual Deployment

```bash
# SSH to traefik-vm01
ssh hermes-admin@192.168.40.20

# Create directories
sudo mkdir -p /opt/traefik/config

# Create network
docker network create traefik

# Create acme.json with correct permissions
sudo touch /opt/traefik/acme.json
sudo chmod 600 /opt/traefik/acme.json

# Create .env file
sudo tee /opt/traefik/.env << 'EOF'
CLOUDFLARE_EMAIL=your-email@example.com
CLOUDFLARE_DNS_API_TOKEN=your-token-here
EOF

# Deploy configuration files (traefik.yml, dynamic.yml, docker-compose.yml)
# ... copy files ...

# Start Traefik
cd /opt/traefik
docker compose up -d

# Verify
docker logs -f traefik
```

---

## Adding New Services

### 1. Add Router

Add to `config/dynamic.yml` under `routers`:

```yaml
new-service:
  rule: "Host(`newservice.hrmsmrflrii.xyz`)"
  service: new-service
  entryPoints:
    - websecure
  tls:
    certResolver: cloudflare
```

### 2. Add Service

Add to `config/dynamic.yml` under `services`:

```yaml
new-service:
  loadBalancer:
    servers:
      - url: "http://192.168.40.XX:PORT"
```

### 3. Add DNS Record

```bash
ansible-playbook opnsense/add-dns-record.yml -e "dns_hostname=newservice"
```

### 4. Reload Traefik

Traefik watches the config directory and reloads automatically. Verify:

```bash
docker logs traefik | tail -20
```

---

## Monitoring

### Dashboard Access

https://traefik.hrmsmrflrii.xyz

**Dashboard features**:
- Router status
- Service health
- Middleware configuration
- Certificate status

### Health Check

```bash
# Check Traefik is responding
curl -s https://traefik.hrmsmrflrii.xyz/api/overview | jq

# Check specific router
curl -s https://traefik.hrmsmrflrii.xyz/api/http/routers | jq
```

### View Logs

```bash
# Container logs
docker logs -f traefik

# Access logs (if configured)
tail -f /opt/traefik/logs/access.log
```

---

## Troubleshooting

### 404 Not Found

**Cause**: Router rule not matching

**Check**:
```bash
# Verify router exists
curl -s https://traefik.hrmsmrflrii.xyz/api/http/routers | jq '.[].name'

# Check rule
curl -s https://traefik.hrmsmrflrii.xyz/api/http/routers/routername@file | jq '.rule'
```

### 502 Bad Gateway

**Cause**: Backend service unreachable

**Check**:
```bash
# Test backend directly
curl -v http://192.168.40.XX:PORT

# Check service in Traefik
curl -s https://traefik.hrmsmrflrii.xyz/api/http/services/servicename@file | jq
```

### SSL Certificate Issues

**Check**:
```bash
# View acme.json (contains certs)
sudo cat /opt/traefik/acme.json | jq '.cloudflare.Certificates[].domain'

# Check Traefik logs for ACME errors
docker logs traefik 2>&1 | grep -i acme
```

**Force renewal**:
```bash
sudo rm /opt/traefik/acme.json
sudo touch /opt/traefik/acme.json
sudo chmod 600 /opt/traefik/acme.json
docker restart traefik
```

---

## What's Next?

- **[SSL Certificates](SSL-Certificates)** - Certificate management
- **[Authentik](Authentik)** - Add SSO to services
- **[Services Overview](Services-Overview)** - All services

---

*Traefik: the front door to your homelab.*
