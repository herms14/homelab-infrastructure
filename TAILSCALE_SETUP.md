# Tailscale Remote Access Setup

> Complete guide for connecting to the homelab from a MacBook via Tailscale.

## Overview

This guide sets up secure remote access to all homelab VMs and services using Tailscale's subnet router feature. Once configured, you can:

- SSH to any VM using local IPs (192.168.x.x)
- Access all services via domain names (*.hrmsmrflrii.xyz)
- Run Ansible playbooks and deployments remotely
- Access Proxmox Web UI

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Tailscale Network                            │
│                                                                      │
│   ┌──────────────┐         ┌──────────────┐         ┌─────────────┐ │
│   │   MacBook    │◄───────►│   node01     │◄───────►│   node02    │ │
│   │ 100.90.207.58│ WireGuard│ 100.89.33.5 │         │100.96.195.27│ │
│   └──────────────┘         │ SUBNET ROUTER│         └─────────────┘ │
│                            └──────┬───────┘                         │
│                                   │                                  │
└───────────────────────────────────┼──────────────────────────────────┘
                                    │ Advertises Routes
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │192.168.20 │   │192.168.40 │   │192.168.91 │
            │  /24      │   │  /24      │   │  /24      │
            │ Infra     │   │ Services  │   │ Firewall  │
            └───────────┘   └───────────┘   └───────────┘
```

## Prerequisites

- [ ] Tailscale app installed on MacBook
- [ ] Signed into Tailscale with correct account (herms14@gmail.com)
- [ ] SSH private key (`homelab_ed25519`) available in OneDrive

---

## Step 1: Copy SSH Key from OneDrive

The SSH key should be in OneDrive. Run these commands on your MacBook:

```bash
# Create .ssh directory if it doesn't exist
mkdir -p ~/.ssh && chmod 700 ~/.ssh

# Copy key from OneDrive
cp ~/Library/CloudStorage/OneDrive-Personal/homelab_ed25519 ~/.ssh/

# Set correct permissions (CRITICAL - SSH will refuse keys with wrong permissions)
chmod 600 ~/.ssh/homelab_ed25519

# Verify permissions
ls -la ~/.ssh/homelab_ed25519
# Expected output: -rw-------

# Delete from OneDrive for security
rm ~/Library/CloudStorage/OneDrive-Personal/homelab_ed25519
```

---

## Step 2: Create SSH Config

This creates shortcuts for all homelab hosts:

```bash
cat >> ~/.ssh/config << 'EOF'
# ============================================
# HOMELAB SSH CONFIGURATION
# ============================================

# Proxmox Nodes (root access)
Host node01
    HostName 192.168.20.20
    User root
    IdentityFile ~/.ssh/homelab_ed25519

Host node02
    HostName 192.168.20.21
    User root
    IdentityFile ~/.ssh/homelab_ed25519

Host node03
    HostName 192.168.20.22
    User root
    IdentityFile ~/.ssh/homelab_ed25519

# Ansible Controller
Host ansible
    HostName 192.168.20.30
    User hermes-admin
    IdentityFile ~/.ssh/homelab_ed25519

# Docker Hosts
Host docker-utilities
    HostName 192.168.40.10
    User hermes-admin
    IdentityFile ~/.ssh/homelab_ed25519

Host docker-media
    HostName 192.168.40.11
    User hermes-admin
    IdentityFile ~/.ssh/homelab_ed25519

# Service VMs
Host traefik
    HostName 192.168.40.20
    User hermes-admin
    IdentityFile ~/.ssh/homelab_ed25519

Host authentik
    HostName 192.168.40.21
    User hermes-admin
    IdentityFile ~/.ssh/homelab_ed25519

Host immich
    HostName 192.168.40.22
    User hermes-admin
    IdentityFile ~/.ssh/homelab_ed25519

Host gitlab
    HostName 192.168.40.23
    User hermes-admin
    IdentityFile ~/.ssh/homelab_ed25519
EOF

chmod 600 ~/.ssh/config
```

---

## Step 3: Configure Tailscale

### Add Tailscale Alias

The Tailscale CLI isn't in PATH by default on macOS:

```bash
# Add alias to .zshrc
echo 'alias tailscale="/Applications/Tailscale.app/Contents/MacOS/Tailscale"' >> ~/.zshrc

# Reload shell config
source ~/.zshrc
```

### Connect with Subnet Routes

```bash
# Connect to Tailscale and accept subnet routes
tailscale up --accept-routes

# Verify connection
tailscale status
```

**Expected output:**
```
100.89.33.5    node01               herms14@  linux  -
100.90.207.58  hermess-macbook-pro  herms14@  macOS  -
100.96.195.27  node02               herms14@  linux  -
100.76.81.39   node03               herms14@  linux  -
```

---

## Step 4: Verify Connectivity

### Test Subnet Routing

```bash
# Test Infrastructure VLAN (192.168.20.x)
ping -c 3 192.168.20.30    # Ansible controller

# Test Services VLAN (192.168.40.x)
ping -c 3 192.168.40.10    # Docker utilities

# Test Firewall VLAN (192.168.91.x)
ping -c 3 192.168.91.30    # OPNsense DNS
```

### Test DNS Resolution

```bash
# Should resolve to 192.168.40.20 (Traefik)
nslookup grafana.hrmsmrflrii.xyz

# Test service access
curl -I https://glance.hrmsmrflrii.xyz
```

### Test SSH Connection

```bash
# Quick test
ssh ansible "hostname"
# Expected output: ansible-controller01

# Test Proxmox node
ssh node01 "hostname"
# Expected output: node01
```

---

## Step 5: Clone Repository (Optional)

If you want to run deployments directly from MacBook:

```bash
# Clone the repo
cd ~/Projects  # or your preferred directory
git clone https://github.com/herms14/Proxmox-TerraformDeployments.git
cd Proxmox-TerraformDeployments

# Install Ansible (optional, for direct playbook runs)
brew install ansible
```

---

## Quick Reference

### Host Aliases

| Alias | IP | User | Purpose |
|-------|-----|------|---------|
| `node01` | 192.168.20.20 | root | Proxmox (Subnet Router) |
| `node02` | 192.168.20.21 | root | Proxmox |
| `node03` | 192.168.20.22 | root | Proxmox |
| `ansible` | 192.168.20.30 | hermes-admin | Ansible Controller |
| `docker-utilities` | 192.168.40.10 | hermes-admin | Glance, Grafana, Prometheus |
| `docker-media` | 192.168.40.11 | hermes-admin | Jellyfin, *arr stack |
| `traefik` | 192.168.40.20 | hermes-admin | Reverse Proxy |
| `authentik` | 192.168.40.21 | hermes-admin | SSO/Auth |

### Common Commands

```bash
# SSH to hosts
ssh ansible
ssh docker-utilities
ssh node01

# Run deployments via Ansible controller
ssh ansible "cd ~/ansible && ansible-playbook services/deploy-xyz.yml"

# Check container status
ssh docker-utilities "docker ps"

# View logs
ssh docker-media "docker logs jellyfin --tail 50"

# Restart a service
ssh docker-utilities "docker restart glance"
```

### Service URLs

All accessible via browser when connected to Tailscale:

| Service | URL |
|---------|-----|
| Glance Dashboard | https://glance.hrmsmrflrii.xyz |
| Grafana | https://grafana.hrmsmrflrii.xyz |
| Proxmox | https://proxmox.hrmsmrflrii.xyz |
| Traefik | https://traefik.hrmsmrflrii.xyz |
| Authentik | https://auth.hrmsmrflrii.xyz |
| Jellyfin | https://jellyfin.hrmsmrflrii.xyz |
| GitLab | https://gitlab.hrmsmrflrii.xyz |

---

## Troubleshooting

### Tailscale Not Connecting

```bash
# Restart Tailscale
sudo killall Tailscale tailscaled
open -a Tailscale
tailscale up --accept-routes
```

### Can't Reach Local IPs (192.168.x.x)

1. Verify subnet routes are approved in Tailscale Admin Console:
   - Go to https://login.tailscale.com/admin/machines
   - Find `node01` → Click `...` → Edit route settings
   - Ensure all three subnets are enabled:
     - 192.168.20.0/24
     - 192.168.40.0/24
     - 192.168.91.0/24

2. Verify routes are accepted on MacBook:
   ```bash
   tailscale up --accept-routes
   ```

### DNS Not Resolving

Check split DNS configuration in Tailscale Admin Console → DNS:
- Nameserver: `192.168.91.30`
- Restricted to domain: `hrmsmrflrii.xyz`
- Override local DNS: Enabled

Test directly:
```bash
nslookup grafana.hrmsmrflrii.xyz 192.168.91.30
```

### SSH Permission Denied

```bash
# Check key permissions
ls -la ~/.ssh/homelab_ed25519
# Must be: -rw------- (600)

# Fix if wrong
chmod 600 ~/.ssh/homelab_ed25519

# Add key to agent
ssh-add ~/.ssh/homelab_ed25519

# Test with verbose output
ssh -v ansible
```

### SSH Host Key Verification Failed

If you get "Host key verification failed":
```bash
# Remove old host key
ssh-keygen -R 192.168.20.30

# Or remove all homelab keys
ssh-keygen -R 192.168.20.20
ssh-keygen -R 192.168.20.21
ssh-keygen -R 192.168.20.22
ssh-keygen -R 192.168.40.10
ssh-keygen -R 192.168.40.11
```

---

## Security Notes

- **WireGuard Encryption**: All traffic through Tailscale is encrypted end-to-end
- **No Port Forwarding**: No ports are exposed to the public internet
- **Device Authentication**: Only devices in your Tailnet can access the subnets
- **SSH Key**: Keep `homelab_ed25519` secure, never share or commit to git

---

## Tailscale Admin Console

Manage your Tailnet at: https://login.tailscale.com/admin

Key settings:
- **Machines**: View/manage connected devices
- **DNS**: Configure split DNS for homelab domain
- **Access Controls**: Set up ACLs if needed

---

## Related Documentation

- [CLAUDE.md](./CLAUDE.md) - Full infrastructure context
- [docs/NETWORKING.md](./docs/NETWORKING.md) - Network architecture details
- [docs/ANSIBLE.md](./docs/ANSIBLE.md) - Ansible playbook guide
