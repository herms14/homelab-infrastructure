# =============================================================================
# Variables - Hyper-V VM Deployment
# =============================================================================

# -----------------------------------------------------------------------------
# Hyper-V Host Configuration
# -----------------------------------------------------------------------------

variable "hyperv_switch_name" {
  description = "Name of the Hyper-V virtual switch"
  type        = string
  default     = "External Switch"
}

variable "vlan_id" {
  description = "VLAN ID for VM network adapters"
  type        = number
  default     = 80
}

variable "vm_path" {
  description = "Base path for VM storage"
  type        = string
  default     = "D:\\Hyper-V\\VMs"
}

variable "vhdx_path" {
  description = "Base path for VHDX files"
  type        = string
  default     = "D:\\Hyper-V\\Virtual Hard Disks"
}

# -----------------------------------------------------------------------------
# Template Paths (from Packer builds)
# -----------------------------------------------------------------------------

variable "ws2025_template_vhdx" {
  description = "Path to Windows Server 2025 template VHDX"
  type        = string
  default     = "D:\\Hyper-V\\Packer\\WS2025-Template\\Virtual Hard Disks\\WS2025-Template.vhdx"
}

variable "win11_template_vhdx" {
  description = "Path to Windows 11 template VHDX"
  type        = string
  default     = "D:\\Hyper-V\\Packer\\Win11-Template\\Virtual Hard Disks\\Win11-Template.vhdx"
}

# -----------------------------------------------------------------------------
# Network Configuration
# -----------------------------------------------------------------------------

variable "domain_name" {
  description = "Active Directory domain name"
  type        = string
  default     = "hrmsmrflrii.xyz"
}

variable "subnet_prefix" {
  description = "Network subnet prefix"
  type        = string
  default     = "192.168.80"
}

variable "subnet_mask" {
  description = "Subnet mask"
  type        = string
  default     = "255.255.255.0"
}

variable "default_gateway" {
  description = "Default gateway IP"
  type        = string
  default     = "192.168.80.1"
}

variable "dns_servers" {
  description = "DNS servers (will be DCs after AD setup)"
  type        = list(string)
  default     = ["8.8.8.8", "1.1.1.1"]  # Temporary until DCs are configured
}

# -----------------------------------------------------------------------------
# VM Specifications
# -----------------------------------------------------------------------------

variable "server_vms" {
  description = "Windows Server 2025 VM configurations"
  type = map(object({
    hostname    = string
    ip_suffix   = number
    cpu         = number
    memory_mb   = number
    disk_gb     = number
    role        = string
    description = string
  }))
  default = {
    dc01 = {
      hostname    = "DC01"
      ip_suffix   = 2
      cpu         = 2
      memory_mb   = 4096
      disk_gb     = 60
      role        = "Domain Controller"
      description = "Primary Domain Controller"
    }
    dc02 = {
      hostname    = "DC02"
      ip_suffix   = 3
      cpu         = 2
      memory_mb   = 4096
      disk_gb     = 60
      role        = "Domain Controller"
      description = "Secondary Domain Controller"
    }
    fs01 = {
      hostname    = "FS01"
      ip_suffix   = 4
      cpu         = 2
      memory_mb   = 4096
      disk_gb     = 100
      role        = "File Server"
      description = "File Server 1"
    }
    fs02 = {
      hostname    = "FS02"
      ip_suffix   = 5
      cpu         = 2
      memory_mb   = 4096
      disk_gb     = 100
      role        = "File Server"
      description = "File Server 2"
    }
    sql01 = {
      hostname    = "SQL01"
      ip_suffix   = 6
      cpu         = 4
      memory_mb   = 8192
      disk_gb     = 120
      role        = "SQL Server"
      description = "SQL Server"
    }
    aadcon01 = {
      hostname    = "AADCON01"
      ip_suffix   = 7
      cpu         = 2
      memory_mb   = 4096
      disk_gb     = 60
      role        = "Entra Connect"
      description = "Entra ID Connect Server"
    }
    aadpp01 = {
      hostname    = "AADPP01"
      ip_suffix   = 8
      cpu         = 2
      memory_mb   = 4096
      disk_gb     = 60
      role        = "Password Protection"
      description = "Entra Password Protection Proxy 1"
    }
    aadpp02 = {
      hostname    = "AADPP02"
      ip_suffix   = 9
      cpu         = 2
      memory_mb   = 4096
      disk_gb     = 60
      role        = "Password Protection"
      description = "Entra Password Protection Proxy 2"
    }
    iis01 = {
      hostname    = "IIS01"
      ip_suffix   = 10
      cpu         = 2
      memory_mb   = 4096
      disk_gb     = 60
      role        = "Web Server"
      description = "IIS Web Server 1"
    }
    iis02 = {
      hostname    = "IIS02"
      ip_suffix   = 11
      cpu         = 2
      memory_mb   = 4096
      disk_gb     = 60
      role        = "Web Server"
      description = "IIS Web Server 2"
    }
  }
}

variable "client_vms" {
  description = "Windows 11 VM configurations"
  type = map(object({
    hostname    = string
    ip_suffix   = number
    cpu         = number
    memory_mb   = number
    disk_gb     = number
    description = string
  }))
  default = {
    client01 = {
      hostname    = "CLIENT01"
      ip_suffix   = 12
      cpu         = 2
      memory_mb   = 4096
      disk_gb     = 60
      description = "Windows 11 Workstation 1"
    }
    client02 = {
      hostname    = "CLIENT02"
      ip_suffix   = 13
      cpu         = 2
      memory_mb   = 4096
      disk_gb     = 60
      description = "Windows 11 Workstation 2"
    }
  }
}

# -----------------------------------------------------------------------------
# Credentials (sensitive)
# -----------------------------------------------------------------------------

variable "admin_username" {
  description = "Local administrator username"
  type        = string
  default     = "Administrator"
}

variable "admin_password" {
  description = "Local administrator password"
  type        = string
  sensitive   = true
}
