# =============================================================================
# Variables - Azure Hybrid Lab
# =============================================================================

# -----------------------------------------------------------------------------
# Subscription Configuration
# -----------------------------------------------------------------------------
variable "platform_subscription_id" {
  description = "Subscription ID for Platform Landing Zone (FireGiants-Prod)"
  type        = string
  default     = "2212d587-1bad-4013-b605-b421b1f83c30"
}

variable "app_subscription_id" {
  description = "Subscription ID for Application Landing Zone (Nokron-Prod)"
  type        = string
  default     = "9dde5c52-88be-4608-9bee-c52d1909693f"
}

# -----------------------------------------------------------------------------
# General Configuration
# -----------------------------------------------------------------------------
variable "location" {
  description = "Primary Azure region"
  type        = string
  default     = "australiaeast"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "azurehybrid"
}

variable "domain_name" {
  description = "Active Directory domain name"
  type        = string
  default     = "hrmsmrflrii.xyz"
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Environment = "Production"
    Project     = "Azure-Hybrid-Lab"
    ManagedBy   = "Terraform"
    Owner       = "hermes-admin"
  }
}

# -----------------------------------------------------------------------------
# On-Premises Network Configuration
# -----------------------------------------------------------------------------
variable "onprem_network" {
  description = "On-premises network configuration"
  type = object({
    vlan_id         = number
    address_space   = string
    gateway_ip      = string
    wan_ip          = string
    vpn_psk         = string
  })
  default = {
    vlan_id         = 80
    address_space   = "192.168.80.0/24"
    gateway_ip      = "192.168.80.1"
    wan_ip          = "136.158.11.91"
    vpn_psk         = "" # Set via TF_VAR_onprem_network or tfvars
  }
  sensitive = true
}

# -----------------------------------------------------------------------------
# Azure Network Configuration
# -----------------------------------------------------------------------------
variable "azure_hub_vnet" {
  description = "Hub VNet configuration (Platform LZ)"
  type = object({
    address_space = list(string)
    subnets = map(object({
      address_prefix = string
    }))
  })
  default = {
    address_space = ["10.0.0.0/16"]
    subnets = {
      GatewaySubnet = {
        address_prefix = "10.0.0.0/24"
      }
      AzureFirewallSubnet = {
        address_prefix = "10.0.1.0/24"
      }
      identity = {
        address_prefix = "10.0.2.0/24"
      }
      management = {
        address_prefix = "10.0.3.0/24"
      }
    }
  }
}

variable "azure_spoke_vnet" {
  description = "Spoke VNet configuration (App LZ)"
  type = object({
    address_space = list(string)
    subnets = map(object({
      address_prefix = string
    }))
  })
  default = {
    address_space = ["10.1.0.0/16"]
    subnets = {
      aks = {
        address_prefix = "10.1.0.0/22"
      }
      appgw = {
        address_prefix = "10.1.4.0/24"
      }
      private_endpoints = {
        address_prefix = "10.1.5.0/24"
      }
      workloads = {
        address_prefix = "10.1.6.0/24"
      }
    }
  }
}

# -----------------------------------------------------------------------------
# Azure DC Configuration
# -----------------------------------------------------------------------------
variable "azure_dcs" {
  description = "Azure Domain Controller configuration"
  type = list(object({
    name    = string
    ip      = string
    size    = string
    role    = string
  }))
  default = [
    {
      name = "AZDC01"
      ip   = "10.0.2.4"
      size = "Standard_B2s"
      role = "Primary Azure DC"
    },
    {
      name = "AZDC02"
      ip   = "10.0.2.5"
      size = "Standard_B2s"
      role = "Secondary Azure DC"
    },
    {
      name = "AZRODC01"
      ip   = "10.0.2.6"
      size = "Standard_B2s"
      role = "Read-Only DC"
    },
    {
      name = "AZRODC02"
      ip   = "10.0.2.7"
      size = "Standard_B2s"
      role = "Read-Only DC"
    }
  ]
}

# -----------------------------------------------------------------------------
# AKS Configuration
# -----------------------------------------------------------------------------
variable "aks_config" {
  description = "Azure Kubernetes Service configuration"
  type = object({
    kubernetes_version   = string
    node_count           = number
    node_size            = string
    max_pods             = number
    network_plugin       = string
    private_cluster      = bool
  })
  default = {
    kubernetes_version   = "1.28"
    node_count           = 2
    node_size            = "Standard_B2s"
    max_pods             = 30
    network_plugin       = "azure"
    private_cluster      = true
  }
}

# -----------------------------------------------------------------------------
# Admin Configuration
# -----------------------------------------------------------------------------
variable "admin_username" {
  description = "Administrator username for VMs"
  type        = string
  default     = "azureadmin"
}

variable "admin_password" {
  description = "Administrator password for VMs"
  type        = string
  sensitive   = true
}
