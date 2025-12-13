# VM Basic Configuration
variable "vm_name" {
  description = "Name of the VM"
  type        = string
}

variable "target_node" {
  description = "Proxmox node to deploy to"
  type        = string
}

variable "template_name" {
  description = "Name of the template to clone"
  type        = string
}

# VM Resources
variable "cores" {
  description = "Number of CPU cores"
  type        = number
  default     = 4
}

variable "sockets" {
  description = "Number of CPU sockets"
  type        = number
  default     = 1
}

variable "memory" {
  description = "Memory in MB"
  type        = number
  default     = 8192
}

# Storage Configuration
variable "storage" {
  description = "Storage pool"
  type        = string
}

variable "disk_size" {
  description = "Disk size (e.g., '100G')"
  type        = string
  default     = "100G"
}

variable "ssd_emulation" {
  description = "Enable SSD emulation"
  type        = bool
  default     = false
}

# Network Configuration
variable "network_bridge" {
  description = "Network bridge"
  type        = string
  default     = "vmbr0"
}

variable "vlan_tag" {
  description = "VLAN tag for the network interface"
  type        = number
  default     = -1
}

variable "use_dhcp" {
  description = "Use DHCP for network configuration"
  type        = bool
  default     = true
}

variable "ip_address" {
  description = "Static IP address for the VM (if not using DHCP)"
  type        = string
  default     = ""
}

variable "subnet_mask" {
  description = "Subnet mask (CIDR notation)"
  type        = number
  default     = 24
}

variable "gateway" {
  description = "Default gateway"
  type        = string
  default     = ""
}

# VM Behavior
variable "onboot" {
  description = "Start VM on boot"
  type        = bool
  default     = false
}

variable "qemu_agent_enabled" {
  description = "Enable QEMU guest agent"
  type        = bool
  default     = true
}
