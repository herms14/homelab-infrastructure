# Azure Hybrid Lab - Proxmox Deployment

Deploy Windows Server 2022 VMs to Proxmox for Active Directory lab.

## VM Inventory

| VM | VMID | Node | IP | Role |
|----|------|------|-----|------|
| DC01 | 300 | node01 | 192.168.20.60 | Primary Domain Controller |
| DC02 | 301 | node02 | 192.168.20.61 | Secondary Domain Controller |
| FS01 | 302 | node01 | 192.168.20.62 | File Server |
| FS02 | 303 | node02 | 192.168.20.63 | File Server |
| SQL01 | 304 | node01 | 192.168.20.64 | SQL Server |
| AADCON01 | 305 | node02 | 192.168.20.65 | Entra ID Connect |
| AADPP01 | 306 | node01 | 192.168.20.66 | Password Protection Proxy |
| AADPP02 | 307 | node02 | 192.168.20.67 | Password Protection Proxy |
| CLIENT01 | 308 | node01 | 192.168.20.68 | Domain Workstation |
| CLIENT02 | 309 | node02 | 192.168.20.69 | Domain Workstation |
| IIS01 | 310 | node01 | 192.168.20.70 | Web Server |
| IIS02 | 311 | node02 | 192.168.20.71 | Web Server |

**Total**: 12 VMs × 2GB RAM = 24GB RAM, 12 × 60GB = 720GB storage

## Prerequisites

1. **VirtIO drivers ISO** - Already uploaded to `ISOs:iso/virtio-win.iso`
2. **Windows Server 2022 ISO** - Already at `ISOs:iso/en-us_windows_server_2022_updated_oct_2025_x64_dvd_26e9af36.iso`
3. **Terraform** - Install if not present
4. **Network access** - Tailscale or local network to Proxmox

## Quick Start

```bash
# 1. Navigate to terraform directory
cd Azure-Hybrid-Lab/terraform/proxmox

# 2. Create terraform.tfvars (copy from example)
cp terraform.tfvars.example terraform.tfvars

# 3. Edit with your Proxmox API token
# Get token from Proxmox UI: Datacenter → Permissions → API Tokens
nano terraform.tfvars

# 4. Initialize Terraform
terraform init

# 5. Review plan
terraform plan

# 6. Deploy VMs
terraform apply
```

## Post-Deployment: Windows Installation

After Terraform creates the VMs, you need to manually install Windows:

### Step 1: Open VM Console
1. Go to Proxmox UI: https://proxmox.hrmsmrflrii.xyz
2. Select a VM (e.g., DC01)
3. Click **Console** → **noVNC** or **xterm.js**

### Step 2: Boot Windows Installer
1. Start the VM
2. Press any key to boot from CD
3. Select language and click **Install Now**
4. Choose **Windows Server 2022 Standard (Desktop Experience)**
5. Accept license → **Custom: Install Windows only**

### Step 3: Load VirtIO Drivers
When you see "Where do you want to install Windows?" with no drives:
1. Click **Load driver**
2. Click **Browse**
3. Navigate to the VirtIO CD (D:) → `vioscsi` → `2k22` → `amd64`
4. Select the driver and click **Next**
5. Now the disk should appear

### Step 4: Complete Installation
1. Select the disk and click **Next**
2. Wait for Windows to install
3. Set Administrator password
4. Log in

### Step 5: Install Guest Agent & Drivers
After Windows boots:
1. Open File Explorer → D: drive (VirtIO)
2. Run `virtio-win-guest-tools.exe` to install:
   - VirtIO drivers (network, balloon, etc.)
   - QEMU Guest Agent
3. Reboot if prompted

### Step 6: Configure Static IP
1. Open **Network and Sharing Center**
2. Click adapter → **Properties** → **IPv4**
3. Set static IP per the table above
4. DNS: 192.168.20.60 (DC01), 192.168.20.61 (DC02)
5. Gateway: 192.168.20.1

## Domain Configuration Order

Install in this order:

1. **DC01** - Install Windows, promote to Domain Controller
   - `Install-WindowsFeature AD-Domain-Services -IncludeManagementTools`
   - `Install-ADDSForest -DomainName "azurelab.local"`

2. **DC02** - Install Windows, join as additional DC
   - `Install-WindowsFeature AD-Domain-Services -IncludeManagementTools`
   - `Install-ADDSDomainController -DomainName "azurelab.local"`

3. **All other VMs** - Install Windows, join domain

## Destroy VMs

```bash
terraform destroy
```

## Files

| File | Purpose |
|------|---------|
| `main.tf` | VM resource definitions |
| `variables.tf` | Variable declarations |
| `terraform.tfvars` | Your API token (gitignored) |
| `terraform.tfvars.example` | Template for tfvars |
