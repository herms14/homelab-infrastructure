# Site-to-Site VPN Configuration - Azure Hybrid Lab

## Overview

Configures IPsec Site-to-Site VPN between Omada ER605 router and Azure vWAN VPN Gateway.

## Network Summary

| Side | Network | Gateway |
|------|---------|---------|
| On-Premises | 192.168.80.0/24 | 192.168.80.1 (Omada ER605) |
| Azure Hub | 10.0.0.0/16 | Azure VPN Gateway |
| Azure Spoke | 10.1.0.0/16 | Via Hub |

## Prerequisites

1. Azure Terraform deployed (`terraform apply`)
2. Obtain Azure VPN Gateway public IP from Terraform output:
   ```bash
   terraform output vpn_gateway_public_ip
   ```

## Omada ER605 Configuration

### Step 1: Access Omada Controller

1. Navigate to Omada Controller web UI
2. Go to **Settings** → **VPN** → **Site-to-Site VPN**

### Step 2: Create IPsec Policy

Click **+ Create New VPN** with these settings:

#### Basic Settings

| Setting | Value |
|---------|-------|
| Name | Azure-Hybrid-Lab |
| Status | Enabled |
| Remote Gateway | `<Azure VPN Gateway IP from Terraform>` |
| Remote Subnets | 10.0.0.0/16, 10.1.0.0/16 |
| Local Networks | 192.168.80.0/24 |
| WAN | WAN (your internet-facing interface) |

#### IKE Policy (Phase 1)

| Setting | Value |
|---------|-------|
| IKE Version | IKEv2 |
| Encryption | AES256 |
| Integrity | SHA256 |
| DH Group | 14 (2048-bit MODP) |
| Lifetime | 28800 seconds |
| Pre-Shared Key | `<Same key used in Terraform>` |

#### IPsec Policy (Phase 2)

| Setting | Value |
|---------|-------|
| Encryption | AES256 |
| Integrity | SHA256 |
| PFS Group | 14 (2048-bit MODP) |
| Lifetime | 3600 seconds |

#### Advanced Settings

| Setting | Value |
|---------|-------|
| DPD | Enabled |
| DPD Interval | 30 seconds |
| DPD Timeout | 120 seconds |
| NAT-T | Enabled |

### Step 3: Firewall Rules

Ensure the following firewall rules allow VPN traffic:

| Rule | Source | Destination | Action |
|------|--------|-------------|--------|
| Azure-to-OnPrem | 10.0.0.0/8 | 192.168.80.0/24 | Allow |
| OnPrem-to-Azure | 192.168.80.0/24 | 10.0.0.0/8 | Allow |

### Step 4: Routing

Add static routes if not automatically created:

| Destination | Gateway | Interface |
|-------------|---------|-----------|
| 10.0.0.0/16 | VPN Tunnel | Azure-Hybrid-Lab |
| 10.1.0.0/16 | VPN Tunnel | Azure-Hybrid-Lab |

## Dynamic WAN IP Handling

Since WAN IP (136.158.11.91) is dynamic, consider:

1. **DDNS**: Configure Dynamic DNS on ER605
2. **Azure Automation**: Create runbook to update VPN Site IP
3. **Manual Update**: Update Azure VPN Site when IP changes

### Ansible Playbook for IP Update

Create a playbook to update Azure VPN Site when WAN IP changes:

```yaml
# update-vpn-site-ip.yml
- name: Update Azure VPN Site IP
  hosts: localhost
  vars:
    new_wan_ip: "{{ lookup('env', 'NEW_WAN_IP') }}"
  tasks:
    - name: Update VPN Site IP in Azure
      azure.azcollection.azure_rm_resource:
        resource_group: rg-azurehybrid-connectivity-prod
        provider: Network
        resource_type: vpnSites
        resource_name: vpnsite-onprem-prod
        api_version: "2023-05-01"
        body:
          properties:
            ipAddress: "{{ new_wan_ip }}"
```

## Verification

### On Omada ER605

1. Check VPN status: **VPN** → **IPsec Status**
2. Verify tunnel is "Established"
3. Check traffic counters

### From On-Premises VM

```powershell
# Test connectivity to Azure DC
Test-NetConnection -ComputerName 10.0.2.4 -Port 389

# Ping Azure VNet
ping 10.0.2.4
```

### From Azure VM (after deployment)

```powershell
# Test connectivity to on-prem DC
Test-NetConnection -ComputerName 192.168.80.2 -Port 389

# Ping on-prem
ping 192.168.80.2
```

## Troubleshooting

| Issue | Check |
|-------|-------|
| Phase 1 fails | Verify pre-shared key, IKE settings match |
| Phase 2 fails | Verify IPsec settings, remote subnets |
| No traffic | Check firewall rules, routing |
| Intermittent | Check DPD settings, NAT-T |

### Azure VPN Diagnostics

```bash
# Check VPN connection status
az network vpn-gateway connection show \
  --gateway-name vpngw-azurehybrid-prod \
  --name vpnconn-onprem-prod \
  --resource-group rg-azurehybrid-connectivity-prod
```
