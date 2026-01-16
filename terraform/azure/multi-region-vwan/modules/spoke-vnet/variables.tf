# =============================================================================
# Spoke VNet Module Variables
# =============================================================================

variable "vnet_name" {
  description = "Name of the virtual network"
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

variable "address_space" {
  description = "VNet address space"
  type        = list(string)
}

variable "subnets" {
  description = "Map of subnets to create"
  type = map(object({
    address_prefix = string
    delegations    = optional(list(string), null)
  }))
}

variable "dns_servers" {
  description = "DNS servers for the VNet"
  type        = list(string)
  default     = []
}

variable "vwan_hub_id" {
  description = "VWAN Hub ID to connect to (optional)"
  type        = string
  default     = null
}

variable "vwan_route_table_id" {
  description = "VWAN route table ID for association"
  type        = string
  default     = null
}

variable "propagated_route_table_ids" {
  description = "Route table IDs to propagate routes to"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
