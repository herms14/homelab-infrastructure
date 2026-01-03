# Architecture - Azure Hybrid Lab

> Enterprise-grade hybrid infrastructure design document.
> **Last Updated**: 2025-12-31

---

## Executive Summary

This document describes a hybrid Active Directory infrastructure spanning:
- **On-premises**: 12 Hyper-V VMs running Windows Server 2025 and Windows 11
- **Azure**: 4 Domain Controllers across 2 regions + Private AKS cluster
- **Connectivity**: Site-to-Site VPN via Azure vWAN

### Design Principles

1. **Enterprise patterns**: Tiered admin model, OU delegation, GPO baselines
2. **Cost awareness**: Start with NSGs, prepare for Azure Firewall migration
3. **Private by default**: No public IPs on VMs, private AKS, Bastion for access
4. **Resilience**: Multi-region DCs, VPN failover design for dynamic IP

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                 ON-PREMISES                                          │
│                              Hyper-V on Windows 10                                   │
│                                  VLAN 80                                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │                        IDENTITY TIER (Tier 0)                                │   │
│   │   ┌─────────────┐    ┌─────────────┐                                        │   │
│   │   │    DC01     │◄──►│    DC02     │  AD DS: hrmsmrflrii.xyz                │   │
│   │   │ 192.168.80.2│    │ 192.168.80.3│  DNS, DHCP, GPO                        │   │
│   │   └─────────────┘    └─────────────┘                                        │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │                      INFRASTRUCTURE TIER (Tier 1)                            │   │
│   │   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ ┌─────────┐ │   │
│   │   │    FS01     │ │    FS02     │ │   SQL01     │ │ AADCON01  │ │ AADPP01 │ │   │
│   │   │ File Server │ │ File Server │ │ SQL Server  │ │ Entra Con │ │ Pwd Prot│ │   │
│   │   │   .80.4     │ │   .80.5     │ │   .80.6     │ │   .80.7   │ │  .80.8  │ │   │
│   │   └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ └─────────┘ │   │
│   │                                                   ┌───────────┐              │   │
│   │                                                   │ AADPP02   │              │   │
│   │                                                   │ Pwd Prot  │              │   │
│   │                                                   │  .80.9    │              │   │
│   │                                                   └───────────┘              │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │                       APPLICATION TIER (Tier 2)                              │   │
│   │   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │   │
│   │   │   IIS01     │ │   IIS02     │ │  CLIENT01   │ │  CLIENT02   │           │   │
│   │   │ Web Server  │ │ Web Server  │ │ Windows 11  │ │ Windows 11  │           │   │
│   │   │   .80.10    │ │   .80.11    │ │   .80.12    │ │   .80.13    │           │   │
│   │   └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│                              ┌─────────────────┐                                     │
│                              │     ER605       │                                     │
│                              │   VPN Gateway   │                                     │
│                              │ 136.158.11.91   │                                     │
│                              └────────┬────────┘                                     │
└───────────────────────────────────────┼─────────────────────────────────────────────┘
                                        │
                                   IPsec IKEv2
                                   S2S VPN Tunnel
                                        │
┌───────────────────────────────────────┼─────────────────────────────────────────────┐
│                              AZURE vWAN                                              │
│                                        │                                             │
│                         ┌──────────────┴──────────────┐                             │
│                         │        vWAN Hub             │                             │
│                         │     (Southeast Asia)        │                             │
│                         └──────────────┬──────────────┘                             │
│                                        │                                             │
├────────────────────────────────────────┼────────────────────────────────────────────┤
│                                        │                                             │
│   ┌────────────────────────────────────┼───────────────────────────────────────┐    │
│   │            PLATFORM LANDING ZONE (FireGiants-Prod)                         │    │
│   │                                    │                                        │    │
│   │   ┌────────────────────────────────┼───────────────────────────────────┐   │    │
│   │   │              CONNECTIVITY (hm-rg-connectivity)                      │   │    │
│   │   │                                │                                    │   │    │
│   │   │   ┌─────────────┐    ┌─────────▼─────────┐    ┌─────────────┐      │   │    │
│   │   │   │ VPN Gateway │    │  Azure Bastion    │    │ Private DNS │      │   │    │
│   │   │   │  (VpnGw1)   │    │ (Secure Access)   │    │   Zones     │      │   │    │
│   │   │   └─────────────┘    └───────────────────┘    └─────────────┘      │   │    │
│   │   └────────────────────────────────────────────────────────────────────┘   │    │
│   │                                                                             │    │
│   │   ┌────────────────────────────────────────────────────────────────────┐   │    │
│   │   │                   IDENTITY (hm-rg-identity)                         │   │    │
│   │   │                                                                     │   │    │
│   │   │   Southeast Asia                      East Asia                     │   │    │
│   │   │   ┌─────────────┐ ┌─────────────┐    ┌─────────────┐ ┌────────────┐│   │    │
│   │   │   │ AZDC01-SEA  │ │ AZDC02-SEA  │    │ AZDC01-EA   │ │ AZDC02-EA  ││   │    │
│   │   │   │ 10.110.0.4  │ │ 10.110.0.5  │    │ 10.111.0.4  │ │ 10.111.0.5 ││   │    │
│   │   │   └─────────────┘ └─────────────┘    └─────────────┘ └────────────┘│   │    │
│   │   └────────────────────────────────────────────────────────────────────┘   │    │
│   │                                                                             │    │
│   │   ┌────────────────────────────────────────────────────────────────────┐   │    │
│   │   │                  MANAGEMENT (hm-rg-management)                      │   │    │
│   │   │   ┌─────────────────────┐    ┌─────────────────────────────────┐   │   │    │
│   │   │   │ Log Analytics       │    │ Azure Policy + Diagnostics      │   │   │    │
│   │   │   │ Workspace           │    │ (All resources log here)        │   │   │    │
│   │   │   └─────────────────────┘    └─────────────────────────────────┘   │   │    │
│   │   └────────────────────────────────────────────────────────────────────┘   │    │
│   └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │              APPLICATION LANDING ZONE (Nokron-Prod)                          │   │
│   │                                                                              │   │
│   │   ┌──────────────────────────────────────────────────────────────────────┐  │   │
│   │   │                        AKS (hm-rg-applz)                              │  │   │
│   │   │                                                                       │  │   │
│   │   │   ┌───────────────────────────────────────────────────────────────┐  │  │   │
│   │   │   │                    hm-aks-main (Private)                       │  │  │   │
│   │   │   │                                                                │  │  │   │
│   │   │   │   ┌─────────────────────┐    ┌─────────────────────────────┐  │  │  │   │
│   │   │   │   │   System Nodepool   │    │      User Nodepool          │  │  │  │   │
│   │   │   │   │   2× D2s_v3         │    │      4× D4s_v3              │  │  │  │   │
│   │   │   │   │   (4 vCPU, 16GB)    │    │      (16 vCPU, 64GB)        │  │  │  │   │
│   │   │   │   └─────────────────────┘    └─────────────────────────────┘  │  │  │   │
│   │   │   └───────────────────────────────────────────────────────────────┘  │  │   │
│   │   └──────────────────────────────────────────────────────────────────────┘  │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. On-Premises Infrastructure

#### 1.1 Hyper-V Host

| Specification | Value |
|---------------|-------|
| **OS** | Windows 10 Pro (20H2) |
| **CPU** | 16 logical cores |
| **RAM** | 62 GB |
| **Storage** | D:\ (3.6 TB free) |
| **Network** | External Switch on trunk port (VLAN 80 tagged) |

#### 1.2 Virtual Machines

All VMs are:
- **Generation 2** with UEFI
- **Secure Boot** enabled
- **vTPM** enabled (required for Windows 11)
- **VLAN 80** tagged on virtual NIC

| Category | VMs | Purpose |
|----------|-----|---------|
| **Domain Controllers** | DC01, DC02 | AD DS, DNS, DHCP |
| **File Servers** | FS01, FS02 | DFS, file shares |
| **SQL Server** | SQL01 | Database services |
| **Identity** | AADCON01, AADPP01, AADPP02 | Entra integration |
| **Web Servers** | IIS01, IIS02 | Application hosting |
| **Workstations** | CLIENT01, CLIENT02 | End-user testing |

### 2. Azure Landing Zone

#### 2.1 Subscription Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    Erdtree Guardians Tenant                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │           FireGiants-Prod (Platform LZ)                  │   │
│   │           2212d587-1bad-4013-b605-b421b1f83c30          │   │
│   │                                                          │   │
│   │   • hm-rg-connectivity (vWAN, VPN, Bastion)             │   │
│   │   • hm-rg-identity (Domain Controllers)                  │   │
│   │   • hm-rg-management (Log Analytics, Policies)          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │           Nokron-Prod (Application LZ)                   │   │
│   │           9dde5c52-88be-4608-9bee-c52d1909693f          │   │
│   │                                                          │   │
│   │   • hm-rg-applz (AKS Cluster)                           │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.2 Network Topology

```
                          Internet
                              │
                    ┌─────────▼─────────┐
                    │    Azure vWAN     │
                    │   Virtual Hub     │
                    │ (Southeast Asia)  │
                    └─────────┬─────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
    ┌────▼────┐         ┌─────▼─────┐        ┌────▼────┐
    │ VPN GW  │         │ Hub VNet  │        │Peering  │
    │ S2S     │         │ SEA       │        │to EA    │
    └────┬────┘         └───────────┘        └────┬────┘
         │                                        │
    ┌────▼────────────────┐              ┌───────▼───────┐
    │ On-Prem             │              │ Hub VNet EA   │
    │ 192.168.80.0/24     │              │ 10.101.0.0/16 │
    └─────────────────────┘              └───────────────┘
```

### 3. Active Directory Design

#### 3.1 Forest & Domain

| Setting | Value |
|---------|-------|
| **Forest Name** | hrmsmrflrii.xyz |
| **Domain Name** | hrmsmrflrii.xyz |
| **Forest Functional Level** | Windows Server 2025 |
| **Domain Functional Level** | Windows Server 2025 |
| **NetBIOS Name** | HRMSMRFLRII |

#### 3.2 Sites and Subnets

| Site Name | Subnets | Domain Controllers |
|-----------|---------|-------------------|
| OnPrem-Site | 192.168.80.0/24 | DC01, DC02 |
| Azure-SEA-Site | 10.110.0.0/24 | AZDC01-SEA, AZDC02-SEA |
| Azure-EA-Site | 10.111.0.0/24 | AZDC01-EA, AZDC02-EA |

#### 3.3 Site Links

| Link | Sites | Cost | Replication Interval |
|------|-------|------|---------------------|
| OnPrem-to-SEA | OnPrem-Site, Azure-SEA-Site | 100 | 15 min |
| SEA-to-EA | Azure-SEA-Site, Azure-EA-Site | 100 | 15 min |
| OnPrem-to-EA | OnPrem-Site, Azure-EA-Site | 200 | 30 min |

---

## OU Structure (Tiered Admin Model)

```
hrmsmrflrii.xyz (Domain)
│
├── Admin
│   ├── Tier 0
│   │   ├── Accounts          # Domain Admins, Enterprise Admins
│   │   ├── Groups            # Tier 0 security groups
│   │   └── Service Accounts  # AD service accounts
│   │
│   ├── Tier 1
│   │   ├── Accounts          # Server admins
│   │   ├── Groups            # Server admin groups
│   │   └── Service Accounts  # Server service accounts
│   │
│   └── Tier 2
│       ├── Accounts          # Workstation admins
│       ├── Groups            # Helpdesk, desktop support
│       └── Service Accounts  # Desktop service accounts
│
├── Servers
│   ├── Domain Controllers    # DC01, DC02, AZDC*
│   ├── Member Servers
│   │   ├── File Servers      # FS01, FS02
│   │   ├── SQL Servers       # SQL01
│   │   ├── Web Servers       # IIS01, IIS02
│   │   └── Identity Servers  # AADCON01, AADPP01, AADPP02
│   └── Azure
│       ├── SEA               # Azure DCs SEA
│       └── EA                # Azure DCs EA
│
├── Workstations
│   ├── Windows 11            # CLIENT01, CLIENT02
│   └── Kiosks                # Future kiosk devices
│
├── Users
│   ├── IT                    # IT department users
│   ├── HR                    # HR department users
│   ├── Finance               # Finance department users
│   ├── Engineering           # Engineering department users
│   ├── Sales                 # Sales department users
│   └── Marketing             # Marketing department users
│
├── Groups
│   ├── Security              # Role-based security groups
│   ├── Distribution          # Email distribution lists
│   └── File Share Access     # Share permission groups
│
└── Service Accounts
    ├── SQL                   # SQL service accounts
    ├── Web                   # IIS app pool accounts
    └── Backup                # Backup service accounts
```

---

## Security Design

### Network Security Groups

| NSG | Purpose | Key Rules |
|-----|---------|-----------|
| hm-nsg-bastion | Azure Bastion | Inbound HTTPS from Internet |
| hm-nsg-dc-sea | DC SEA | AD ports from VNet + On-prem |
| hm-nsg-dc-ea | DC EA | AD ports from VNet + On-prem |
| hm-nsg-aks | AKS | HTTPS from VNet only |

### Azure Firewall Readiness

Current state uses NSGs. For future Azure Firewall migration:

1. **Route Tables**: Already configured with default routes
2. **Subnet Design**: Firewall subnet pre-allocated (10.100.2.0/24)
3. **Application Rules**: Documented but not deployed
4. **Network Rules**: Documented but not deployed

### Bastion Access Flow

```
User (Internet)
      │
      ▼
Azure Bastion (hm-bastion)
      │
      ├──────► Azure VMs (direct RDP/SSH)
      │
      ▼
VPN Tunnel (S2S)
      │
      ▼
On-Prem VMs (192.168.80.x)
```

---

## Deployment Sequence

### Phase 1: Foundation (Packer)
1. Build Windows Server 2025 base image
2. Build Windows 11 base image
3. Validate images with WinRM/Ansible connectivity

### Phase 2: On-Prem Infrastructure (Terraform + Ansible)
1. Deploy DC01, configure as first DC
2. Deploy DC02, join domain, promote to DC
3. Deploy remaining VMs, domain join
4. Configure file shares, SQL, IIS

### Phase 3: Azure Connectivity (Terraform)
1. Deploy vWAN Hub
2. Deploy VPN Gateway
3. Configure S2S VPN connection
4. Validate tunnel

### Phase 4: Azure Identity (Terraform + Ansible)
1. Deploy Azure VNet for identity
2. Deploy AZDC01-SEA, AZDC02-SEA
3. Deploy AZDC01-EA, AZDC02-EA
4. Configure AD Sites and replication

### Phase 5: Azure Workloads (Terraform)
1. Deploy AKS cluster
2. Configure private DNS
3. Validate on-prem to AKS connectivity

### Phase 6: Management & Governance
1. Deploy Log Analytics
2. Configure diagnostic settings
3. Deploy Azure Policy assignments
4. Arc-enable on-prem VMs

---

## Cost Estimate (Monthly)

| Resource | SKU | Est. Cost |
|----------|-----|-----------|
| vWAN Hub | Standard | ~$150 |
| VPN Gateway | VpnGw1 | ~$140 |
| Azure Bastion | Basic | ~$140 |
| 4× DC VMs | Standard_D2s_v3 | ~$280 |
| AKS System (2× D2s_v3) | Pay-as-you-go | ~$140 |
| AKS User (4× D4s_v3) | Pay-as-you-go | ~$560 |
| Log Analytics | Pay-as-you-go | ~$50 |
| **Total (NSG mode)** | | **~$1,460/month** |

*Azure Firewall Standard would add ~$912/month*

---

## Related Documents

- [IP Addressing Plan](./IP_ADDRESSING.md)
- [Deployment Runbook](./DEPLOYMENT_RUNBOOK.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)

---

*Document created: 2025-12-31*
