# Deployment Runbook - Azure Hybrid Lab

Complete deployment guide for the Azure Hybrid Lab infrastructure.

## Prerequisites Checklist

- [ ] Windows Hyper-V host with WinRM enabled
- [ ] ISOs on D: drive (Windows Server 2025, Windows 11)
- [ ] Azure CLI authenticated (`az login`)
- [ ] Terraform installed on Ansible controller
- [ ] Ansible Controller (192.168.20.30) accessible

## Phase 1: Hyper-V VM Creation (On-Premises)

### Step 1.1: Configure Ansible Controller

```bash
# SSH to Ansible Controller
ssh hermes-admin@192.168.20.30

# Clone/Copy the Azure-Hybrid-Lab files
cd ~
mkdir -p azure-hybrid-lab
# Copy files from your local machine or git clone

# Install pywinrm
pip install pywinrm

# Create vault file
cd ~/azure-hybrid-lab/ansible
ansible-vault create group_vars/vault.yml
```

Add to vault.yml:
```yaml
vault_hyperv_password: "YourWindowsPCPassword"
vault_windows_password: "P@ssw0rd123!"
vault_domain_admin_password: "P@ssw0rd123!"
vault_safe_mode_password: "P@ssw0rd123!"
vault_azure_admin_password: "YourAzureAdminPassword!"
```

### Step 1.2: Update Inventory

Edit `ansible/inventory/hosts.yml`:
- Update `hyperv-host` IP to your Windows PC IP
- Update `ansible_user` to your Windows username

### Step 1.3: Verify Hyper-V Connectivity

```bash
cd ~/azure-hybrid-lab/ansible

# Test WinRM connection
ansible hyperv_hosts -m win_ping --ask-vault-pass
```

### Step 1.4: Create VMs on Hyper-V

```bash
# Create all 12 VMs
ansible-playbook playbooks/create-hyperv-vms.yml --ask-vault-pass

# Start VMs
ansible-playbook playbooks/start-vms.yml --ask-vault-pass
```

### Step 1.5: Manual Windows Installation

For each VM:
1. Connect to Hyper-V console
2. Complete Windows installation
3. Set Administrator password to match `vault_windows_password`
4. Enable WinRM:
   ```powershell
   Enable-PSRemoting -Force
   Set-Item WSMan:\localhost\Service\AllowUnencrypted -Value true
   Set-Item WSMan:\localhost\Service\Auth\Basic -Value true
   New-NetFirewallRule -DisplayName "WinRM HTTP" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5985
   ```

### Step 1.6: Configure Network

```bash
# Configure static IPs on all VMs
ansible-playbook playbooks/configure-network.yml --ask-vault-pass
```

## Phase 2: Active Directory Setup

### Step 2.1: Install AD Forest on DC01

```bash
ansible-playbook playbooks/install-ad-forest.yml --ask-vault-pass
```

Wait for DC01 to reboot and AD to be fully operational (~10 minutes).

### Step 2.2: Promote DC02

```bash
ansible-playbook playbooks/promote-dc02.yml --ask-vault-pass
```

### Step 2.3: Join Member Servers to Domain

```bash
ansible-playbook playbooks/domain-join.yml --ask-vault-pass
```

### Step 2.4: Verify AD

```bash
# Run from DC01
ansible DC01 -m win_shell -a "Get-ADDomain" --ask-vault-pass
ansible DC01 -m win_shell -a "Get-ADDomainController -Filter *" --ask-vault-pass
```

## Phase 3: Azure Infrastructure

### Step 3.1: Configure Terraform

```bash
# On Ansible Controller
cd ~/azure-hybrid-lab/terraform

# Copy and configure tfvars
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars
```

Fill in:
- `admin_password`: Your Azure VM admin password
- `vpn_psk`: Your VPN pre-shared key (same as Omada config)

### Step 3.2: Deploy Azure Infrastructure

```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan -out=tfplan

# Apply (takes ~30-45 minutes for VPN Gateway)
terraform apply tfplan
```

### Step 3.3: Note VPN Gateway IP

```bash
# Get VPN Gateway public IP
terraform output vpn_gateway_public_ip
```

## Phase 4: VPN Configuration

### Step 4.1: Configure Omada ER605

See [docs/VPN_CONFIGURATION.md](docs/VPN_CONFIGURATION.md) for detailed steps.

Key settings:
- Remote Gateway: `<Azure VPN Gateway IP>`
- Pre-Shared Key: Same as Terraform `vpn_psk`
- Remote Subnets: 10.0.0.0/16, 10.1.0.0/16
- Local Networks: 192.168.80.0/24

### Step 4.2: Verify VPN Tunnel

From on-prem DC01:
```powershell
# Test connectivity to Azure
Test-NetConnection -ComputerName 10.0.2.4 -Port 3389
ping 10.0.2.4
```

## Phase 5: Azure Domain Controllers

### Step 5.1: Prepare Azure DCs

The Terraform deployment already configured WinRM on Azure DCs.

### Step 5.2: Promote Azure DCs

```bash
# On Ansible Controller
ansible-playbook playbooks/promote-azure-dcs.yml --ask-vault-pass
```

### Step 5.3: Verify Hybrid AD

```bash
# List all DCs
ansible DC01 -m win_shell -a "Get-ADDomainController -Filter * | Select Name, IPv4Address, Site" --ask-vault-pass

# Check replication
ansible DC01 -m win_shell -a "repadmin /replsummary" --ask-vault-pass
```

## Verification Commands

### On-Premises

```bash
# Test all VMs
ansible all_vms -m win_ping --ask-vault-pass

# Check domain membership
ansible member_servers -m win_shell -a "(Get-WmiObject Win32_ComputerSystem).Domain" --ask-vault-pass
```

### Azure

```bash
# Check Azure DCs
ansible azure_dcs -m win_ping --ask-vault-pass

# Verify AD replication
ansible AZDC01 -m win_shell -a "repadmin /showrepl" --ask-vault-pass
```

## Resource Summary

### On-Premises (VLAN 80)

| VM | IP | Role |
|----|-----|------|
| DC01 | 192.168.80.2 | Primary DC |
| DC02 | 192.168.80.3 | Secondary DC |
| FS01 | 192.168.80.4 | File Server |
| FS02 | 192.168.80.5 | File Server |
| SQL01 | 192.168.80.6 | SQL Server |
| AADCON01 | 192.168.80.7 | Entra Connect |
| AADPP01 | 192.168.80.8 | Password Protection |
| AADPP02 | 192.168.80.9 | Password Protection |
| IIS01 | 192.168.80.10 | Web Server |
| IIS02 | 192.168.80.11 | Web Server |
| CLIENT01 | 192.168.80.12 | Windows 11 |
| CLIENT02 | 192.168.80.13 | Windows 11 |

### Azure

| VM | IP | Role |
|----|-----|------|
| AZDC01 | 10.0.2.4 | Azure Primary DC |
| AZDC02 | 10.0.2.5 | Azure Secondary DC |
| AZRODC01 | 10.0.2.6 | Azure RODC |
| AZRODC02 | 10.0.2.7 | Azure RODC |
| AKS | 10.1.0.0/22 | Kubernetes Cluster |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| WinRM connection fails | Check firewall, verify WinRM enabled |
| DNS resolution fails | Verify DNS servers on VMs point to DCs |
| VPN tunnel down | Check pre-shared key, IKE/IPsec settings |
| AD replication fails | Check sites/subnets config, VPN connectivity |
| Ansible vault error | Use `--ask-vault-pass` or set `ANSIBLE_VAULT_PASSWORD_FILE` |

## Clean Up

To destroy all resources:

```bash
# Azure resources
cd ~/azure-hybrid-lab/terraform
terraform destroy

# On-prem VMs (via Hyper-V console or playbook)
ansible-playbook playbooks/destroy-vms.yml --ask-vault-pass  # If created
```
