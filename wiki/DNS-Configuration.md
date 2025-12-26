# DNS Configuration

> **TL;DR**: OPNsense Unbound provides internal DNS resolution, mapping `*.hrmsmrflrii.xyz` to Traefik (192.168.40.20) for all services.

## DNS Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DNS Resolution Flow                             │
│                                                                              │
│   Client Request                                                             │
│   "photos.hrmsmrflrii.xyz"                                                  │
│          │                                                                   │
│          ▼                                                                   │
│   ┌─────────────────┐                                                       │
│   │    OPNsense     │                                                       │
│   │    Unbound      │                                                       │
│   │ 192.168.91.30   │                                                       │
│   │                 │                                                       │
│   │ Check: Local    │                                                       │
│   │ Override?       │                                                       │
│   └────────┬────────┘                                                       │
│            │                                                                 │
│     ┌──────┴──────┐                                                         │
│     │             │                                                         │
│     ▼             ▼                                                         │
│   Found         Not Found                                                   │
│     │             │                                                         │
│     │             ▼                                                         │
│     │      Forward to                                                       │
│     │      Cloudflare                                                       │
│     │      (1.1.1.1)                                                        │
│     │             │                                                         │
│     ▼             ▼                                                         │
│   Return       Return                                                       │
│   192.168.40.20 External IP                                                 │
│   (Traefik)                                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## OPNsense DNS Server

### Accessing OPNsense

| Method | Address | Credentials |
|--------|---------|-------------|
| Web UI | https://192.168.91.30 | See CREDENTIALS.md |
| SSH | `ssh root@192.168.91.30` | See CREDENTIALS.md |
| API | https://192.168.91.30/api/ | API key in CREDENTIALS.md |

### Unbound DNS Service

OPNsense uses **Unbound** as its DNS resolver, providing:
- Recursive DNS resolution
- DNS caching
- Local zone overrides (host overrides)
- DNSSEC validation

**Configuration location**: Services → Unbound DNS → General

[Screenshot: OPNsense Unbound settings]

---

## Host Override Configuration

Host overrides map internal hostnames to IP addresses, bypassing external DNS.

### Adding Host Override (Web UI)

**Navigate to**: Services → Unbound DNS → Overrides → Host Overrides

**Configuration for each service**:

| Host | Domain | Type | IP Address |
|------|--------|------|------------|
| photos | hrmsmrflrii.xyz | A | 192.168.40.20 |
| jellyfin | hrmsmrflrii.xyz | A | 192.168.40.20 |
| radarr | hrmsmrflrii.xyz | A | 192.168.40.20 |
| auth | hrmsmrflrii.xyz | A | 192.168.40.20 |
| traefik | hrmsmrflrii.xyz | A | 192.168.40.20 |
| proxmox | hrmsmrflrii.xyz | A | 192.168.20.21 |

**Note**: All services point to Traefik (192.168.40.20), which routes to the actual backend based on hostname.

[Screenshot: Host override configuration form]

### Adding Host Override (API)

OPNsense provides a REST API for automation.

**API Endpoint**: `POST /api/unbound/settings/addHostOverride`

**Example request**:
```bash
curl -k -u "API_KEY:API_SECRET" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "host": {
      "enabled": "1",
      "hostname": "n8n",
      "domain": "hrmsmrflrii.xyz",
      "rr": "A",
      "server": "192.168.40.20",
      "description": "n8n workflow automation"
    }
  }' \
  "https://192.168.91.30/api/unbound/settings/addHostOverride"
```

**Parameter reference**:
- `enabled`: "1" for active, "0" for disabled
- `hostname`: Subdomain (e.g., "n8n")
- `domain`: Base domain (e.g., "hrmsmrflrii.xyz")
- `rr`: Record type (A, AAAA, MX)
- `server`: Target IP address
- `description`: Optional description

### Apply DNS Changes

After adding overrides, reconfigure Unbound to apply:

**Web UI**: Services → Unbound DNS → General → Apply

**API**:
```bash
curl -k -u "API_KEY:API_SECRET" \
  -X POST \
  "https://192.168.91.30/api/unbound/service/reconfigure"
```

---

## Ansible DNS Automation

### Single Record Playbook

**File**: `ansible/opnsense/add-dns-record.yml`

```yaml
---
- name: Add DNS record to OPNsense
  hosts: localhost
  gather_facts: no
  vars:
    opnsense_url: "https://192.168.91.30"
    opnsense_api_key: "{{ lookup('env', 'OPNSENSE_API_KEY') }}"
    opnsense_api_secret: "{{ lookup('env', 'OPNSENSE_API_SECRET') }}"
    # Override these variables when running
    dns_hostname: ""
    dns_domain: "hrmsmrflrii.xyz"
    dns_ip: "192.168.40.20"

  tasks:
    - name: Add host override
      uri:
        url: "{{ opnsense_url }}/api/unbound/settings/addHostOverride"
        method: POST
        user: "{{ opnsense_api_key }}"
        password: "{{ opnsense_api_secret }}"
        force_basic_auth: yes
        validate_certs: no
        body_format: json
        body:
          host:
            enabled: "1"
            hostname: "{{ dns_hostname }}"
            domain: "{{ dns_domain }}"
            rr: "A"
            server: "{{ dns_ip }}"
            description: "Added via Ansible"
        status_code: [200]

    - name: Reconfigure Unbound
      uri:
        url: "{{ opnsense_url }}/api/unbound/service/reconfigure"
        method: POST
        user: "{{ opnsense_api_key }}"
        password: "{{ opnsense_api_secret }}"
        force_basic_auth: yes
        validate_certs: no
        status_code: [200]
```

**Usage**:
```bash
# Set credentials
export OPNSENSE_API_KEY="your-api-key"
export OPNSENSE_API_SECRET="your-api-secret"

# Add single record
ansible-playbook ansible/opnsense/add-dns-record.yml \
  -e "dns_hostname=newservice" \
  -e "dns_ip=192.168.40.20"
```

### Bulk Records Playbook

**File**: `ansible/opnsense/add-all-services-dns.yml`

```yaml
---
- name: Add all service DNS records to OPNsense
  hosts: localhost
  gather_facts: no
  vars:
    opnsense_url: "https://192.168.91.30"
    opnsense_api_key: "{{ lookup('env', 'OPNSENSE_API_KEY') }}"
    opnsense_api_secret: "{{ lookup('env', 'OPNSENSE_API_SECRET') }}"
    traefik_ip: "192.168.40.20"
    domain: "hrmsmrflrii.xyz"

    services:
      - { name: "traefik", description: "Traefik Dashboard" }
      - { name: "proxmox", description: "Proxmox Cluster", ip: "192.168.20.21" }
      - { name: "auth", description: "Authentik SSO" }
      - { name: "photos", description: "Immich Photos" }
      - { name: "gitlab", description: "GitLab" }
      - { name: "jellyfin", description: "Jellyfin Media" }
      - { name: "radarr", description: "Radarr Movies" }
      - { name: "sonarr", description: "Sonarr TV" }
      - { name: "lidarr", description: "Lidarr Music" }
      - { name: "prowlarr", description: "Prowlarr Indexers" }
      - { name: "bazarr", description: "Bazarr Subtitles" }
      - { name: "overseerr", description: "Overseerr Requests" }
      - { name: "jellyseerr", description: "Jellyseerr Requests" }
      - { name: "tdarr", description: "Tdarr Transcoding" }
      - { name: "autobrr", description: "Autobrr" }
      - { name: "paperless", description: "Paperless-ngx" }
      - { name: "glance", description: "Glance Dashboard" }
      - { name: "n8n", description: "n8n Automation" }

  tasks:
    - name: Add DNS records for all services
      uri:
        url: "{{ opnsense_url }}/api/unbound/settings/addHostOverride"
        method: POST
        user: "{{ opnsense_api_key }}"
        password: "{{ opnsense_api_secret }}"
        force_basic_auth: yes
        validate_certs: no
        body_format: json
        body:
          host:
            enabled: "1"
            hostname: "{{ item.name }}"
            domain: "{{ domain }}"
            rr: "A"
            server: "{{ item.ip | default(traefik_ip) }}"
            description: "{{ item.description }}"
      loop: "{{ services }}"
      register: add_results

    - name: Reconfigure Unbound
      uri:
        url: "{{ opnsense_url }}/api/unbound/service/reconfigure"
        method: POST
        user: "{{ opnsense_api_key }}"
        password: "{{ opnsense_api_secret }}"
        force_basic_auth: yes
        validate_certs: no
```

**Usage**:
```bash
ansible-playbook ansible/opnsense/add-all-services-dns.yml
```

---

## OPNsense API Setup

### Creating API Credentials

1. **Navigate to**: System → Access → Users
2. **Create or edit user** (e.g., `homelab-api`)
3. **Add to group**: `admins` (required for Unbound API access)
4. **Generate API key**: User → API Keys → Add

**Store credentials in CREDENTIALS.md**:
```
## OPNsense API
| Setting | Value |
|---------|-------|
| **API User** | homelab-api |
| **API Key** | [key value] |
| **API Secret** | [secret value] |
```

### API Permission Requirements

The API user requires membership in a group with these privileges:
- Services: Unbound DNS: General
- Services: Unbound DNS: Overrides
- Status: Services

**Minimum group**: `admins` (or custom group with above privileges)

---

## DNS Verification

### Test Resolution

```bash
# Query OPNsense directly
nslookup photos.hrmsmrflrii.xyz 192.168.91.30

# Expected output:
Server:         192.168.91.30
Address:        192.168.91.30#53

Name:   photos.hrmsmrflrii.xyz
Address: 192.168.40.20
```

```bash
# Using dig for detailed output
dig @192.168.91.30 photos.hrmsmrflrii.xyz

# Check TTL and authoritative response
dig @192.168.91.30 photos.hrmsmrflrii.xyz +noall +answer
```

### Verify from VM

```bash
# SSH to any VM
ssh hermes-admin@192.168.20.30

# Check configured DNS server
cat /etc/resolv.conf
# Should show: nameserver 192.168.91.30

# Test resolution
ping -c 1 photos.hrmsmrflrii.xyz
```

---

## DNS Record Reference

### All Configured Services

| Hostname | FQDN | IP | Backend |
|----------|------|-----|---------|
| traefik | traefik.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.20:8080 |
| proxmox | proxmox.hrmsmrflrii.xyz | 192.168.20.21 | 192.168.20.21:8006 |
| node01 | node01.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.20.20:8006 |
| node02 | node02.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.20.21:8006 |
| node03 | node03.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.20.22:8006 |
| auth | auth.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.21:9000 |
| photos | photos.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.22:2283 |
| gitlab | gitlab.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.23:80 |
| jellyfin | jellyfin.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.11:8096 |
| radarr | radarr.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.11:7878 |
| sonarr | sonarr.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.11:8989 |
| lidarr | lidarr.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.11:8686 |
| prowlarr | prowlarr.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.11:9696 |
| bazarr | bazarr.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.11:6767 |
| overseerr | overseerr.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.11:5055 |
| jellyseerr | jellyseerr.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.11:5056 |
| tdarr | tdarr.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.11:8265 |
| autobrr | autobrr.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.11:7474 |
| paperless | paperless.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.10:8000 |
| glance | glance.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.10:8080 |
| n8n | n8n.hrmsmrflrii.xyz | 192.168.40.20 | 192.168.40.10:5678 |

---

## Troubleshooting

### DNS Not Resolving

**Symptom**: `nslookup` returns NXDOMAIN or times out

**Diagnosis**:
```bash
# Check Unbound service status
ssh root@192.168.91.30 "pluginctl -s unbound status"

# View Unbound logs
ssh root@192.168.91.30 "clog -f /var/log/resolver.log"

# Check if override exists
ssh root@192.168.91.30 "cat /var/unbound/host_entries.conf | grep photos"
```

**Common fixes**:
1. **Missing reconfigure**: Apply changes via Web UI or API
2. **Typo in hostname**: Verify spelling in host override
3. **Wrong DNS server**: Check VM's `/etc/resolv.conf`

### API Returns 403 Forbidden

**Cause**: Insufficient permissions

**Fix**:
1. Add API user to `admins` group
2. Or create custom group with required privileges

### Changes Not Taking Effect

**Cause**: Unbound not reconfigured after adding override

**Fix**:
```bash
# Via API
curl -k -u "KEY:SECRET" -X POST \
  "https://192.168.91.30/api/unbound/service/reconfigure"

# Via SSH
ssh root@192.168.91.30 "pluginctl -s unbound restart"
```

---

## What's Next?

- **[SSL Certificates](SSL-Certificates)** - HTTPS with Let's Encrypt
- **[Traefik](Traefik)** - Reverse proxy routing
- **[Services Overview](Services-Overview)** - All deployed services

---

*DNS is the phonebook of the homelab. Get it right, and everything finds its way.*
