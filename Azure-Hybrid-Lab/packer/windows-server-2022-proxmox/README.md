# Windows Server 2022 Packer Template for Proxmox

Automated Windows Server 2022 template creation for Proxmox VE with unattended installation.

## Features

- Fully automated Windows Server 2022 installation (no manual steps)
- VirtIO drivers pre-installed for optimal performance
- QEMU Guest Agent installed
- WinRM configured for Ansible connectivity
- Sysprep ready for cloning
- UEFI boot with Secure Boot support

## Prerequisites

### 1. Upload ISOs to Proxmox

Upload these ISOs to your Proxmox storage (default: `local`):

| ISO | Download Link | Storage Path |
|-----|--------------|--------------|
| Windows Server 2022 | [Microsoft Eval Center](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-server-2022) | `local:iso/en-us_windows_server_2022_updated_feb_2025_x64_dvd.iso` |
| VirtIO Drivers | [Fedora VirtIO](https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso) | `local:iso/virtio-win.iso` |

### 2. Install Packer on Ansible Controller

```bash
ssh hermes-admin@192.168.20.30

# Install HashiCorp repo
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install packer

# Verify
packer version
```

### 3. Configure Variables

```bash
cd ~/azure-hybrid-lab/packer/windows-server-2022-proxmox
cp variables.pkrvars.hcl.example variables.pkrvars.hcl
vim variables.pkrvars.hcl
```

Update:
- `proxmox_api_token_secret` - Your Proxmox API token
- `ws2022_iso_file` - Exact ISO filename
- `virtio_iso_file` - VirtIO ISO filename

## Build the Template

```bash
cd ~/azure-hybrid-lab/packer/windows-server-2022-proxmox

# Initialize Packer plugins
packer init .

# Validate the template
packer validate -var-file="variables.pkrvars.hcl" .

# Build the template (takes 30-60 minutes)
packer build -var-file="variables.pkrvars.hcl" .
```

### Build Time Estimate

| Phase | Duration |
|-------|----------|
| Windows Installation | 10-15 min |
| VirtIO/Agent Install | 2-3 min |
| Windows Updates (if enabled) | 20-40 min |
| Sysprep | 5 min |
| **Total (skip updates)** | **~20 min** |
| **Total (with updates)** | **~60 min** |

## After Building

The template will be created as VM ID `9022` (configurable) on the specified Proxmox node.

### Verify Template

```bash
# Check template exists
ssh root@192.168.20.20 "qm list | grep 9022"

# Convert to template (if not already)
ssh root@192.168.20.20 "qm template 9022"
```

### Clone VMs from Template

Use Terraform:

```bash
cd ~/azure-hybrid-lab/terraform/proxmox
terraform apply -var="use_template=true"
```

Or manually:

```bash
# Clone DC01 from template
ssh root@192.168.20.20 "qm clone 9022 300 --name DC01 --full"
ssh root@192.168.20.20 "qm set 300 --memory 4096"
ssh root@192.168.20.20 "qm start 300"
```

## Template Contents

After sysprep, the template includes:

| Component | Status |
|-----------|--------|
| VirtIO SCSI Driver | Installed |
| VirtIO Network Driver | Installed |
| VirtIO Balloon Driver | Installed |
| QEMU Guest Agent | Installed & Running |
| WinRM HTTP | Enabled (port 5985) |
| Remote Desktop | Enabled |
| Windows Firewall | Rules configured |
| Windows Updates | Optional (see `skip_windows_updates`) |

## Troubleshooting

### Build Fails at WinRM Connection

**Symptom**: Packer times out waiting for WinRM

**Solutions**:
1. Check VirtIO network driver loaded (console shows network)
2. Verify VLAN tag matches your network
3. Check autounattend.xml syntax
4. Increase `winrm_timeout` in template

### Windows Setup Asks for Product Key

**Symptom**: Installation pauses for key input

**Solution**: The autounattend.xml uses evaluation mode. For licensed media:
1. Add `<ProductKey>` element to autounattend.xml
2. Or use KMS activation after deployment

### VirtIO Drivers Not Loading

**Symptom**: "No drives found" during Windows setup

**Solutions**:
1. Verify VirtIO ISO is mounted as SATA1
2. Check driver paths in autounattend.xml match ISO structure
3. Use `w2k22` folder (not `2k22` or `w2k19`)

### QEMU Guest Agent Not Starting

**Symptom**: Proxmox shows "QEMU Guest Agent not running"

**Solution**:
```powershell
# On the VM
Start-Service QEMU-GA
Set-Service QEMU-GA -StartupType Automatic
```

## Files

| File | Purpose |
|------|---------|
| `windows-server-2022.pkr.hcl` | Main Packer template |
| `autounattend.xml` | Unattended Windows installation |
| `variables.pkrvars.hcl.example` | Variable template |
| `scripts/setup-winrm.ps1` | WinRM configuration |
| `scripts/enable-remoting.ps1` | PowerShell remoting |
| `scripts/install-virtio.ps1` | VirtIO driver installation |
