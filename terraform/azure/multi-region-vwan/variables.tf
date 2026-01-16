# =============================================================================
# Multi-Region Azure Infrastructure with VWAN
# Variables
# =============================================================================

# -----------------------------------------------------------------------------
# Azure Subscription
# -----------------------------------------------------------------------------
variable "subscription_id" {
  description = "Azure Subscription ID"
  type        = string
  default     = "2212d587-1bad-4013-b605-b421b1f83c30"
}

variable "tenant_id" {
  description = "Azure Tenant ID"
  type        = string
  default     = "b6458a9a-9661-468c-bda3-5f496727d0b0"
}

# -----------------------------------------------------------------------------
# Regions
# -----------------------------------------------------------------------------
variable "regions" {
  description = "Azure regions for deployment"
  type = object({
    primary   = string
    secondary = string
  })
  default = {
    primary   = "southeastasia"
    secondary = "eastasia"
  }
}

# -----------------------------------------------------------------------------
# Tags
# -----------------------------------------------------------------------------
variable "tags" {
  description = "Default tags for all resources"
  type        = map(string)
  default = {
    Environment = "Production"
    Project     = "Homelab-MultiRegion"
    ManagedBy   = "Terraform"
    Owner       = "hermes-admin"
  }
}

# -----------------------------------------------------------------------------
# Virtual WAN
# -----------------------------------------------------------------------------
variable "vwan_name" {
  description = "Name of the Virtual WAN"
  type        = string
  default     = "vwan-homelab-prod"
}

variable "vwan_hub_sea_address_prefix" {
  description = "Address prefix for SEA VWAN hub"
  type        = string
  default     = "10.100.0.0/23"
}

variable "vwan_hub_eastasia_address_prefix" {
  description = "Address prefix for East Asia VWAN hub"
  type        = string
  default     = "10.110.0.0/23"
}

# -----------------------------------------------------------------------------
# VPN Configuration (On-premises)
# -----------------------------------------------------------------------------
variable "onprem_vpn_site_name" {
  description = "Name of the on-premises VPN site"
  type        = string
  default     = "vpn-site-homelab-onprem"
}

variable "onprem_public_ip" {
  description = "Public IP of on-premises VPN gateway (OPNsense)"
  type        = string
  # Set via tfvars - this is your OPNsense WAN IP
}

variable "onprem_address_spaces" {
  description = "On-premises address spaces to route"
  type        = list(string)
  default = [
    "192.168.10.0/24",
    "192.168.20.0/24",
    "192.168.30.0/24",
    "192.168.40.0/24",
    "192.168.80.0/24",
    "192.168.90.0/24"
  ]
}

variable "vpn_shared_key" {
  description = "Shared key for VPN connection"
  type        = string
  sensitive   = true
}

# -----------------------------------------------------------------------------
# Existing Resources
# -----------------------------------------------------------------------------
variable "existing_identity_vnet_id" {
  description = "Resource ID of existing identity VNet (erd-shared-corp-vnet-sea)"
  type        = string
  default     = "/subscriptions/2212d587-1bad-4013-b605-b421b1f83c30/resourceGroups/erd-connectivity-sea-rg/providers/Microsoft.Network/virtualNetworks/erd-shared-corp-vnet-sea"
}

variable "existing_sentinel_law_id" {
  description = "Resource ID of existing Sentinel Log Analytics Workspace"
  type        = string
  default     = "/subscriptions/2212d587-1bad-4013-b605-b421b1f83c30/resourceGroups/rg-homelab-sentinel/providers/Microsoft.OperationalInsights/workspaces/law-homelab-sentinel"
}

# -----------------------------------------------------------------------------
# Spoke VNets - Southeast Asia
# -----------------------------------------------------------------------------
variable "vnet_app_servers_sea" {
  description = "App servers VNet configuration in SEA"
  type = object({
    name          = string
    address_space = list(string)
    subnets = map(object({
      address_prefix = string
      delegations    = optional(list(string), [])
    }))
  })
  default = {
    name          = "vnet-app-servers-prod-sea"
    address_space = ["10.11.0.0/16"]
    subnets = {
      "snet-app-servers" = {
        address_prefix = "10.11.1.0/24"
      }
      "AzureBastionSubnet" = {
        address_prefix = "10.11.2.0/26"
      }
      "snet-private-endpoints" = {
        address_prefix = "10.11.3.0/24"
      }
    }
  }
}

variable "vnet_file_servers_sea" {
  description = "File servers VNet configuration in SEA"
  type = object({
    name          = string
    address_space = list(string)
    subnets = map(object({
      address_prefix = string
      delegations    = optional(list(string), [])
    }))
  })
  default = {
    name          = "vnet-file-servers-prod-sea"
    address_space = ["10.12.0.0/16"]
    subnets = {
      "snet-file-servers" = {
        address_prefix = "10.12.1.0/24"
      }
      "snet-private-endpoints" = {
        address_prefix = "10.12.2.0/24"
      }
    }
  }
}

# -----------------------------------------------------------------------------
# Spoke VNet - East Asia
# -----------------------------------------------------------------------------
variable "vnet_servers_eastasia" {
  description = "Servers VNet configuration in East Asia"
  type = object({
    name          = string
    address_space = list(string)
    subnets = map(object({
      address_prefix = string
      delegations    = optional(list(string), [])
    }))
  })
  default = {
    name          = "vnet-servers-prod-eas"
    address_space = ["10.20.0.0/16"]
    subnets = {
      "snet-servers" = {
        address_prefix = "10.20.1.0/24"
      }
      "snet-aks-nodes" = {
        address_prefix = "10.20.4.0/22"
      }
      "snet-sqlmi" = {
        address_prefix = "10.20.8.0/24"
        delegations    = ["Microsoft.Sql/managedInstances"]
      }
      "snet-rodc" = {
        address_prefix = "10.20.10.0/24"
      }
      "AzureBastionSubnet" = {
        address_prefix = "10.20.100.0/26"
      }
      "snet-private-endpoints" = {
        address_prefix = "10.20.101.0/24"
      }
    }
  }
}

# -----------------------------------------------------------------------------
# VM Configuration
# -----------------------------------------------------------------------------
variable "vm_admin_username" {
  description = "Admin username for VMs"
  type        = string
  default     = "azureadmin"
}

variable "vm_admin_password" {
  description = "Admin password for VMs"
  type        = string
  sensitive   = true
}

variable "vm_size_default" {
  description = "Default VM size"
  type        = string
  default     = "Standard_B2s"
}

variable "vm_size_aks_system" {
  description = "VM size for AKS system nodes"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "vm_size_aks_user" {
  description = "VM size for AKS user nodes"
  type        = string
  default     = "Standard_D2s_v3"
}

# -----------------------------------------------------------------------------
# VMs to Deploy
# -----------------------------------------------------------------------------
variable "vms_sea_app_servers" {
  description = "App server VMs in SEA"
  type = map(object({
    name       = string
    ip_address = string
    size       = optional(string)
    data_disks = optional(list(object({
      name         = string
      size_gb      = number
      storage_type = optional(string, "Premium_LRS")
    })), [])
  }))
  default = {
    "app-sea01" = {
      name       = "APP-SEA01"
      ip_address = "10.11.1.4"
    }
  }
}

variable "vms_sea_file_servers" {
  description = "File server VMs in SEA"
  type = map(object({
    name       = string
    ip_address = string
    size       = optional(string)
    data_disks = optional(list(object({
      name         = string
      size_gb      = number
      storage_type = optional(string, "Premium_LRS")
    })), [])
  }))
  default = {
    "fs-sea01" = {
      name       = "FS-SEA01"
      ip_address = "10.12.1.4"
      data_disks = [{
        name    = "data"
        size_gb = 64
      }]
    }
    "fs-sea02" = {
      name       = "FS-SEA02"
      ip_address = "10.12.1.5"
      data_disks = [{
        name    = "data"
        size_gb = 64
      }]
    }
  }
}

variable "vms_eastasia_servers" {
  description = "Server VMs in East Asia"
  type = map(object({
    name       = string
    ip_address = string
    subnet     = string
    size       = optional(string)
    data_disks = optional(list(object({
      name         = string
      size_gb      = number
      storage_type = optional(string, "Premium_LRS")
    })), [])
  }))
  default = {
    "srv-ea01" = {
      name       = "SRV-EA01"
      ip_address = "10.20.1.4"
      subnet     = "snet-servers"
    }
    "srv-ea02" = {
      name       = "SRV-EA02"
      ip_address = "10.20.1.5"
      subnet     = "snet-servers"
    }
    "app-ea01" = {
      name       = "APP-EA01"
      ip_address = "10.20.1.6"
      subnet     = "snet-servers"
    }
    "azrodc01" = {
      name       = "AZRODC01"
      ip_address = "10.20.10.4"
      subnet     = "snet-rodc"
      data_disks = [{
        name    = "ntds"
        size_gb = 32
      }]
    }
    "azrodc02" = {
      name       = "AZRODC02"
      ip_address = "10.20.10.5"
      subnet     = "snet-rodc"
      data_disks = [{
        name    = "ntds"
        size_gb = 32
      }]
    }
  }
}

# -----------------------------------------------------------------------------
# AKS Configuration
# -----------------------------------------------------------------------------
variable "aks_cluster_name" {
  description = "Name of the AKS cluster"
  type        = string
  default     = "aks-lab-prod-eas"
}

variable "aks_kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "aks_system_node_count" {
  description = "Number of system nodes"
  type        = number
  default     = 1
}

variable "aks_user_node_count" {
  description = "Number of user/worker nodes"
  type        = number
  default     = 3
}

variable "aks_service_cidr" {
  description = "Kubernetes service CIDR"
  type        = string
  default     = "10.200.0.0/16"
}

variable "aks_dns_service_ip" {
  description = "Kubernetes DNS service IP"
  type        = string
  default     = "10.200.0.10"
}

# -----------------------------------------------------------------------------
# SQL Managed Instance
# -----------------------------------------------------------------------------
variable "sqlmi_name" {
  description = "Name of SQL Managed Instance"
  type        = string
  default     = "sqlmi-lab-prod-eas"
}

variable "sqlmi_sku" {
  description = "SQL MI SKU"
  type        = string
  default     = "GP_Gen5"
}

variable "sqlmi_vcores" {
  description = "Number of vCores"
  type        = number
  default     = 4
}

variable "sqlmi_storage_gb" {
  description = "Storage size in GB"
  type        = number
  default     = 32
}

variable "sqlmi_admin_login" {
  description = "SQL MI admin login"
  type        = string
  default     = "sqladmin"
}

variable "sqlmi_admin_password" {
  description = "SQL MI admin password"
  type        = string
  sensitive   = true
}

# -----------------------------------------------------------------------------
# Log Analytics
# -----------------------------------------------------------------------------
variable "law_sea_name" {
  description = "Log Analytics workspace name for SEA"
  type        = string
  default     = "law-homelab-sea"
}

variable "law_eastasia_name" {
  description = "Log Analytics workspace name for East Asia"
  type        = string
  default     = "law-homelab-eas"
}

variable "law_retention_days" {
  description = "Log Analytics retention in days"
  type        = number
  default     = 30
}

# -----------------------------------------------------------------------------
# Domain Configuration
# -----------------------------------------------------------------------------
variable "domain_name" {
  description = "Active Directory domain name"
  type        = string
  default     = "hrmsmrflrii.xyz"
}

variable "domain_netbios" {
  description = "NetBIOS domain name"
  type        = string
  default     = "HRMSMRFLRII"
}

variable "domain_controllers" {
  description = "IP addresses of domain controllers"
  type        = list(string)
  default     = ["10.10.4.4", "10.10.4.5"]
}

# -----------------------------------------------------------------------------
# Feature Flags
# -----------------------------------------------------------------------------
variable "deploy_bastion" {
  description = "Deploy Azure Bastion hosts"
  type        = bool
  default     = false
}

variable "deploy_aks" {
  description = "Deploy AKS cluster"
  type        = bool
  default     = true
}

variable "deploy_sqlmi" {
  description = "Deploy SQL Managed Instance"
  type        = bool
  default     = true
}
