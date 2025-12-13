terraform {
  required_providers {
    proxmox = {
      source  = "telmate/proxmox"
      version = ">=3.0.2-rc06"
    }
  }
}

resource "proxmox_lxc" "container" {
  hostname     = var.hostname
  target_node  = var.target_node
  ostemplate   = var.ostemplate
  unprivileged = var.unprivileged

  # Resources
  cores  = var.cores
  memory = var.memory
  swap   = var.swap

  # Root filesystem
  rootfs {
    storage = var.storage
    size    = var.disk_size
  }

  # Network Configuration
  network {
    name   = "eth0"
    bridge = var.network_bridge
    ip     = "${var.ip_address}/${var.subnet_mask}"
    gw     = var.gateway
    tag    = var.vlan_tag != null ? var.vlan_tag : -1
  }

  # DNS Configuration
  nameserver = var.nameserver
  searchdomain = var.searchdomain

  # SSH Keys
  ssh_public_keys = var.ssh_keys != "" ? var.ssh_keys : null

  # Container Behavior
  onboot = var.onboot
  start  = var.start

  # Features
  features {
    nesting = var.nesting
  }

  # Lifecycle
  lifecycle {
    ignore_changes = [
      network,
    ]
  }
}
