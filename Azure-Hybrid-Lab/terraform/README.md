# Terraform - Azure Hybrid Lab

Deploys Azure infrastructure for hybrid connectivity with on-premises Hyper-V environment.

## Prerequisites

### On Ansible Controller

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Install Terraform
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# Login to Azure
az login

# Set subscription (Platform LZ first)
az account set --subscription "2212d587-1bad-4013-b605-b421b1f83c30"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AZURE CLOUD                                       │
├─────────────────────────────────┬───────────────────────────────────────────┤
│  Platform LZ (FireGiants-Prod)  │  Application LZ (Nokron-Prod)             │
│  ───────────────────────────────│───────────────────────────────────────────│
│  ┌─────────────────────────┐    │  ┌─────────────────────────────────────┐  │
│  │     Hub VNet            │    │  │        Spoke VNet                   │  │
│  │     10.0.0.0/16         │    │  │        10.1.0.0/16                  │  │
│  │  ┌─────────────────┐    │    │  │  ┌──────────────────────────────┐   │  │
│  │  │ Identity Subnet │    │    │  │  │    AKS Subnet (10.1.0.0/22)  │   │  │
│  │  │ AZDC01/02       │    │────│──│  │    Private AKS Cluster       │   │  │
│  │  │ AZRODC01/02     │    │    │  │  └──────────────────────────────┘   │  │
│  │  └─────────────────┘    │    │  └─────────────────────────────────────┘  │
│  │  ┌─────────────────┐    │    │                                           │
│  │  │ vWAN Hub        │    │    │                                           │
│  │  │ VPN Gateway ────│────│────│─── S2S VPN ─────────────────────────────┐ │
│  │  └─────────────────┘    │    │                                         │ │
│  └─────────────────────────┘    │                                         │ │
└─────────────────────────────────┴─────────────────────────────────────────│─┘
                                                                            │
┌───────────────────────────────────────────────────────────────────────────│─┐
│                           ON-PREMISES (VLAN 80)                           │ │
│                           192.168.80.0/24                                 │ │
│  ┌───────────────────────────────────────────────────────────────────┐    │ │
│  │  Omada ER605 ──────────────────────────────────────────────────────────┘ │
│  │  WAN: 136.158.11.91                                               │      │
│  └───────────────────────────────────────────────────────────────────┘      │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                    │
│  │ DC01/DC02     │  │ FS01/FS02     │  │ CLIENT01/02   │                    │
│  │ .2/.3         │  │ .4/.5         │  │ .12/.13       │                    │
│  └───────────────┘  └───────────────┘  └───────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Modules

| Module | Subscription | Resources |
|--------|--------------|-----------|
| `connectivity` | FireGiants-Prod | Hub VNet, vWAN, VPN Gateway, NSGs |
| `platform-lz` | FireGiants-Prod | 4 Azure DCs, Key Vault, Private DNS |
| `app-lz` | Nokron-Prod | Spoke VNet, Private AKS, ACR |

## Resource Summary

| Resource | Name | CIDR/Details |
|----------|------|--------------|
| Hub VNet | vnet-azurehybrid-hub-prod | 10.0.0.0/16 |
| Identity Subnet | identity | 10.0.2.0/24 |
| Spoke VNet | vnet-azurehybrid-spoke-prod | 10.1.0.0/16 |
| AKS Subnet | aks | 10.1.0.0/22 |
| vWAN Hub | vhub-azurehybrid-prod | 10.100.0.0/23 |

## Usage

### From Ansible Controller

```bash
# Navigate to terraform directory
cd ~/azure-hybrid-lab/terraform

# Create tfvars file
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars  # Fill in sensitive values

# Initialize
terraform init

# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan
```

### Environment Variables (Alternative)

```bash
export TF_VAR_admin_password="YourSecurePassword123!"
export TF_VAR_onprem_network='{"vlan_id":80,"address_space":"192.168.80.0/24","gateway_ip":"192.168.80.1","wan_ip":"136.158.11.91","vpn_psk":"YourVPNKey"}'

terraform apply
```

## Outputs

After deployment, Terraform outputs:

| Output | Description |
|--------|-------------|
| `vpn_gateway_public_ip` | Azure VPN Gateway public IP (configure on Omada ER605) |
| `dc_private_ips` | IP addresses of Azure DCs |
| `aks_cluster_fqdn` | Private FQDN for AKS cluster |
| `vpn_config_for_omada` | Complete VPN config for router |

## Post-Deployment Steps

1. **Configure Omada ER605 VPN**
   - Get Azure VPN Gateway public IP from outputs
   - Configure IPsec VPN with matching pre-shared key

2. **Promote Azure DCs**
   - Run Ansible playbook to configure AD DS
   - Establish replication with on-prem DC01/DC02

3. **Configure DNS**
   - Point Azure DCs to on-prem DCs as forwarders
   - Configure conditional forwarding for hybrid resolution

## Network Connectivity

| Source | Destination | Port | Purpose |
|--------|-------------|------|---------|
| On-Prem DCs | Azure DCs | 53, 88, 389, 636 | AD Replication |
| Ansible Controller | Azure DCs | 5985, 5986 | WinRM Management |
| Azure AKS | On-Prem | Various | Application Traffic |
| All | Azure VPN GW | 500, 4500 | IPsec VPN |
