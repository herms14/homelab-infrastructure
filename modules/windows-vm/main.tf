resource "proxmox_vm_qemu" "windows_vm" {
  name        = var.vm_name
  target_node = var.target_node
  clone       = var.template_name

  # VM Settings
  cores   = var.cores
  sockets = var.sockets
  memory  = var.memory

  # Start VM on boot
  onboot = var.onboot

  # VM Agent
  agent = var.qemu_agent_enabled ? 1 : 0

  # Network Configuration
  network {
    model  = "virtio"
    bridge = var.network_bridge
    tag    = var.vlan_tag
  }

  # Disk Configuration
  disk {
    type    = "scsi"
    storage = var.storage
    size    = var.disk_size
    ssd     = var.ssd_emulation ? 1 : 0
  }

  # Windows-specific OS type
  os_type = "win10"

  # Network IP Configuration (if using cloud-init or similar)
  ipconfig0 = var.use_dhcp ? "ip=dhcp" : "ip=${var.ip_address}/${var.subnet_mask},gw=${var.gateway}"

  # Lifecycle
  lifecycle {
    ignore_changes = [
      network,
    ]
  }
}
