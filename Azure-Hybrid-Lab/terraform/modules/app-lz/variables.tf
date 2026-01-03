# =============================================================================
# Variables - Application Landing Zone Module
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

variable "spoke_vnet_config" {
  description = "Spoke VNet configuration"
  type = object({
    address_space = list(string)
    subnets = map(object({
      address_prefix = string
    }))
  })
}

variable "hub_vnet_id" {
  description = "Hub VNet ID for peering"
  type        = string
}

variable "aks_config" {
  description = "AKS configuration"
  type = object({
    kubernetes_version = string
    node_count         = number
    node_size          = string
    max_pods           = number
    network_plugin     = string
    private_cluster    = bool
  })
}
