# =============================================================================
# Outputs - Platform Landing Zone Module
# =============================================================================

output "resource_group_name" {
  description = "Name of the identity resource group"
  value       = azurerm_resource_group.identity.name
}

output "resource_group_id" {
  description = "ID of the identity resource group"
  value       = azurerm_resource_group.identity.id
}

output "key_vault_id" {
  description = "ID of the Key Vault"
  value       = azurerm_key_vault.identity.id
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = azurerm_key_vault.identity.vault_uri
}

output "dc_private_ips" {
  description = "Private IP addresses of Domain Controllers"
  value       = { for k, v in azurerm_network_interface.dc : k => v.private_ip_address }
}

output "dc_vm_ids" {
  description = "VM IDs of Domain Controllers"
  value       = { for k, v in azurerm_windows_virtual_machine.dc : k => v.id }
}

output "private_dns_zone_id" {
  description = "ID of the AD Private DNS Zone"
  value       = azurerm_private_dns_zone.ad.id
}
