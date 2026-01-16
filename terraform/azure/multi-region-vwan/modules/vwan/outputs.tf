# =============================================================================
# VWAN Module Outputs
# =============================================================================

output "vwan_id" {
  description = "Virtual WAN ID"
  value       = azurerm_virtual_wan.main.id
}

output "hub_sea_id" {
  description = "SEA Hub ID"
  value       = azurerm_virtual_hub.sea.id
}

output "hub_eastasia_id" {
  description = "East Asia Hub ID"
  value       = azurerm_virtual_hub.eastasia.id
}

output "hub_sea_default_route_table_id" {
  description = "SEA Hub default route table ID"
  value       = azurerm_virtual_hub.sea.default_route_table_id
}

output "hub_eastasia_default_route_table_id" {
  description = "East Asia Hub default route table ID"
  value       = azurerm_virtual_hub.eastasia.default_route_table_id
}

output "vpn_gateway_sea_id" {
  description = "VPN Gateway ID in SEA"
  value       = azurerm_vpn_gateway.sea.id
}

output "vpn_gateway_sea_public_ips" {
  description = "VPN Gateway public IPs (for OPNsense configuration)"
  value = {
    instance0 = azurerm_vpn_gateway.sea.bgp_settings[0].instance_0_bgp_peering_address[0].tunnel_ips
    instance1 = azurerm_vpn_gateway.sea.bgp_settings[0].instance_1_bgp_peering_address[0].tunnel_ips
  }
}
