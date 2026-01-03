# =============================================================================
# Packer Template: Windows 11 for Hyper-V (Gen 2 with UEFI/TPM)
# =============================================================================
#
# This template creates a Windows 11 workstation image with:
# - Gen 2 VM with Secure Boot and TPM (required for Windows 11)
# - WinRM enabled for Ansible connectivity
# - PowerShell remoting configured
# - Windows Updates applied
# - Sysprep ready for cloning
#
# Usage:
#   packer init .
#   packer build -var-file="../variables.pkrvars.hcl" .
# =============================================================================

packer {
  required_version = ">= 1.9.0"

  required_plugins {
    hyperv = {
      version = ">= 1.1.0"
      source  = "github.com/hashicorp/hyperv"
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

variable "hyperv_output_path" {
  type        = string
  description = "Path to store Packer output VMs"
  default     = "D:\\Hyper-V\\Packer"
}

variable "hyperv_switch_name" {
  type        = string
  description = "Hyper-V virtual switch name"
  default     = "External Switch"
}

variable "hyperv_vlan_id" {
  type        = number
  description = "VLAN ID for the VM (0 = no tagging)"
  default     = 80
}

variable "win11_iso_path" {
  type        = string
  description = "Path to Windows 11 ISO"
}

variable "win11_iso_checksum" {
  type        = string
  description = "SHA256 checksum of the ISO"
  default     = "none"
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

variable "timezone" {
  type        = string
  description = "Windows timezone"
  default     = "Singapore Standard Time"
}

variable "locale" {
  type        = string
  description = "Windows locale"
  default     = "en-US"
}

variable "win11_product_key" {
  type        = string
  description = "Windows 11 product key (optional)"
  default     = ""
}

variable "default_memory_mb" {
  type        = number
  description = "VM memory in MB"
  default     = 4096
}

variable "default_cpu_count" {
  type        = number
  description = "Number of vCPUs"
  default     = 2
}

variable "default_disk_size" {
  type        = number
  description = "Disk size in bytes"
  default     = 64424509440  # 60GB
}

# =============================================================================
# Locals
# =============================================================================

locals {
  vm_name       = "Win11-Template"
  output_dir    = "${var.hyperv_output_path}\\${local.vm_name}"
  timestamp     = formatdate("YYYYMMDD-hhmmss", timestamp())
}

# =============================================================================
# Source: Hyper-V ISO Builder (Gen 2 with UEFI)
# =============================================================================

source "hyperv-iso" "win11" {
  # VM Settings - Gen 2
  vm_name              = local.vm_name
  generation           = 2
  cpus                 = var.default_cpu_count
  memory               = var.default_memory_mb
  disk_size            = var.default_disk_size
  disk_block_size      = 1

  # Gen 2 Security Features
  enable_secure_boot   = true
  secure_boot_template = "MicrosoftWindows"
  enable_tpm           = true

  # ISO Configuration
  iso_url              = var.win11_iso_path
  iso_checksum         = var.win11_iso_checksum

  # Network
  switch_name          = var.hyperv_switch_name
  vlan_id              = var.hyperv_vlan_id

  # Boot Configuration
  boot_wait            = "5s"
  boot_command         = ["<enter>"]

  # Secondary ISO for autounattend (Gen 2 uses CD, not floppy)
  cd_files = [
    "${path.root}/autounattend.xml",
    "${path.root}/scripts/setup-winrm.ps1",
    "${path.root}/scripts/enable-remoting.ps1"
  ]

  # WinRM Communicator
  communicator         = "winrm"
  winrm_username       = var.admin_username
  winrm_password       = var.admin_password
  winrm_timeout        = "6h"
  winrm_use_ssl        = false
  winrm_insecure       = true

  # Output
  output_directory     = local.output_dir

  # Shutdown
  shutdown_command     = "shutdown /s /t 10 /f /d p:4:1 /c \"Packer Shutdown\""
  shutdown_timeout     = "15m"

  # Skip export for template
  skip_export          = false

  # Headless mode
  headless             = true
}

# =============================================================================
# Build
# =============================================================================

build {
  name    = "windows-11"
  sources = ["source.hyperv-iso.win11"]

  # Wait for WinRM to become available
  provisioner "powershell" {
    inline = [
      "Write-Host 'WinRM is available!'",
      "Write-Host \"Hostname: $env:COMPUTERNAME\"",
      "Write-Host \"OS: $(Get-CimInstance Win32_OperatingSystem | Select-Object -ExpandProperty Caption)\""
    ]
  }

  # Configure PowerShell remoting
  provisioner "powershell" {
    script = "${path.root}/scripts/enable-remoting.ps1"
  }

  # Install Windows Updates
  provisioner "windows-update" {
    search_criteria = "IsInstalled=0"
    filters = [
      "exclude:$_.Title -like '*Preview*'",
      "include:$true"
    ]
    update_limit = 50
  }

  # Restart after updates
  provisioner "windows-restart" {
    restart_timeout = "30m"
  }

  # Final configuration
  provisioner "powershell" {
    inline = [
      # Enable Remote Desktop
      "Set-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name 'fDenyTSConnections' -Value 0",
      "Enable-NetFirewallRule -DisplayGroup 'Remote Desktop'",

      # Configure Windows Firewall for Ansible
      "Enable-NetFirewallRule -Name 'WINRM-HTTP-In-TCP'",
      "Enable-NetFirewallRule -Name 'WINRM-HTTP-In-TCP-PUBLIC'",

      # Set power plan to High Performance
      "powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",

      # Disable hibernation
      "powercfg /hibernate off",

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

  # Post-processor to create manifest
  post-processor "manifest" {
    output     = "${local.output_dir}\\manifest.json"
    strip_path = true
  }
}
