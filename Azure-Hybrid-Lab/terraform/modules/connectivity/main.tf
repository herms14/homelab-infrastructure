# =============================================================================
# Connectivity Module - Azure Hybrid Lab
# =============================================================================
# Deploys:
# - Resource Group
# - Hub Virtual Network
# - Azure vWAN and vWAN Hub
# - Site-to-Site VPN to On-Premises
# =============================================================================

# -----------------------------------------------------------------------------
# Resource Group
# -----------------------------------------------------------------------------
resource "azurerm_resource_group" "connectivity" {
  name     = "rg-${var.project_name}-connectivity-${var.environment}"
  location = var.location
  tags     = var.tags
}

# -----------------------------------------------------------------------------
# Hub Virtual Network
# -----------------------------------------------------------------------------
resource "azurerm_virtual_network" "hub" {
  name                = "vnet-${var.project_name}-hub-${var.environment}"
  location            = azurerm_resource_group.connectivity.location
  resource_group_name = azurerm_resource_group.connectivity.name
  address_space       = var.hub_vnet_config.address_space
  tags                = var.tags
}

# -----------------------------------------------------------------------------
# Hub Subnets
# -----------------------------------------------------------------------------
resource "azurerm_subnet" "hub_subnets" {
  for_each = var.hub_vnet_config.subnets

  name                 = each.key
  resource_group_name  = azurerm_resource_group.connectivity.name
  virtual_network_name = azurerm_virtual_network.hub.name
  address_prefixes     = [each.value.address_prefix]
}

# -----------------------------------------------------------------------------
# Azure Virtual WAN
# -----------------------------------------------------------------------------
resource "azurerm_virtual_wan" "main" {
  name                = "vwan-${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.connectivity.name
  location            = azurerm_resource_group.connectivity.location
  tags                = var.tags

  type                           = "Standard"
  disable_vpn_encryption         = false
  allow_branch_to_branch_traffic = true
}

# -----------------------------------------------------------------------------
# vWAN Hub
# -----------------------------------------------------------------------------
resource "azurerm_virtual_hub" "main" {
  name                = "vhub-${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.connectivity.name
  location            = azurerm_resource_group.connectivity.location
  virtual_wan_id      = azurerm_virtual_wan.main.id
  address_prefix      = "10.100.0.0/23"
  tags                = var.tags
}

# -----------------------------------------------------------------------------
# VPN Gateway in vWAN Hub
# -----------------------------------------------------------------------------
resource "azurerm_vpn_gateway" "main" {
  name                = "vpngw-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.connectivity.location
  resource_group_name = azurerm_resource_group.connectivity.name
  virtual_hub_id      = azurerm_virtual_hub.main.id
  tags                = var.tags

  scale_unit = 1
}

# -----------------------------------------------------------------------------
# VPN Site (On-Premises)
# -----------------------------------------------------------------------------
resource "azurerm_vpn_site" "onprem" {
  name                = "vpnsite-onprem-${var.environment}"
  resource_group_name = azurerm_resource_group.connectivity.name
  location            = azurerm_resource_group.connectivity.location
  virtual_wan_id      = azurerm_virtual_wan.main.id
  tags                = var.tags

  address_cidrs = [var.onprem_network.address_space]

  link {
    name       = "onprem-link"
    ip_address = var.onprem_network.wan_ip
    speed_in_mbps = 100

    bgp {
      asn             = 65001
      peering_address = var.onprem_network.gateway_ip
    }
  }
}

# -----------------------------------------------------------------------------
# VPN Site Connection
# -----------------------------------------------------------------------------
resource "azurerm_vpn_gateway_connection" "onprem" {
  name               = "vpnconn-onprem-${var.environment}"
  vpn_gateway_id     = azurerm_vpn_gateway.main.id
  remote_vpn_site_id = azurerm_vpn_site.onprem.id

  vpn_link {
    name             = "onprem-link"
    vpn_site_link_id = azurerm_vpn_site.onprem.link[0].id
    shared_key       = var.onprem_network.vpn_psk
  }
}

# -----------------------------------------------------------------------------
# Hub VNet Connection to vWAN
# -----------------------------------------------------------------------------
resource "azurerm_virtual_hub_connection" "hub_vnet" {
  name                      = "vhubconn-hub-vnet"
  virtual_hub_id            = azurerm_virtual_hub.main.id
  remote_virtual_network_id = azurerm_virtual_network.hub.id

  internet_security_enabled = true
}

# -----------------------------------------------------------------------------
# Network Security Group - Identity Subnet
# -----------------------------------------------------------------------------
resource "azurerm_network_security_group" "identity" {
  name                = "nsg-identity-${var.environment}"
  location            = azurerm_resource_group.connectivity.location
  resource_group_name = azurerm_resource_group.connectivity.name
  tags                = var.tags

  # Allow AD replication from on-prem
  security_rule {
    name                       = "Allow-AD-Replication-OnPrem"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_ranges    = ["53", "88", "135", "389", "445", "464", "636", "3268", "3269", "49152-65535"]
    source_address_prefix      = var.onprem_network.address_space
    destination_address_prefix = var.hub_vnet_config.subnets["identity"].address_prefix
  }

  # Allow RDP from on-prem (management)
  security_rule {
    name                       = "Allow-RDP-OnPrem"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "3389"
    source_address_prefix      = var.onprem_network.address_space
    destination_address_prefix = var.hub_vnet_config.subnets["identity"].address_prefix
  }

  # Allow WinRM from on-prem (Ansible)
  security_rule {
    name                       = "Allow-WinRM-OnPrem"
    priority                   = 120
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = ["5985", "5986"]
    source_address_prefix      = var.onprem_network.address_space
    destination_address_prefix = var.hub_vnet_config.subnets["identity"].address_prefix
  }
}

resource "azurerm_subnet_network_security_group_association" "identity" {
  subnet_id                 = azurerm_subnet.hub_subnets["identity"].id
  network_security_group_id = azurerm_network_security_group.identity.id
}
