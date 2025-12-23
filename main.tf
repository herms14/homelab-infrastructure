# Main Terraform configuration
# Dynamic VM deployment with auto-incrementing hostnames and IPs

# Define your VM groups here
locals {
  vm_groups = {
    # ============================================
    # Agent 1: Ansible Controller on node01
    # ============================================
    ansible-controller = {
      count         = 1
      starting_ip   = "192.168.20.30"
      target_node   = "node01"
      template      = "tpl-ubuntuv24.04-v1"
      cores         = 2
      sockets       = 1
      memory        = 8192   # 8GB
      disk_size     = "20G"
      storage       = "VMDisks"
      vlan_tag      = null   # VLAN 20
      gateway       = "192.168.20.1"
      nameserver    = "192.168.20.1"
    }

    # ============================================
    # Agent 2: Kubernetes Infrastructure on node03
    # ============================================
    k8s-controller = {
      count         = 3
      starting_ip   = "192.168.20.32"
      target_node   = "node01"
      template      = "tpl-ubuntuv24.04-v1"
      cores         = 2
      sockets       = 1
      memory        = 8192   # 8GB
      disk_size     = "20G"
      storage       = "VMDisks"
      vlan_tag      = null   # VLAN 20
      gateway       = "192.168.20.1"
      nameserver    = "192.168.20.1"
    }

    k8s-worker = {
      count         = 6
      starting_ip   = "192.168.20.40"
      target_node   = "node01"
      template      = "tpl-ubuntuv24.04-v1"
      cores         = 2
      sockets       = 1
      memory        = 8192   # 8GB
      disk_size     = "20G"
      storage       = "VMDisks"
      vlan_tag      = null   # VLAN 20
      gateway       = "192.168.20.1"
      nameserver    = "192.168.20.1"
    }

    # ============================================
    # Agent 3: Services on node02 - VLAN 40
    # ============================================
    linux-syslog-server = {
      count         = 1
      starting_ip   = "192.168.40.5"
      target_node   = "node02"
      template      = "tpl-ubuntu-shared-v1"
      cores         = 4
      sockets       = 2
      memory        = 8192   # 8GB
      disk_size     = "50G"
      storage       = "VMDisks"
      vlan_tag      = 40     # VLAN 40
      gateway       = "192.168.40.1"
      nameserver    = "192.168.20.1"
    }

    docker-vm-utilities = {
      count         = 1
      starting_ip   = "192.168.40.10"
      target_node   = "node02"
      template      = "tpl-ubuntu-shared-v1"
      cores         = 2
      sockets       = 1
      memory        = 12288  # 12GB
      disk_size     = "20G"
      storage       = "VMDisks"
      vlan_tag      = 40     # VLAN 40
      gateway       = "192.168.40.1"
      nameserver    = "192.168.20.1"
    }

    docker-vm-media = {
      count         = 1
      starting_ip   = "192.168.40.11"
      target_node   = "node02"
      template      = "tpl-ubuntu-shared-v1"
      cores         = 2
      sockets       = 1
      memory        = 12288  # 12GB
      disk_size     = "100G"
      storage       = "VMDisks"
      vlan_tag      = 40     # VLAN 40
      gateway       = "192.168.40.1"
      nameserver    = "192.168.20.1"
    }

    traefik-vm = {
      count         = 1
      starting_ip   = "192.168.40.20"
      target_node   = "node02"
      template      = "tpl-ubuntu-shared-v1"
      cores         = 2
      sockets       = 1
      memory        = 8192   # 8GB
      disk_size     = "20G"
      storage       = "VMDisks"
      vlan_tag      = 40     # VLAN 40
      gateway       = "192.168.40.1"
      nameserver    = "192.168.20.1"
    }

    authentik-vm = {
      count         = 1
      starting_ip   = "192.168.40.21"
      target_node   = "node02"
      template      = "tpl-ubuntu-shared-v1"
      cores         = 2
      sockets       = 1
      memory        = 8192   # 8GB
      disk_size     = "20G"
      storage       = "VMDisks"
      vlan_tag      = 40     # VLAN 40
      gateway       = "192.168.40.1"
      nameserver    = "192.168.20.1"
    }

    immich-vm = {
      count         = 1
      starting_ip   = "192.168.40.22"
      target_node   = "node02"
      template      = "tpl-ubuntu-shared-v1"
      cores         = 2
      sockets       = 1
      memory        = 8192   # 8GB
      disk_size     = "20G"
      storage       = "VMDisks"
      vlan_tag      = 40     # VLAN 40
      gateway       = "192.168.40.1"
      nameserver    = "192.168.20.1"
    }

    gitlab-vm = {
      count         = 1
      starting_ip   = "192.168.40.23"
      target_node   = "node02"
      template      = "tpl-ubuntu-shared-v1"
      cores         = 2
      sockets       = 1
      memory        = 8192   # 8GB
      disk_size     = "20G"
      storage       = "VMDisks"
      vlan_tag      = 40     # VLAN 40
      gateway       = "192.168.40.1"
      nameserver    = "192.168.20.1"
    }

    # ============================================
    # GitLab CI/CD Runner for service automation
    # ============================================
    gitlab-runner-vm = {
      count         = 1
      starting_ip   = "192.168.40.24"
      target_node   = "node02"
      template      = "tpl-ubuntu-shared-v1"
      cores         = 2
      sockets       = 1
      memory        = 2048   # 2GB - lightweight runner
      disk_size     = "20G"
      storage       = "VMDisks"
      vlan_tag      = 40     # VLAN 40
      gateway       = "192.168.40.1"
      nameserver    = "192.168.20.1"
    }
  }

  # Generate flat map of all VMs to create
  vms = flatten([
    for vm_prefix, config in local.vm_groups : [
      for i in range(1, config.count + 1) : {
        key        = "${vm_prefix}${format("%02d", i)}"
        vm_name    = "${vm_prefix}${format("%02d", i)}"
        ip_address = join(".", concat(slice(split(".", config.starting_ip), 0, 3), [tonumber(split(".", config.starting_ip)[3]) + i - 1]))
        # Target node - use fixed node if specified, otherwise use default
        target_node = can(config.target_node) ? config.target_node : (
          can(config.starting_node) ? (
            can(regex("^node(\\d+)$", config.starting_node)) ?
            "node${format("%02d", tonumber(regex("\\d+", config.starting_node)) + i - 1)}" :
            config.starting_node
          ) : var.default_node
        )
        template   = config.template
        cores      = config.cores
        sockets    = config.sockets
        memory     = config.memory
        disk_size  = config.disk_size
        storage    = config.storage
        vlan_tag   = config.vlan_tag
        gateway    = config.gateway
        nameserver = config.nameserver
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
  target_node   = each.value.target_node
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
  ci_user  = var.ci_user
  ssh_keys = var.ssh_public_key

  # VM Behavior
  onboot             = true
  qemu_agent_enabled = true

}
