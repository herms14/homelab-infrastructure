# Multi-Region Azure Infrastructure with VWAN

## Overview

This document describes the multi-region Azure infrastructure using Azure Virtual WAN with hubs in Southeast Asia (SEA) and East Asia. All Windows servers are domain-joined to **hrmsmrflrii.xyz**.

## Architecture

```
                              AZURE VIRTUAL WAN (vwan-homelab-prod)
                    ┌─────────────────────────────────────────────────────┐
                    │                                                      │
         ┌──────────▼──────────┐              ┌───────────▼────────────┐
         │   sea-hub           │◄── Hub2Hub ─►│   eastasia-hub         │
         │   10.100.0.0/23     │              │   10.110.0.0/23        │
         │   VPN Gateway ──────┼──────────────┤                        │
         └──────────┬──────────┘              └───────────┬────────────┘
                    │                                      │
    ┌───────────────┼───────────────┐          ┌──────────┴──────────┐
    │               │               │          │                      │
┌───▼───┐      ┌────▼────┐    ┌────▼────┐  ┌──▼──────────────────┐
│Identity│     │App Svrs │    │File Svrs│  │ vnet-servers-eastasia│
│ VNet   │     │  VNet   │    │  VNet   │  │     10.20.0.0/16     │
│10.10.x │     │10.11.x  │    │10.12.x  │  │                      │
│        │     │         │    │         │  │ ┌─────┐ ┌─────┐      │
│AZDC01/02│    │APP-SEA01│    │FS-SEA01 │  │ │AKS  │ │SQLMI│      │
└────────┘     └─────────┘    │FS-SEA02 │  │ └─────┘ └─────┘      │
                              └─────────┘  │ SRV-EA01/02, APP-EA01│
                                           │ AZRODC01/02          │
                                           └──────────────────────┘
        │
        │ S2S VPN (IPsec)
        ▼
   ON-PREMISES HOMELAB (192.168.x.x)
```

## Resource Groups

| Resource Group | Region | Purpose |
|----------------|--------|---------|
| rg-vwan-prod | Southeast Asia | Virtual WAN and hubs |
| rg-app-servers-prod-sea | Southeast Asia | Application servers |
| rg-file-servers-prod-sea | Southeast Asia | File servers |
| rg-servers-prod-eas | East Asia | All East Asia resources |

## Network Address Plan

### Southeast Asia

| VNet | CIDR | Purpose |
|------|------|---------|
| vnet-identity-sea (existing) | 10.10.0.0/21 | AZDC01/02 |
| vnet-app-servers-sea | 10.11.0.0/16 | APP-SEA01 |
| vnet-file-servers-sea | 10.12.0.0/16 | FS-SEA01/02 |

### East Asia

| Subnet | CIDR | Hosts |
|--------|------|-------|
| snet-servers | 10.20.1.0/24 | SRV-EA01/02, APP-EA01 |
| snet-aks-nodes | 10.20.4.0/22 | AKS nodes |
| snet-sqlmi | 10.20.8.0/24 | SQL MI |
| snet-rodc | 10.20.10.0/24 | AZRODC01/02 |

### VWAN Hubs

| Hub | Address Space |
|-----|---------------|
| sea-hub | 10.100.0.0/23 |
| eastasia-hub | 10.110.0.0/23 |

## VM Inventory

| VM | Region | IP | Role | Domain Join |
|----|--------|-----|------|-------------|
| AZDC01 | SEA | 10.10.4.4 | Primary DC | N/A (DC) |
| AZDC02 | SEA | 10.10.4.5 | Secondary DC | N/A (DC) |
| APP-SEA01 | SEA | 10.11.1.4 | App Server | Yes |
| FS-SEA01 | SEA | 10.12.1.4 | File Server | Yes |
| FS-SEA02 | SEA | 10.12.1.5 | File Server | Yes |
| SRV-EA01 | East Asia | 10.20.1.4 | General Server | Yes |
| SRV-EA02 | East Asia | 10.20.1.5 | General Server | Yes |
| APP-EA01 | East Asia | 10.20.1.6 | App Server | Yes |
| AZRODC01 | East Asia | 10.20.10.4 | Read-Only DC | Promoted |
| AZRODC02 | East Asia | 10.20.10.5 | Read-Only DC | Promoted |

## PaaS Resources

### AKS Cluster (East Asia)

| Setting | Value |
|---------|-------|
| Name | aks-homelab-prod-eas |
| Kubernetes Version | 1.28 |
| System Nodes | 1x Standard_D2s_v3 |
| User Nodes | 3x Standard_D2s_v3 |
| Network | Azure CNI Overlay |
| Access | Private cluster (no public IP) |

### SQL Managed Instance (East Asia)

| Setting | Value |
|---------|-------|
| Name | sqlmi-homelab-prod-eas |
| SKU | GP_Gen5 |
| vCores | 4 |
| Storage | 32 GB |
| Subnet | snet-sqlmi (10.20.8.0/24) |

## Monitoring

### Log Analytics Workspaces

| Workspace | Region | Purpose |
|-----------|--------|---------|
| law-homelab-sea | Southeast Asia | Regional monitoring, patch management |
| law-homelab-eas | East Asia | Regional monitoring, patch management |
| law-homelab-sentinel | Southeast Asia | Security logs (existing) |

### Data Collection

- Azure Monitor Agent installed on all VMs
- Windows Event Logs collected to regional LAW
- Security Events forwarded to Sentinel LAW
- Data Collection Rules per region

## Deployment

### Prerequisites

1. Azure subscription with sufficient quota
2. Existing identity VNet with domain controllers (AZDC01/02)
3. OPNsense firewall with public IP for VPN
4. ubuntu-deploy-vm with managed identity

### Terraform Deployment

```bash
# SSH to deployment VM
ssh ubuntu-deploy

# Navigate to module
cd ~/tf-proxmox/terraform/azure/multi-region-vwan

# Create terraform.tfvars from example
cp terraform.tfvars.example terraform.tfvars
# Edit with actual values (VPN key, passwords, OPNsense IP)

# Deploy
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### Post-Deployment: VPN Configuration

After Terraform deployment, update OPNsense with the new VPN gateway IPs:

```bash
# Get VPN gateway public IPs
terraform output vpn_gateway_public_ips
```

Configure OPNsense IPsec tunnel with these IPs.

### Ansible Domain Configuration

```bash
# SSH to deployment VM
ssh ubuntu-deploy

# Navigate to playbooks
cd ~/tf-proxmox/ansible/playbooks/azure-multiregion

# Create vault file
ansible-vault create vault.yml
# Add: vault_admin_password, vault_domain_password, vault_dsrm_password

# Step 1: Domain join member servers
ansible-playbook -i inventory.yml 01-domain-join.yml --ask-vault-pass

# Step 2: Promote RODCs in East Asia
ansible-playbook -i inventory.yml 02-promote-rodc.yml --ask-vault-pass
```

## Security Design

- **No Public IPs**: All VMs accessible only via VPN or Bastion
- **NSGs**: Applied to all subnets with least-privilege rules
- **Private Endpoints**: AKS and SQL MI use private networking
- **VWAN Routing**: All inter-region traffic through VWAN hubs
- **Azure Bastion**: Optional for emergency management access

## Estimated Monthly Cost

| Category | Cost |
|----------|------|
| Compute (8 VMs + AKS) | ~$520 |
| VWAN + Hubs + VPN | ~$550 |
| Storage (Managed Disks) | ~$280 |
| SQL MI (GP 4 vCore) | ~$350 |
| Log Analytics | ~$185 |
| **Total** | **~$1,885/month** |

## File Structure

```
terraform/azure/multi-region-vwan/
├── main.tf                    # Root orchestration
├── providers.tf               # Azure provider config
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── terraform.tfvars.example   # Example variables
└── modules/
    ├── vwan/                  # Virtual WAN + Hubs
    ├── spoke-vnet/            # Reusable spoke VNet
    ├── windows-vm/            # Windows Server VM
    ├── aks-cluster/           # Private AKS
    ├── sql-mi/                # SQL Managed Instance
    └── log-analytics/         # Regional LAW + DCRs

ansible/playbooks/azure-multiregion/
├── inventory.yml              # Host inventory
├── vault.yml                  # Encrypted credentials
├── 01-domain-join.yml         # Domain join playbook
└── 02-promote-rodc.yml        # RODC promotion playbook
```

## Verification Checklist

- [ ] VPN connectivity from on-prem to both regions
- [ ] Inter-region routing through VWAN
- [ ] Domain join successful for all member servers
- [ ] RODC promotion completed in East Asia
- [ ] AD replication working between all DCs
- [ ] AKS cluster accessible from on-prem
- [ ] SQL MI accessible via private endpoint
- [ ] Logs flowing to Sentinel workspace

## Troubleshooting

### VPN Not Connecting

1. Verify OPNsense has correct VWAN gateway IPs
2. Check shared key matches
3. Verify BGP settings if using BGP

### Domain Join Fails

1. Verify DNS resolution: `nslookup hrmsmrflrii.xyz`
2. Check DNS servers set to AZDC01/02 IPs
3. Verify VPN routing to 10.10.4.0/24

### RODC Promotion Fails

1. Ensure EastAsia AD site exists
2. Verify replication from AZDC01
3. Check DSRM password meets complexity requirements

## Related Documentation

- [Azure Hybrid Lab](AZURE_HYBRID_LAB.md) - Domain controller setup
- [Azure Environment](AZURE_ENVIRONMENT.md) - Overall Azure setup
- [Azure Sentinel Setup](AZURE_SENTINEL_SETUP.md) - SIEM configuration
