# GitLab CI/CD Service Onboarding

Automated service deployment using GitLab CI/CD pipelines. When you commit a `service.yml` to a repository, the pipeline automatically deploys and configures your service.

## Overview

| Component | Location | Purpose |
|-----------|----------|---------|
| GitLab Server | 192.168.40.23 | CI/CD coordinator |
| GitLab Runner | 192.168.40.24 | Job executor |
| Scripts | /opt/gitlab-runner/scripts/ | Automation scripts |

## Quick Start

### 1. Create a New Repository in GitLab

Navigate to http://192.168.40.23 and create a new project.

### 2. Add Required Files

**`.gitlab-ci.yml`** - Copy from `/opt/gitlab-runner/scripts/.gitlab-ci.yml` on the runner VM.

**`service.yml`** - Define your service:

```yaml
service:
  name: "myservice"
  display_name: "My Service"
  description: "What it does"

deployment:
  target_host: "docker-vm-utilities01"
  port: 8080
  container_port: 8080
  image: "myorg/myservice:latest"

traefik:
  enabled: true
  subdomain: "myservice"

dns:
  enabled: true

watchtower:
  enabled: true
```

### 3. Commit and Push

```bash
git add .
git commit -m "Add service configuration"
git push origin main
```

The pipeline will automatically:
1. Deploy the container to the target host
2. Configure Traefik reverse proxy
3. Add DNS record in OPNsense
4. Register with Watchtower for updates
5. Send Discord notification

## Pipeline Stages

| Stage | Description | Required |
|-------|-------------|----------|
| validate | Parse and validate service.yml | Yes |
| deploy | Deploy container via Ansible | Yes |
| configure_traefik | Add Traefik routes | Yes |
| configure_dns | Add OPNsense DNS record | No |
| register_watchtower | Register with Update Manager | No |
| configure_sso | Configure Authentik SSO | No |
| notify | Send Discord notification | No |

## Service Definition Schema

### Required Fields

```yaml
service:
  name: "string"        # Unique ID (lowercase, no spaces)
  display_name: "string" # Human-readable name
  description: "string"  # Brief description

deployment:
  target_host: "string"  # Docker host
  port: number          # Host port
  container_port: number # Container port
  image: "string"       # Docker image
```

### Optional Fields

```yaml
deployment:
  install_path: "/opt/myservice"
  restart_policy: "unless-stopped"
  volumes:
    - "/opt/myservice/config:/config"
  environment:
    TZ: "America/New_York"
  healthcheck_path: "/health"
  healthcheck_status: [200]

traefik:
  enabled: true
  subdomain: "myservice"
  websocket: false

dns:
  enabled: true
  hostname: "myservice"
  ip: "192.168.40.20"

watchtower:
  enabled: true
  container_name: "myservice"

authentik:
  enabled: false
  method: "forward_auth"
```

## Target Hosts

| Host | IP | Use For |
|------|-----|---------|
| docker-vm-utilities01 | 192.168.40.10 | Utility services |
| docker-vm-media01 | 192.168.40.11 | Media services |

## CI/CD Variables

Configure in GitLab > Settings > CI/CD > Variables:

| Variable | Required | Description |
|----------|----------|-------------|
| DISCORD_WEBHOOK_URL | No | Discord notifications |
| OPNSENSE_API_KEY | No | DNS automation |
| OPNSENSE_API_SECRET | No | DNS automation |
| AUTHENTIK_TOKEN | No | SSO automation |

## Rollback

If deployment fails, use the manual rollback jobs in the pipeline:

- **rollback_traefik** - Restore Traefik config from backup
- **rollback_container** - Remove the deployed container

## Automation Scripts

Located at `/opt/gitlab-runner/scripts/` on the runner VM:

| Script | Purpose |
|--------|---------|
| validate_service.py | Validate service.yml |
| generate_playbook.py | Generate Ansible playbook |
| configure_traefik.py | Add Traefik routes |
| configure_dns.py | Add OPNsense DNS |
| register_watchtower.py | Register with Update Manager |
| configure_authentik.py | Configure SSO |
| notify_discord.py | Send notifications |
| rollback_traefik.py | Restore Traefik |
| rollback_container.py | Remove container |

## Example: Deploy a Test Service

```yaml
# service.yml
service:
  name: "whoami"
  display_name: "WhoAmI Test"
  description: "Simple test service"

deployment:
  target_host: "docker-vm-utilities01"
  port: 8888
  container_port: 80
  image: "traefik/whoami:latest"

traefik:
  enabled: true
  subdomain: "whoami"
```

After commit, access at: https://whoami.hrmsmrflrii.xyz

## Troubleshooting

### Runner Not Picking Up Jobs

```bash
ssh hermes-admin@192.168.40.24
sudo gitlab-runner verify
sudo gitlab-runner status
```

### Pipeline Fails at Deploy Stage

Check Ansible connectivity:
```bash
ssh hermes-admin@192.168.40.24
sudo -u gitlab-runner ansible docker-vm-utilities01 -m ping
```

### Traefik Not Routing

Check Traefik logs:
```bash
ssh hermes-admin@192.168.40.20
docker logs traefik --tail 50
```

---

*Last updated: December 2025*
