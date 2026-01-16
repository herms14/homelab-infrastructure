# =============================================================================
# Multi-Region Azure Infrastructure with VWAN
# Provider Configuration
# =============================================================================
# Deploy from: ubuntu-deploy-vm (10.90.10.5) using Managed Identity
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    virtual_machine {
      delete_os_disk_on_deletion     = true
      graceful_shutdown              = false
      skip_shutdown_and_force_delete = false
    }
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }

  # Use Managed Identity when running from ubuntu-deploy-vm
  use_msi         = true
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
}

# Alias for SEA region
provider "azurerm" {
  alias = "sea"
  features {}
  use_msi         = true
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
}

# Alias for East Asia region
provider "azurerm" {
  alias = "eastasia"
  features {}
  use_msi         = true
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
}
