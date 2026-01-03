# =============================================================================
# Azure Providers - Azure Hybrid Lab
# =============================================================================
# Configures providers for both Azure subscriptions
# Run from Ansible Controller with Azure CLI authenticated
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.85"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

# -----------------------------------------------------------------------------
# Platform Landing Zone Provider (FireGiants-Prod)
# Identity, Connectivity, Management resources
# -----------------------------------------------------------------------------
provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  subscription_id = var.platform_subscription_id
  alias           = "platform"
}

# -----------------------------------------------------------------------------
# Application Landing Zone Provider (Nokron-Prod)
# Workload resources (AKS, databases, apps)
# -----------------------------------------------------------------------------
provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
  subscription_id = var.app_subscription_id
  alias           = "app"
}

# Default provider (Platform subscription)
provider "azurerm" {
  features {}
  subscription_id = var.platform_subscription_id
}

# Azure AD Provider
provider "azuread" {}
