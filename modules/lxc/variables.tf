# Container Identification
variable "hostname" {
  description = "Container hostname"
  type        = string
}

variable "target_node" {
  description = "Proxmox node to deploy on"
  type        = string
}

variable "ostemplate" {
  description = "OS template to use (e.g., local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst)"
  type        = string
}

variable "unprivileged" {
  description = "Whether to create an unprivileged container"
  type        = bool
  default     = true
}

# Resources
variable "cores" {
  description = "Number of CPU cores"
  type        = number
  default     = 1
}

variable "memory" {
  description = "Memory in MB"
  type        = number
  default     = 512
}

variable "swap" {
  description = "Swap in MB"
  type        = number
  default     = 512
}

# Storage
variable "storage" {
  description = "Storage pool for container"
  type        = string
  default     = "local-lvm"
}

variable "disk_size" {
  description = "Root filesystem size"
  type        = string
  default     = "8G"
}

# Network Configuration
variable "network_bridge" {
  description = "Network bridge"
  type        = string
  default     = "vmbr0"
}

variable "vlan_tag" {
  description = "VLAN tag (null for no VLAN)"
  type        = number
  default     = null
}

variable "ip_address" {
  description = "Static IP address"
  type        = string
}

variable "subnet_mask" {
  description = "Subnet mask (CIDR notation)"
  type        = number
  default     = 24
}

variable "gateway" {
  description = "Network gateway"
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

# SSH Configuration
variable "ssh_keys" {
  description = "SSH public keys (one per line)"
  type        = string
  default     = ""
}

# Container Behavior
variable "onboot" {
  description = "Start container on boot"
  type        = bool
  default     = true
}

variable "start" {
  description = "Start container after creation"
  type        = bool
  default     = true
}

# Features
variable "nesting" {
  description = "Enable nesting (for Docker, etc.)"
  type        = bool
  default     = false
}
