# Ansible Playbooks

Ansible playbooks for deploying and configuring homelab services.

## Directory Structure

```
ansible/
├── glance/          # Dashboard deployment
├── monitoring/      # Prometheus/Grafana stack
├── discord-bots/    # Bot deployments
├── media/           # Media stack
├── infrastructure/  # Core services
├── kubernetes/      # K8s deployment
└── config/          # Configuration
```

## Playbooks

### Glance Dashboard

| Playbook | Description |
|----------|-------------|
| `deploy-glance-dashboard.yml` | Deploy Glance dashboard |
| `deploy-media-stats-api.yml` | Deploy media statistics API |
| `deploy-life-progress-api.yml` | Deploy life progress API |
| `deploy-reddit-manager.yml` | Deploy Reddit manager |

### Monitoring

| Playbook | Description |
|----------|-------------|
| `deploy-monitoring-stack.yml` | Deploy Prometheus, Grafana, SNMP exporter |
| `deploy-observability-stack.yml` | Deploy OTEL, Jaeger tracing |
| `deploy-cadvisor.yml` | Deploy cAdvisor for container metrics |
| `deploy-docker-exporter.yml` | Deploy Docker stats exporter |
| `configure-uptime-kuma.yml` | Configure Uptime Kuma monitors |

### Discord Bots

| Playbook | Description |
|----------|-------------|
| `deploy-sysadmin-bot.yml` | Deploy Argus SysAdmin bot |
| `deploy-download-monitor.yml` | Deploy media download monitor |

### Infrastructure

| Playbook | Description |
|----------|-------------|
| `configure-ssl.yml` | Configure Proxmox SSL |
| `configure-google-sso.yml` | Configure Authentik SSO |
| `deploy-portainer.yml` | Deploy Portainer |

## Usage

```bash
# Run a playbook
ansible-playbook glance/deploy-glance-dashboard.yml

# Run with specific inventory
ansible-playbook -i inventory.yml monitoring/deploy-monitoring-stack.yml

# Dry run
ansible-playbook --check glance/deploy-glance-dashboard.yml
```

## Inventory

Default inventory targets:
- `docker-utilities`: 192.168.40.10
- `docker-media`: 192.168.40.11
- `traefik`: 192.168.40.20
