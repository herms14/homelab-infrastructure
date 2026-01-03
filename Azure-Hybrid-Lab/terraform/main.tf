# =============================================================================
# Main Configuration - Azure Hybrid Lab
# =============================================================================
# Orchestrates deployment of:
# - Platform Landing Zone (FireGiants-Prod): Identity, Connectivity
# - Application Landing Zone (Nokron-Prod): AKS, Workloads
# =============================================================================

# -----------------------------------------------------------------------------
# Platform Landing Zone - Connectivity
# vWAN, VPN Gateway, Hub VNet
# -----------------------------------------------------------------------------
module "connectivity" {
  source = "./modules/connectivity"

  providers = {
    azurerm = azurerm.platform
  }

  location        = var.location
  environment     = var.environment
  project_name    = var.project_name
  tags            = var.tags
  hub_vnet_config = var.azure_hub_vnet
  onprem_network  = var.onprem_network
}

# -----------------------------------------------------------------------------
# Platform Landing Zone - Identity
# Azure DCs, Key Vault, Private DNS
# -----------------------------------------------------------------------------
module "platform_identity" {
  source = "./modules/platform-lz"

  providers = {
    azurerm = azurerm.platform
  }

  location         = var.location
  environment      = var.environment
  project_name     = var.project_name
  tags             = var.tags
  domain_name      = var.domain_name
  azure_dcs        = var.azure_dcs
  identity_subnet_id = module.connectivity.identity_subnet_id
  admin_username   = var.admin_username
  admin_password   = var.admin_password

  depends_on = [module.connectivity]
}

# -----------------------------------------------------------------------------
# Application Landing Zone
# Spoke VNet, AKS, Workload Resources
# -----------------------------------------------------------------------------
module "app_lz" {
  source = "./modules/app-lz"

  providers = {
    azurerm = azurerm.app
  }

  location          = var.location
  environment       = var.environment
  project_name      = var.project_name
  tags              = var.tags
  spoke_vnet_config = var.azure_spoke_vnet
  hub_vnet_id       = module.connectivity.hub_vnet_id
  aks_config        = var.aks_config

  depends_on = [module.connectivity]
}

# -----------------------------------------------------------------------------
# VNet Peering (Hub to Spoke)
# -----------------------------------------------------------------------------
resource "azurerm_virtual_network_peering" "hub_to_spoke" {
  provider = azurerm.platform

  name                         = "peer-hub-to-spoke"
  resource_group_name          = module.connectivity.resource_group_name
  virtual_network_name         = module.connectivity.hub_vnet_name
  remote_virtual_network_id    = module.app_lz.spoke_vnet_id
  allow_virtual_network_access = true
  allow_forwarded_traffic      = true
  allow_gateway_transit        = true

  depends_on = [module.connectivity, module.app_lz]
}

resource "azurerm_virtual_network_peering" "spoke_to_hub" {
  provider = azurerm.app

  name                         = "peer-spoke-to-hub"
  resource_group_name          = module.app_lz.resource_group_name
  virtual_network_name         = module.app_lz.spoke_vnet_name
  remote_virtual_network_id    = module.connectivity.hub_vnet_id
  allow_virtual_network_access = true
  allow_forwarded_traffic      = true
  use_remote_gateways          = true

  depends_on = [
    module.connectivity,
    module.app_lz,
    azurerm_virtual_network_peering.hub_to_spoke
  ]
}
