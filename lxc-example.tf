# Example LXC Container Deployment
# Uncomment and customize to deploy LXC containers

/*
locals {
  # Define your LXC container groups here
  lxc_groups = {
    # Example: Docker host containers
    docker-host = {
      count         = 2
      starting_ip   = "192.168.20.50"
      ostemplate    = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
      unprivileged  = false  # Set to false for Docker
      cores         = 2
      memory        = 2048
      swap          = 512
      disk_size     = "20G"
      storage       = "Synology-VMDisks"
      vlan_tag      = null
      gateway       = "192.168.20.1"
      nameserver    = "192.168.20.1"
      nesting       = true   # Required for Docker
    }

    # Example: Web server containers
    web-server = {
      count         = 3
      starting_ip   = "192.168.20.60"
      ostemplate    = "local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
      unprivileged  = true
      cores         = 1
      memory        = 512
      swap          = 256
      disk_size     = "8G"
      storage       = "local-lvm"
      vlan_tag      = null
      gateway       = "192.168.20.1"
      nameserver    = "192.168.20.1"
      nesting       = false
    }
  }

  # Generate flat map of all LXC containers to create
  lxc_containers = flatten([
    for lxc_prefix, config in local.lxc_groups : [
      for i in range(1, config.count + 1) : {
        key          = "${lxc_prefix}${format("%02d", i)}"
        hostname     = "${lxc_prefix}${format("%02d", i)}"
        ip_address   = join(".", concat(slice(split(".", config.starting_ip), 0, 3), [tonumber(split(".", config.starting_ip)[3]) + i - 1]))
        ostemplate   = config.ostemplate
        unprivileged = config.unprivileged
        cores        = config.cores
        memory       = config.memory
        swap         = config.swap
        disk_size    = config.disk_size
        storage      = config.storage
        vlan_tag     = config.vlan_tag
        gateway      = config.gateway
        nameserver   = config.nameserver
        nesting      = config.nesting
      }
    ]
  ])

  # Convert to map for for_each
  lxc_map = { for lxc in local.lxc_containers : lxc.key => lxc }
}

# Create all LXC containers using for_each
module "lxc" {
  source   = "./modules/lxc"
  for_each = local.lxc_map

  # Container Identification
  hostname     = each.value.hostname
  target_node  = var.lxc_node  # LXCs always deploy to node02
  ostemplate   = each.value.ostemplate
  unprivileged = each.value.unprivileged

  # Resources
  cores  = each.value.cores
  memory = each.value.memory
  swap   = each.value.swap

  # Storage
  storage   = each.value.storage
  disk_size = each.value.disk_size

  # Network Configuration
  network_bridge = "vmbr0"
  vlan_tag       = each.value.vlan_tag
  ip_address     = each.value.ip_address
  subnet_mask    = 24
  gateway        = each.value.gateway
  nameserver     = each.value.nameserver

  # SSH Keys
  ssh_keys = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAby7br+5MzyDus2fi2UFjUBZvGucN40Gxa29bgUTbfz hermes@homelab"

  # Container Behavior
  onboot  = true
  start   = true
  nesting = each.value.nesting
}

# Outputs for LXC containers
output "lxc_summary" {
  description = "Summary of all created LXC containers"
  value = {
    for key, lxc in module.lxc : key => {
      hostname = lxc.hostname
      id       = lxc.container_id
      ip       = lxc.ip_address
    }
  }
}

output "lxc_ips" {
  description = "Map of LXC hostnames to IP addresses"
  value = {
    for key, lxc in module.lxc : lxc.hostname => lxc.ip_address
  }
}
*/
