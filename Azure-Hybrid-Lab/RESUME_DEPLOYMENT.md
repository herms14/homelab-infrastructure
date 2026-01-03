# Resume Deployment - Azure Hybrid Lab

**Last Updated:** 2025-12-31
**Status:** VMs created, Windows installation pending

## Current Progress

- ✅ All 12 Hyper-V VMs created
- ✅ Ansible connectivity working
- ✅ Terraform and Azure CLI installed on Ansible controller
- ⏸️ Windows installation paused (switching from Server 2025 to 2022 due to ISO errors)

## VMs Created

| VM | Role | Status |
|----|------|--------|
| DC01 | Primary Domain Controller | Created |
| DC02 | Secondary Domain Controller | Created |
| FS01 | File Server | Created |
| FS02 | File Server | Created |
| SQL01 | SQL Server | Created |
| AADCON01 | Entra ID Connect | Created |
| AADPP01 | Password Protection Proxy | Created |
| AADPP02 | Password Protection Proxy | Created |
| IIS01 | IIS Web Server | Created |
| IIS02 | IIS Web Server | Created |
| CLIENT01 | Windows 11 Workstation | Created |
| CLIENT02 | Windows 11 Workstation | Created |

## Resume Commands (Run in Elevated PowerShell)

### Step 1: Update Server VMs to Windows Server 2022 ISO

```powershell
# Update all server VMs to use Windows Server 2022 ISO
$serverVMs = @('DC01','DC02','FS01','FS02','SQL01','AADCON01','AADPP01','AADPP02','IIS01','IIS02')
foreach ($vm in $serverVMs) {
    Set-VMDvdDrive -VMName $vm -Path "D:\en-us_windows_server_2022_updated_feb_2025_x64_dvd_0398a40c.iso"
    Write-Host "Updated $vm to Windows Server 2022"
}
```

### Step 2: Start VMs (DCs First)

```powershell
# Start Domain Controllers first
Start-VM -Name DC01, DC02
Start-Sleep -Seconds 30

# Start remaining servers
Start-VM -Name FS01, FS02, SQL01, AADCON01, AADPP01, AADPP02, IIS01, IIS02
Start-Sleep -Seconds 30

# Start Windows 11 clients
Start-VM -Name CLIENT01, CLIENT02

# Verify all running
Get-VM | Select Name, State | Format-Table
```

### Step 3: Install Windows on Each VM

For each VM, connect via Hyper-V Manager and complete Windows installation:
1. Select language/keyboard
2. Click "Install now"
3. Select **Windows Server 2022 Standard (Desktop Experience)**
4. Accept license terms
5. Select **Custom: Install Windows only**
6. Select the disk and click Next
7. Wait for installation to complete
8. Set Administrator password to: `c@llimachus14`
9. Enable WinRM after login:

```powershell
# Run on each VM after Windows install
Enable-PSRemoting -Force
Set-Item WSMan:\localhost\Service\AllowUnencrypted -Value true
Set-Item WSMan:\localhost\Service\Auth\Basic -Value true
New-NetFirewallRule -DisplayName "WinRM HTTP" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5985
```

### Step 4: Configure Network (via Ansible)

After all VMs have Windows installed and WinRM enabled:

```bash
# SSH to Ansible Controller
ssh hermes-admin@192.168.20.30

# Run network configuration
cd ~/azure-hybrid-lab/ansible
ansible-playbook playbooks/configure-network.yml -e @group_vars/all.yml -e @group_vars/hyperv_hosts.yml
```

### Step 5: Install Active Directory

```bash
# Install AD Forest on DC01
ansible-playbook playbooks/install-ad-forest.yml -e @group_vars/all.yml -e @group_vars/hyperv_hosts.yml

# Wait 10 minutes for AD to be fully operational

# Promote DC02 as secondary DC
ansible-playbook playbooks/promote-dc02.yml -e @group_vars/all.yml -e @group_vars/hyperv_hosts.yml

# Join member servers to domain
ansible-playbook playbooks/domain-join.yml -e @group_vars/all.yml -e @group_vars/hyperv_hosts.yml
```

## Credentials

| Purpose | Username | Password |
|---------|----------|----------|
| Windows Admin | Administrator | c@llimachus14 |
| Ansible (Hyper-V) | ansible-admin | c@llimachus14 |
| Domain Admin | HRMSMRFLRII\Administrator | c@llimachus14 |

## Files Location

- **Ansible Playbooks:** `~/azure-hybrid-lab/ansible/` (on Ansible Controller 192.168.20.30)
- **Terraform:** `~/azure-hybrid-lab/terraform/` (on Ansible Controller)
- **Local Copy:** `Azure-Hybrid-Lab/` (in this repo)

## Troubleshooting

If VMs won't start:
```powershell
Get-VM | Select Name, State, Status
```

If WinRM fails:
```powershell
# On the VM
winrm quickconfig -quiet
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
winrm set winrm/config/service/auth '@{Basic="true"}'
```

If Ansible can't connect:
```bash
# Test connectivity
ansible hyperv_hosts -m win_ping -e @group_vars/all.yml
```
