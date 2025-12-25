# Conventions & Standards

> Patterns, standards, and workflows for this homelab infrastructure.
> Reference this when adding new services or updating documentation.

---

## Adding New VMs

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

See [docs/TERRAFORM.md](../docs/TERRAFORM.md) for complete guide.

---

## Adding New Services Checklist

1. Deploy VM via Terraform
2. Create Ansible playbook in `ansible-playbooks/`
3. Add to Traefik dynamic config (`/opt/traefik/config/dynamic/services.yml`)
4. Update DNS in OPNsense
5. **Add Authentik protection** (if needed):
   - Create Proxy Provider in Authentik Admin
   - Create Application linked to provider
   - **Assign provider to Embedded Outpost** (critical!)
6. **Update Discord Bots**:
   - Add container to `CONTAINER_HOSTS` in Update Manager (`/opt/update-manager/update_manager.py`)
   - Add VM to `VM_MAPPING` in Argus bot (`/opt/sysadmin-bot/sysadmin-bot.py`)
   - Configure webhooks to Download Monitor (for media services)
7. **Update Documentation**: All three locations (docs/, wiki, Obsidian)

---

## Troubleshooting Documentation Format

When adding issues to [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md):

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

**Categories**:
- Proxmox Cluster Issues
- Kubernetes Issues
- Authentication Issues
- Container & Docker Issues
- Service-Specific Issues
- Dashboard Issues
- Network Issues
- Common Issues

---

## Documentation Sync Guide

Documentation is maintained in **three locations**:

| Location | Purpose | Format |
|----------|---------|--------|
| `docs/` | Git-tracked technical reference | Concise, technical |
| `Proxmox-TerraformDeployments.wiki/` | GitHub wiki (public) | Beginner-friendly |
| `~/OneDrive/Obsidian Vault/.../Claude Managed Homelab/` | Personal vault | Internal, credentials |

### Obsidian Vault Path

```
C:\Users\herms\OneDrive\Obsidian Vault\Hermes's Life Knowledge Base\07 HomeLab Things\Claude Managed Homelab\
```

### Document Mapping

| docs/ File | Wiki Page | Obsidian File |
|------------|-----------|---------------|
| NETWORKING.md | Network-Architecture.md | 01 - Network Architecture.md |
| PROXMOX.md | Proxmox-Cluster.md | 02 - Proxmox Cluster.md |
| STORAGE.md | Storage-Architecture.md | 03 - Storage Architecture.md |
| TERRAFORM.md | Terraform-Basics.md | 05 - Terraform Configuration.md |
| SERVICES.md | Services-Overview.md | 07 - Deployed Services.md |
| APPLICATION_CONFIGURATIONS.md | Application-Configurations.md | 21 - Application Configurations.md |
| ANSIBLE.md | Ansible-Basics.md | 06 - Ansible Automation.md |
| OBSERVABILITY.md | Observability.md | 18 - Observability Stack.md |
| WATCHTOWER.md | Watchtower.md | 19 - Watchtower Updates.md |
| CICD.md | GitLab-CICD.md | 20 - GitLab CI-CD Automation.md |
| SERVICE_ONBOARDING.md | Service-Onboarding.md | 22 - Service Onboarding Workflow.md |
| TROUBLESHOOTING.md | Troubleshooting.md | 12 - Troubleshooting.md |

### Documentation Content Requirements

Each update MUST include:
1. **Code Configuration** - All code with inline comments
2. **Architecture Diagrams** - ASCII diagrams showing relationships
3. **Decision Explanations** - Why certain approaches were chosen
4. **Troubleshooting Steps** - Common issues and fixes
5. **Health Check Endpoints** - URLs and expected responses
6. **Deployment Commands** - Copy-paste ready
7. **File Locations** - Where configs are stored

### Push Wiki Changes

```bash
cd Proxmox-TerraformDeployments.wiki
git add .
git commit -m "Sync: description of changes"
git push
```

Obsidian syncs automatically via OneDrive.

---

## Repository Structure

```
tf-proxmox/
├── main.tf                 # VM definitions
├── lxc.tf                  # LXC container definitions
├── variables.tf            # Global variables
├── outputs.tf              # Output definitions
├── claude.md               # Quick reference + handoff protocol
├── CHANGELOG.md            # Change history
├── .claude/                # Multi-session context
│   ├── context.md          # Infrastructure reference
│   ├── active-tasks.md     # Work in progress
│   ├── session-log.md      # Session history
│   └── conventions.md      # This file
├── modules/
│   ├── linux-vm/           # VM module
│   └── lxc/                # LXC module
├── ansible-playbooks/      # Ansible playbooks
├── docs/                   # Modular documentation
└── Proxmox-TerraformDeployments.wiki/  # GitHub wiki
```

---

## Glance Dashboard Configuration

### Protected Pages (DO NOT MODIFY)

- **Home** - Service monitors, bookmarks, markets
- **Compute** - Proxmox cluster + Container monitoring
- **Media** - Media stats, downloads, queue

### Configuration Scripts

| Script | Purpose |
|--------|---------|
| `temp-home-fix.py` | Home page updates |
| `temp-media-page-update.py` | Media page updates |
| `temp-media-api-update.py` | Media Stats API |
| `temp-glance-update.py` | Full dashboard update |

### Media Stats API Endpoints

| Endpoint | Port | Description |
|----------|------|-------------|
| `/api/stats` | 5054 | Stats for 6-tile grid |
| `/api/recent` | 5054 | Top 5 recent downloads |
| `/api/queue` | 5054 | Active downloads (max 10) |
| `/health` | 5054 | Health check |

---

## Prometheus Exporters

| Exporter | Port | Target | Status |
|----------|------|--------|--------|
| OPNsense Exporter | 9198 | 192.168.91.30 | Active |
| Omada Exporter | 9202 | 192.168.0.103 | Pending |
| Docker Exporter | 9417 | docker hosts | Active |

---

## Security Practices

- **API Tokens**: Stored in `terraform.tfvars` (gitignored)
- **SSH**: Public key only, password auth disabled
- **LXC**: Unprivileged by default
- **Network**: VLAN segmentation
- **Credentials**: Only in Obsidian `11 - Credentials.md` (private)
