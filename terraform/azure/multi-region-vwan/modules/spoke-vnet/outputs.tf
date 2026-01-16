# =============================================================================
# Spoke VNet Module Outputs
# =============================================================================

output "vnet_id" {
  description = "Virtual Network ID"
  value       = azurerm_virtual_network.spoke.id
}

output "vnet_name" {
  description = "Virtual Network name"
  value       = azurerm_virtual_network.spoke.name
}

output "subnet_ids" {
  description = "Map of subnet names to IDs"
  value       = { for k, v in azurerm_subnet.subnets : k => v.id }
}

output "nsg_ids" {
  description = "Map of NSG names to IDs"
  value       = { for k, v in azurerm_network_security_group.subnets : k => v.id }
}

output "vwan_connection_id" {
  description = "VWAN Hub connection ID"
  value       = try(azurerm_virtual_hub_connection.spoke[0].id, null)
}
