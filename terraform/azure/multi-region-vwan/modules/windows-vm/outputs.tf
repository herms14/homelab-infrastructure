# =============================================================================
# Windows VM Module Outputs
# =============================================================================

output "vm_id" {
  description = "VM resource ID"
  value       = azurerm_windows_virtual_machine.vm.id
}

output "vm_name" {
  description = "VM name"
  value       = azurerm_windows_virtual_machine.vm.name
}

output "private_ip_address" {
  description = "Private IP address"
  value       = azurerm_network_interface.vm.private_ip_address
}

output "principal_id" {
  description = "System-assigned managed identity principal ID"
  value       = azurerm_windows_virtual_machine.vm.identity[0].principal_id
}

output "nic_id" {
  description = "Network interface ID"
  value       = azurerm_network_interface.vm.id
}
