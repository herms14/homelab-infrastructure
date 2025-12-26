# SSL Certificates

> **TL;DR**: Traefik automatically obtains and renews Let's Encrypt certificates using Cloudflare DNS-01 challenge for all `*.hrmsmrflrii.xyz` services.

## SSL Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SSL Certificate Flow                                 │
│                                                                              │
│   1. Traefik starts, reads config                                           │
│          │                                                                   │
│          ▼                                                                   │
│   2. Certificate needed for "photos.hrmsmrflrii.xyz"                        │
│          │                                                                   │
│          ▼                                                                   │
│   ┌─────────────────┐                                                       │
│   │   Let's Encrypt │                                                       │
│   │   ACME Server   │                                                       │
│   │                 │                                                       │
│   │ "Prove you own  │                                                       │
│   │  this domain"   │                                                       │
│   └────────┬────────┘                                                       │
│            │                                                                 │
│            ▼                                                                 │
│   3. DNS-01 Challenge                                                        │
│          │                                                                   │
│          ▼                                                                   │
│   ┌─────────────────┐                                                       │
│   │   Cloudflare    │  Traefik creates TXT record:                         │
│   │   DNS API       │  _acme-challenge.photos.hrmsmrflrii.xyz              │
│   │                 │                                                       │
│   └────────┬────────┘                                                       │
│            │                                                                 │
│            ▼                                                                 │
│   4. Let's Encrypt verifies TXT record                                      │
│          │                                                                   │
│          ▼                                                                   │
│   5. Certificate issued → stored in acme.json                               │
│          │                                                                   │
│          ▼                                                                   │
│   6. Traefik serves HTTPS with valid certificate                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Why DNS-01 Challenge?

| Challenge Type | Requirement | Use Case |
|----------------|-------------|----------|
| **HTTP-01** | Port 80 publicly accessible | Public-facing servers |
| **DNS-01** | DNS API access | Internal services, wildcards |
| **TLS-ALPN-01** | Port 443 publicly accessible | Public servers |

**DNS-01 advantages for homelab**:
- No ports need to be open to the internet
- Works for wildcard certificates (`*.hrmsmrflrii.xyz`)
- Validation happens via DNS, not HTTP

---

## Cloudflare Setup

### Domain Configuration

| Setting | Value |
|---------|-------|
| **Domain** | hrmsmrflrii.xyz |
| **Registrar** | Cloudflare |
| **DNS Provider** | Cloudflare |

### API Token Creation

1. **Navigate to**: https://dash.cloudflare.com/profile/api-tokens
2. **Click**: Create Token
3. **Select template**: Edit zone DNS

**Token permissions**:
```
Zone - DNS - Edit
Zone - Zone - Read
```

**Zone resources**:
```
Include - Specific zone - hrmsmrflrii.xyz
```

4. **Copy token** and store in CREDENTIALS.md

[Screenshot: Cloudflare API token creation]

---

## Traefik SSL Configuration

### File Structure

```
/opt/traefik/
├── docker-compose.yml    # Traefik container definition
├── traefik.yml          # Static configuration
├── config/
│   └── dynamic.yml      # Dynamic configuration (routers, services)
├── acme.json            # Certificate storage (chmod 600)
└── .env                 # Cloudflare credentials
```

### Static Configuration

**File**: `/opt/traefik/traefik.yml`

```yaml
api:
  dashboard: true
  insecure: false

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"

certificatesResolvers:
  cloudflare:
    acme:
      email: your-email@example.com
      storage: /etc/traefik/acme.json
      dnsChallenge:
        provider: cloudflare
        resolvers:
          - "1.1.1.1:53"
          - "8.8.8.8:53"

providers:
  file:
    directory: /etc/traefik/config
    watch: true
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false

log:
  level: INFO
```

**Key sections explained**:

| Section | Purpose |
|---------|---------|
| `entryPoints.web` | HTTP listener, redirects to HTTPS |
| `entryPoints.websecure` | HTTPS listener |
| `certificatesResolvers.cloudflare` | ACME/Let's Encrypt config |
| `acme.dnsChallenge.provider` | Use Cloudflare for DNS validation |
| `acme.storage` | Where certificates are stored |

### Environment Variables

**File**: `/opt/traefik/.env`

```bash
CLOUDFLARE_EMAIL=your-email@example.com
CLOUDFLARE_DNS_API_TOKEN=your-cloudflare-api-token
```

**Alternative variables** (older method using Global API Key):
```bash
CF_API_EMAIL=your-email@example.com
CF_API_KEY=your-global-api-key
```

### Docker Compose

**File**: `/opt/traefik/docker-compose.yml`

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

### Certificate Storage

**File**: `/opt/traefik/acme.json`

This file stores all obtained certificates. It must have restricted permissions:

```bash
# Create file if not exists
touch /opt/traefik/acme.json

# Set permissions (CRITICAL)
chmod 600 /opt/traefik/acme.json
```

**File contents** (auto-populated by Traefik):
```json
{
  "cloudflare": {
    "Account": {
      "Email": "your-email@example.com",
      "Registration": { ... },
      "PrivateKey": "..."
    },
    "Certificates": [
      {
        "domain": {
          "main": "photos.hrmsmrflrii.xyz"
        },
        "certificate": "base64-encoded-cert",
        "key": "base64-encoded-key",
        "Store": "default"
      }
    ]
  }
}
```

---

## Dynamic Configuration

### Router with TLS

**File**: `/opt/traefik/config/dynamic.yml`

```yaml
http:
  routers:
    immich:
      rule: "Host(`photos.hrmsmrflrii.xyz`)"
      service: immich
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare
      middlewares:
        - secure-headers

    jellyfin:
      rule: "Host(`jellyfin.hrmsmrflrii.xyz`)"
      service: jellyfin
      entryPoints:
        - websecure
      tls:
        certResolver: cloudflare

  services:
    immich:
      loadBalancer:
        servers:
          - url: "http://192.168.40.22:2283"

    jellyfin:
      loadBalancer:
        servers:
          - url: "http://192.168.40.11:8096"

  middlewares:
    secure-headers:
      headers:
        stsSeconds: 31536000
        stsIncludeSubdomains: true
        stsPreload: true
        forceSTSHeader: true
```

**Configuration elements**:

| Element | Purpose |
|---------|---------|
| `rule: "Host(...)"` | Match requests by hostname |
| `entryPoints: websecure` | Use HTTPS entrypoint |
| `tls.certResolver: cloudflare` | Use our ACME resolver |
| `service` | Backend service definition |
| `loadBalancer.servers.url` | Actual backend address |

---

## Wildcard Certificates

For fewer certificates and simpler management, use wildcards:

### Wildcard Configuration

**traefik.yml** modification:
```yaml
certificatesResolvers:
  cloudflare:
    acme:
      email: your-email@example.com
      storage: /etc/traefik/acme.json
      dnsChallenge:
        provider: cloudflare

# Request wildcard cert
tls:
  certificates:
    - certFile: /etc/traefik/acme.json
      keyFile: /etc/traefik/acme.json
      stores:
        - default
```

**dynamic.yml** with wildcard:
```yaml
tls:
  stores:
    default:
      defaultCertificate:
        certFile: ""
        keyFile: ""

  options:
    default:
      minVersion: VersionTLS12
      sniStrict: true
```

**Router using wildcard**:
```yaml
http:
  routers:
    photos:
      rule: "Host(`photos.hrmsmrflrii.xyz`)"
      service: immich
      entryPoints:
        - websecure
      tls: {}  # Uses default/wildcard cert
```

---

## Certificate Operations

### View Current Certificates

```bash
# On traefik-vm01
cat /opt/traefik/acme.json | jq '.cloudflare.Certificates[].domain'
```

### Force Certificate Renewal

```bash
# Remove specific certificate (Traefik will re-request)
# Edit acme.json carefully or:

# Full renewal (removes all certs)
rm /opt/traefik/acme.json
touch /opt/traefik/acme.json
chmod 600 /opt/traefik/acme.json
docker restart traefik
```

### Check Certificate Status

```bash
# Via OpenSSL
echo | openssl s_client -servername photos.hrmsmrflrii.xyz \
  -connect 192.168.40.20:443 2>/dev/null | openssl x509 -noout -dates

# Expected output:
notBefore=Dec 18 00:00:00 2025 GMT
notAfter=Mar 18 23:59:59 2026 GMT
```

### Traefik Dashboard

View certificate status in Traefik dashboard:

| URL | Access |
|-----|--------|
| https://traefik.hrmsmrflrii.xyz | Via browser |
| http://192.168.40.20:8080 | Direct (if enabled) |

**Dashboard sections**:
- HTTP Routers: Shows all routes and their TLS status
- HTTPS: Certificate resolver status
- Services: Backend health

[Screenshot: Traefik dashboard showing TLS status]

---

## Ansible Deployment

### Traefik Playbook

**File**: `ansible/traefik/deploy-traefik.yml`

```yaml
---
- name: Deploy Traefik with SSL
  hosts: traefik-vm01
  become: yes
  vars:
    traefik_dir: /opt/traefik
    cloudflare_email: "{{ lookup('env', 'CLOUDFLARE_EMAIL') }}"
    cloudflare_token: "{{ lookup('env', 'CLOUDFLARE_DNS_API_TOKEN') }}"

  tasks:
    - name: Create Traefik directories
      file:
        path: "{{ item }}"
        state: directory
        mode: '0755'
      loop:
        - "{{ traefik_dir }}"
        - "{{ traefik_dir }}/config"

    - name: Create acme.json
      file:
        path: "{{ traefik_dir }}/acme.json"
        state: touch
        mode: '0600'

    - name: Deploy traefik.yml
      template:
        src: traefik.yml.j2
        dest: "{{ traefik_dir }}/traefik.yml"
        mode: '0644'

    - name: Deploy dynamic config
      template:
        src: dynamic.yml.j2
        dest: "{{ traefik_dir }}/config/dynamic.yml"
        mode: '0644'

    - name: Deploy .env file
      template:
        src: env.j2
        dest: "{{ traefik_dir }}/.env"
        mode: '0600'

    - name: Deploy docker-compose.yml
      template:
        src: docker-compose.yml.j2
        dest: "{{ traefik_dir }}/docker-compose.yml"
        mode: '0644'

    - name: Create Traefik network
      docker_network:
        name: traefik
        state: present

    - name: Start Traefik
      docker_compose:
        project_src: "{{ traefik_dir }}"
        state: present
        pull: yes
```

---

## Troubleshooting

### Certificate Not Issued

**Symptom**: Browser shows SSL error, self-signed or no certificate

**Diagnosis**:
```bash
# Check Traefik logs
docker logs traefik 2>&1 | grep -i acme

# Common errors:
# - "unable to generate a certificate": DNS challenge failed
# - "DNS record not found": Cloudflare API issue
```

**Fixes**:
1. Verify Cloudflare API token has correct permissions
2. Check `CLOUDFLARE_DNS_API_TOKEN` environment variable
3. Ensure domain is managed by Cloudflare

### DNS Challenge Timeout

**Symptom**: `acme: error: 400 :: urn:ietf:params:acme:error:dns`

**Cause**: DNS propagation delay or wrong DNS servers

**Fix**: Add explicit resolvers in traefik.yml:
```yaml
dnsChallenge:
  provider: cloudflare
  resolvers:
    - "1.1.1.1:53"
    - "8.8.8.8:53"
  delayBeforeCheck: 30
```

### Permission Denied on acme.json

**Symptom**: `unable to write acme.json`

**Fix**:
```bash
chmod 600 /opt/traefik/acme.json
chown root:root /opt/traefik/acme.json
```

### Rate Limits

Let's Encrypt has rate limits:
- 50 certificates per registered domain per week
- 5 duplicate certificates per week
- 5 failed validations per account per hour

**Check rate limit status**: https://crt.sh/?q=hrmsmrflrii.xyz

**Workaround for testing**: Use Let's Encrypt staging server:
```yaml
certificatesResolvers:
  cloudflare:
    acme:
      caServer: https://acme-staging-v02.api.letsencrypt.org/directory
      # ...
```

---

## Security Best Practices

### TLS Configuration

**Minimum TLS version** (in dynamic.yml):
```yaml
tls:
  options:
    default:
      minVersion: VersionTLS12
      cipherSuites:
        - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
        - TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
        - TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
```

### HSTS Headers

**Strict Transport Security** (in middleware):
```yaml
middlewares:
  secure-headers:
    headers:
      stsSeconds: 31536000
      stsIncludeSubdomains: true
      stsPreload: true
      forceSTSHeader: true
      contentTypeNosniff: true
      browserXssFilter: true
```

### Certificate Backup

```bash
# Backup certificates
cp /opt/traefik/acme.json /backup/acme.json.$(date +%Y%m%d)

# Restore (stop Traefik first)
docker stop traefik
cp /backup/acme.json.20251219 /opt/traefik/acme.json
chmod 600 /opt/traefik/acme.json
docker start traefik
```

---

## What's Next?

- **[Traefik](Traefik)** - Full reverse proxy configuration
- **[Services Overview](Services-Overview)** - All HTTPS-enabled services
- **[DNS Configuration](DNS-Configuration)** - Internal DNS setup

---

*Valid SSL certificates are non-negotiable. Let's Encrypt makes it free and automatic.*
