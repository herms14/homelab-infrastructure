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
  default     = 2
}

variable "sockets" {
  description = "Number of CPU sockets"
  type        = number
  default     = 1
}

variable "memory" {
  description = "Memory in MB"
  type        = number
  default     = 2048
}

# Storage Configuration
variable "storage" {
  description = "Storage pool"
  type        = string
}

variable "disk_size" {
  description = "Disk size (e.g., '20G')"
  type        = string
  default     = "20G"
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
  description = "VLAN tag for the network interface (omit or set to null for no VLAN)"
  type        = number
  default     = null
}

variable "ip_address" {
  description = "IP address for the VM"
  type        = string
}

variable "subnet_mask" {
  description = "Subnet mask (CIDR notation)"
  type        = number
  default     = 24
}

variable "gateway" {
  description = "Default gateway"
  type        = string
}

variable "nameserver" {
  description = "DNS nameserver"
  type        = string
  default     = "8.8.8.8"
}

variable "searchdomain" {
  description = "DNS search domain"
  type        = string
  default     = ""
}

# Cloud-Init Configuration
variable "ci_user" {
  description = "Cloud-init user name"
  type        = string
  default     = "ubuntu"
}

variable "ci_password" {
  description = "Cloud-init user password"
  type        = string
  default     = ""
  sensitive   = true
}

variable "ssh_keys" {
  description = "SSH public keys for cloud-init"
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
