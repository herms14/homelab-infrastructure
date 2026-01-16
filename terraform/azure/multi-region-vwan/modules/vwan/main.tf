# =============================================================================
# Azure Virtual WAN Module
# Creates VWAN, Hubs, VPN Gateway, and VPN Site connections
# =============================================================================

# -----------------------------------------------------------------------------
# Virtual WAN
# -----------------------------------------------------------------------------
resource "azurerm_virtual_wan" "main" {
  name                = var.vwan_name
  resource_group_name = var.resource_group_name
  location            = var.location_primary
  type                = "Standard"

  allow_branch_to_branch_traffic = true

  tags = var.tags
}

# -----------------------------------------------------------------------------
# VWAN Hub - Southeast Asia
# -----------------------------------------------------------------------------
resource "azurerm_virtual_hub" "sea" {
  name                = "vhub-homelab-prod-sea"
  resource_group_name = var.resource_group_name
  location            = var.location_primary
  virtual_wan_id      = azurerm_virtual_wan.main.id
  address_prefix      = var.hub_sea_address_prefix

  tags = var.tags
}

# -----------------------------------------------------------------------------
# VWAN Hub - East Asia
# -----------------------------------------------------------------------------
resource "azurerm_virtual_hub" "eastasia" {
  name                = "vhub-homelab-prod-eas"
  resource_group_name = var.resource_group_name
  location            = var.location_secondary
  virtual_wan_id      = azurerm_virtual_wan.main.id
  address_prefix      = var.hub_eastasia_address_prefix

  tags = var.tags
}

# -----------------------------------------------------------------------------
# VPN Gateway in SEA Hub (for on-premises connection)
# -----------------------------------------------------------------------------
resource "azurerm_vpn_gateway" "sea" {
  name                = "vpngw-homelab-prod-sea"
  resource_group_name = var.resource_group_name
  location            = var.location_primary
  virtual_hub_id      = azurerm_virtual_hub.sea.id

  scale_unit = 1

  bgp_settings {
    asn         = 65515
    peer_weight = 0
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# VPN Site - On-Premises Homelab
# -----------------------------------------------------------------------------
resource "azurerm_vpn_site" "onprem" {
  name                = var.onprem_vpn_site_name
  resource_group_name = var.resource_group_name
  location            = var.location_primary
  virtual_wan_id      = azurerm_virtual_wan.main.id

  address_cidrs = var.onprem_address_spaces

  link {
    name       = "link-onprem-primary"
    ip_address = var.onprem_public_ip
    speed_in_mbps = 100
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# VPN Gateway Connection to On-Premises
# -----------------------------------------------------------------------------
resource "azurerm_vpn_gateway_connection" "onprem" {
  name               = "conn-onprem-homelab"
  vpn_gateway_id     = azurerm_vpn_gateway.sea.id
  remote_vpn_site_id = azurerm_vpn_site.onprem.id

  vpn_link {
    name             = "link-onprem-primary"
    vpn_site_link_id = azurerm_vpn_site.onprem.link[0].id
    shared_key       = var.vpn_shared_key

    ipsec_policy {
      dh_group                 = "DHGroup14"
      ike_encryption_algorithm = "AES256"
      ike_integrity_algorithm  = "SHA256"
      encryption_algorithm     = "AES256"
      integrity_algorithm      = "SHA256"
      pfs_group                = "PFS14"
      sa_data_size_kb          = 102400000
      sa_lifetime_sec          = 27000
    }
  }

  routing {
    associated_route_table = azurerm_virtual_hub.sea.default_route_table_id
    propagated_route_table {
      route_table_ids = [
        azurerm_virtual_hub.sea.default_route_table_id,
        azurerm_virtual_hub.eastasia.default_route_table_id
      ]
      labels = ["default"]
    }
  }
}

# -----------------------------------------------------------------------------
# Hub Route Table (Default) - Enable routing to on-prem from East Asia
# -----------------------------------------------------------------------------
resource "azurerm_virtual_hub_route_table_route" "onprem_to_eastasia" {
  route_table_id = azurerm_virtual_hub.eastasia.default_route_table_id

  name              = "route-to-onprem"
  destinations_type = "CIDR"
  destinations      = var.onprem_address_spaces
  next_hop_type     = "ResourceId"
  next_hop          = azurerm_vpn_gateway_connection.onprem.id
}
