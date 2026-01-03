# Azure Hybrid Lab

Enterprise-grade hybrid infrastructure spanning on-prem Hyper-V and Azure, using Packer + Terraform + Ansible.

## Project Status: Gathering Inputs

**Current Phase**: Waiting for required inputs before implementation

See [docs/REQUIRED_INPUTS.md](docs/REQUIRED_INPUTS.md) for the input checklist.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                              ON-PREMISES (Hyper-V)                              │
│                              VLAN 20 - 192.168.20.0/24                          │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │    DC01     │  │    DC02     │  │   FS01      │  │   FS02      │            │
│  │ (Primary)   │  │ (Secondary) │  │ File Server │  │ File Server │            │
│  │ Win 2025   │  │ Win 2025   │  │ Win 2025   │  │ Win 2025   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   SQL01     │  │  AADCON01   │  │  AADPP01    │  │  AADPP02    │            │
│  │ SQL Server  │  │ Entra Conn  │  │ Pwd Protect │  │ Pwd Protect │            │
│  │ Win 2025   │  │ Win 2025   │  │ Win 2025   │  │ Win 2025   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  CLIENT01   │  │  CLIENT02   │  │   IIS01     │  │   IIS02     │            │
│  │ Windows 11  │  │ Windows 11  │  │ Web Server  │  │ Web Server  │            │
│  │ (Domain)    │  │ (Domain)    │  │ Win 2025   │  │ Win 2025   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                                 │
│                           ┌─────────────┐                                       │
│                           │   ER605     │                                       │
│                           │ VPN Gateway │                                       │
│                           └──────┬──────┘                                       │
└──────────────────────────────────┼─────────────────────────────────────────────┘
                                   │
                          IPsec S2S VPN
                                   │
┌──────────────────────────────────┼─────────────────────────────────────────────┐
│                           AZURE vWAN HUB                                        │
│                     ┌────────────┴───────────┐                                  │
├─────────────────────┼────────────────────────┼──────────────────────────────────┤
│                     │                        │                                  │
│           ┌─────────▼─────────┐    ┌─────────▼─────────┐                       │
│           │   Southeast Asia   │    │    East Asia       │                       │
│           │   (Singapore)      │    │    (Hong Kong)     │                       │
│           └─────────┬─────────┘    └─────────┬─────────┘                       │
│                     │                        │                                  │
│  ┌──────────────────┼────────────────────────┼─────────────────────────────┐   │
│  │             CONNECTIVITY RG               │                              │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌───────┴───────┐ ┌──────────────┐     │   │
│  │  │ vWAN Hub    │ │ VPN Gateway │ │ Azure Bastion │ │ Private DNS  │     │   │
│  │  └─────────────┘ └─────────────┘ └───────────────┘ └──────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         IDENTITY RG                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │   │
│  │  │  AZDC01-SEA │  │  AZDC02-SEA │  │  AZDC01-EA  │  │  AZDC02-EA  │      │   │
│  │  │  DC (SEA)   │  │  DC (SEA)   │  │  DC (EA)    │  │  DC (EA)    │      │   │
│  │  │  Win 2025   │  │  Win 2025   │  │  Win 2025   │  │  Win 2025   │      │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        MANAGEMENT RG                                      │   │
│  │  ┌─────────────────────────┐  ┌─────────────────────────────────────┐    │   │
│  │  │   Log Analytics         │  │   Azure Policy + Diagnostics        │    │   │
│  │  │   Workspace             │  │   (All resources log here)          │    │   │
│  │  └─────────────────────────┘  └─────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                      APP LANDING ZONE RG                                  │   │
│  │  ┌───────────────────────────────────────────────────────────────────┐   │   │
│  │  │                        AKS CLUSTER                                 │   │   │
│  │  │  ┌─────────────────────────┐  ┌─────────────────────────────────┐ │   │   │
│  │  │  │   System Nodepool       │  │     User Nodepool               │ │   │   │
│  │  │  │   2× nodes              │  │     4× nodes                    │ │   │   │
│  │  │  └─────────────────────────┘  └─────────────────────────────────┘ │   │   │
│  │  └───────────────────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
Azure-Hybrid-Lab/
├── README.md                    # This file
├── packer/                      # Packer templates for Windows images
│   ├── windows-server-2025/
│   └── windows-11/
├── terraform/
│   ├── hyperv/                  # Hyper-V VM provisioning
│   │   ├── modules/
│   │   └── environments/
│   └── azure/                   # Azure Landing Zone
│       ├── modules/
│       └── environments/
├── ansible/
│   ├── inventory/               # Dynamic/static inventory
│   ├── playbooks/               # Configuration playbooks
│   └── roles/                   # Reusable roles
├── scripts/                     # Helper scripts
└── docs/                        # Documentation (Obsidian-compatible)
    ├── REQUIRED_INPUTS.md       # Input checklist
    ├── ARCHITECTURE.md          # Detailed architecture
    ├── IP_ADDRESSING.md         # IP plan
    ├── DEPLOYMENT_RUNBOOK.md    # Step-by-step deployment
    └── TROUBLESHOOTING.md       # Common issues
```

---

## Planned VM Inventory

### On-Premises (Hyper-V) - 14 VMs

| VM Name | Role | OS | IP (TBD) | vCPU | RAM |
|---------|------|----|----|------|-----|
| DC01 | Primary Domain Controller | WS 2025 | 192.168.20.5X | 2 | 4GB |
| DC02 | Secondary Domain Controller | WS 2025 | 192.168.20.5X | 2 | 4GB |
| FS01 | File Server | WS 2025 | 192.168.20.5X | 2 | 4GB |
| FS02 | File Server | WS 2025 | 192.168.20.5X | 2 | 4GB |
| SQL01 | SQL Server | WS 2025 | 192.168.20.5X | 4 | 8GB |
| AADCON01 | Entra ID Connect | WS 2025 | 192.168.20.5X | 2 | 4GB |
| AADPP01 | Password Protection Proxy | WS 2025 | 192.168.20.5X | 2 | 4GB |
| AADPP02 | Password Protection Proxy | WS 2025 | 192.168.20.5X | 2 | 4GB |
| CLIENT01 | Domain Workstation | Win 11 | 192.168.20.5X | 2 | 4GB |
| CLIENT02 | Domain Workstation | Win 11 | 192.168.20.5X | 2 | 4GB |
| IIS01 | Web Server | WS 2025 | 192.168.20.5X | 2 | 4GB |
| IIS02 | Web Server | WS 2025 | 192.168.20.5X | 2 | 4GB |

**Total On-Prem**: 26 vCPU, 52GB RAM

### Azure - 4 DCs + AKS

| VM Name | Role | Region | vCPU | RAM |
|---------|------|--------|------|-----|
| AZDC01-SEA | Domain Controller | Southeast Asia | 2 | 8GB |
| AZDC02-SEA | Domain Controller | Southeast Asia | 2 | 8GB |
| AZDC01-EA | Domain Controller | East Asia | 2 | 8GB |
| AZDC02-EA | Domain Controller | East Asia | 2 | 8GB |

**AKS Cluster**: 2 system nodes + 4 worker nodes

---

## Tools Used

| Tool | Version | Purpose |
|------|---------|---------|
| Packer | Latest | Windows image automation |
| Terraform | Latest | Infrastructure provisioning |
| Ansible | Latest | Configuration management |
| Azure CLI | Latest | Azure authentication & management |
| PowerShell | 7.x | Windows automation |

---

## Quick Start (After Inputs Provided)

```bash
# 1. Build Windows images with Packer
cd packer/windows-server-2025
packer build -var-file=vars.pkrvars.hcl .

# 2. Deploy Hyper-V VMs with Terraform
cd terraform/hyperv/environments/prod
terraform init && terraform apply

# 3. Configure VMs with Ansible
cd ansible
ansible-playbook -i inventory playbooks/site.yml

# 4. Deploy Azure infrastructure
cd terraform/azure/environments/prod
terraform init && terraform apply

# 5. Configure S2S VPN
# (Manual step on Omada Controller)

# 6. Validate connectivity
ansible all -m win_ping
```

---

## Related Documentation

- [Main Project README](../README.md)
- [Proxmox Infrastructure](../docs/PROXMOX.md)
- [Network Architecture](../docs/NETWORKING.md)

---

*Project created: 2025-12-31*
