# Proxmox Terraform Infrastructure

Terraform infrastructure-as-code for deploying VMs and LXC containers on a Proxmox VE 9.1.2 cluster.

## Session Start Protocol

**IMPORTANT: At the start of EVERY session or when the user asks for a new task, display the Infrastructure Context Summary below.**

### Infrastructure Context Summary (Display This)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                        HOMELAB INFRASTRUCTURE CONTEXT                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ PROXMOX CLUSTER: MorpheusCluster (3-node + Qdevice)                          ║
║   • node01: 192.168.20.20 (Tailscale: 100.89.33.5)  - Primary VM Host        ║
║   • node02: 192.168.20.21 (Tailscale: 100.96.195.27) - Service Host          ║
║   • node03: 192.168.20.22 (Tailscale: 100.88.228.34) - Additional Node       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ SYNOLOGY NAS: 192.168.20.31                                                  ║
║   • DSM: https://192.168.20.31:5001                                          ║
║   • Plex: http://192.168.20.31:32400/web                                     ║
║   • Media: /volume2/Proxmox-Media/ (Movies, Series, Music)                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ NETWORKS                                                                      ║
║   • VLAN 20 (192.168.20.0/24): Infrastructure (K8s, Ansible, Proxmox)        ║
║   • VLAN 40 (192.168.40.0/24): Services (Docker, Apps)                       ║
║   • VLAN 90 (192.168.90.0/24): Management (Pi-hole DNS: 192.168.90.53)       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ KEY HOSTS                                                                     ║
║   • ansible:        192.168.20.30  - Ansible Controller + Packer             ║
║   • docker-media:   192.168.40.11  - Jellyfin, *arr stack                    ║
║   • docker-glance:  192.168.40.12  - Glance Dashboard, APIs                  ║
║   • docker-utils:   192.168.40.13  - Grafana, Prometheus, Sentinel Bot       ║
║   • traefik:        192.168.40.20  - Reverse Proxy                           ║
║   • authentik:      192.168.40.21  - SSO/Identity                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ MEDIA SERVERS                                                                 ║
║   • Plex (Synology):   http://192.168.20.31:32400  - TV apps, remote access  ║
║   • Jellyfin (Docker): http://192.168.40.11:8096   - Open-source alternative ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ KEY URLS                                                                      ║
║   • Proxmox:  https://proxmox.hrmsmrflrii.xyz                                ║
║   • Glance:   https://glance.hrmsmrflrii.xyz                                 ║
║   • Grafana:  https://grafana.hrmsmrflrii.xyz                                ║
║   • Traefik:  https://traefik.hrmsmrflrii.xyz                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ AZURE CLOUD (FireGiants-Prod)                                                ║
║   • ubuntu-deploy-vm: 10.90.10.5 - Primary Terraform/Ansible deployment VM   ║
║   • Sentinel SIEM:    law-homelab-sentinel - Log aggregation & analytics     ║
║   • VPN:              Site-to-Site (OPNsense <-> Azure)                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ AZURE HYBRID LAB (Active Directory)                                          ║
║   • Domain:   hrmsmrflrii.xyz (HRMSMRFLRII)                                  ║
║   • AZDC01:   10.10.4.4  - Primary DC (Forest Root)                          ║
║   • AZDC02:   10.10.4.5  - Secondary DC                                      ║
║   • AZRODC01: 10.10.4.6  - Read-Only DC                                      ║
║   • AZRODC02: 10.10.4.7  - Read-Only DC                                      ║
║   • Admin:    HRMSMRFLRII\azureadmin                                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ SSH ACCESS                                                                    ║
║   • User: hermes-admin (VMs) | root (Proxmox)                                ║
║   • Homelab Key:  ~/.ssh/homelab_ed25519                                     ║
║   • Azure Key:    ~/.ssh/ubuntu-deploy-vm.pem                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Multi-Session Workflow

**CRITICAL: Follow this protocol for all sessions to ensure context continuity.**

### Before Starting ANY Work

1. **Check active tasks**: Read `.claude/active-tasks.md` for in-progress work
2. **Check session log**: Read `.claude/session-log.md` for recent history
3. **Avoid conflicts**: Don't work on something another session is handling

### During Work (Document As You Go)

1. **Log immediately**: Add entry to `.claude/session-log.md` when starting
2. **Mark active**: Update `.claude/active-tasks.md` with your current task
3. **Update docs incrementally**: Don't wait until the end
4. **Update CHANGELOG.md**: Add entry for significant changes

### If Tokens Running Low

Before tokens exhaust, write a handoff:
1. Update `.claude/active-tasks.md` with:
   - What's completed
   - What's remaining
   - Specific resume instructions
2. Commit changes so next session has context

### After Completing Work

1. Move task from "In Progress" to "Recently Completed" in active-tasks.md
2. Update session-log.md with final status
3. Clear your entry from active tasks

---

## Context Files

| File | Purpose | When to Read |
|------|---------|--------------|
| `.claude/context.md` | Infrastructure reference (IPs, services, auth) | Always |
| `.claude/active-tasks.md` | Work in progress tracking | Before starting work |
| `.claude/session-log.md` | Recent session history | To understand recent changes |
| `.claude/conventions.md` | Standards, patterns, checklists | When adding services/docs |

---

## Quick Reference

| Resource | Documentation |
|----------|---------------|
| **Network** | [docs/NETWORKING.md](./docs/NETWORKING.md) |
| **Compute** | [docs/PROXMOX.md](./docs/PROXMOX.md) |
| **Storage** | [docs/STORAGE.md](./docs/STORAGE.md) |
| **Terraform** | [docs/TERRAFORM.md](./docs/TERRAFORM.md) |
| **Packer** | [docs/PACKER.md](./docs/PACKER.md) |
| **Services** | [docs/SERVICES.md](./docs/SERVICES.md) |
| **App Config** | [docs/APPLICATION_CONFIGURATIONS.md](./docs/APPLICATION_CONFIGURATIONS.md) |
| **Ansible** | [docs/ANSIBLE.md](./docs/ANSIBLE.md) |
| **Inventory** | [docs/INVENTORY.md](./docs/INVENTORY.md) |
| **Observability** | [docs/OBSERVABILITY.md](./docs/OBSERVABILITY.md) |
| **Watchtower** | [docs/WATCHTOWER.md](./docs/WATCHTOWER.md) |
| **Glance** | [docs/GLANCE.md](./docs/GLANCE.md) |
| **CI/CD** | [docs/CICD.md](./docs/CICD.md) |
| **Service Onboarding** | [docs/SERVICE_ONBOARDING.md](./docs/SERVICE_ONBOARDING.md) |
| **Discord Bots** | [docs/DISCORD_BOTS.md](./docs/DISCORD_BOTS.md) |
| **Azure Environment** | [docs/AZURE_ENVIRONMENT.md](./docs/AZURE_ENVIRONMENT.md) |
| **Azure Hybrid Lab** | [docs/AZURE_HYBRID_LAB.md](./docs/AZURE_HYBRID_LAB.md) |
| **PBS Monitoring** | [docs/PBS_MONITORING.md](./docs/PBS_MONITORING.md) |
| **Troubleshooting** | [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) |

---

## Infrastructure Overview

### Proxmox Cluster

**Cluster**: MorpheusCluster (3-node + Qdevice)

| Node | Local IP | Tailscale IP | Purpose |
|------|----------|--------------|---------|
| node01 | 192.168.20.20 | 100.89.33.5 | Primary VM Host (K8s, LXCs, Core Services) |
| node02 | 192.168.20.21 | 100.96.195.27 | Service Host (Traefik, Authentik, GitLab, Immich) |
| node03 | 192.168.20.22 | - | Additional Node |

### Remote Access (Tailscale)

When outside the local network:
```bash
ssh root@100.89.33.5         # node01
ssh root@100.96.195.27       # node02
ssh root@192.168.20.22       # node03 (local only)
```

### Networks

| VLAN | Network | Purpose |
|------|---------|---------|
| VLAN 20 | 192.168.20.0/24 | Infrastructure (K8s, Ansible) |
| VLAN 40 | 192.168.40.0/24 | Services (Docker, Apps) |

### Azure Cloud Environment

**Subscription**: FireGiants-Prod (`2212d587-1bad-4013-b605-b421b1f83c30`)

| Resource | IP/Name | Purpose |
|----------|---------|---------|
| ubuntu-deploy-vm | 10.90.10.5 | **Primary deployment VM** (Terraform, Ansible, Azure CLI) |
| ans-tf-vm01 | 10.90.10.4 | Windows management VM (legacy) |
| law-homelab-sentinel | - | Log Analytics + Sentinel SIEM |
| linux-syslog-server01 | 192.168.40.5 (Arc) | Syslog aggregator (homelab) |

**Connectivity**: Site-to-Site VPN (OPNsense <-> Azure VNet 10.90.10.0/29)

```bash
# SSH to Azure deployment VM
ssh ubuntu-deploy

# Or explicitly
ssh -i ~/.ssh/ubuntu-deploy-vm.pem hermes-admin@10.90.10.5
```

### Deployed Infrastructure

**18 VMs Total**: 1 Ansible + 9 Kubernetes + 8 Services

See [docs/INVENTORY.md](./docs/INVENTORY.md) for full details.

---

## Quick Start

```bash
# Deploy Infrastructure (from terraform/proxmox/)
cd terraform/proxmox && terraform init && terraform plan && terraform apply

# Access Ansible Controller
ssh hermes-admin@192.168.20.30

# SSH Quick Access (from ~/.ssh/config)
ssh node01              # Proxmox node01
ssh ansible             # Ansible controller
ssh docker-vm-core-utilities01    # Docker utilities host
```

---

## Documentation Update Protocol

**CRITICAL: When user says "update all documentation" or "update all docs", you MUST update ALL of these locations:**

| Location | Path | What to Update |
|----------|------|----------------|
| **docs/** | `docs/*.md` | Technical reference files |
| **GitHub Wiki** | `wiki/*.md` | Corresponding wiki pages |
| **Obsidian Vault** | See path below | Corresponding Obsidian notes |
| **Technical Manual** | `38 - Homelab Technical Manual.md` in Obsidian | Comprehensive reference manual |
| **.claude/context.md** | `.claude/context.md` | Infrastructure context |
| **CHANGELOG.md** | `CHANGELOG.md` | Add change entry |

This is NOT optional - ALL 6 locations must be updated for documentation consistency.

See `.claude/conventions.md` for full sync guide and document mapping.

### Obsidian Vault Path
```
C:\Users\herms14\OneDrive\Obsidian Vault\Hermes's Life Knowledge Base\07 HomeLab Things\Claude Managed Homelab\
```

---

## Protected Configurations

**DO NOT modify without explicit user permission:**

### Glance Dashboard Pages
- Glance Home page layout
- Glance Media page layout
- Glance Compute tab layout
- Glance Storage tab layout
- Glance Network tab layout

### Grafana Dashboards
- **Container Status History** (`container-status`)
  - Iframe height: 1250px
  - Dashboard JSON: `dashboards/container-status.json`
  - Ansible: `ansible/playbooks/monitoring/deploy-container-status-dashboard.yml`

- **Synology NAS Storage** (`synology-nas-modern`)
  - Iframe height: 1350px
  - Dashboard JSON: `dashboards/synology-nas.json`
  - Ansible: `ansible/playbooks/monitoring/deploy-synology-nas-dashboard.yml`

- **Omada Network Overview** (`omada-network`)
  - Iframe height: 2200px
  - Dashboard JSON: `dashboards/omada-network.json`
  - Ansible: `ansible/playbooks/monitoring/deploy-omada-full-dashboard.yml`

See `.claude/context.md` for current structure details.

---

## Key Service URLs

| Service | URL |
|---------|-----|
| Proxmox | https://proxmox.hrmsmrflrii.xyz |
| Traefik | https://traefik.hrmsmrflrii.xyz |
| Authentik | https://auth.hrmsmrflrii.xyz |
| GitLab | https://gitlab.hrmsmrflrii.xyz |
| Glance | https://glance.hrmsmrflrii.xyz |
| Grafana | https://grafana.hrmsmrflrii.xyz |
| PBS | https://pbs.hrmsmrflrii.xyz |
| **New Services** | |
| Lagident | https://lagident.hrmsmrflrii.xyz |
| Karakeep | https://karakeep.hrmsmrflrii.xyz |
| Wizarr | https://wizarr.hrmsmrflrii.xyz |
| Tracearr | https://tracearr.hrmsmrflrii.xyz |

Full service list in `.claude/context.md`.

---

## Homelab Blog

Personal blog documenting the homelab journey, hosted on GitHub Pages using Hugo.

| Resource | URL |
|----------|-----|
| **Blog URL** | https://herms14.github.io/Clustered-Thoughts/ |
| **GitHub Repo** | https://github.com/herms14/Clustered-Thoughts |
| **Theme** | PaperMod |
| **Deployment** | GitHub Actions (automatic on push to main) |

### Adding New Blog Posts

1. Create a new `.md` file in `content/posts/`
2. Use this front matter:
```yaml
---
title: "Your Post Title"
date: 2025-12-27
draft: false
tags: ["homelab", "networking"]
categories: ["homelab"]
---
```
3. Commit and push - auto-deploys via GitHub Actions

### Blog Post Source (Obsidian)

Blog posts are drafted in Obsidian before publishing:
```
~/Library/CloudStorage/OneDrive-Personal/Obsidian Vault/Hermes's Life Knowledge Base/07 HomeLab Things/Homelab Blog Posts/
```

---

## Authentication

| Access | Details |
|--------|---------|
| SSH User | hermes-admin (VMs), root (Proxmox) |
| SSH Key | `~/.ssh/homelab_ed25519` (no passphrase) |
| Proxmox API | terraform-deployment-user@pve!tf |

---

## SSH Key Deployment (REQUIRED)

**CRITICAL: When deploying ANY new infrastructure (VM, LXC, Docker container), you MUST configure SSH key authentication using the homelab SSH key.**

### SSH Public Key

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINVYlOowJQE4tC4GEo17MptDGdaQfWwMDMRxLdKd/yui hermes@homelab-nopass
```

### Deployment Requirements

| Infrastructure Type | SSH Key Setup Method |
|---------------------|---------------------|
| **Terraform VMs** | Use `ssh_public_key` variable in `terraform.tfvars` |
| **LXC Containers** | Add to `authorized_keys` in Terraform or cloud-init |
| **Docker Hosts** | Ensure key is in `~/.ssh/authorized_keys` for hermes-admin |
| **Manual VMs** | Copy key to `/home/hermes-admin/.ssh/authorized_keys` |

### How to Add Key to New Infrastructure

**For cloud-init based VMs (Terraform):**
```yaml
# Already configured in terraform.tfvars
ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINVYlOowJQE4tC4GEo17MptDGdaQfWwMDMRxLdKd/yui hermes@homelab-nopass"
```

**For manual setup:**
```bash
# On the new VM/LXC/container
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINVYlOowJQE4tC4GEo17MptDGdaQfWwMDMRxLdKd/yui hermes@homelab-nopass" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

**For Ansible playbooks:**
```yaml
- name: Add SSH key for hermes-admin
  authorized_key:
    user: hermes-admin
    key: "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINVYlOowJQE4tC4GEo17MptDGdaQfWwMDMRxLdKd/yui hermes@homelab-nopass"
    state: present
```

### Verification

After deploying new infrastructure, verify SSH access works:
```bash
ssh hermes-admin@<new-host-ip>
```

---

## Remote Deployment via Tailscale (MacBook)

This section covers deploying to the homelab from a MacBook connected via Tailscale.

### Prerequisites Checklist

Before deploying remotely, ensure:

- [ ] Tailscale installed and signed in
- [ ] Subnet routes accepted (`tailscale up --accept-routes`)
- [ ] SSH key copied to `~/.ssh/homelab_ed25519`
- [ ] SSH key permissions set (`chmod 600 ~/.ssh/homelab_ed25519`)

### Tailscale Subnet Router

node01 (100.89.33.5) is configured as a **subnet router** advertising:

| Network | Purpose | Reachable Hosts |
|---------|---------|-----------------|
| 192.168.20.0/24 | Infrastructure | Proxmox nodes, Ansible, K8s |
| 192.168.40.0/24 | Services | Docker hosts, all applications |
| 192.168.91.0/24 | Firewall | OPNsense DNS (192.168.91.30) |

### Verify Tailscale Connection

```bash
# Check Tailscale status
/Applications/Tailscale.app/Contents/MacOS/Tailscale status

# Verify subnet routes are accepted
ping 192.168.20.30    # Ansible controller
ping 192.168.40.13    # Docker utilities

# Verify DNS works
nslookup grafana.hrmsmrflrii.xyz
```

### SSH Key Setup (One-Time)

```bash
# Create .ssh directory if needed
mkdir -p ~/.ssh && chmod 700 ~/.ssh

# Copy key from Windows (via OneDrive or manual transfer)
# The key should be at: ~/.ssh/homelab_ed25519

# Set permissions
chmod 600 ~/.ssh/homelab_ed25519

# Add to SSH config (~/.ssh/config)
cat >> ~/.ssh/config << 'EOF'
# Homelab - Proxmox Nodes
Host node01
    HostName 192.168.20.20
    User root
    IdentityFile ~/.ssh/homelab_ed25519

Host node02
    HostName 192.168.20.21
    User root
    IdentityFile ~/.ssh/homelab_ed25519

# Homelab - Ansible Controller
Host ansible
    HostName 192.168.20.30
    User hermes-admin
    IdentityFile ~/.ssh/homelab_ed25519

# Homelab - Docker Hosts
Host docker-vm-core-utilities01
    HostName 192.168.40.13
    User hermes-admin
    IdentityFile ~/.ssh/homelab_ed25519

Host docker-lxc-glance
    HostName 192.168.40.12
    User hermes-admin
    IdentityFile ~/.ssh/homelab_ed25519

Host docker-media
    HostName 192.168.40.11
    User hermes-admin
    IdentityFile ~/.ssh/homelab_ed25519

# Homelab - Service VMs
Host traefik
    HostName 192.168.40.20
    User hermes-admin
    IdentityFile ~/.ssh/homelab_ed25519

Host authentik
    HostName 192.168.40.21
    User hermes-admin
    IdentityFile ~/.ssh/homelab_ed25519
EOF

chmod 600 ~/.ssh/config
```

### Deployment Methods

#### Method 1: Via Ansible Controller (Recommended)

The Ansible controller already has everything configured. SSH in and run deployments from there:

```bash
# Connect to Ansible controller
ssh ansible

# Navigate to playbooks
cd ~/ansible

# Run any playbook
ansible-playbook services/deploy-xyz.yml
ansible-playbook monitoring/deploy-grafana-dashboard.yml

# Check service status
ansible docker_hosts -m shell -a "docker ps"
```

#### Method 2: Direct from MacBook

Run Ansible directly from MacBook (requires Ansible installed):

```bash
# Install Ansible on MacBook
brew install ansible

# From the repo directory
cd ~/path/to/tf-proxmox

# Run playbook with inventory
ansible-playbook -i ansible/playbooks/inventory.ini \
    ansible/playbooks/services/deploy-xyz.yml
```

#### Method 3: Direct SSH Commands

For quick tasks without Ansible:

```bash
# Restart a container
ssh docker-utilities "cd /opt/glance && docker compose restart"

# Check container logs
ssh docker-media "docker logs jellyfin --tail 50"

# Deploy a simple compose file
scp docker-compose.yml docker-utilities:/opt/myservice/
ssh docker-utilities "cd /opt/myservice && docker compose up -d"
```

### Key Hosts Quick Reference

| Alias | IP | User | Purpose |
|-------|-----|------|---------|
| `ansible` | 192.168.20.30 | hermes-admin | Ansible controller, run playbooks |
| `docker-vm-core-utilities01` | 192.168.40.13 | hermes-admin | Grafana, Prometheus, n8n, Life Progress API |
| `docker-lxc-glance` | 192.168.40.12 | hermes-admin | Glance Dashboard |
| `docker-media` | 192.168.40.11 | hermes-admin | Jellyfin, *arr stack |
| `traefik` | 192.168.40.20 | hermes-admin | Reverse proxy |
| `authentik` | 192.168.40.21 | hermes-admin | SSO/Authentication |
| `node01` | 192.168.20.20 | root | Proxmox node (subnet router) |
| `node02` | 192.168.20.21 | root | Proxmox node |

### Common Deployment Commands

```bash
# === Service Management ===
ssh docker-vm-core-utilities01 "docker ps"                          # List containers
ssh docker-vm-core-utilities01 "docker restart grafana"             # Restart service
ssh docker-vm-core-utilities01 "docker logs glance --tail 100"      # View logs

# === Glance Dashboard ===
ssh docker-lxc-glance "docker restart glance"
ssh docker-lxc-glance "cat /opt/glance/config/glance.yml"  # View config

# === Grafana Dashboards ===
ssh ansible "cd ~/ansible && ansible-playbook monitoring/deploy-container-status-dashboard.yml"

# === Traefik Routes ===
ssh traefik "cat /opt/traefik/config/dynamic/services.yml"
ssh traefik "docker logs traefik --tail 50"

# === Full Service Deployment ===
ssh ansible "cd ~/ansible && ansible-playbook services/deploy-all-new-services.yml"
```

### Credentials Location

Credentials are NOT in this repo. They are stored in:

| Location | Contents | Access |
|----------|----------|--------|
| **Obsidian Vault** | All passwords, API keys, tokens | OneDrive sync |
| **Ansible Controller** | SSH keys, ansible vault | Already configured |
| **1Password/Bitwarden** | Master credentials | Your password manager |

**Obsidian Vault Path (MacBook via OneDrive):**
```
~/Library/CloudStorage/OneDrive-Personal/Obsidian Vault/Hermes's Life Knowledge Base/07 HomeLab Things/Claude Managed Homelab/11 - Credentials.md
```

### Terraform Deployment (Optional)

If running Terraform directly from MacBook:

```bash
# Install Terraform
brew install terraform

# Create terraform.tfvars (NOT committed to git)
cat > terraform.tfvars << 'EOF'
proxmox_api_url   = "https://192.168.20.21:8006/api2/json"
proxmox_api_token = "terraform-deployment-user@pve!tf=YOUR_TOKEN"
EOF

# Deploy
terraform init
terraform plan
terraform apply
```

### Troubleshooting Remote Access

```bash
# Tailscale not connecting
sudo killall Tailscale tailscaled
open -a Tailscale
/Applications/Tailscale.app/Contents/MacOS/Tailscale up --accept-routes

# SSH permission denied
chmod 600 ~/.ssh/homelab_ed25519
ssh-add ~/.ssh/homelab_ed25519

# Can't reach local IPs
# Verify subnet routes are approved in Tailscale Admin Console
# https://login.tailscale.com/admin/machines → node01 → Edit route settings

# DNS not resolving
# Check split DNS in Tailscale Admin Console → DNS tab
# Nameserver: 192.168.91.30, Restricted to: hrmsmrflrii.xyz

# Test connectivity step by step
ping 100.89.33.5      # Tailscale direct to node01
ping 192.168.20.20    # Via subnet router to node01
ping 192.168.40.13    # Via subnet router to docker-utilities
```

### macOS Tailscale Alias (Recommended)

Add to `~/.zshrc`:
```bash
alias tailscale="/Applications/Tailscale.app/Contents/MacOS/Tailscale"
```

Then reload: `source ~/.zshrc`

---

## Obsidian Daily Notes Integration

The Glance Home page includes an Obsidian Daily Notes widget that displays today's note from your MacBook's Obsidian vault. This requires specific setup to work.

### Requirements

| Component | Details |
|-----------|---------|
| **Obsidian Plugin** | Local REST API (Community Plugin) |
| **MacBook Tailscale IP** | 100.90.207.58 |
| **API Port** | 27123 |
| **API Key** | Stored in Obsidian vault (11 - Credentials.md) |

### Setup Checklist (Local Network)

When connected to the local network and want the Obsidian Daily Notes widget to work:

1. **MacBook Requirements**:
   - [ ] Obsidian must be running
   - [ ] Local REST API plugin enabled and running
   - [ ] Plugin must bind to `0.0.0.0` (not localhost) - Settings > Local REST API > Network Interface
   - [ ] MacBook connected to Tailscale

2. **Server Requirements** (docker-vm-core-utilities01):
   - [ ] Tailscale installed and authenticated (already done)
   - [ ] Can reach MacBook via Tailscale IP (100.90.207.58)

### Verify Connectivity

```bash
# From docker-vm-core-utilities01 server
ssh docker-vm-core-utilities01 "curl -s -H 'Authorization: Bearer YOUR_API_KEY' http://100.90.207.58:27123/vault/"

# Test from MacBook (should work locally)
curl -s -H 'Authorization: Bearer YOUR_API_KEY' http://localhost:27123/vault/
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Widget shows "Create today's note" | Obsidian not running or today's note doesn't exist |
| Widget shows error | Check API key, verify Obsidian plugin is running |
| Connection refused | Plugin bound to localhost; change to 0.0.0.0 |
| Server can't reach MacBook | Verify both devices on Tailscale |

### Configuration

The widget is configured in Glance at `/opt/glance/config/glance.yml`:
- API URL: `http://100.90.207.58:27123/vault/05%20Periodic%20Notes/00%20Daily/{DATE}.md`
- Cache: 5 minutes
- Daily note path: `05 Periodic Notes/00 Daily/YYYY-MM-DD.md`

---

## Adding New Services

Quick checklist (full details in `.claude/conventions.md`):

1. Deploy VM via Terraform
2. Create Ansible playbook
3. Add Traefik route
4. Update DNS in OPNsense
5. Add Authentik protection (if needed)
6. Update Discord bots
7. Update ALL documentation locations

---

## Tutorial Creation Standards

When asked to create a tutorial, follow the comprehensive format established in `docs/DISCORD_BOT_DEPLOYMENT_TUTORIAL.md`.

### Required Tutorial Structure

1. **Title & Introduction**
   - Clear title describing what the tutorial covers
   - Brief overview of what will be built/learned

2. **Table of Contents**
   - Numbered sections with anchor links
   - Logical progression from basics to advanced

3. **Architecture Overview**
   - ASCII diagram showing the system architecture
   - Key concepts table with Term → Definition format
   - "Why" explanations for technology choices

4. **Prerequisites**
   - Infrastructure requirements
   - Software/accounts needed
   - Network requirements table

5. **Step-by-Step Parts**
   - Number each major section (Part 1, Part 2, etc.)
   - Sub-steps with clear numbering (Step 1.1, Step 1.2)
   - Code blocks with comments explaining each line
   - Tables explaining command parameters/options
   - "Line-by-Line Explanation" sections for complex code

6. **Command Reference Tables**
   - Format: `| Command | Purpose |`
   - Group by category (Docker, SSH, Proxmox, etc.)

7. **Troubleshooting Section**
   - Common issues with solutions
   - Error messages and fixes

8. **Appendix (if needed)**
   - Configuration examples
   - Environment-specific settings

### Formatting Guidelines

- Use tables liberally for structured information
- Include ASCII diagrams for architecture
- Every code block should have context/explanation
- Use `> **Note:**` callouts for important information
- Include "Key Concepts Explained" tables after complex sections
- End with a Summary section recapping what was learned

### Example Reference

See `docs/DISCORD_BOT_DEPLOYMENT_TUTORIAL.md` for the gold standard format (~500 lines, comprehensive coverage from basics to production deployment).
