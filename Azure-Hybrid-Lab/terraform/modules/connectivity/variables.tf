# =============================================================================
# Variables - Connectivity Module
# =============================================================================

variable "location" {
  description = "Azure region"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
}

variable "hub_vnet_config" {
  description = "Hub VNet configuration"
  type = object({
    address_space = list(string)
    subnets = map(object({
      address_prefix = string
    }))
  })
}

variable "onprem_network" {
  description = "On-premises network configuration"
  type = object({
    vlan_id       = number
    address_space = string
    gateway_ip    = string
    wan_ip        = string
    vpn_psk       = string
  })
  sensitive = true
}
