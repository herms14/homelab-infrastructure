# =============================================================================
# Platform Landing Zone Module - Azure Hybrid Lab
# =============================================================================
# Deploys identity resources:
# - Azure Domain Controllers (VMs)
# - Key Vault for secrets
# - Private DNS Zones
# =============================================================================

# -----------------------------------------------------------------------------
# Resource Group
# -----------------------------------------------------------------------------
resource "azurerm_resource_group" "identity" {
  name     = "rg-${var.project_name}-identity-${var.environment}"
  location = var.location
  tags     = var.tags
}

# -----------------------------------------------------------------------------
# Key Vault for Secrets
# -----------------------------------------------------------------------------
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "identity" {
  name                        = "kv-${var.project_name}-id-${var.environment}"
  location                    = azurerm_resource_group.identity.location
  resource_group_name         = azurerm_resource_group.identity.name
  enabled_for_disk_encryption = true
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false
  sku_name                    = "standard"
  tags                        = var.tags

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    key_permissions = [
      "Get", "List", "Create", "Delete", "Update"
    ]
    secret_permissions = [
      "Get", "List", "Set", "Delete"
    ]
  }
}

# Store admin password in Key Vault
resource "azurerm_key_vault_secret" "admin_password" {
  name         = "dc-admin-password"
  value        = var.admin_password
  key_vault_id = azurerm_key_vault.identity.id
}

# -----------------------------------------------------------------------------
# Availability Set for DCs
# -----------------------------------------------------------------------------
resource "azurerm_availability_set" "dc" {
  name                         = "avset-dc-${var.environment}"
  location                     = azurerm_resource_group.identity.location
  resource_group_name          = azurerm_resource_group.identity.name
  platform_fault_domain_count  = 2
  platform_update_domain_count = 5
  managed                      = true
  tags                         = var.tags
}

# -----------------------------------------------------------------------------
# Network Interfaces for DCs
# -----------------------------------------------------------------------------
resource "azurerm_network_interface" "dc" {
  for_each = { for dc in var.azure_dcs : dc.name => dc }

  name                = "nic-${lower(each.value.name)}-${var.environment}"
  location            = azurerm_resource_group.identity.location
  resource_group_name = azurerm_resource_group.identity.name
  tags                = var.tags

  ip_configuration {
    name                          = "ipconfig1"
    subnet_id                     = var.identity_subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = each.value.ip
  }
}

# -----------------------------------------------------------------------------
# Azure Domain Controller VMs
# -----------------------------------------------------------------------------
resource "azurerm_windows_virtual_machine" "dc" {
  for_each = { for dc in var.azure_dcs : dc.name => dc }

  name                  = each.value.name
  location              = azurerm_resource_group.identity.location
  resource_group_name   = azurerm_resource_group.identity.name
  size                  = each.value.size
  admin_username        = var.admin_username
  admin_password        = var.admin_password
  availability_set_id   = azurerm_availability_set.dc.id
  network_interface_ids = [azurerm_network_interface.dc[each.key].id]
  tags                  = merge(var.tags, { Role = each.value.role })

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 127
  }

  source_image_reference {
    publisher = "MicrosoftWindowsServer"
    offer     = "WindowsServer"
    sku       = "2022-datacenter-azure-edition"
    version   = "latest"
  }

  identity {
    type = "SystemAssigned"
  }

  # Enable WinRM for Ansible
  winrm_listener {
    protocol = "Http"
  }

  # Boot diagnostics
  boot_diagnostics {
    storage_account_uri = null # Use managed storage
  }
}

# -----------------------------------------------------------------------------
# Data Disks for AD Database
# -----------------------------------------------------------------------------
resource "azurerm_managed_disk" "dc_data" {
  for_each = { for dc in var.azure_dcs : dc.name => dc }

  name                 = "disk-${lower(each.value.name)}-data"
  location             = azurerm_resource_group.identity.location
  resource_group_name  = azurerm_resource_group.identity.name
  storage_account_type = "Premium_LRS"
  create_option        = "Empty"
  disk_size_gb         = 64
  tags                 = var.tags
}

resource "azurerm_virtual_machine_data_disk_attachment" "dc_data" {
  for_each = { for dc in var.azure_dcs : dc.name => dc }

  managed_disk_id    = azurerm_managed_disk.dc_data[each.key].id
  virtual_machine_id = azurerm_windows_virtual_machine.dc[each.key].id
  lun                = 0
  caching            = "None"
}

# -----------------------------------------------------------------------------
# Private DNS Zone for AD
# -----------------------------------------------------------------------------
resource "azurerm_private_dns_zone" "ad" {
  name                = var.domain_name
  resource_group_name = azurerm_resource_group.identity.name
  tags                = var.tags
}

# -----------------------------------------------------------------------------
# VM Extension - Configure WinRM for Ansible
# -----------------------------------------------------------------------------
resource "azurerm_virtual_machine_extension" "dc_winrm" {
  for_each = { for dc in var.azure_dcs : dc.name => dc }

  name                 = "ConfigureWinRM"
  virtual_machine_id   = azurerm_windows_virtual_machine.dc[each.key].id
  publisher            = "Microsoft.Compute"
  type                 = "CustomScriptExtension"
  type_handler_version = "1.10"

  settings = <<SETTINGS
    {
      "commandToExecute": "powershell -ExecutionPolicy Unrestricted -Command \"Enable-PSRemoting -Force; Set-Item WSMan:\\localhost\\Service\\AllowUnencrypted -Value true; Set-Item WSMan:\\localhost\\Service\\Auth\\Basic -Value true; New-NetFirewallRule -DisplayName 'WinRM HTTP' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5985\""
    }
  SETTINGS

  tags = var.tags
}
