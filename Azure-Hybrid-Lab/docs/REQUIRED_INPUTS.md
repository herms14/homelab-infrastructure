# Required Inputs for Azure Hybrid Lab

> **CRITICAL**: Do NOT proceed with implementation until all required inputs are provided.
> Guessing values can cause IP conflicts, broken VPN, or misconfigured Azure resources.

---

## Input Status Tracker

| Category | Status | Notes |
|----------|--------|-------|
| VLAN 80 IP Allocation | ✅ Complete | See IP_ADDRESSING.md - 192.168.80.0/24 |
| Hyper-V Host Details | ✅ Complete | Win 10 Pro, 16 cores, 62GB RAM, D:\ |
| Windows Media & Licensing | ⏳ Pending | Need ISO paths (WS2025, Win11) |
| Omada VPN Gateway | ✅ Complete | ER605 v2.20, WAN 136.158.11.91 (dynamic) |
| Azure Subscriptions | ✅ Complete | FireGiants-Prod + Nokron-Prod |
| CI/CD Preference | ⏳ Pending | Not yet specified |
| Azure Firewall Decision | ✅ Complete | NSG only (future Azure FW ready) |
| AKS Configuration | ✅ Complete | Private, 2× D2s_v3 + 4× D4s_v3 |

---

## 1. VLAN 20 Network Details (CRITICAL)

I need to understand your existing VLAN 20 network to avoid IP conflicts.

### Questions:

**1.1 What is your VLAN 20 CIDR?**
- From your docs, I see it's `192.168.20.0/24` with gateway `192.168.20.1`
- **Please confirm this is correct**

**1.2 What IP addresses are ALREADY IN USE on VLAN 20?**

From your context, I found these in use:
| IP | Host | Purpose |
|----|------|---------|
| 192.168.20.1 | Gateway | VLAN 20 Gateway |
| 192.168.20.20 | node01 | Proxmox Primary |
| 192.168.20.21 | node02 | Proxmox Service Host |
| 192.168.20.30 | ansible-controller01 | Ansible |
| 192.168.20.31 | Synology NAS (eth1) | Storage |
| 192.168.20.32-34 | K8s controllers | Kubernetes |
| 192.168.20.40-45 | K8s workers | Kubernetes |

**Questions:**
- Are there any OTHER IPs in use on VLAN 20 not listed above?
- What IP range do you want to reserve for the new Hyper-V VMs?
- Suggested: `192.168.20.50-70` for 14 VMs + Azure DCs replica

**1.3 DNS Configuration**
- Current DNS: `192.168.90.53` (Pi-hole + Unbound)
- Will the new AD DCs provide DNS, or continue using Pi-hole?
- Do you want conditional forwarding configured?

**Where to find this:**
```powershell
# On any Windows machine on VLAN 20
ipconfig /all
# Or check your Omada DHCP reservation list
# Or check OPNsense DNS/DHCP settings
```

---

## 2. Hyper-V Host Details (CRITICAL)

### Questions:

**2.1 Windows Host Information**
- What Windows version is your Hyper-V host running? (e.g., Windows 11 Pro, Windows Server 2022)
  ```powershell
  # Run this to get exact version
  Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsHardwareAbstractionLayer
  ```

**2.2 Hyper-V Switch Configuration**
- What is the name of your external virtual switch?
  ```powershell
  Get-VMSwitch | Select-Object Name, SwitchType, NetAdapterInterfaceDescription
  ```
- Is VLAN tagging configured on the switch? How?
- Is the physical NIC connected to a trunk port with VLAN 20 tagged?

**2.3 Storage Path**
- Where should VM disks be stored?
  - Default: `C:\Hyper-V\Virtual Hard Disks\`
  - Or custom path?
- How much free disk space is available?
  ```powershell
  Get-Volume | Where-Object DriveLetter -eq 'C' | Select-Object SizeRemaining
  ```

**2.4 Host Resources**
- Total RAM available for VMs?
  ```powershell
  Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory
  ```
- Total CPU cores available?
  ```powershell
  Get-CimInstance Win32_Processor | Select-Object NumberOfCores, NumberOfLogicalProcessors
  ```

**2.5 VM Generation & Security**
- Should VMs be Generation 2? (Recommended: Yes)
- Enable Secure Boot? (Required for Windows 11)
- Enable vTPM? (Required for Windows 11)
- If Windows 11, do you have the required Hyper-V isolation features enabled?

---

## 3. Windows Media & Licensing (CRITICAL)

### Questions:

**3.1 Windows Server 2025 ISO**
- Do you have a Windows Server 2025 ISO?
- If so, what is the full path?
  - Example: `C:\ISOs\WindowsServer2025.iso`
- Is this Evaluation or Licensed media?

**3.2 Windows 11 ISO**
- Do you have a Windows 11 ISO?
- If so, what is the full path?
- Which edition? (Pro, Enterprise, Education)

**3.3 Product Keys**
- Do you have volume license keys (VLK/MAK)?
- Or will you use evaluation mode (180-day trial)?
- **NOTE**: I will NOT hardcode keys. Provide them via:
  - Environment variable
  - Secrets file (not committed to git)
  - Azure Key Vault (for Azure VMs)

**3.4 Autounattend.xml Preferences**
- Default admin username? (Suggestion: `Administrator`)
- Default admin password? (I'll use a placeholder variable)
- Timezone? (Suggestion: `Singapore Standard Time` based on your location)
- Locale/Language? (en-US?)

**Where to find ISOs:**
- Visual Studio Subscription: https://my.visualstudio.com/Downloads
- Microsoft Evaluation Center: https://www.microsoft.com/en-us/evalcenter/
- Volume Licensing Service Center (VLSC): https://www.microsoft.com/Licensing/servicecenter/

---

## 4. Omada VPN Gateway (CRITICAL for S2S VPN)

### Questions:

**4.1 Gateway Model & Firmware**
- What is your Omada gateway model?
  - From your docs: ER605 v2.20
  - **Confirm this is the VPN endpoint**
- Current firmware version?
  - Check: Omada Controller → Devices → Gateway → Firmware

**4.2 VPN Capability**
- Does ER605 support IPsec Site-to-Site VPN? (Yes, it does)
- Do you have an existing VPN configuration?
- What is the WAN IP or DDNS hostname?
  - Static public IP? Or dynamic with DDNS?

**4.3 Omada Controller Access**
- Controller IP: `192.168.0.103` (OC300) - from your docs
- Do you have admin credentials for VPN configuration?
- Can I configure VPN via API, or must it be manual?

**Where to find this:**
```
Omada Controller → Devices → Gateway → Details
Omada Controller → VPN → Site-to-Site VPN
```

---

## 5. Azure Configuration (CRITICAL)

### Questions:

**5.1 Subscription Details**
- Subscription 1 ID: `________________________________________`
- Subscription 1 Name: `________________________________________`
- Subscription 2 ID: `________________________________________`
- Subscription 2 Name: `________________________________________`

**How to find:**
```powershell
az account list --output table
# Or: Azure Portal → Subscriptions
```

**5.2 Target Regions**
- Primary Region: `Southeast Asia` (Singapore) - confirm?
- Secondary Region: `East Asia` (Hong Kong) - confirm?
- Or different regions?

**5.3 Naming Prefix**
- What prefix for Azure resources?
  - Example: `hrmlab`, `homelab`, `hl`
  - This will be used: `{prefix}-rg-connectivity`, `{prefix}-vnet-hub`, etc.

**5.4 Authentication Method**
- Can you create a Service Principal for Terraform?
  ```bash
  az ad sp create-for-rbac --name "terraform-sp" --role Contributor --scopes /subscriptions/<SUB_ID>
  ```
- Or prefer Managed Identity? (requires Azure VM for Terraform)
- Or use Azure CLI auth? (interactive login)

**5.5 Required RBAC Roles**
For Terraform SP/identity, these roles are needed at subscription scope:
- `Contributor` - Create/manage resources
- `User Access Administrator` - Assign roles (for AKS, etc.)
- `Network Contributor` - VPN/vWAN configuration

Can you assign these roles?

---

## 6. CI/CD Preference

**6.1 Which CI system do you prefer?**
- [ ] GitHub Actions (stored in `.github/workflows/`)
- [ ] Azure DevOps Pipelines (stored in `azure-pipelines.yml`)

**6.2 Do you have existing repos?**
- Is this repo already connected to GitHub/Azure DevOps?
- Should I create pipeline files, or just document the steps?

---

## 7. Azure Firewall vs NSG Decision (Cost Consideration)

**Options:**

| Option | Monthly Cost (Est.) | Features |
|--------|---------------------|----------|
| **Azure Firewall Standard** | ~$912/month | Full L7 filtering, threat intel, FQDN rules |
| **Azure Firewall Basic** | ~$270/month | L3/L4 filtering, limited throughput |
| **NSG + UDR only** | ~$0/month | Basic packet filtering, no inspection |
| **Third-party NVA** | Varies | Depends on vendor (Palo Alto, Fortinet, etc.) |

**7.1 Which approach do you prefer?**
- [ ] Azure Firewall Standard (enterprise features, highest cost)
- [ ] Azure Firewall Basic (good balance)
- [ ] NSG + UDR only (lowest cost, less features)
- [ ] Skip firewall for now, add later

**Recommendation**: For a lab/learning environment, NSG + UDR is sufficient. Add Azure Firewall later if needed.

---

## 8. AKS Configuration

**8.1 Private Cluster?**
- [ ] Yes - API server not publicly accessible (requires private DNS, more complex)
- [ ] No - Public API server with authorized IP ranges (simpler for learning)

**8.2 Node SKU Preferences**
Default plan:
- System nodepool: 2× `Standard_D2s_v3` (2 vCPU, 8GB RAM)
- User nodepool: 4× `Standard_D4s_v3` (4 vCPU, 16GB RAM)

**Questions:**
- Is this acceptable, or prefer smaller SKUs?
- Have you encountered quota issues in these regions?

**How to check quotas:**
```bash
az vm list-usage --location southeastasia --output table | grep -i "Standard D"
```

**8.3 Kubernetes Version**
- Latest stable? (Currently ~1.29.x)
- Or specific version?

---

## 9. Additional Preferences

**9.1 AD Domain Name**
- Planned: `hrmsmrflrii.xyz` (matches your existing domain)
- **Confirm this is correct**
- Note: This will be a NEW AD forest, separate from any existing cloud-only Entra ID

**9.2 OU Structure Preference**
- [ ] Use Microsoft's tiered admin model (Tier 0/1/2)
- [ ] Custom OU structure (describe below)

**9.3 Test Users**
- How many dummy users per department? (Suggestion: 5-10)
- Which departments?
  - IT
  - HR
  - Finance
  - Engineering
  - Sales
  - Marketing
  - Executive

**9.4 Remote Desktop Access**
For reaching on-prem VMs through the VPN tunnel:
- [ ] Use Azure Bastion as jump host → RDP through VPN tunnel
- [ ] Deploy a jump box in Azure that can reach on-prem
- [ ] Use your existing Tailscale setup
- [ ] Other preference?

---

## Quick Response Template

Copy and fill in this template:

```yaml
# VLAN 20 Network
vlan20_cidr: "192.168.20.0/24"
vlan20_gateway: "192.168.20.1"
reserved_ips_additional: []  # List any IPs not in my findings
new_vm_ip_range_start: "192.168.20.50"
new_vm_ip_range_end: "192.168.20.70"

# Hyper-V Host
windows_version: ""  # e.g., "Windows 11 Pro 23H2"
hyperv_switch_name: ""  # e.g., "External Virtual Switch"
vlan_tagging_method: ""  # e.g., "Trunk port on physical switch"
vm_storage_path: ""  # e.g., "D:\\Hyper-V\\Virtual Hard Disks"
available_ram_gb: ""  # e.g., "64"
available_cpu_cores: ""  # e.g., "16"
use_gen2_vms: true
use_secure_boot: true
use_vtpm: true

# Windows Media
win_server_2025_iso_path: ""
win_11_iso_path: ""
license_type: ""  # "evaluation" or "licensed"
timezone: "Singapore Standard Time"

# Omada VPN
gateway_model: "ER605"
gateway_firmware: "v2.20"
wan_type: ""  # "static" or "ddns"
wan_ip_or_hostname: ""

# Azure
subscription_1_id: ""
subscription_1_name: ""
subscription_2_id: ""
subscription_2_name: ""
primary_region: "southeastasia"
secondary_region: "eastasia"
naming_prefix: ""  # e.g., "hrmlab"
auth_method: ""  # "service_principal" or "cli" or "managed_identity"

# Preferences
ci_system: ""  # "github_actions" or "azure_devops"
firewall_option: ""  # "standard" | "basic" | "nsg_only" | "skip"
aks_private: false
aks_system_node_sku: "Standard_D2s_v3"
aks_user_node_sku: "Standard_D4s_v3"

# AD Configuration
ad_domain: "hrmsmrflrii.xyz"
ou_model: "tiered"  # "tiered" or "custom"
users_per_department: 5

# Remote Access
remote_access_method: ""  # "bastion_jump" | "azure_jumpbox" | "tailscale" | "other"
```

---

## What Happens After You Provide Inputs

1. **Phase 1**: I'll create a detailed IP addressing plan and get your approval
2. **Phase 2**: Create Packer templates for Windows images
3. **Phase 3**: Create Terraform modules (Hyper-V + Azure)
4. **Phase 4**: Create Ansible playbooks for all Windows configuration
5. **Phase 5**: Configure Site-to-Site VPN
6. **Phase 6**: Deploy and validate

Each phase will include documentation updates to:
- This repo (`Azure-Hybrid-Lab/docs/`)
- Obsidian vault (same structure)
- GitHub Wiki

---

*Document created: 2025-12-31*
*Last updated: 2025-12-31*
