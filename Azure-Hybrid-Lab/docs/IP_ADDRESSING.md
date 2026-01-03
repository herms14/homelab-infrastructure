# IP Addressing Plan - Azure Hybrid Lab

> Complete IP allocation for on-premises and Azure infrastructure.
> **Status**: Approved
> **Last Updated**: 2025-12-31

---

## Network Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ON-PREMISES NETWORK                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  VLAN 10: 192.168.10.0/24  │  Host Network (Hyper-V host, workstations)     │
│  VLAN 80: 192.168.80.0/24  │  Azure Hybrid Lab VMs (NEW)                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                              IPsec S2S VPN
                         (WAN: 136.158.11.91 - Dynamic)
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AZURE NETWORKS                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Hub SEA:      10.100.0.0/16   │  vWAN Hub - Southeast Asia                 │
│  Hub EA:       10.101.0.0/16   │  vWAN Hub - East Asia                      │
│  Identity SEA: 10.110.0.0/24   │  Domain Controllers - SEA                  │
│  Identity EA:  10.111.0.0/24   │  Domain Controllers - East Asia            │
│  AKS:          10.120.0.0/16   │  AKS Cluster (private)                     │
│  Bastion:      10.130.0.0/24   │  Azure Bastion subnet                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## On-Premises: VLAN 80 (192.168.80.0/24)

### Network Configuration

| Setting | Value |
|---------|-------|
| **Subnet** | 192.168.80.0/24 |
| **Gateway** | 192.168.80.1 |
| **Subnet Mask** | 255.255.255.0 |
| **DNS (Initial)** | 192.168.80.2, 192.168.80.3 (DCs after AD setup) |
| **DNS (Fallback)** | 8.8.8.8 (during initial setup only) |
| **DHCP Range** | 192.168.80.100 - 192.168.80.254 |
| **Static Range** | 192.168.80.2 - 192.168.80.99 |

### VM IP Allocations

| IP | Hostname | Role | OS | vCPU | RAM | Disk |
|----|----------|------|-----|------|-----|------|
| 192.168.80.1 | - | Gateway | - | - | - | - |
| 192.168.80.2 | DC01 | Primary Domain Controller | WS 2025 | 2 | 4 GB | 60 GB |
| 192.168.80.3 | DC02 | Secondary Domain Controller | WS 2025 | 2 | 4 GB | 60 GB |
| 192.168.80.4 | FS01 | File Server 1 | WS 2025 | 2 | 4 GB | 100 GB |
| 192.168.80.5 | FS02 | File Server 2 | WS 2025 | 2 | 4 GB | 100 GB |
| 192.168.80.6 | SQL01 | SQL Server | WS 2025 | 4 | 8 GB | 120 GB |
| 192.168.80.7 | AADCON01 | Entra ID Connect | WS 2025 | 2 | 4 GB | 60 GB |
| 192.168.80.8 | AADPP01 | Password Protection Proxy 1 | WS 2025 | 2 | 4 GB | 60 GB |
| 192.168.80.9 | AADPP02 | Password Protection Proxy 2 | WS 2025 | 2 | 4 GB | 60 GB |
| 192.168.80.10 | IIS01 | Web Server 1 | WS 2025 | 2 | 4 GB | 60 GB |
| 192.168.80.11 | IIS02 | Web Server 2 | WS 2025 | 2 | 4 GB | 60 GB |
| 192.168.80.12 | CLIENT01 | Windows 11 Workstation | Win 11 | 2 | 4 GB | 60 GB |
| 192.168.80.13 | CLIENT02 | Windows 11 Workstation | Win 11 | 2 | 4 GB | 60 GB |
| 192.168.80.14-99 | - | Reserved for future use | - | - | - | - |
| 192.168.80.100-254 | - | DHCP Pool | - | - | - | - |

### Resource Summary (On-Prem)

| Resource | Total |
|----------|-------|
| **VMs** | 12 |
| **vCPU** | 26 cores |
| **RAM** | 52 GB |
| **Storage** | 860 GB |
| **Available (Host)** | 16 cores, 62 GB RAM, 3.6 TB |

---

## Azure: Platform Landing Zone (FireGiants-Prod)

**Subscription ID**: `2212d587-1bad-4013-b605-b421b1f83c30`

### Connectivity Resource Group (`hm-rg-connectivity`)

#### Hub VNet - Southeast Asia (`hm-vnet-hub-sea`)

| Subnet | CIDR | Purpose |
|--------|------|---------|
| GatewaySubnet | 10.100.0.0/24 | VPN Gateway (reserved name) |
| AzureBastionSubnet | 10.100.1.0/24 | Azure Bastion (reserved name) |
| hm-snet-firewall | 10.100.2.0/24 | Future Azure Firewall |
| hm-snet-management | 10.100.3.0/24 | Jump boxes, management VMs |

#### Hub VNet - East Asia (`hm-vnet-hub-ea`)

| Subnet | CIDR | Purpose |
|--------|------|---------|
| GatewaySubnet | 10.101.0.0/24 | VPN Gateway |
| hm-snet-management-ea | 10.101.1.0/24 | Management VMs |

### Identity Resource Group (`hm-rg-identity`)

#### Identity VNet - Southeast Asia (`hm-vnet-identity-sea`)

| Subnet | CIDR | Purpose |
|--------|------|---------|
| hm-snet-dc-sea | 10.110.0.0/24 | Domain Controllers |

**Domain Controller IPs:**

| IP | Hostname | Role |
|----|----------|------|
| 10.110.0.4 | AZDC01-SEA | Domain Controller (SEA) |
| 10.110.0.5 | AZDC02-SEA | Domain Controller (SEA) |

#### Identity VNet - East Asia (`hm-vnet-identity-ea`)

| Subnet | CIDR | Purpose |
|--------|------|---------|
| hm-snet-dc-ea | 10.111.0.0/24 | Domain Controllers |

**Domain Controller IPs:**

| IP | Hostname | Role |
|----|----------|------|
| 10.111.0.4 | AZDC01-EA | Domain Controller (East Asia) |
| 10.111.0.5 | AZDC02-EA | Domain Controller (East Asia) |

### Management Resource Group (`hm-rg-management`)

| Resource | Purpose |
|----------|---------|
| hm-law-main | Log Analytics Workspace |
| hm-aa-main | Automation Account (optional) |

---

## Azure: Application Landing Zone (Nokron-Prod)

**Subscription ID**: `9dde5c52-88be-4608-9bee-c52d1909693f`

### App Landing Zone Resource Group (`hm-rg-applz`)

#### AKS VNet (`hm-vnet-aks`)

| Subnet | CIDR | Purpose |
|--------|------|---------|
| hm-snet-aks-system | 10.120.0.0/22 | AKS System Nodepool (1024 IPs) |
| hm-snet-aks-user | 10.120.4.0/22 | AKS User Nodepool (1024 IPs) |
| hm-snet-aks-api | 10.120.8.0/28 | AKS Private API Server |
| hm-snet-aks-ilb | 10.120.9.0/24 | Internal Load Balancers |

**AKS Cluster Configuration:**

| Setting | Value |
|---------|-------|
| **Cluster Name** | hm-aks-main |
| **Kubernetes Version** | 1.29.x (latest stable) |
| **Network Plugin** | Azure CNI |
| **Private Cluster** | Yes |
| **System Nodepool** | 2× Standard_D2s_v3 |
| **User Nodepool** | 4× Standard_D4s_v3 |

---

## VPN Configuration

### Site-to-Site VPN Details

| Parameter | On-Prem (Omada) | Azure |
|-----------|-----------------|-------|
| **Gateway** | ER605 v2.20 | VPN Gateway (VpnGw1) |
| **Public IP** | 136.158.11.91 (dynamic) | Static (Azure assigned) |
| **IKE Version** | IKEv2 | IKEv2 |
| **DH Group** | 14 (2048-bit) | DHGroup14 |
| **Encryption** | AES256 | AES256 |
| **Integrity** | SHA256 | SHA256 |
| **SA Lifetime** | 28800 seconds | 28800 seconds |

### Dynamic IP Resilience

Since the on-prem WAN IP is dynamic:

1. **Azure VPN Gateway**: Configure with `LocalNetworkGateway` that can be updated
2. **DDNS Option**: Configure DDNS on Omada (e.g., no-ip.com, duckdns.org)
3. **Automation**: Script to detect IP change and update Azure LNG via Azure CLI

### VPN Routing

| Network | Direction | Path |
|---------|-----------|------|
| 192.168.80.0/24 | On-prem → Azure | Via S2S VPN |
| 10.100.0.0/16 | Azure → On-prem | Via S2S VPN |
| 10.110.0.0/24 | Azure → On-prem | Via vWAN + S2S |
| 10.111.0.0/24 | Azure → On-prem | Via vWAN + S2S |
| 10.120.0.0/16 | Azure → On-prem | Via vWAN + S2S |

---

## DNS Configuration

### AD DNS Hierarchy

```
                    ┌─────────────────────┐
                    │   hrmsmrflrii.xyz   │
                    │   (AD DNS Zone)     │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼────┐           ┌─────▼─────┐          ┌─────▼─────┐
   │  DC01   │           │ AZDC01-SEA│          │ AZDC01-EA │
   │  DC02   │           │ AZDC02-SEA│          │ AZDC02-EA │
   │ On-Prem │           │ Azure SEA │          │ Azure EA  │
   └─────────┘           └───────────┘          └───────────┘
   192.168.80.2-3         10.110.0.4-5          10.111.0.4-5
```

### DNS Forwarders

| Source | Forwards To | Purpose |
|--------|-------------|---------|
| DC01/DC02 | 8.8.8.8, 1.1.1.1 | Internet resolution |
| Azure DCs | DC01, DC02 | AD zone replication |
| AKS DNS | Azure DNS + DCs | Hybrid resolution |

---

## Naming Convention

### Pattern

```
{prefix}-{resource-type}-{workload}-{region}-{instance}
```

### Examples

| Resource | Name |
|----------|------|
| Resource Group | `hm-rg-connectivity` |
| VNet | `hm-vnet-hub-sea` |
| Subnet | `hm-snet-dc-sea` |
| VM | `hm-vm-dc-sea-01` |
| NSG | `hm-nsg-dc-sea` |
| Public IP | `hm-pip-vpngw-sea` |
| VPN Gateway | `hm-vpng-sea` |
| AKS | `hm-aks-main` |

### Abbreviations

| Type | Abbreviation |
|------|--------------|
| Resource Group | rg |
| Virtual Network | vnet |
| Subnet | snet |
| Virtual Machine | vm |
| Network Security Group | nsg |
| Public IP | pip |
| VPN Gateway | vpng |
| Local Network Gateway | lng |
| Log Analytics Workspace | law |
| Azure Kubernetes Service | aks |

---

## Security Groups (NSGs)

### On-Prem VM Access

| NSG | Applied To | Inbound Rules |
|-----|------------|---------------|
| hm-nsg-dc | DC Subnet | RDP (3389), DNS (53), LDAP (389/636), Kerberos (88), SMB (445) |
| hm-nsg-sql | SQL Subnet | SQL (1433), RDP (3389) |
| hm-nsg-web | IIS Subnet | HTTP (80), HTTPS (443), RDP (3389) |

### Azure NSG Rules

| NSG | Inbound Allow | Source |
|-----|---------------|--------|
| hm-nsg-bastion | HTTPS (443) | Internet |
| hm-nsg-dc-azure | AD Ports | VNet + On-prem (192.168.80.0/24) |
| hm-nsg-aks | HTTPS (443) | VNet |

---

## Validation Checklist

After deployment, verify:

- [ ] On-prem VMs can ping 192.168.80.1 (gateway)
- [ ] On-prem VMs can ping each other
- [ ] DC01 → DC02 AD replication works
- [ ] On-prem → Azure VPN tunnel established
- [ ] On-prem can ping Azure DCs (10.110.0.4)
- [ ] Azure DCs can ping on-prem DCs (192.168.80.2)
- [ ] AD replication across sites works
- [ ] AKS nodes can resolve AD DNS
- [ ] Bastion can RDP to Azure VMs
- [ ] Bastion can RDP to on-prem VMs (via VPN)

---

*Document created: 2025-12-31*
