resource "proxmox_vm_qemu" "linux_vm" {
  name        = var.vm_name
  target_node = var.target_node
  clone       = var.template_name

  # UEFI Boot Configuration
  bios    = "ovmf"
  machine = "q35"

  # EFI Disk (required for UEFI boot)
  efidisk {
    storage  = var.storage
    efitype  = "4m"
    pre_enrolled_keys = true
  }

  # VM Settings
  cpu {
    cores   = var.cores
    sockets = var.sockets
  }
  memory = var.memory

  # SCSI Controller (match template)
  scsihw = "virtio-scsi-single"

  # Start VM on boot
  onboot = var.onboot

  # VM Agent
  agent = var.qemu_agent_enabled ? 1 : 0

  # Network Configuration
  network {
    id     = 0
    model  = "virtio"
    bridge = var.network_bridge
    tag    = var.vlan_tag  # No default - let it be untagged if null
  }

  # Disk Configuration
  disk {
    slot    = "scsi0"
    type    = "disk"
    storage = var.storage
    size    = var.disk_size
  }

  # Cloud-Init Drive
  disk {
    slot    = "ide2"
    type    = "cloudinit"
    storage = var.storage
  }

  # Cloud-Init Configuration
  os_type   = "cloud-init"
  ciupgrade = true  # Upgrade packages on first boot

  # Network IP Configuration
  ipconfig0 = "ip=${var.ip_address}/${var.subnet_mask},gw=${var.gateway}"

  # DNS Configuration
  nameserver   = var.nameserver
  searchdomain = var.searchdomain

  # Cloud-Init User Configuration
  ciuser     = var.ci_user
  cipassword = var.ci_password
  sshkeys    = var.ssh_keys != "" ? var.ssh_keys : null
}
