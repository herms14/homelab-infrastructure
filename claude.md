# Proxmox Terraform Infrastructure

Terraform infrastructure-as-code for deploying VMs and LXC containers on a Proxmox VE 9.1.2 cluster.

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
| **Services** | [docs/SERVICES.md](./docs/SERVICES.md) |
| **App Config** | [docs/APPLICATION_CONFIGURATIONS.md](./docs/APPLICATION_CONFIGURATIONS.md) |
| **Ansible** | [docs/ANSIBLE.md](./docs/ANSIBLE.md) |
| **Inventory** | [docs/INVENTORY.md](./docs/INVENTORY.md) |
| **Observability** | [docs/OBSERVABILITY.md](./docs/OBSERVABILITY.md) |
| **Watchtower** | [docs/WATCHTOWER.md](./docs/WATCHTOWER.md) |
| **Glance** | [docs/GLANCE.md](./docs/GLANCE.md) |
| **CI/CD** | [docs/CICD.md](./docs/CICD.md) |
| **Service Onboarding** | [docs/SERVICE_ONBOARDING.md](./docs/SERVICE_ONBOARDING.md) |
| **Troubleshooting** | [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) |

---

## Infrastructure Overview

### Proxmox Cluster

| Node | Local IP | Tailscale IP | Purpose |
|------|----------|--------------|---------|
| node01 | 192.168.20.20 | 100.89.33.5 | VM Host |
| node02 | 192.168.20.21 | 100.96.195.27 | LXC/Service Host |
| node03 | 192.168.20.22 | 100.76.81.39 | Kubernetes |

### Remote Access (Tailscale)

When outside the local network:
```bash
ssh root@100.89.33.5         # node01
ssh root@100.96.195.27       # node02
ssh root@100.76.81.39        # node03
```

### Networks

| VLAN | Network | Purpose |
|------|---------|---------|
| VLAN 20 | 192.168.20.0/24 | Infrastructure (K8s, Ansible) |
| VLAN 40 | 192.168.40.0/24 | Services (Docker, Apps) |

### Deployed Infrastructure

**18 VMs Total**: 1 Ansible + 9 Kubernetes + 8 Services

See [docs/INVENTORY.md](./docs/INVENTORY.md) for full details.

---

## Quick Start

```bash
# Deploy Infrastructure
terraform init && terraform plan && terraform apply

# Access Ansible Controller
ssh hermes-admin@192.168.20.30

# SSH Quick Access (from ~/.ssh/config)
ssh node01              # Proxmox node01
ssh ansible             # Ansible controller
ssh docker-utilities    # Docker utilities host
```

---

## Documentation Update Protocol

**When updating documentation, you MUST update ALL locations:**

1. **docs/** - Technical reference
2. **Proxmox-TerraformDeployments.wiki/** - GitHub wiki (beginner-friendly)
3. **Obsidian Vault** - Personal notes (includes credentials)
4. **CHANGELOG.md** - Change history

See `.claude/conventions.md` for full sync guide and document mapping.

### Obsidian Vault Path
```
C:\Users\herms\OneDrive\Obsidian Vault\Hermes's Life Knowledge Base\07 HomeLab Things\Claude Managed Homelab\
```

---

## Protected Configurations

**DO NOT modify without explicit user permission:**

### Glance Dashboard Pages
- Glance Home page layout
- Glance Media page layout
- Glance Compute tab layout

### Grafana Dashboards
- **Container Status History** (`container-status`)
  - Iframe height: 1250px
  - Dashboard JSON: `temp-container-status-fixed.json`
  - Ansible: `ansible-playbooks/monitoring/deploy-container-status-dashboard.yml`

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

Full service list in `.claude/context.md`.

---

## Authentication

| Access | Details |
|--------|---------|
| SSH User | hermes-admin (VMs), root (Proxmox) |
| SSH Key | `~/.ssh/homelab_ed25519` (no passphrase) |
| Proxmox API | terraform-deployment-user@pve!tf |

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
