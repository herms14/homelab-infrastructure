# Terraform Basics

> **TL;DR**: Terraform defines infrastructure as code. Write HCL files describing desired state, run `terraform apply`, and Terraform creates/modifies resources to match.

## What is Terraform?

Terraform is an Infrastructure as Code (IaC) tool that allows you to define, provision, and manage infrastructure using declarative configuration files.

### Declarative vs Imperative

| Approach | Description | Example |
|----------|-------------|---------|
| **Imperative** | Describe steps to execute | "Create VM, set name, add disk, configure network..." |
| **Declarative** | Describe desired end state | "I want a VM named X with these specs" |

Terraform is declarative - you describe what you want, and Terraform figures out how to achieve it.

### State Management

Terraform maintains a **state file** (`terraform.tfstate`) that maps your configuration to real resources:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   main.tf       │     │  terraform.     │     │    Proxmox      │
│   (Desired)     │────▶│  tfstate        │────▶│    (Actual)     │
│                 │     │  (Mapping)      │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Project Structure

```
tf-proxmox/
├── main.tf              # VM definitions and orchestration
├── lxc.tf               # LXC container definitions
├── variables.tf         # Variable declarations
├── outputs.tf           # Output definitions
├── providers.tf         # Provider configuration
├── terraform.tfvars     # Variable values (gitignored)
├── terraform.tfstate    # State file (auto-generated)
├── modules/
│   ├── linux-vm/       # VM deployment module
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── lxc/            # LXC deployment module
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── .terraform/          # Provider plugins (auto-generated)
```

### File Purposes

| File | Purpose |
|------|---------|
| `main.tf` | Resource definitions (VMs, modules) |
| `variables.tf` | Input variable declarations with types and defaults |
| `outputs.tf` | Values to display after apply |
| `providers.tf` | Provider versions and configuration |
| `terraform.tfvars` | Actual variable values (secrets, credentials) |

---

## Core Concepts

### Providers

Providers are plugins that interface with APIs. We use the Proxmox provider:

**providers.tf**:
```hcl
terraform {
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
  pm_tls_insecure     = true  # Self-signed cert
}
```

### Resources

Resources are the infrastructure objects Terraform manages:

```hcl
resource "proxmox_vm_qemu" "example" {
  name        = "example-vm"
  target_node = "node01"
  clone       = "ubuntu-template"

  cores  = 4
  memory = 8192

  disk {
    storage = "VMDisks"
    size    = "20G"
  }
}
```

**Resource syntax**: `resource "<type>" "<name>" { ... }`
- `type`: Resource type from provider (e.g., `proxmox_vm_qemu`)
- `name`: Local identifier used in Terraform
- `{ ... }`: Configuration block

### Variables

Variables parameterize configuration:

**variables.tf**:
```hcl
variable "proxmox_api_url" {
  type        = string
  description = "Proxmox API URL"
}

variable "vm_cores" {
  type        = number
  default     = 4
  description = "Number of CPU cores per VM"
}

variable "ssh_keys" {
  type        = list(string)
  description = "SSH public keys to add to VMs"
}
```

**terraform.tfvars**:
```hcl
proxmox_api_url = "https://192.168.20.21:8006/api2/json"
vm_cores        = 2
ssh_keys        = ["ssh-ed25519 AAAA... user@host"]
```

### Outputs

Outputs display values after apply:

**outputs.tf**:
```hcl
output "vm_ips" {
  value = {
    for k, v in module.vms : k => v.ip_address
  }
  description = "IP addresses of all VMs"
}
```

### Modules

Modules encapsulate reusable configuration:

```hcl
module "vms" {
  source   = "./modules/linux-vm"
  for_each = local.vm_groups

  hostname    = each.key
  ip_address  = each.value.starting_ip
  target_node = each.value.starting_node
  # ... more variables
}
```

---

## Essential Commands

### Initialize Project

```bash
terraform init
```

**What it does**:
- Downloads provider plugins to `.terraform/`
- Initializes backend (state storage)
- Validates configuration syntax

**When to run**: First time, after adding providers, after changing backend

### Preview Changes

```bash
terraform plan
```

**What it does**:
- Compares desired state (config) to actual state
- Shows what will be created, modified, or destroyed
- Does NOT make any changes

**Output explanation**:
```
+ create    # New resource will be created
~ update    # Existing resource will be modified
- destroy   # Resource will be deleted
-/+ replace # Resource will be destroyed and recreated
```

### Apply Changes

```bash
terraform apply
```

**What it does**:
- Shows plan
- Prompts for confirmation
- Creates/modifies/destroys resources
- Updates state file

**Skip confirmation**:
```bash
terraform apply -auto-approve
```

### Destroy Resources

```bash
terraform destroy
```

**What it does**:
- Shows resources to be destroyed
- Prompts for confirmation
- Removes all managed resources

**Target specific resource**:
```bash
terraform destroy -target=module.vms["docker-hosts"]
```

### View State

```bash
# List all resources in state
terraform state list

# Show specific resource details
terraform state show module.vms["ansible-controller"].proxmox_vm_qemu.linux_vm

# Remove resource from state (doesn't delete actual resource)
terraform state rm <resource_address>
```

### Refresh State

```bash
terraform refresh
```

**What it does**: Updates state file to match actual infrastructure (useful if resources were modified outside Terraform)

### Format Code

```bash
terraform fmt
```

**What it does**: Reformats `.tf` files to canonical style

### Validate Configuration

```bash
terraform validate
```

**What it does**: Checks syntax and internal consistency without accessing providers

---

## HCL Syntax Reference

### Basic Types

```hcl
# String
name = "example"

# Number
cores = 4

# Boolean
enabled = true

# List
tags = ["web", "production"]

# Map
labels = {
  environment = "prod"
  team        = "infra"
}
```

### String Interpolation

```hcl
# Variable reference
name = var.hostname

# Interpolation in string
description = "VM ${var.hostname} on ${var.node}"

# Function call
lower_name = lower(var.hostname)
```

### Conditional Expression

```hcl
# condition ? true_value : false_value
vlan_tag = var.vlan == "40" ? 40 : null
```

### For Expressions

```hcl
# List comprehension
names = [for vm in var.vms : vm.name]

# Map comprehension
ips = {for k, v in var.vms : k => v.ip}

# With condition
prod_vms = [for vm in var.vms : vm.name if vm.env == "prod"]
```

### Dynamic Blocks

```hcl
resource "proxmox_vm_qemu" "vm" {
  # ...

  dynamic "disk" {
    for_each = var.additional_disks
    content {
      storage = disk.value.storage
      size    = disk.value.size
    }
  }
}
```

### Local Values

```hcl
locals {
  common_tags = {
    project = "homelab"
    managed = "terraform"
  }

  vm_groups = {
    k8s-workers = {
      count       = 6
      starting_ip = "192.168.20.40"
    }
  }
}
```

---

## Working with Modules

### Module Structure

```
modules/linux-vm/
├── main.tf          # Resource definitions
├── variables.tf     # Input variables
└── outputs.tf       # Output values
```

### Calling a Module

```hcl
module "web_servers" {
  source = "./modules/linux-vm"

  # Pass variables
  hostname    = "web-01"
  ip_address  = "192.168.40.50"
  target_node = "node02"

  # Pass through common variables
  ssh_key    = var.ssh_public_key
  nameserver = var.nameserver
}
```

### Module Outputs

Access module outputs:
```hcl
# Single module
output "web_ip" {
  value = module.web_servers.ip_address
}

# Multiple modules (for_each)
output "all_ips" {
  value = {
    for k, v in module.vms : k => v.ip_address
  }
}
```

---

## State Management

### State File Location

Default: `terraform.tfstate` in project directory

**Never commit state to git** - contains secrets and sensitive data

### State Locking

Terraform locks state during operations to prevent conflicts:

```
Error: Error acquiring the state lock
```

**Force unlock** (use carefully):
```bash
terraform force-unlock <lock_id>
```

### Importing Existing Resources

Import resources created outside Terraform:

```bash
# Syntax: terraform import <resource_address> <resource_id>
terraform import proxmox_vm_qemu.existing_vm node01/qemu/100
```

Then add corresponding configuration in `.tf` files.

---

## Targeting Specific Resources

### Apply to Specific Target

```bash
# Single resource
terraform apply -target=module.vms["ansible-controller"]

# Multiple targets
terraform apply -target=module.vms["k8s-controller01"] \
                -target=module.vms["k8s-controller02"]
```

### Plan for Specific Target

```bash
terraform plan -target=module.vms["docker-hosts"]
```

---

## Debugging

### Enable Verbose Logging

```bash
# Debug level
export TF_LOG=DEBUG
terraform apply

# Trace level (most verbose)
export TF_LOG=TRACE
terraform apply

# Disable
unset TF_LOG
```

### Log to File

```bash
export TF_LOG=DEBUG
export TF_LOG_PATH=./terraform.log
terraform apply
```

### Common Errors

**Provider not found**:
```
Error: Failed to query available provider packages
```
Fix: Run `terraform init`

**State lock**:
```
Error: Error acquiring the state lock
```
Fix: Wait for other operation or `terraform force-unlock`

**Resource already exists**:
```
Error: A resource with the ID "..." already exists
```
Fix: Import existing resource or manually remove

---

## Best Practices

### File Organization

- One resource type per file for large projects
- Use modules for reusable components
- Keep `terraform.tfvars` out of version control

### Variable Management

- Define all variables in `variables.tf`
- Use `terraform.tfvars` for environment-specific values
- Use environment variables for CI/CD: `TF_VAR_<name>`

### State Management

- Use remote backend for team environments
- Never edit state manually
- Backup state before major operations

### Code Style

- Run `terraform fmt` before committing
- Use meaningful resource names
- Add descriptions to variables and outputs

---

## What's Next?

- **[Provider Setup](Provider-Setup)** - Configure Proxmox provider
- **[VM Deployment](VM-Deployment)** - Create VMs with Terraform
- **[Cloud-Init Templates](Cloud-Init-Templates)** - Template creation

---

*Infrastructure as Code: reproducible, version-controlled, and self-documenting.*
