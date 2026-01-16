# =============================================================================
# Log Analytics Module Variables
# =============================================================================

variable "workspace_name" {
  description = "Name of the Log Analytics workspace"
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

variable "region_code" {
  description = "Region code for naming (e.g., sea, eas)"
  type        = string
}

variable "retention_days" {
  description = "Log retention in days"
  type        = number
  default     = 30
}

variable "sentinel_workspace_id" {
  description = "Sentinel LAW ID for security events (optional)"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
