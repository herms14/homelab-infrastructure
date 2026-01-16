# =============================================================================
# AKS Cluster Module Variables
# =============================================================================

variable "cluster_name" {
  description = "Name of the AKS cluster"
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

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "vnet_id" {
  description = "VNet ID for role assignments"
  type        = string
}

variable "node_subnet_id" {
  description = "Subnet ID for AKS nodes"
  type        = string
}

variable "system_node_count" {
  description = "Number of system nodes"
  type        = number
  default     = 1
}

variable "system_node_size" {
  description = "VM size for system nodes"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "user_node_count" {
  description = "Number of user nodes"
  type        = number
  default     = 3
}

variable "user_node_size" {
  description = "VM size for user nodes"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "enable_autoscaling" {
  description = "Enable cluster autoscaling"
  type        = bool
  default     = false
}

variable "user_node_min" {
  description = "Minimum user nodes when autoscaling"
  type        = number
  default     = 1
}

variable "user_node_max" {
  description = "Maximum user nodes when autoscaling"
  type        = number
  default     = 5
}

variable "service_cidr" {
  description = "Kubernetes service CIDR"
  type        = string
  default     = "10.200.0.0/16"
}

variable "dns_service_ip" {
  description = "Kubernetes DNS service IP"
  type        = string
  default     = "10.200.0.10"
}

variable "pod_cidr" {
  description = "Pod CIDR for overlay networking"
  type        = string
  default     = "10.244.0.0/16"
}

variable "create_private_dns_zone" {
  description = "Create private DNS zone for AKS"
  type        = bool
  default     = true
}

variable "private_dns_zone_id" {
  description = "Existing private DNS zone ID (if not creating)"
  type        = string
  default     = null
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID for monitoring"
  type        = string
}

variable "enable_azure_rbac" {
  description = "Enable Azure RBAC for AKS"
  type        = bool
  default     = false
}

variable "admin_group_object_ids" {
  description = "Azure AD group object IDs for cluster admins"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags for resources"
  type        = map(string)
  default     = {}
}
