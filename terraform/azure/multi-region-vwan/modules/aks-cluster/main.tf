# =============================================================================
# Private AKS Cluster Module
# Creates a private AKS cluster for lab purposes
# =============================================================================

# -----------------------------------------------------------------------------
# User-Assigned Managed Identity for AKS
# -----------------------------------------------------------------------------
resource "azurerm_user_assigned_identity" "aks" {
  name                = "id-${var.cluster_name}"
  resource_group_name = var.resource_group_name
  location            = var.location

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Role Assignments for AKS Identity
# -----------------------------------------------------------------------------
resource "azurerm_role_assignment" "aks_network_contributor" {
  scope                = var.vnet_id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_user_assigned_identity.aks.principal_id
}

resource "azurerm_role_assignment" "aks_dns_contributor" {
  count = var.private_dns_zone_id != null ? 1 : 0

  scope                = var.private_dns_zone_id
  role_definition_name = "Private DNS Zone Contributor"
  principal_id         = azurerm_user_assigned_identity.aks.principal_id
}

# -----------------------------------------------------------------------------
# Private DNS Zone for AKS API Server
# -----------------------------------------------------------------------------
resource "azurerm_private_dns_zone" "aks" {
  count = var.create_private_dns_zone ? 1 : 0

  name                = "privatelink.${var.location}.azmk8s.io"
  resource_group_name = var.resource_group_name

  tags = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "aks" {
  count = var.create_private_dns_zone ? 1 : 0

  name                  = "link-${var.cluster_name}"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.aks[0].name
  virtual_network_id    = var.vnet_id
  registration_enabled  = false

  tags = var.tags
}

# -----------------------------------------------------------------------------
# AKS Cluster
# -----------------------------------------------------------------------------
resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.cluster_name
  resource_group_name = var.resource_group_name
  location            = var.location
  dns_prefix          = var.cluster_name

  kubernetes_version = var.kubernetes_version

  # Private cluster configuration
  private_cluster_enabled             = true
  private_cluster_public_fqdn_enabled = false
  private_dns_zone_id                 = var.create_private_dns_zone ? azurerm_private_dns_zone.aks[0].id : var.private_dns_zone_id

  # Identity
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks.id]
  }

  # Default (system) node pool
  default_node_pool {
    name                = "system"
    node_count          = var.system_node_count
    vm_size             = var.system_node_size
    vnet_subnet_id      = var.node_subnet_id
    type                = "VirtualMachineScaleSets"
    enable_auto_scaling = false

    os_disk_size_gb = 30
    os_disk_type    = "Managed"

    # Node labels
    node_labels = {
      "node-role" = "system"
    }
  }

  # Network configuration
  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    network_policy      = "azure"
    load_balancer_sku   = "standard"
    outbound_type       = "loadBalancer"
    service_cidr        = var.service_cidr
    dns_service_ip      = var.dns_service_ip
    pod_cidr            = var.pod_cidr
  }

  # Azure AD integration (optional)
  dynamic "azure_active_directory_role_based_access_control" {
    for_each = var.enable_azure_rbac ? [1] : []
    content {
      managed                = true
      azure_rbac_enabled     = true
      admin_group_object_ids = var.admin_group_object_ids
    }
  }

  # Monitoring
  oms_agent {
    log_analytics_workspace_id = var.log_analytics_workspace_id
  }

  tags = var.tags

  depends_on = [
    azurerm_role_assignment.aks_network_contributor,
    azurerm_role_assignment.aks_dns_contributor
  ]
}

# -----------------------------------------------------------------------------
# User Node Pool (Workers)
# -----------------------------------------------------------------------------
resource "azurerm_kubernetes_cluster_node_pool" "user" {
  name                  = "user"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size               = var.user_node_size
  node_count            = var.user_node_count
  vnet_subnet_id        = var.node_subnet_id
  enable_auto_scaling   = var.enable_autoscaling

  min_count = var.enable_autoscaling ? var.user_node_min : null
  max_count = var.enable_autoscaling ? var.user_node_max : null

  os_disk_size_gb = 30
  os_disk_type    = "Managed"

  node_labels = {
    "node-role" = "user"
  }

  tags = var.tags
}
