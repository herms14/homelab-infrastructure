# Active Tasks

> Check this file BEFORE starting any work to avoid conflicts with other sessions.
> Update this file IMMEDIATELY when starting or completing work.

---

## Currently In Progress

## Azure Hybrid Lab Infrastructure Project (Proxmox)
**Started**: 2025-12-31
**Updated**: 2026-01-02
**Session**: MacBook via Tailscale

### Progress Summary

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Packer Template | ✅ Complete | Windows Server 2022 automated template |
| Phase 2: Terraform Proxmox | ✅ Complete | 12 VMs on VLAN 80 |
| Phase 3: Ansible Playbooks | ✅ Complete | Network, AD, domain join |
| Phase 4: Template Build | 🔄 In Progress | Fixed autounattend.xml, building template |
| Phase 5: Clone VMs | ⏸️ Pending | Clone from template |
| Phase 6: AD Configuration | ⏸️ Pending | After VMs configured |
| Phase 7: Azure Deployment | ⏸️ Pending | After on-prem AD ready |

### Current Status (2026-01-02)

**Packer Build Troubleshooting:**
- Fixed VLAN 80 tagging on Omada switch
- Fixed VirtIO driver paths (2k22 folder, not w2k22)
- Fixed IMAGE/NAME in autounattend.xml - now uses correct internal name:
  - Changed from: `Windows Server 2022 Datacenter (Desktop Experience)` (Display Name)
  - Changed to: `Windows Server 2022 SERVERDATACENTER` (Internal WIM Name)
- Changed CD label from `cidata` to `OEMDRV`
- Changed CD device from `ide3` to `sata2`
- WinRM static IP: 192.168.80.99 (set via FirstLogonCommands)

**ISO Image Details (from wimlib-imagex):**
| Index | Internal Name | Display Name |
|-------|---------------|--------------|
| 1 | Windows Server 2022 SERVERSTANDARDCORE | Standard |
| 2 | Windows Server 2022 SERVERSTANDARD | Standard (Desktop Experience) |
| 3 | Windows Server 2022 SERVERDATACENTERCORE | Datacenter |
| 4 | Windows Server 2022 SERVERDATACENTER | Datacenter (Desktop Experience) |

**Automated Deployment Ready:**
- Created Packer template for Windows Server 2022 with unattended installation
- All 12 VMs will be deployed to Proxmox on VLAN 80 (192.168.80.0/24)
- Terraform updated to clone from template instead of manual ISO install

### VM Deployment Plan (VLAN 80)

| VM | IP | Node | Role |
|----|-----|------|------|
| DC01 | 192.168.80.2 | node01 | Primary DC |
| DC02 | 192.168.80.3 | node02 | Secondary DC |
| FS01 | 192.168.80.4 | node01 | File Server |
| FS02 | 192.168.80.5 | node02 | File Server |
| SQL01 | 192.168.80.6 | node01 | SQL Server |
| AADCON01 | 192.168.80.7 | node02 | Entra Connect |
| AADPP01 | 192.168.80.8 | node01 | Password Protection |
| AADPP02 | 192.168.80.9 | node02 | Password Protection |
| IIS01 | 192.168.80.10 | node01 | Web Server |
| IIS02 | 192.168.80.11 | node02 | Web Server |
| CLIENT01 | 192.168.80.12 | node01 | Workstation |
| CLIENT02 | 192.168.80.13 | node02 | Workstation |

### Next Steps (Automated Deployment)

#### Step 1: Upload ISOs to Proxmox
```bash
# Upload Windows Server 2022 ISO and VirtIO drivers to Proxmox
# Via Proxmox Web UI: Datacenter > Storage > local > ISO Images > Upload
# Required:
#   - Windows Server 2022 ISO (en-us_windows_server_2022_*.iso)
#   - VirtIO drivers (virtio-win.iso)
```

#### Step 2: Build Packer Template (Ansible Controller)
```bash
ssh hermes-admin@192.168.20.30
cd ~/azure-hybrid-lab/packer/windows-server-2022-proxmox

# Copy and configure variables
cp variables.pkrvars.hcl.example variables.pkrvars.hcl
vim variables.pkrvars.hcl

# Initialize and build (30-60 min)
packer init .
packer build -var-file="variables.pkrvars.hcl" .
```

#### Step 3: Deploy VMs from Template (Terraform)
```bash
cd ~/azure-hybrid-lab/terraform/proxmox

# Clone VMs from template
terraform apply -var="use_template=true"
```

#### Step 4: Configure VMs (Ansible)
```bash
cd ~/azure-hybrid-lab/ansible

# Wait for VMs to boot, then configure
ansible-playbook -i inventory/proxmox-hosts.yml playbooks/configure-cloned-vms.yml
```

#### Step 5: Install Active Directory
```bash
ansible-playbook -i inventory/proxmox-hosts.yml playbooks/install-ad-forest.yml
# Wait 10 minutes
ansible-playbook -i inventory/proxmox-hosts.yml playbooks/promote-dc02.yml
ansible-playbook -i inventory/proxmox-hosts.yml playbooks/domain-join.yml
```

### Key Files

| Location | Purpose |
|----------|---------|
| `Azure-Hybrid-Lab/packer/windows-server-2022-proxmox/` | Packer template for Proxmox |
| `Azure-Hybrid-Lab/terraform/proxmox/` | Terraform for VM deployment |
| `Azure-Hybrid-Lab/ansible/inventory/proxmox-hosts.yml` | Ansible inventory (VLAN 80) |
| `Azure-Hybrid-Lab/ansible/playbooks/configure-cloned-vms.yml` | Post-clone configuration |

### Credentials

| Purpose | Username | Password |
|---------|----------|----------|
| Windows VMs | Administrator | c@llimachus14 |
| Domain Admin | AZURELAB\Administrator | c@llimachus14 |
| Proxmox API | terraform-deployment-user@pve!tf | (see credentials file) |

---

## Recently Completed (Last 24 Hours)

### Sentinel Bot Table Format Fix
**Completed**: 2026-01-02
**Changes**:
- Changed onboarding report to table format with colored circles
- Fixed DNS check to use Pi-hole (192.168.90.53)
- Fixed SSH key permissions for sentinel user
- Added parallel checks for faster results

---

## Interrupted Tasks (Need Resumption)

*No interrupted tasks*

---

## Notes for Next Session

- **Azure Hybrid Lab**: Ready for Packer template build on Proxmox
- **VLAN 80 Required**: Ensure VLAN 80 is configured on Proxmox bridge (vmbr0)
- **CLUSTER**: 2-node (node01, node02) + Qdevice
- Multiple Claude instances may run in parallel - always check active-tasks first
- Glance pages are protected - don't modify without permission
