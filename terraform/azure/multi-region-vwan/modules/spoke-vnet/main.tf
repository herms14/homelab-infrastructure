# =============================================================================
# Spoke VNet Module
# Creates VNet with subnets, NSGs, and VWAN hub connection
# =============================================================================

# -----------------------------------------------------------------------------
# Virtual Network
# -----------------------------------------------------------------------------
resource "azurerm_virtual_network" "spoke" {
  name                = var.vnet_name
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = var.address_space

  dns_servers = var.dns_servers

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Subnets
# -----------------------------------------------------------------------------
resource "azurerm_subnet" "subnets" {
  for_each = var.subnets

  name                 = each.key
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.spoke.name
  address_prefixes     = [each.value.address_prefix]

  # Handle subnet delegations (e.g., for SQL MI)
  dynamic "delegation" {
    for_each = each.value.delegations != null ? each.value.delegations : []
    content {
      name = "delegation-${delegation.key}"
      service_delegation {
        name = delegation.value
        actions = [
          "Microsoft.Network/virtualNetworks/subnets/join/action",
          "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
          "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action"
        ]
      }
    }
  }

  # Don't create NSG association for special subnets
  private_endpoint_network_policies_enabled     = each.key == "snet-private-endpoints" ? false : true
  private_link_service_network_policies_enabled = true
}

# -----------------------------------------------------------------------------
# Network Security Groups
# -----------------------------------------------------------------------------
resource "azurerm_network_security_group" "subnets" {
  for_each = { for k, v in var.subnets : k => v if !contains(["AzureBastionSubnet", "GatewaySubnet"], k) && v.delegations == null }

  name                = "nsg-${each.key}"
  resource_group_name = var.resource_group_name
  location            = var.location

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Default NSG Rules - Allow internal traffic, deny internet inbound
# -----------------------------------------------------------------------------
resource "azurerm_network_security_rule" "allow_vnet_inbound" {
  for_each = azurerm_network_security_group.subnets

  name                        = "Allow-VNet-Inbound"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "VirtualNetwork"
  resource_group_name         = var.resource_group_name
  network_security_group_name = each.value.name
}

resource "azurerm_network_security_rule" "allow_azureloadbalancer" {
  for_each = azurerm_network_security_group.subnets

  name                        = "Allow-AzureLoadBalancer"
  priority                    = 110
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "AzureLoadBalancer"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = each.value.name
}

resource "azurerm_network_security_rule" "deny_internet_inbound" {
  for_each = azurerm_network_security_group.subnets

  name                        = "Deny-Internet-Inbound"
  priority                    = 4096
  direction                   = "Inbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "Internet"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = each.value.name
}

resource "azurerm_network_security_rule" "allow_internet_outbound" {
  for_each = azurerm_network_security_group.subnets

  name                        = "Allow-Internet-Outbound"
  priority                    = 100
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "Internet"
  resource_group_name         = var.resource_group_name
  network_security_group_name = each.value.name
}

# -----------------------------------------------------------------------------
# NSG Associations
# -----------------------------------------------------------------------------
resource "azurerm_subnet_network_security_group_association" "subnets" {
  for_each = { for k, v in var.subnets : k => v if !contains(["AzureBastionSubnet", "GatewaySubnet"], k) && v.delegations == null }

  subnet_id                 = azurerm_subnet.subnets[each.key].id
  network_security_group_id = azurerm_network_security_group.subnets[each.key].id
}

# -----------------------------------------------------------------------------
# VWAN Hub Connection
# -----------------------------------------------------------------------------
resource "azurerm_virtual_hub_connection" "spoke" {
  count = var.vwan_hub_id != null ? 1 : 0

  name                      = "conn-${var.vnet_name}"
  virtual_hub_id            = var.vwan_hub_id
  remote_virtual_network_id = azurerm_virtual_network.spoke.id

  internet_security_enabled = true

  routing {
    associated_route_table_id = var.vwan_route_table_id
    propagated_route_table {
      route_table_ids = var.propagated_route_table_ids
      labels          = ["default"]
    }
  }
}
