# =============================================================================
# SQL Managed Instance Module Outputs
# =============================================================================

output "id" {
  description = "SQL MI resource ID"
  value       = azurerm_mssql_managed_instance.sqlmi.id
}

output "name" {
  description = "SQL MI name"
  value       = azurerm_mssql_managed_instance.sqlmi.name
}

output "fqdn" {
  description = "SQL MI FQDN"
  value       = azurerm_mssql_managed_instance.sqlmi.fqdn
}

output "connection_string" {
  description = "Connection string (without password)"
  value       = "Server=${azurerm_mssql_managed_instance.sqlmi.fqdn};Database=master;User Id=${var.admin_login};"
}

output "principal_id" {
  description = "System-assigned managed identity principal ID"
  value       = azurerm_mssql_managed_instance.sqlmi.identity[0].principal_id
}

output "private_dns_zone_id" {
  description = "Private DNS zone ID"
  value       = try(azurerm_private_dns_zone.sqlmi[0].id, null)
}
