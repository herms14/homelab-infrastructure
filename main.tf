# Main Terraform configuration
# Dynamic VM deployment with auto-incrementing hostnames and IPs

# Define your VM groups here
locals {
  vm_groups = {
    # Kubernetes Control Plane Nodes - VLAN 20
    k8s-controlplane = {
      count         = 3
      starting_ip   = "192.168.20.10"
      template      = "tpl-ubuntu-24.04-cloudinit-v3"
      cores         = 2
      sockets       = 1
      memory        = 4096
      disk_size     = "50G"
      storage       = "Synology-VMDisks"
      vlan_tag      = null  # VLAN 20 is default
      gateway       = "192.168.20.1"
      nameserver    = "192.168.20.1"
    }

    # Kubernetes Worker Nodes - VLAN 20
    k8s-workernode = {
      count         = 6
      starting_ip   = "192.168.20.20"
      template      = "tpl-ubuntu-24.04-cloudinit-v3"
      cores         = 4
      sockets       = 1
      memory        = 8192
      disk_size     = "100G"
      storage       = "Synology-VMDisks"
      vlan_tag      = null  # VLAN 20 is default
      gateway       = "192.168.20.1"
      nameserver    = "192.168.20.1"
    }

    # Docker Media Server - VLAN 40
    docker-media = {
      count         = 1
      starting_ip   = "192.168.40.10"
      template      = "tpl-ubuntu-24.04-cloudinit-v3"
      cores         = 4
      sockets       = 1
      memory        = 8192
      disk_size     = "100G"
      storage       = "Synology-VMDisks"
      vlan_tag      = 40
      gateway       = "192.168.40.1"
      nameserver    = "192.168.40.1"
    }

    # Docker Utilities Server - VLAN 40
    docker-utilities = {
      count         = 1
      starting_ip   = "192.168.40.20"
      template      = "tpl-ubuntu-24.04-cloudinit-v3"
      cores         = 4
      sockets       = 1
      memory        = 8192
      disk_size     = "100G"
      storage       = "Synology-VMDisks"
      vlan_tag      = 40
      gateway       = "192.168.40.1"
      nameserver    = "192.168.40.1"
    }

    # Linux Syslog Server - VLAN 40
    linux-syslogserver = {
      count         = 1
      starting_ip   = "192.168.40.30"
      template      = "tpl-ubuntu-24.04-cloudinit-v3"
      cores         = 2
      sockets       = 1
      memory        = 4096
      disk_size     = "50G"
      storage       = "Synology-VMDisks"
      vlan_tag      = 40
      gateway       = "192.168.40.1"
      nameserver    = "192.168.40.1"
    }

    # Ansible Master Node - VLAN 40
    ansible-master = {
      count         = 1
      starting_ip   = "192.168.40.40"
      template      = "tpl-ubuntu-24.04-cloudinit-v3"
      cores         = 2
      sockets       = 1
      memory        = 4096
      disk_size     = "50G"
      storage       = "Synology-VMDisks"
      vlan_tag      = 40
      gateway       = "192.168.40.1"
      nameserver    = "192.168.40.1"
    }
  }

  # Generate flat map of all VMs to create
  vms = flatten([
    for vm_prefix, config in local.vm_groups : [
      for i in range(1, config.count + 1) : {
        key           = "${vm_prefix}${format("%02d", i)}"
        vm_name       = "${vm_prefix}${format("%02d", i)}"
        ip_address    = join(".", concat(slice(split(".", config.starting_ip), 0, 3), [tonumber(split(".", config.starting_ip)[3]) + i - 1]))
        template      = config.template
        cores         = config.cores
        sockets       = config.sockets
        memory        = config.memory
        disk_size     = config.disk_size
        storage       = config.storage
        vlan_tag      = config.vlan_tag
        gateway       = config.gateway
        nameserver    = config.nameserver
      }
    ]
  ])

  # Convert to map for for_each
  vms_map = { for vm in local.vms : vm.key => vm }
}

# Create all VMs using for_each
module "vms" {
  source   = "./modules/linux-vm"
  for_each = local.vms_map

  # VM Identification
  vm_name       = each.value.vm_name
  target_node   = var.default_node  # VMs always deploy to node01
  template_name = each.value.template

  # Resources
  cores     = each.value.cores
  sockets   = each.value.sockets
  memory    = each.value.memory
  disk_size = each.value.disk_size

  # Storage
  storage = each.value.storage

  # Network Configuration
  network_bridge = "vmbr0"
  vlan_tag       = each.value.vlan_tag
  ip_address     = each.value.ip_address
  subnet_mask    = 24
  gateway        = each.value.gateway
  nameserver     = each.value.nameserver

  # Cloud-Init
  ci_user  = "hermes-admin"
  ssh_keys = var.ssh_public_key


  # VM Behavior
  onboot             = true
  qemu_agent_enabled = true

}
