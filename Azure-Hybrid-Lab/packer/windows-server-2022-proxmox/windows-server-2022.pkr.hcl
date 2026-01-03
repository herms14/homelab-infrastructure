# =============================================================================
# Packer Template: Windows Server 2022 for Proxmox VE
# =============================================================================
#
# This template creates a Windows Server 2022 base image on Proxmox with:
# - VirtIO drivers for optimal performance
# - WinRM enabled for Ansible connectivity
# - PowerShell remoting configured
# - Cloud-init ready (via cloudbase-init)
# - Sysprep ready for cloning
#
# Prerequisites:
#   1. Windows Server 2022 ISO uploaded to Proxmox storage
#   2. VirtIO drivers ISO uploaded (virtio-win.iso)
#   3. Proxmox API token with appropriate permissions
#
# Usage:
#   cd Azure-Hybrid-Lab/packer/windows-server-2022-proxmox
#   packer init .
#   packer build -var-file="variables.pkrvars.hcl" .
# =============================================================================

packer {
  required_version = ">= 1.9.0"

  required_plugins {
    proxmox = {
      version = ">= 1.1.0"
      source  = "github.com/hashicorp/proxmox"
    }
    windows-update = {
      version = ">= 0.14.0"
      source  = "github.com/rgl/windows-update"
    }
  }
}

# =============================================================================
# Variables
# =============================================================================

variable "proxmox_api_url" {
  type        = string
  description = "Proxmox API URL (e.g., https://192.168.20.20:8006/api2/json)"
}

variable "proxmox_api_token_id" {
  type        = string
  description = "Proxmox API token ID (e.g., terraform-deployment-user@pve!tf)"
}

variable "proxmox_api_token_secret" {
  type        = string
  description = "Proxmox API token secret"
  sensitive   = true
}

variable "proxmox_node" {
  type        = string
  description = "Proxmox node to build on"
  default     = "node01"
}

variable "proxmox_storage" {
  type        = string
  description = "Storage pool for VM disks"
  default     = "local-lvm"
}

variable "proxmox_iso_storage" {
  type        = string
  description = "Storage pool for ISOs"
  default     = "local"
}

variable "ws2022_iso_file" {
  type        = string
  description = "Windows Server 2022 ISO filename on Proxmox storage"
  default     = "en-us_windows_server_2022_updated_feb_2025_x64_dvd.iso"
}

variable "virtio_iso_file" {
  type        = string
  description = "VirtIO drivers ISO filename on Proxmox storage"
  default     = "virtio-win.iso"
}

variable "vm_id" {
  type        = number
  description = "VM ID for the template"
  default     = 9022
}

variable "vm_name" {
  type        = string
  description = "VM name for the template"
  default     = "WS2022-Template"
}

variable "admin_username" {
  type        = string
  description = "Administrator username"
  default     = "Administrator"
}

variable "admin_password" {
  type        = string
  description = "Administrator password"
  sensitive   = true
}

variable "vm_cores" {
  type        = number
  description = "Number of CPU cores"
  default     = 2
}

variable "vm_memory" {
  type        = number
  description = "Memory in MB"
  default     = 4096
}

variable "vm_disk_size" {
  type        = string
  description = "Disk size (e.g., 60G)"
  default     = "60G"
}

variable "vlan_tag" {
  type        = number
  description = "VLAN tag for VM network (0 = no tagging)"
  default     = 80
}

variable "bridge" {
  type        = string
  description = "Network bridge name"
  default     = "vmbr0"
}

variable "timezone" {
  type        = string
  description = "Windows timezone"
  default     = "Singapore Standard Time"
}

variable "skip_windows_updates" {
  type        = bool
  description = "Skip Windows Updates during build (faster)"
  default     = false
}

# =============================================================================
# Locals
# =============================================================================

locals {
  timestamp = formatdate("YYYYMMDD-hhmmss", timestamp())
}

# =============================================================================
# Source: Proxmox ISO Builder
# =============================================================================

source "proxmox-iso" "ws2022" {
  # Proxmox Connection
  proxmox_url              = var.proxmox_api_url
  username                 = var.proxmox_api_token_id
  token                    = var.proxmox_api_token_secret
  insecure_skip_tls_verify = true
  node                     = var.proxmox_node

  # VM Settings
  vm_id                = var.vm_id
  vm_name              = var.vm_name
  template_description = "Windows Server 2022 Standard - Built ${local.timestamp}"

  # Hardware
  cores      = var.vm_cores
  memory     = var.vm_memory
  cpu_type   = "host"
  os         = "win10"
  bios       = "ovmf"
  machine    = "q35"
  qemu_agent = true

  # EFI Settings (required for UEFI/OVMF)
  efi_config {
    efi_storage_pool  = var.proxmox_storage
    efi_type          = "4m"
    pre_enrolled_keys = true
  }

  # Disk
  scsi_controller = "virtio-scsi-single"

  disks {
    type         = "scsi"
    disk_size    = var.vm_disk_size
    storage_pool = var.proxmox_storage
    format       = "raw"
    io_thread    = true
  }

  # Network
  network_adapters {
    model    = "virtio"
    bridge   = var.bridge
    vlan_tag = var.vlan_tag
    firewall = false
  }

  # ISO Configuration
  iso_file = "${var.proxmox_iso_storage}:iso/${var.ws2022_iso_file}"

  # Additional ISOs (VirtIO drivers + autounattend)
  additional_iso_files {
    device           = "sata1"
    iso_file         = "${var.proxmox_iso_storage}:iso/${var.virtio_iso_file}"
    unmount          = true
    iso_storage_pool = var.proxmox_iso_storage
  }

  additional_iso_files {
    device   = "sata2"
    cd_files = [
      "${path.root}/autounattend.xml",
      "${path.root}/scripts/setup-winrm.ps1",
      "${path.root}/scripts/enable-remoting.ps1",
      "${path.root}/scripts/install-virtio.ps1"
    ]
    cd_label         = "OEMDRV"
    iso_storage_pool = var.proxmox_iso_storage
    unmount          = true
  }

  # Boot Configuration (wait for Windows installer to read autounattend)
  boot_wait    = "2s"
  boot_command = ["<spacebar>"]  # Press any key to boot from CD

  # WinRM Communicator
  communicator   = "winrm"
  winrm_username = var.admin_username
  winrm_password = var.admin_password
  winrm_timeout  = "4h"
  winrm_use_ssl  = false
  winrm_insecure = true
  winrm_port     = 5985
  winrm_host     = "192.168.80.99"  # Static IP for build (configured in autounattend.xml)

  # Timeouts
  task_timeout = "30m"

  # Don't start VM after creation (it's a template)
  onboot = false
}

# =============================================================================
# Build
# =============================================================================

build {
  name    = "windows-server-2022"
  sources = ["source.proxmox-iso.ws2022"]

  # Wait for WinRM to become available
  provisioner "powershell" {
    inline = [
      "Write-Host 'WinRM is available!'",
      "Write-Host \"Hostname: $env:COMPUTERNAME\"",
      "Write-Host \"OS: $(Get-CimInstance Win32_OperatingSystem | Select-Object -ExpandProperty Caption)\""
    ]
  }

  # Install QEMU Guest Agent
  provisioner "powershell" {
    inline = [
      "Write-Host 'Installing QEMU Guest Agent...'",
      "$installer = Get-ChildItem -Path 'E:\\guest-agent\\' -Filter 'qemu-ga-x86_64.msi' -ErrorAction SilentlyContinue",
      "if ($installer) {",
      "    Start-Process msiexec.exe -ArgumentList '/i', $installer.FullName, '/quiet', '/norestart' -Wait",
      "    Write-Host 'QEMU Guest Agent installed successfully'",
      "} else {",
      "    Write-Host 'QEMU Guest Agent installer not found, skipping...'",
      "}"
    ]
  }

  # Configure PowerShell remoting
  provisioner "powershell" {
    script = "${path.root}/scripts/enable-remoting.ps1"
  }

  # Install Windows Updates (optional, can be slow)
  dynamic "provisioner" {
    labels   = ["windows-update"]
    for_each = var.skip_windows_updates ? [] : [1]
    content {
      search_criteria = "IsInstalled=0"
      filters = [
        "exclude:$_.Title -like '*Preview*'",
        "include:$true"
      ]
      update_limit = 50
    }
  }

  # Restart after updates (if updates were installed)
  dynamic "provisioner" {
    labels   = ["windows-restart"]
    for_each = var.skip_windows_updates ? [] : [1]
    content {
      restart_timeout = "30m"
    }
  }

  # Final configuration
  provisioner "powershell" {
    inline = [
      # Disable Server Manager auto-start
      "Get-ScheduledTask -TaskName ServerManager | Disable-ScheduledTask -Verbose",

      # Enable Remote Desktop
      "Set-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name 'fDenyTSConnections' -Value 0",
      "Enable-NetFirewallRule -DisplayGroup 'Remote Desktop'",

      # Configure Windows Firewall for Ansible
      "Enable-NetFirewallRule -Name 'WINRM-HTTP-In-TCP' -ErrorAction SilentlyContinue",
      "Enable-NetFirewallRule -Name 'WINRM-HTTP-In-TCP-PUBLIC' -ErrorAction SilentlyContinue",

      # Set power plan to High Performance
      "powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",

      # Disable hibernation
      "powercfg /hibernate off",

      # Enable ICMP (ping)
      "New-NetFirewallRule -DisplayName 'ICMPv4' -Protocol ICMPv4 -IcmpType 8 -Direction Inbound -Action Allow -ErrorAction SilentlyContinue",

      # Clear temp files
      "Remove-Item -Path $env:TEMP\\* -Recurse -Force -ErrorAction SilentlyContinue",
      "Remove-Item -Path C:\\Windows\\Temp\\* -Recurse -Force -ErrorAction SilentlyContinue"
    ]
  }

  # Generalize with Sysprep for cloning
  provisioner "powershell" {
    inline = [
      "Write-Host 'Running Sysprep...'",
      "& $env:SystemRoot\\System32\\Sysprep\\Sysprep.exe /generalize /oobe /shutdown /quiet"
    ]
  }
}
