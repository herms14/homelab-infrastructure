# Ansible Automation

> Part of the [Proxmox Infrastructure Documentation](../CLAUDE.md)

## Overview

All configuration management runs from **ansible-controller01** (192.168.20.30).

```bash
# Connect to controller
ssh hermes-admin@192.168.20.30
cd ~/ansible
```

## Playbook Directory

```
~/ansible/
├── docker/
│   ├── install-docker.yml          # Docker installation
│   └── deploy-arr-stack.yml        # Arr media stack
├── authentik/
│   └── deploy-authentik.yml        # SSO/Identity provider
├── immich/
│   └── deploy-immich.yml           # Photo management
├── traefik/
│   ├── deploy-traefik.yml          # Reverse proxy (basic)
│   └── deploy-traefik-ssl.yml      # Reverse proxy with SSL + OTEL
├── gitlab/
│   └── deploy-gitlab.yml           # DevOps platform
├── n8n/
│   └── deploy-n8n.yml              # Workflow automation
├── synology/
│   └── configure-nfs-permissions.yml
├── opnsense/
│   ├── add-dns-record.yml          # Single DNS record
│   ├── add-all-services-dns.yml    # All 27 homelab services
│   └── add-observability-dns.yml   # Observability services only
├── k8s/
│   └── k8s-deploy-all.yml          # Full K8s cluster
└── callback_plugins/
    └── discord_notify.py           # Discord notifications

~/ansible-playbooks/
├── monitoring/
│   ├── deploy-monitoring-stack.yml     # Prometheus, Grafana, Uptime Kuma
│   └── deploy-observability-stack.yml  # OTEL Collector, Jaeger, Demo App
└── ...
```

## Common Operations

### Check Connectivity

```bash
ansible all -m ping
```

### Check Uptime

```bash
ansible all -a uptime
```

### Update All Systems

```bash
ansible-playbook update-systems.yml
```

### Deploy Kubernetes Cluster

```bash
ansible-playbook k8s/k8s-deploy-all.yml
```

See [Kubernetes_Setup.md](./legacy/Kubernetes_Setup.md) for complete guide.

## Service Deployments

| Service | Playbook | Target Host |
|---------|----------|-------------|
| Docker | `docker/install-docker.yml` | Any VM |
| Arr Stack | `docker/deploy-arr-stack.yml` | docker-vm-media01 |
| Traefik (SSL + OTEL) | `traefik/deploy-traefik-ssl.yml` | traefik-vm01 |
| Authentik | `authentik/deploy-authentik.yml` | authentik-vm01 |
| Immich | `immich/deploy-immich.yml` | immich-vm01 |
| GitLab | `gitlab/deploy-gitlab.yml` | gitlab-vm01 |
| n8n | `n8n/deploy-n8n.yml` | docker-vm-utilities01 |
| Monitoring Stack | `monitoring/deploy-monitoring-stack.yml` | docker-vm-utilities01 |
| Observability Stack | `monitoring/deploy-observability-stack.yml` | docker-vm-utilities01 |

## OPNsense DNS Automation

Manage DNS host overrides in OPNsense via API.

### Prerequisites

1. Create API key in OPNsense: System > Access > Users > [user] > API keys
2. Set environment variables:
   ```bash
   export OPNSENSE_API_KEY="your-api-key"
   export OPNSENSE_API_SECRET="your-api-secret"
   ```

### Add Single DNS Record

```bash
ansible-playbook opnsense/add-dns-record.yml -e "hostname=myservice ip=192.168.40.10"
```

### Add All Homelab Services

```bash
ansible-playbook opnsense/add-all-services-dns.yml
```

### Add Observability Services Only

```bash
ansible-playbook opnsense/add-observability-dns.yml
```

Adds DNS for: uptime, prometheus, grafana, jaeger, demo

## Discord Notifications

**Status**: Ready to deploy

Automated Discord notifications for Ansible playbook runs.

### Features

- Automatic notifications at end of every playbook
- Task summaries (OK, Changed, Skipped, Failed counts)
- Duration tracking
- Failed task details with host and task names
- Color-coded status (green=success, orange=changed, red=failed)

### Setup

1. **Create Discord Webhook**:
   - Server Settings > Integrations > Webhooks > New Webhook
   - Copy webhook URL

2. **Set Environment Variable**:
   ```bash
   export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN"
   ```

3. **Deploy to Ansible Controller**:
   ```bash
   scp -r ansible-playbooks/discord-notifications/* hermes-admin@192.168.20.30:~/ansible/
   ```

### Notification Example

```
Playbook: deploy-arr-stack.yml
Status: Success    Hosts: 1    Duration: 2m 15s

Task Summary
OK:      45
Changed: 3
Skipped: 2
Failed:  0

Hosts: docker-vm-media01
```

### Files

| File | Purpose |
|------|---------|
| `callback_plugins/discord_notify.py` | Auto-notification callback |
| `roles/discord-notify/` | Manual notification role |
| `DISCORD_NOTIFICATIONS.md` | Full documentation |

## Inventory

### Static Inventory

Located at `~/ansible/inventory/hosts`:

```ini
[k8s_controllers]
k8s-controller01 ansible_host=192.168.20.32
k8s-controller02 ansible_host=192.168.20.33
k8s-controller03 ansible_host=192.168.20.34

[k8s_workers]
k8s-worker01 ansible_host=192.168.20.40
k8s-worker02 ansible_host=192.168.20.41
k8s-worker03 ansible_host=192.168.20.42
k8s-worker04 ansible_host=192.168.20.43
k8s-worker05 ansible_host=192.168.20.44
k8s-worker06 ansible_host=192.168.20.45

[docker_hosts]
docker-vm-media01 ansible_host=192.168.40.11
docker-vm-utilities01 ansible_host=192.168.40.10

[services]
traefik-vm01 ansible_host=192.168.40.20
authentik-vm01 ansible_host=192.168.40.21
immich-vm01 ansible_host=192.168.40.22
gitlab-vm01 ansible_host=192.168.40.23
```

### Variables

```ini
[all:vars]
ansible_user=hermes-admin
ansible_ssh_private_key_file=~/.ssh/id_ed25519
```

## Related Documentation

- [Services](./SERVICES.md) - Service details and management
- [Inventory](./INVENTORY.md) - Full infrastructure inventory
- [Kubernetes](./legacy/Kubernetes_Setup.md) - K8s deployment guide
- [ANSIBLE_SETUP.md](./legacy/ANSIBLE_SETUP.md) - Full Ansible configuration
