# Provider Setup

> **TL;DR**: Configure the Telmate Proxmox provider with API tokens for secure, automated VM management.

## Proxmox Provider

This project uses the [telmate/proxmox](https://registry.terraform.io/providers/Telmate/proxmox/latest/docs) provider to interact with Proxmox VE.

### Provider Configuration

**File**: `providers.tf`

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    proxmox = {
      source  = "telmate/proxmox"
      version = "3.0.1-rc4"
    }
  }
}

provider "proxmox" {
  pm_api_url          = var.proxmox_api_url
  pm_api_token_id     = var.proxmox_api_token_id
  pm_api_token_secret = var.proxmox_api_token_secret
  pm_tls_insecure     = true
  pm_parallel         = 4
  pm_timeout          = 600
}
```

**Parameter reference**:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `pm_api_url` | Proxmox API endpoint | `https://192.168.20.21:8006/api2/json` |
| `pm_api_token_id` | API token identifier | `root@pam!terraform` |
| `pm_api_token_secret` | API token secret | UUID format |
| `pm_tls_insecure` | Skip TLS verification | `true` for self-signed certs |
| `pm_parallel` | Max concurrent operations | `4` |
| `pm_timeout` | Operation timeout (seconds) | `600` |

---

## API Token Creation

### Via Proxmox Web UI

1. **Navigate to**: Datacenter → Permissions → API Tokens
2. **Click**: Add
3. **Configure**:
   - **User**: `root@pam` (or dedicated user)
   - **Token ID**: `terraform`
   - **Privilege Separation**: Unchecked (for full access)
4. **Click**: Add
5. **Copy the token secret** (displayed only once)

[Screenshot: API token creation dialog]

**Token format**:
```
Token ID: root@pam!terraform
Secret: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### Via CLI

```bash
# SSH to any Proxmox node
ssh root@192.168.20.21

# Create API token
pveum user token add root@pam terraform --privsep=0

# Output:
┌──────────────┬──────────────────────────────────────┐
│ key          │ value                                │
╞══════════════╪══════════════════════════════════════╡
│ full-tokenid │ root@pam!terraform                   │
├──────────────┼──────────────────────────────────────┤
│ info         │ {"privsep":"0"}                      │
├──────────────┼──────────────────────────────────────┤
│ value        │ xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx │
└──────────────┴──────────────────────────────────────┘
```

**Parameter reference**:
- `root@pam`: User to create token for
- `terraform`: Token ID (name)
- `--privsep=0`: Disable privilege separation (token inherits user permissions)

---

## Variable Configuration

### Variable Declarations

**File**: `variables.tf`

```hcl
# Proxmox Connection
variable "proxmox_api_url" {
  type        = string
  description = "Proxmox API URL (https://host:8006/api2/json)"
}

variable "proxmox_api_token_id" {
  type        = string
  description = "Proxmox API token ID (user@realm!tokenid)"
}

variable "proxmox_api_token_secret" {
  type        = string
  description = "Proxmox API token secret"
  sensitive   = true
}

# SSH Configuration
variable "ssh_public_key" {
  type        = string
  description = "SSH public key for VM access"
}

# Network Defaults
variable "gateway" {
  type        = string
  default     = "192.168.20.1"
  description = "Default gateway for VMs"
}

variable "nameserver" {
  type        = string
  default     = "192.168.91.30"
  description = "DNS server for VMs"
}
```

### Variable Values

**File**: `terraform.tfvars` (gitignored)

```hcl
# Proxmox Connection
proxmox_api_url          = "https://192.168.20.21:8006/api2/json"
proxmox_api_token_id     = "root@pam!terraform"
proxmox_api_token_secret = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# SSH Key
ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAby7br+5MzyDus2fi2UFjUBZvGucN40Gxa29bgUTbfz hermes@homelab"

# Network
gateway    = "192.168.20.1"
nameserver = "192.168.91.30"
```

### Environment Variables (Alternative)

Set credentials via environment variables instead of tfvars:

```bash
export TF_VAR_proxmox_api_url="https://192.168.20.21:8006/api2/json"
export TF_VAR_proxmox_api_token_id="root@pam!terraform"
export TF_VAR_proxmox_api_token_secret="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

---

## Dedicated API User (Recommended)

For production, create a dedicated user instead of using root.

### Create User

```bash
# Create user
pveum user add terraform-user@pve

# Create role with required permissions
pveum role add TerraformRole -privs \
  "VM.Allocate,VM.Clone,VM.Config.CDROM,VM.Config.CPU,VM.Config.Cloudinit,\
VM.Config.Disk,VM.Config.HWType,VM.Config.Memory,VM.Config.Network,\
VM.Config.Options,VM.Monitor,VM.Audit,VM.PowerMgmt,\
Datastore.AllocateSpace,Datastore.Audit,\
SDN.Use"

# Assign role to user for specific resources
pveum aclmod / -user terraform-user@pve -role TerraformRole

# Create API token for user
pveum user token add terraform-user@pve terraform --privsep=0
```

**Permission reference**:

| Permission | Purpose |
|------------|---------|
| `VM.Allocate` | Create and delete VMs |
| `VM.Clone` | Clone templates |
| `VM.Config.*` | Modify VM configuration |
| `VM.PowerMgmt` | Start/stop VMs |
| `VM.Audit` | View VM details |
| `Datastore.AllocateSpace` | Create disks on storage |
| `Datastore.Audit` | View storage |
| `SDN.Use` | Use network bridges |

### Scoped Permissions

Limit permissions to specific nodes/storage:

```bash
# Permission only on node01
pveum aclmod /nodes/node01 -user terraform-user@pve -role TerraformRole

# Permission only on VMDisks storage
pveum aclmod /storage/VMDisks -user terraform-user@pve -role TerraformRole
```

---

## Provider Version Considerations

### Version Selection

| Proxmox VE Version | Recommended Provider Version |
|--------------------|------------------------------|
| 8.x | 3.0.1-rc1+ |
| 7.x | 2.9.x |

### Using RC Versions

The RC (Release Candidate) versions include Proxmox 8+ compatibility:

```hcl
required_providers {
  proxmox = {
    source  = "telmate/proxmox"
    version = "3.0.1-rc4"  # RC version for Proxmox 9.x
  }
}
```

### Provider Features by Version

| Feature | Min Version |
|---------|-------------|
| Cloud-init support | 2.6.0+ |
| EFI disk support | 2.9.0+ |
| Proxmox 8 support | 3.0.1-rc1+ |
| UEFI/OVMF improvements | 3.0.1-rc3+ |

---

## Connection Testing

### Verify API Access

```bash
# Using curl to test API connectivity
curl -k -s -X GET \
  -H "Authorization: PVEAPIToken=root@pam!terraform=YOUR_SECRET" \
  "https://192.168.20.21:8006/api2/json/version"
```

**Expected output**:
```json
{
  "data": {
    "version": "9.1.2",
    "release": "9.1",
    "repoid": "..."
  }
}
```

### Terraform Provider Test

Create minimal test configuration:

```hcl
# test.tf
terraform {
  required_providers {
    proxmox = {
      source  = "telmate/proxmox"
      version = "3.0.1-rc4"
    }
  }
}

provider "proxmox" {
  pm_api_url          = "https://192.168.20.21:8006/api2/json"
  pm_api_token_id     = "root@pam!terraform"
  pm_api_token_secret = "YOUR_SECRET"
  pm_tls_insecure     = true
}

data "proxmox_virtual_environment_nodes" "nodes" {}

output "nodes" {
  value = data.proxmox_virtual_environment_nodes.nodes
}
```

```bash
terraform init
terraform plan
```

---

## TLS Configuration

### Self-Signed Certificates (Default)

Proxmox uses self-signed certificates by default. Disable verification:

```hcl
provider "proxmox" {
  pm_tls_insecure = true
  # ...
}
```

### Custom CA Certificate

If using custom CA:

```hcl
provider "proxmox" {
  pm_tls_insecure = false
  # Provider uses system CA store
  # Add your CA to /etc/ssl/certs/
}
```

### Using Let's Encrypt on Proxmox

Configure Proxmox to use Let's Encrypt:

1. **Node → Certificates → ACME**
2. Configure ACME account
3. Add certificate for node hostname

Then disable insecure mode:
```hcl
provider "proxmox" {
  pm_tls_insecure = false
}
```

---

## Parallel Operations

### Configuring Parallelism

```hcl
provider "proxmox" {
  pm_parallel = 4   # Max concurrent API operations
  pm_timeout  = 600 # Operation timeout in seconds
}
```

**Guidance**:
- `pm_parallel`: Start with 4, increase if cluster handles load well
- `pm_timeout`: Increase for slow storage or large VM clones

### Terraform Parallelism

```bash
# Limit concurrent resource operations
terraform apply -parallelism=2
```

---

## Troubleshooting

### Authentication Errors

**Error**: `401 Unauthorized`

**Causes**:
- Wrong token ID format (should be `user@realm!tokenid`)
- Wrong secret
- Token expired or deleted

**Diagnosis**:
```bash
# Test with curl
curl -k -v -X GET \
  -H "Authorization: PVEAPIToken=root@pam!terraform=SECRET" \
  "https://192.168.20.21:8006/api2/json/version"
```

### Permission Errors

**Error**: `403 permission denied`

**Causes**:
- User lacks required permissions
- Token has privilege separation enabled

**Fix**:
```bash
# Check user permissions
pveum user permissions terraform-user@pve

# Verify token privilege separation
pveum user token list root@pam
```

### Connection Errors

**Error**: `connection refused` or timeout

**Causes**:
- Wrong API URL
- Firewall blocking port 8006
- Proxmox API not running

**Diagnosis**:
```bash
# Test connectivity
nc -zv 192.168.20.21 8006

# Check Proxmox API status
ssh root@192.168.20.21 "systemctl status pveproxy"
```

### Certificate Errors

**Error**: `x509: certificate signed by unknown authority`

**Fix**: Enable `pm_tls_insecure = true` or configure custom CA

---

## Security Best Practices

### Token Management

- Create dedicated user for Terraform (not root)
- Use minimal required permissions
- Rotate tokens periodically
- Never commit tokens to version control

### Network Security

- Limit API access to management network
- Use VPN for remote Terraform operations
- Consider API rate limiting

### State Security

- State file contains token (encrypted)
- Use remote backend with encryption
- Restrict state file access

---

## What's Next?

- **[VM Deployment](VM-Deployment)** - Create VMs with Terraform
- **[Cloud-Init Templates](Cloud-Init-Templates)** - Prepare VM templates
- **[LXC Containers](LXC-Containers)** - Deploy containers

---

*Secure API access is the foundation of infrastructure automation.*
