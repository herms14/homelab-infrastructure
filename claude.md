# Proxmox Terraform Infrastructure

Terraform infrastructure-as-code for deploying VMs and LXC containers on a Proxmox VE 9.1.2 cluster. Designed for a homelab environment with Kubernetes, Docker services, and supporting infrastructure.

## Quick Reference

| Resource | Documentation |
|----------|---------------|
| **Network** | [docs/NETWORKING.md](./docs/NETWORKING.md) - VLANs, IPs, DNS, SSL |
| **Compute** | [docs/PROXMOX.md](./docs/PROXMOX.md) - Cluster nodes, VM/LXC standards |
| **Storage** | [docs/STORAGE.md](./docs/STORAGE.md) - NFS, Synology, storage pools |
| **Terraform** | [docs/TERRAFORM.md](./docs/TERRAFORM.md) - Modules, deployment |
| **Services** | [docs/SERVICES.md](./docs/SERVICES.md) - Docker services |
| **App Config** | [docs/APPLICATION_CONFIGURATIONS.md](./docs/APPLICATION_CONFIGURATIONS.md) - Detailed app setup |
| **Ansible** | [docs/ANSIBLE.md](./docs/ANSIBLE.md) - Automation, playbooks |
| **Inventory** | [docs/INVENTORY.md](./docs/INVENTORY.md) - Deployed infrastructure |
| **Observability** | [docs/OBSERVABILITY.md](./docs/OBSERVABILITY.md) - Tracing, metrics |
| **Watchtower** | [docs/WATCHTOWER.md](./docs/WATCHTOWER.md) - Interactive container updates |
| **CI/CD** | [docs/CICD.md](./docs/CICD.md) - Automated service onboarding |
| **Service Onboarding** | [docs/SERVICE_ONBOARDING.md](./docs/SERVICE_ONBOARDING.md) - Automated status checker |
| **Troubleshooting** | [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md) - Common issues |

## Infrastructure Overview

### Proxmox Cluster

| Node | IP | Purpose |
|------|----|---------|
| node01 | 192.168.20.20 | VM Host |
| node02 | 192.168.20.21 | LXC/Service Host |
| node03 | 192.168.20.22 | Kubernetes |

### Networks

| VLAN | Network | Purpose |
|------|---------|---------|
| VLAN 20 | 192.168.20.0/24 | Infrastructure (K8s, Ansible) |
| VLAN 40 | 192.168.40.0/24 | Services (Docker, Apps) |

### Deployed Infrastructure

**18 VMs Total**: 1 Ansible + 9 Kubernetes + 8 Services

| Category | Hosts | Details |
|----------|-------|---------|
| Kubernetes | 9 VMs | 3 controllers + 6 workers (v1.28.15) |
| Services | 8 VMs | Traefik, Authentik, Immich, GitLab, GitLab Runner, Arr Stack, n8n |
| Ansible | 1 VM | Configuration management controller |

See [docs/INVENTORY.md](./docs/INVENTORY.md) for full details.

## Quick Start

### Deploy Infrastructure

```bash
terraform init
terraform plan
terraform apply
```

### Access Ansible Controller

```bash
ssh hermes-admin@192.168.20.30
cd ~/ansible
```

### Common Operations

```bash
# Deploy VMs only
terraform apply -target=module.vms

# Check Ansible connectivity
ansible all -m ping

# Deploy Kubernetes
ansible-playbook k8s/k8s-deploy-all.yml
```

See [docs/TERRAFORM.md](./docs/TERRAFORM.md) for more operations.

## Authentication

| Access | Details |
|--------|---------|
| SSH User | hermes-admin (VMs), root (Proxmox) |
| SSH Key | `~/.ssh/homelab_ed25519` (no passphrase) |
| SSH Config | `~/.ssh/config` with host aliases |
| Proxmox API | terraform-deployment-user@pve!tf |

### SSH Quick Access

```bash
# Using host aliases (from ~/.ssh/config)
ssh node01              # Proxmox node01 as root
ssh ansible             # Ansible controller
ssh k8s-controller01    # K8s primary controller
ssh docker-utilities    # Docker utilities host

# Direct IP access (auto-selects key)
ssh root@192.168.20.20
ssh hermes-admin@192.168.20.30
```

## Service URLs

| Service | URL |
|---------|-----|
| Proxmox | https://proxmox.hrmsmrflrii.xyz |
| Traefik | https://traefik.hrmsmrflrii.xyz |
| Authentik | https://auth.hrmsmrflrii.xyz |
| Immich | https://photos.hrmsmrflrii.xyz |
| GitLab | https://gitlab.hrmsmrflrii.xyz |
| Jellyfin | https://jellyfin.hrmsmrflrii.xyz |
| Deluge | https://deluge.hrmsmrflrii.xyz |
| SABnzbd | https://sabnzbd.hrmsmrflrii.xyz |
| n8n | https://n8n.hrmsmrflrii.xyz |
| **Monitoring** | |
| Uptime Kuma | https://uptime.hrmsmrflrii.xyz |
| Prometheus | https://prometheus.hrmsmrflrii.xyz |
| Grafana | https://grafana.hrmsmrflrii.xyz |
| **Observability** | |
| Jaeger | https://jaeger.hrmsmrflrii.xyz |
| Demo App | https://demo.hrmsmrflrii.xyz |

See [docs/NETWORKING.md](./docs/NETWORKING.md) for complete URL list.

## Repository Structure

```
tf-proxmox/
├── main.tf                 # VM definitions
├── lxc.tf                  # LXC container definitions
├── variables.tf            # Global variables
├── outputs.tf              # Output definitions
├── modules/
│   ├── linux-vm/           # VM module
│   └── lxc/                # LXC module
├── ansible-playbooks/      # Ansible playbooks
├── docs/                   # Modular documentation
│   ├── NETWORKING.md       # Network configuration
│   ├── PROXMOX.md          # Cluster & VM standards
│   ├── STORAGE.md          # Storage configuration
│   ├── TERRAFORM.md        # IaC deployment
│   ├── SERVICES.md         # Docker services
│   ├── APPLICATION_CONFIGURATIONS.md  # Detailed app setup guides
│   ├── ANSIBLE.md          # Automation
│   ├── INVENTORY.md        # Deployed resources
│   ├── OBSERVABILITY.md    # Tracing & metrics
│   ├── WATCHTOWER.md       # Container updates
│   ├── CICD.md             # GitLab CI/CD automation
│   ├── TROUBLESHOOTING.md  # Issue resolution
│   └── legacy/             # Extended documentation
├── Proxmox-TerraformDeployments.wiki/  # GitHub wiki (synced)
└── CLAUDE.md               # This file
```

## Troubleshooting Documentation Format

Troubleshooting docs are organized by category in [docs/TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md):

- **Proxmox Cluster Issues** - Corosync, node health, boot failures
- **Kubernetes Issues** - kubectl, kubeconfig, cluster problems
- **Authentication Issues** - Authentik, ForwardAuth, SSO
- **Container & Docker Issues** - Watchtower, build cache, SSH keys
- **Service-Specific Issues** - GitLab, individual service problems
- **Network Issues** - VLAN, NFS, connectivity
- **Common Issues** - Terraform, templates, general errors
- **Diagnostic Commands** - Quick reference commands

When adding new issues, use this format:

```markdown
### Issue Title

**Resolved**: Month Day, Year

**Symptoms**: What the user sees (error messages, behavior)

**Root Cause**: Why it happened

**Fix**:
```bash
# Commands to resolve
```

**Verification**: How to confirm it's fixed

**Prevention**: How to avoid in the future (optional)
```

## Key Configuration

### Adding New VMs

Edit `main.tf`, add to `vm_groups`:

```hcl
new-service = {
  count       = 1
  starting_ip = "192.168.40.50"
  template    = "tpl-ubuntu-shared-v1"
  cores       = 4
  memory      = 8192
  disk_size   = "20G"
  storage     = "VMDisks"
  vlan_tag    = 40              # null for VLAN 20
  gateway     = "192.168.40.1"
  nameserver  = "192.168.91.30"
}
```

See [docs/TERRAFORM.md](./docs/TERRAFORM.md) for complete guide.

### Adding New Services

1. Deploy VM via Terraform
2. Create Ansible playbook in `ansible-playbooks/`
3. Add to Traefik dynamic config (`/opt/traefik/config/dynamic/services.yml`)
4. Update DNS in OPNsense
5. **Add Authentik protection** (if needed):
   - Create Proxy Provider in Authentik Admin
   - Create Application linked to provider
   - **Assign provider to Embedded Outpost** (critical!)
6. **Update Discord Bot**: Add container to `CONTAINER_HOSTS` mapping in Update Manager
7. **Update Documentation**: All three locations (docs/, wiki, Obsidian)

See [docs/SERVICES.md](./docs/SERVICES.md) and [docs/ANSIBLE.md](./docs/ANSIBLE.md).

## Documentation Sync Guide

Documentation is maintained in **three locations** that must stay synchronized:

| Location | Purpose | Format |
|----------|---------|--------|
| `docs/` | Git-tracked technical reference | Concise, technical |
| `Proxmox-TerraformDeployments.wiki/` | GitHub wiki (public) | Beginner-friendly, detailed |
| `~/OneDrive/Obsidian Vault/.../Claude Managed Homelab/` | Personal Obsidian vault | Internal, includes credentials |

### Obsidian Vault Path

```
C:\Users\herms\OneDrive\Obsidian Vault\Hermes's Life Knowledge Base\07 HomeLab Things\Claude Managed Homelab\
```

### Document Mapping (All Three Locations)

| docs/ File | Wiki Page | Obsidian File |
|------------|-----------|---------------|
| NETWORKING.md | Network-Architecture.md | 01 - Network Architecture.md |
| PROXMOX.md | Proxmox-Cluster.md | 02 - Proxmox Cluster.md |
| STORAGE.md | Storage-Architecture.md | 03 - Storage Architecture.md |
| TERRAFORM.md | Terraform-Basics.md | 05 - Terraform Configuration.md |
| SERVICES.md | Services-Overview.md | 07 - Deployed Services.md |
| APPLICATION_CONFIGURATIONS.md | Application-Configurations.md | 21 - Application Configurations.md |
| ANSIBLE.md | Ansible-Basics.md | 06 - Ansible Automation.md |
| INVENTORY.md | Inventory-Management.md | (embedded in Index) |
| OBSERVABILITY.md | Observability.md | 18 - Observability Stack.md |
| WATCHTOWER.md | Watchtower.md | 19 - Watchtower Updates.md |
| CICD.md | GitLab-CICD.md | 20 - GitLab CI-CD Automation.md |
| TROUBLESHOOTING.md | Troubleshooting.md | 12 - Troubleshooting.md |
| - | - | 11 - Credentials.md (private) |

### Sync Requirements

When updating documentation:

1. **Update both locations** - Changes to `docs/` must be reflected in wiki and vice versa
2. **Maintain consistency** - Same facts, commands, and configurations in both
3. **Preserve format differences** - Wiki is more detailed/beginner-friendly, docs are concise
4. **Update cross-references** - Links in Related Documentation sections
5. **Update sidebar** - Wiki `_Sidebar.md` for new pages

### Sync Checklist for New Features

When adding a new feature or service, update ALL THREE locations:

```markdown
## Infrastructure
- [ ] Add Traefik route to /opt/traefik/config/dynamic/services.yml
- [ ] Add DNS entry in OPNsense
- [ ] Create Authentik provider + application (if SSO protected)
- [ ] Assign provider to Embedded Outpost (critical!)

## docs/ (Git-tracked)
- [ ] Update relevant docs/*.md file
- [ ] Add to CLAUDE.md Quick Reference (if major feature)

## GitHub Wiki
- [ ] Update corresponding wiki page
- [ ] Update wiki _Sidebar.md (if new page)
- [ ] Update wiki Home.md quick reference table

## Obsidian Vault (Personal)
- [ ] Update corresponding Obsidian file
- [ ] Update 00 - Homelab Index.md with new link
- [ ] Update 07 - Deployed Services.md service tables
- [ ] Add credentials to 11 - Credentials.md (if any)

## All Locations
- [ ] Add troubleshooting entries to all three locations
- [ ] Verify cross-references are consistent
```

### Push Wiki Changes

```bash
cd Proxmox-TerraformDeployments.wiki
git add .
git commit -m "Sync: description of changes"
git push
```

### Obsidian Sync

Obsidian vault syncs automatically via OneDrive. No manual push needed.

## Security

- **API Tokens**: Stored in `terraform.tfvars` (gitignored)
- **SSH**: Public key only, password auth disabled
- **LXC**: Unprivileged by default
- **Network**: VLAN segmentation

## Notes

- All VMs use Ubuntu 24.04 LTS cloud-init template
- VMs use UEFI boot mode (ovmf)
- LXC containers use Ubuntu 22.04 or Debian 12
- Auto-start enabled on production infrastructure
- Proxmox node02 dedicated to service VMs
