# Azure Hybrid Lab - Proxmox Variables

variable "proxmox_api_url" {
  description = "Proxmox API URL"
  type        = string
  default     = "https://192.168.20.20:8006"
}

variable "proxmox_api_token" {
  description = "Proxmox API token (format: user@realm!tokenid=token-secret)"
  type        = string
  sensitive   = true
}

variable "ssh_private_key_path" {
  description = "Path to SSH private key for Proxmox nodes"
  type        = string
  default     = "~/.ssh/homelab_ed25519"
}

variable "windows_iso" {
  description = "Windows Server 2022 ISO filename in ISOs storage"
  type        = string
  default     = "en-us_windows_server_2022_updated_oct_2025_x64_dvd_26e9af36.iso"
}

variable "virtio_iso" {
  description = "VirtIO drivers ISO filename in ISOs storage"
  type        = string
  default     = "virtio-win.iso"
}

variable "domain_name" {
  description = "Active Directory domain name"
  type        = string
  default     = "azurelab.local"
}

variable "vm_memory_mb" {
  description = "RAM for each VM in MB"
  type        = number
  default     = 2048
}

variable "vm_disk_size_gb" {
  description = "Disk size for each VM in GB"
  type        = number
  default     = 60
}

# Template-based deployment variables
variable "use_template" {
  description = "Clone VMs from template instead of installing from ISO"
  type        = bool
  default     = false
}

variable "vm_template_id" {
  description = "VM ID of the Windows Server 2022 template (created by Packer)"
  type        = number
  default     = 9022
}

variable "admin_password" {
  description = "Administrator password for Windows VMs"
  type        = string
  sensitive   = true
  default     = "c@llimachus14"
}
