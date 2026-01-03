# Ansible Playbooks - Azure Hybrid Lab

All infrastructure automation runs from the **Ansible Controller** (192.168.20.30).

## Prerequisites

### On Ansible Controller
```bash
# Install pywinrm for Windows management
pip install pywinrm

# Verify connection to Hyper-V host
ansible hyperv_hosts -m win_ping
```

### On Windows Hyper-V Host
```powershell
# Enable WinRM (run as Administrator)
winrm quickconfig -quiet
Enable-PSRemoting -Force

# Configure WinRM for Ansible
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
winrm set winrm/config/service/auth '@{Basic="true"}'

# Open firewall
New-NetFirewallRule -DisplayName "WinRM HTTP" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5985
```

## Directory Structure

```
ansible/
├── ansible.cfg              # Ansible configuration
├── inventory/
│   └── hosts.yml           # All hosts (Hyper-V + VMs)
├── group_vars/
│   └── hyperv_hosts.yml    # Hyper-V host variables
├── playbooks/
│   ├── vars/
│   │   └── vms.yml         # VM definitions
│   ├── create-hyperv-vms.yml    # Create all VMs
│   ├── start-vms.yml            # Start VMs in order
│   └── (more playbooks...)
└── roles/                  # Reusable roles
```

## Playbooks

### Phase 1: VM Creation

| Playbook | Description |
|----------|-------------|
| `create-hyperv-vms.yml` | Creates all 12 VMs on Hyper-V host |
| `start-vms.yml` | Starts VMs in correct order (DCs first) |

### Usage

```bash
# From Ansible Controller
cd ~/azure-hybrid-lab/ansible

# Create VMs
ansible-playbook playbooks/create-hyperv-vms.yml

# Start VMs
ansible-playbook playbooks/start-vms.yml

# Check VM status
ansible hyperv_hosts -m win_shell -a "Get-VM | Select Name, State"
```

## VM Summary

| VM | IP | Role | Gen | CPU | RAM | Disk |
|----|-----|------|-----|-----|-----|------|
| DC01 | 192.168.80.2 | Primary DC | 1 | 2 | 4 GB | 60 GB |
| DC02 | 192.168.80.3 | Secondary DC | 1 | 2 | 4 GB | 60 GB |
| FS01 | 192.168.80.4 | File Server | 1 | 2 | 4 GB | 100 GB |
| FS02 | 192.168.80.5 | File Server | 1 | 2 | 4 GB | 100 GB |
| SQL01 | 192.168.80.6 | SQL Server | 1 | 4 | 8 GB | 120 GB |
| AADCON01 | 192.168.80.7 | Entra Connect | 1 | 2 | 4 GB | 60 GB |
| AADPP01 | 192.168.80.8 | Password Protection | 1 | 2 | 4 GB | 60 GB |
| AADPP02 | 192.168.80.9 | Password Protection | 1 | 2 | 4 GB | 60 GB |
| IIS01 | 192.168.80.10 | Web Server | 1 | 2 | 4 GB | 60 GB |
| IIS02 | 192.168.80.11 | Web Server | 1 | 2 | 4 GB | 60 GB |
| CLIENT01 | 192.168.80.12 | Windows 11 | 2 | 2 | 4 GB | 60 GB |
| CLIENT02 | 192.168.80.13 | Windows 11 | 2 | 2 | 4 GB | 60 GB |

**Total**: 26 vCPU, 52 GB RAM, 860 GB Storage

## Credentials

Create `vault.yml` with encrypted credentials:

```bash
ansible-vault create group_vars/vault.yml
```

Contents:
```yaml
vault_hyperv_password: "your_windows_password"
vault_windows_password: "P@ssw0rd123!"
```

## Network Requirements

- **VLAN 80**: 192.168.80.0/24
- **Gateway**: 192.168.80.1
- **Hyper-V Switch**: "External Switch" with VLAN 80 tagging
- **WinRM**: Port 5985 open from Ansible Controller to Hyper-V host
