# Homelab Infrastructure

Infrastructure-as-code repository for a Proxmox-based homelab environment with Kubernetes, Docker services, monitoring, and automation.

## Overview

This repository contains all the automation, configuration, and infrastructure code for managing a homelab environment:

- **Proxmox Cluster**: 3-node virtualization cluster
- **Kubernetes**: 9-node K8s cluster (3 controllers + 6 workers)
- **Docker Services**: Media stack, monitoring, dashboards, bots
- **Automation**: Ansible playbooks for deployment and configuration

## Architecture

| Component | Count | Purpose |
|-----------|-------|---------|
| Proxmox Nodes | 3 | Virtualization hosts |
| Kubernetes VMs | 9 | Container orchestration |
| Docker VMs | 2 | Service hosting |
| LXC Containers | 4 | Lightweight services |

### Network Layout

| VLAN | Network | Purpose |
|------|---------|---------|
| VLAN 20 | 192.168.20.0/24 | Infrastructure |
| VLAN 40 | 192.168.40.0/24 | Services |

## Repository Structure

```
homelab-infrastructure/
├── ansible/                 # Ansible playbooks
│   ├── glance/              # Dashboard deployment
│   ├── monitoring/          # Prometheus/Grafana stack
│   ├── discord-bots/        # Bot deployments
│   ├── media/               # Media stack (Arr services)
│   ├── infrastructure/      # Core services
│   ├── kubernetes/          # K8s deployment
│   └── config/              # Configuration playbooks
│
├── terraform/               # Infrastructure as Code
│   ├── main.tf              # VM definitions
│   ├── lxc.tf               # LXC containers
│   ├── variables.tf         # Variables
│   └── modules/             # Reusable modules
│
├── python/                  # Python applications
│   ├── apis/                # Flask APIs
│   ├── discord-bots/        # Discord bots
│   ├── exporters/           # Prometheus exporters
│   └── ci-cd/               # GitLab CI/CD scripts
│
├── dashboards/              # Grafana dashboards
│   └── grafana/             # Dashboard JSON files
│
├── configs/                 # Configuration files
│   ├── glance/              # Glance dashboard config
│   ├── traefik/             # Traefik proxy config
│   └── prometheus/          # Prometheus config
│
└── docs/                    # Documentation
```

## Services

### Deployed Services

| Service | URL | Description |
|---------|-----|-------------|
| Traefik | traefik.hrmsmrflrii.xyz | Reverse proxy |
| Authentik | auth.hrmsmrflrii.xyz | SSO/Identity |
| Glance | glance.hrmsmrflrii.xyz | Dashboard |
| Grafana | grafana.hrmsmrflrii.xyz | Metrics visualization |
| Prometheus | prometheus.hrmsmrflrii.xyz | Metrics collection |
| Uptime Kuma | uptime.hrmsmrflrii.xyz | Status monitoring |
| Jellyfin | jellyfin.hrmsmrflrii.xyz | Media server |
| GitLab | gitlab.hrmsmrflrii.xyz | Version control |
| Immich | photos.hrmsmrflrii.xyz | Photo management |
| n8n | n8n.hrmsmrflrii.xyz | Workflow automation |

### Discord Bots

| Bot | Channel | Purpose |
|-----|---------|---------|
| Update Manager | #update-manager | Container updates |
| Argus SysAdmin | #argus-assistant | VM/container control |
| Download Monitor | #media-downloads | Media notifications |

## Quick Start

### Prerequisites

- Proxmox VE 8.x cluster
- Ansible 2.15+
- Terraform 1.5+
- SSH access to all hosts

### Deploy Infrastructure

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/homelab-infrastructure.git
cd homelab-infrastructure

# Configure Terraform
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit terraform.tfvars with your values

# Deploy VMs
cd terraform
terraform init
terraform plan
terraform apply
```

### Deploy Services

```bash
# Deploy monitoring stack
cd ansible
ansible-playbook monitoring/deploy-monitoring-stack.yml

# Deploy Glance dashboard
ansible-playbook glance/deploy-glance-dashboard.yml

# Deploy Discord bots
ansible-playbook discord-bots/deploy-sysadmin-bot.yml
```

## Configuration

### Environment Variables

Each service has a `.env.example` file that needs to be copied and configured:

```bash
cp python/discord-bots/sysadmin-bot/.env.example python/discord-bots/sysadmin-bot/.env
# Edit .env with your values
```

### SSH Access

Configure SSH access using key-based authentication:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/homelab_ed25519
ssh-copy-id -i ~/.ssh/homelab_ed25519 hermes-admin@192.168.40.10
```

## Documentation

- [Ansible Playbooks](ansible/README.md)
- [Python Applications](python/README.md)
- [Grafana Dashboards](dashboards/README.md)
- [Configuration Files](configs/README.md)

## Security Notes

- All secrets are stored in `.env` files (gitignored)
- Example configuration files provided as `*.example`
- SSH keys must be generated locally
- API tokens should be rotated regularly

## License

Private repository - not for public distribution.
