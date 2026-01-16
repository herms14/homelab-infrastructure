# =============================================================================
# Windows VM Module Variables
# =============================================================================

variable "vm_name" {
  description = "Name of the VM"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for the VM NIC"
  type        = string
}

variable "private_ip_address" {
  description = "Static private IP address"
  type        = string
}

variable "vm_size" {
  description = "VM size"
  type        = string
  default     = "Standard_B2s"
}

variable "admin_username" {
  description = "Admin username"
  type        = string
  default     = "azureadmin"
}

variable "admin_password" {
  description = "Admin password"
  type        = string
  sensitive   = true
}

variable "data_disks" {
  description = "List of data disks to attach"
  type = list(object({
    name         = string
    size_gb      = number
    storage_type = optional(string, "Premium_LRS")
  }))
  default = []
}

variable "dns_servers" {
  description = "DNS servers to configure"
  type        = list(string)
  default     = []
}

variable "install_ama" {
  description = "Install Azure Monitor Agent"
  type        = bool
  default     = true
}

variable "configure_winrm" {
  description = "Configure WinRM for Ansible"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
