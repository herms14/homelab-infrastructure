# =============================================================================
# Outputs - Connectivity Module
# =============================================================================

output "resource_group_name" {
  description = "Name of the connectivity resource group"
  value       = azurerm_resource_group.connectivity.name
}

output "resource_group_id" {
  description = "ID of the connectivity resource group"
  value       = azurerm_resource_group.connectivity.id
}

output "hub_vnet_id" {
  description = "ID of the hub virtual network"
  value       = azurerm_virtual_network.hub.id
}

output "hub_vnet_name" {
  description = "Name of the hub virtual network"
  value       = azurerm_virtual_network.hub.name
}

output "identity_subnet_id" {
  description = "ID of the identity subnet for DCs"
  value       = azurerm_subnet.hub_subnets["identity"].id
}

output "management_subnet_id" {
  description = "ID of the management subnet"
  value       = azurerm_subnet.hub_subnets["management"].id
}

output "vwan_id" {
  description = "ID of the Azure Virtual WAN"
  value       = azurerm_virtual_wan.main.id
}

output "vwan_hub_id" {
  description = "ID of the vWAN Hub"
  value       = azurerm_virtual_hub.main.id
}

output "vpn_gateway_id" {
  description = "ID of the VPN Gateway"
  value       = azurerm_vpn_gateway.main.id
}

output "vpn_gateway_public_ip" {
  description = "Public IP addresses of the VPN Gateway"
  value       = azurerm_vpn_gateway.main.bgp_settings[0].instance_0_bgp_peering_address[0].tunnel_ips
}
