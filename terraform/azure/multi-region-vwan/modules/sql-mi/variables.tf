# =============================================================================
# SQL Managed Instance Module Variables
# =============================================================================

variable "name" {
  description = "Name of the SQL Managed Instance"
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
  description = "Subnet ID for SQL MI (must be delegated)"
  type        = string
}

variable "subnet_address_prefix" {
  description = "Subnet address prefix (for NSG rules)"
  type        = string
}

variable "sku_name" {
  description = "SQL MI SKU name"
  type        = string
  default     = "GP_Gen5"
}

variable "storage_size_gb" {
  description = "Storage size in GB"
  type        = number
  default     = 32
}

variable "vcores" {
  description = "Number of vCores"
  type        = number
  default     = 4
}

variable "admin_login" {
  description = "SQL admin login"
  type        = string
  default     = "sqladmin"
}

variable "admin_password" {
  description = "SQL admin password"
  type        = string
  sensitive   = true
}

variable "create_private_dns_zone" {
  description = "Create private DNS zone"
  type        = bool
  default     = true
}

variable "dns_zone_vnet_links" {
  description = "Map of VNet IDs to link to DNS zone"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
