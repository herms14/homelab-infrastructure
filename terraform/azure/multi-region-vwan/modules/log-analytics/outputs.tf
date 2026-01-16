# =============================================================================
# Log Analytics Module Outputs
# =============================================================================

output "workspace_id" {
  description = "Log Analytics workspace ID"
  value       = azurerm_log_analytics_workspace.law.id
}

output "workspace_name" {
  description = "Log Analytics workspace name"
  value       = azurerm_log_analytics_workspace.law.name
}

output "workspace_customer_id" {
  description = "Log Analytics workspace customer ID"
  value       = azurerm_log_analytics_workspace.law.workspace_id
}

output "primary_shared_key" {
  description = "Log Analytics primary shared key"
  value       = azurerm_log_analytics_workspace.law.primary_shared_key
  sensitive   = true
}

output "dce_id" {
  description = "Data Collection Endpoint ID"
  value       = azurerm_monitor_data_collection_endpoint.dce.id
}

output "dcr_windows_events_id" {
  description = "Windows Events DCR ID"
  value       = azurerm_monitor_data_collection_rule.windows_events.id
}

output "dcr_windows_security_id" {
  description = "Windows Security DCR ID (for Sentinel)"
  value       = try(azurerm_monitor_data_collection_rule.windows_security[0].id, null)
}
