# Proxmox Connection Variables
variable "proxmox_api_url" {
  description = "Proxmox API URL"
  type        = string
}

variable "proxmox_api_token_id" {
  description = "Proxmox API Token ID"
  type        = string
  sensitive   = true
}

variable "proxmox_api_token_secret" {
  description = "Proxmox API Token Secret"
  type        = string
  sensitive   = true
}

variable "proxmox_tls_insecure" {
  description = "Allow insecure TLS connections"
  type        = bool
  default     = true
}

# Common Infrastructure Variables
variable "default_storage" {
  description = "Default storage pool for VMs"
  type        = string
  default     = "local-lvm"
}

variable "default_node" {
  description = "Default Proxmox node for VM deployments"
  type        = string
  default     = "node01"
}

variable "lxc_node" {
  description = "Proxmox node for LXC container deployments"
  type        = string
  default     = "node02"
}

variable "default_vlan" {
  description = "Default VLAN tag (-1 for no VLAN)"
  type        = number
  default     = 20
}

variable "default_gateway" {
  description = "Default network gateway"
  type        = string
  default     = "192.168.20.1"
}

variable "default_nameserver" {
  description = "Default DNS nameserver"
  type        = string
  default     = "192.168.20.1"
}

# VLAN 40 Network Configuration
variable "vlan40_gateway" {
  description = "VLAN 40 network gateway"
  type        = string
  default     = "192.168.40.1"
}

variable "vlan40_nameserver" {
  description = "VLAN 40 DNS nameserver"
  type        = string
  default     = "192.168.40.1"
}

# SSH Configuration
variable "ssh_public_key" {
  description = "SSH public key for VM and container access"
  type        = string
  sensitive   = true
}
