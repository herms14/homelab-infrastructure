# =============================================================================
# Variables - Platform Landing Zone Module
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

variable "domain_name" {
  description = "Active Directory domain name"
  type        = string
}

variable "azure_dcs" {
  description = "Azure Domain Controller configuration"
  type = list(object({
    name = string
    ip   = string
    size = string
    role = string
  }))
}

variable "identity_subnet_id" {
  description = "Subnet ID for identity resources"
  type        = string
}

variable "admin_username" {
  description = "Administrator username"
  type        = string
}

variable "admin_password" {
  description = "Administrator password"
  type        = string
  sensitive   = true
}
