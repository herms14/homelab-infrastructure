# Azure Hybrid Lab - Proxmox Windows VMs (Clone from Template)
# ============================================================
# This version clones VMs from a pre-built Windows Server 2022 template
# created by Packer with automated OS installation.
#
# Prerequisites:
#   1. Build the template using Packer first:
#      cd ../../packer/windows-server-2022-proxmox
#      packer init .
#      packer build -var-file="variables.pkrvars.hcl" .
#
#   2. The template VM ID should match the vm_template_id variable (default: 9022)
#
# Usage:
#   terraform init
#   terraform apply -var="use_template=true"
# ============================================================

# VMs cloned from template (when use_template = true)
resource "proxmox_virtual_environment_vm" "windows_vm_from_template" {
  for_each = var.use_template ? local.all_vms : {}

  name        = each.key
  description = each.value.role
  tags        = ["windows", "azure-hybrid-lab", each.value.role]

  node_name = each.value.node
  vm_id     = each.value.vmid

  # Clone from template
  clone {
    vm_id = var.vm_template_id
    full  = true  # Full clone (not linked)
  }

  # Machine type and BIOS (inherited from template, but can override)
  machine = "q35"
  bios    = "ovmf"
  on_boot = false

  # CPU (can be customized per VM)
  cpu {
    cores   = lookup(local.vm_hardware, each.key, { cores = 2 }).cores
    sockets = 1
    type    = "host"
  }

  # Memory (can be customized per VM)
  memory {
    dedicated = lookup(local.vm_hardware, each.key, { memory = 2048 }).memory
    floating  = 0
  }

  # Network - VirtIO on VLAN 80 (Azure Hybrid Lab network)
  network_device {
    bridge  = "vmbr0"
    model   = "virtio"
    vlan_id = 80
  }

  # Guest agent
  agent {
    enabled = true
    type    = "virtio"
  }

  # Initialize with cloud-init equivalent for Windows (sysprep handles this)
  # The cloned VM will boot into OOBE and need to be configured

  initialization {
    # This works with cloud-init, but for Windows we'll use Ansible after clone
    ip_config {
      ipv4 {
        address = "${each.value.ip}/24"
        gateway = "192.168.80.1"
      }
    }
    dns {
      servers = ["192.168.80.2", "192.168.80.3"]  # DC01, DC02 after AD is up
    }
  }

  # Lifecycle
  lifecycle {
    ignore_changes = [
      initialization,  # Ignore after first boot
    ]
  }

  depends_on = [
    # Ensure template exists before cloning
  ]
}

# Hardware customization per VM role
locals {
  vm_hardware = {
    DC01     = { cores = 2, memory = 4096 }   # Domain Controller needs more RAM
    DC02     = { cores = 2, memory = 4096 }
    SQL01    = { cores = 4, memory = 8192 }   # SQL Server needs more resources
    FS01     = { cores = 2, memory = 2048 }
    FS02     = { cores = 2, memory = 2048 }
    AADCON01 = { cores = 2, memory = 4096 }   # Entra Connect is resource hungry
    AADPP01  = { cores = 2, memory = 2048 }
    AADPP02  = { cores = 2, memory = 2048 }
    IIS01    = { cores = 2, memory = 2048 }
    IIS02    = { cores = 2, memory = 2048 }
    CLIENT01 = { cores = 2, memory = 2048 }
    CLIENT02 = { cores = 2, memory = 2048 }
  }
}

# Output for template-based VMs
output "cloned_vm_info" {
  description = "Cloned Windows VM information"
  value = var.use_template ? {
    for name, vm in proxmox_virtual_environment_vm.windows_vm_from_template : name => {
      vmid = vm.vm_id
      node = vm.node_name
      ip   = local.all_vms[name].ip
      role = local.all_vms[name].role
    }
  } : {}
}

output "post_clone_instructions" {
  description = "Instructions after cloning"
  value = var.use_template ? <<-EOT
    ╔══════════════════════════════════════════════════════════════════╗
    ║           Azure Hybrid Lab - VMs Cloned from Template            ║
    ╠══════════════════════════════════════════════════════════════════╣
    ║ Template VM ID: ${var.vm_template_id}                                             ║
    ║                                                                  ║
    ║ Next Steps:                                                      ║
    ║ 1. Start all VMs (they will complete Windows OOBE/Sysprep)       ║
    ║ 2. Wait for QEMU Guest Agent to report IPs                       ║
    ║ 3. Run Ansible playbook to configure network and hostname:       ║
    ║    ansible-playbook playbooks/configure-cloned-vms.yml           ║
    ║ 4. Run AD installation playbooks                                 ║
    ╚══════════════════════════════════════════════════════════════════╝
  EOT : "Not using template cloning"
}
