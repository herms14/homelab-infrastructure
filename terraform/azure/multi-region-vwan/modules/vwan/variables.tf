# =============================================================================
# VWAN Module Variables
# =============================================================================

variable "vwan_name" {
  description = "Name of the Virtual WAN"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "location_primary" {
  description = "Primary location (SEA)"
  type        = string
}

variable "location_secondary" {
  description = "Secondary location (East Asia)"
  type        = string
}

variable "hub_sea_address_prefix" {
  description = "Address prefix for SEA hub"
  type        = string
}

variable "hub_eastasia_address_prefix" {
  description = "Address prefix for East Asia hub"
  type        = string
}

variable "onprem_vpn_site_name" {
  description = "Name of on-premises VPN site"
  type        = string
}

variable "onprem_public_ip" {
  description = "Public IP of on-premises VPN gateway"
  type        = string
}

variable "onprem_address_spaces" {
  description = "On-premises address spaces"
  type        = list(string)
}

variable "vpn_shared_key" {
  description = "VPN shared key"
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
