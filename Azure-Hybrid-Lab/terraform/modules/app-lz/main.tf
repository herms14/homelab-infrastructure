# =============================================================================
# Application Landing Zone Module - Azure Hybrid Lab
# =============================================================================
# Deploys workload resources:
# - Spoke Virtual Network
# - Private AKS Cluster
# - Container Registry
# =============================================================================

# -----------------------------------------------------------------------------
# Resource Group
# -----------------------------------------------------------------------------
resource "azurerm_resource_group" "app" {
  name     = "rg-${var.project_name}-app-${var.environment}"
  location = var.location
  tags     = var.tags
}

# -----------------------------------------------------------------------------
# Spoke Virtual Network
# -----------------------------------------------------------------------------
resource "azurerm_virtual_network" "spoke" {
  name                = "vnet-${var.project_name}-spoke-${var.environment}"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  address_space       = var.spoke_vnet_config.address_space
  tags                = var.tags
}

# -----------------------------------------------------------------------------
# Spoke Subnets
# -----------------------------------------------------------------------------
resource "azurerm_subnet" "spoke_subnets" {
  for_each = var.spoke_vnet_config.subnets

  name                 = each.key
  resource_group_name  = azurerm_resource_group.app.name
  virtual_network_name = azurerm_virtual_network.spoke.name
  address_prefixes     = [each.value.address_prefix]
}

# -----------------------------------------------------------------------------
# User Assigned Identity for AKS
# -----------------------------------------------------------------------------
resource "azurerm_user_assigned_identity" "aks" {
  name                = "id-aks-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  tags                = var.tags
}

# Role assignment for AKS to manage subnet
resource "azurerm_role_assignment" "aks_network" {
  scope                = azurerm_subnet.spoke_subnets["aks"].id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_user_assigned_identity.aks.principal_id
}

# -----------------------------------------------------------------------------
# Private DNS Zone for AKS
# -----------------------------------------------------------------------------
resource "azurerm_private_dns_zone" "aks" {
  name                = "privatelink.${var.location}.azmk8s.io"
  resource_group_name = azurerm_resource_group.app.name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "aks_spoke" {
  name                  = "link-aks-spoke"
  resource_group_name   = azurerm_resource_group.app.name
  private_dns_zone_name = azurerm_private_dns_zone.aks.name
  virtual_network_id    = azurerm_virtual_network.spoke.id
  registration_enabled  = false
}

# Link to Hub VNet for DNS resolution
resource "azurerm_private_dns_zone_virtual_network_link" "aks_hub" {
  name                  = "link-aks-hub"
  resource_group_name   = azurerm_resource_group.app.name
  private_dns_zone_name = azurerm_private_dns_zone.aks.name
  virtual_network_id    = var.hub_vnet_id
  registration_enabled  = false
}

# Role assignment for AKS to manage Private DNS
resource "azurerm_role_assignment" "aks_dns" {
  scope                = azurerm_private_dns_zone.aks.id
  role_definition_name = "Private DNS Zone Contributor"
  principal_id         = azurerm_user_assigned_identity.aks.principal_id
}

# -----------------------------------------------------------------------------
# Azure Container Registry
# -----------------------------------------------------------------------------
resource "azurerm_container_registry" "main" {
  name                = "acr${var.project_name}${var.environment}"
  resource_group_name = azurerm_resource_group.app.name
  location            = azurerm_resource_group.app.location
  sku                 = "Standard"
  admin_enabled       = false
  tags                = var.tags
}

# -----------------------------------------------------------------------------
# Private AKS Cluster
# -----------------------------------------------------------------------------
resource "azurerm_kubernetes_cluster" "main" {
  name                    = "aks-${var.project_name}-${var.environment}"
  location                = azurerm_resource_group.app.location
  resource_group_name     = azurerm_resource_group.app.name
  dns_prefix              = "aks-${var.project_name}"
  kubernetes_version      = var.aks_config.kubernetes_version
  private_cluster_enabled = var.aks_config.private_cluster
  private_dns_zone_id     = azurerm_private_dns_zone.aks.id
  tags                    = var.tags

  default_node_pool {
    name                = "default"
    node_count          = var.aks_config.node_count
    vm_size             = var.aks_config.node_size
    vnet_subnet_id      = azurerm_subnet.spoke_subnets["aks"].id
    max_pods            = var.aks_config.max_pods
    enable_auto_scaling = false
    tags                = var.tags
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks.id]
  }

  network_profile {
    network_plugin    = var.aks_config.network_plugin
    network_policy    = "azure"
    load_balancer_sku = "standard"
    service_cidr      = "10.2.0.0/16"
    dns_service_ip    = "10.2.0.10"
  }

  depends_on = [
    azurerm_role_assignment.aks_network,
    azurerm_role_assignment.aks_dns
  ]
}

# Role assignment for AKS to pull from ACR
resource "azurerm_role_assignment" "aks_acr" {
  scope                            = azurerm_container_registry.main.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  skip_service_principal_aad_check = true
}

# -----------------------------------------------------------------------------
# Network Security Group - AKS Subnet
# -----------------------------------------------------------------------------
resource "azurerm_network_security_group" "aks" {
  name                = "nsg-aks-${var.environment}"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
  tags                = var.tags

  # Allow AKS management traffic
  security_rule {
    name                       = "Allow-AKS-Management"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "AzureCloud"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "aks" {
  subnet_id                 = azurerm_subnet.spoke_subnets["aks"].id
  network_security_group_id = azurerm_network_security_group.aks.id
}
