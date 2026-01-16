# =============================================================================
# Windows VM Module
# Creates Windows Server 2022 VM with NIC, disks, and AMA extension
# =============================================================================

# -----------------------------------------------------------------------------
# Network Interface
# -----------------------------------------------------------------------------
resource "azurerm_network_interface" "vm" {
  name                = "nic-${lower(var.vm_name)}"
  resource_group_name = var.resource_group_name
  location            = var.location

  ip_configuration {
    name                          = "ipconfig1"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Static"
    private_ip_address            = var.private_ip_address
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Windows Virtual Machine
# -----------------------------------------------------------------------------
resource "azurerm_windows_virtual_machine" "vm" {
  name                = var.vm_name
  resource_group_name = var.resource_group_name
  location            = var.location
  size                = var.vm_size
  admin_username      = var.admin_username
  admin_password      = var.admin_password

  network_interface_ids = [azurerm_network_interface.vm.id]

  os_disk {
    name                 = "disk-${lower(var.vm_name)}-os"
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

  # Enable boot diagnostics
  boot_diagnostics {
    storage_account_uri = null # Use managed boot diagnostics
  }

  # Timezone
  timezone = "Singapore Standard Time"

  # Patch settings
  patch_assessment_mode = "AutomaticByPlatform"
  patch_mode            = "AutomaticByPlatform"

  tags = var.tags

  lifecycle {
    ignore_changes = [
      admin_password
    ]
  }
}

# -----------------------------------------------------------------------------
# Data Disks
# -----------------------------------------------------------------------------
resource "azurerm_managed_disk" "data" {
  for_each = { for idx, disk in var.data_disks : disk.name => disk }

  name                 = "disk-${lower(var.vm_name)}-${each.key}"
  resource_group_name  = var.resource_group_name
  location             = var.location
  storage_account_type = each.value.storage_type
  create_option        = "Empty"
  disk_size_gb         = each.value.size_gb

  tags = var.tags
}

resource "azurerm_virtual_machine_data_disk_attachment" "data" {
  for_each = azurerm_managed_disk.data

  managed_disk_id    = each.value.id
  virtual_machine_id = azurerm_windows_virtual_machine.vm.id
  lun                = index(keys(azurerm_managed_disk.data), each.key)
  caching            = "ReadWrite"
}

# -----------------------------------------------------------------------------
# Azure Monitor Agent Extension
# -----------------------------------------------------------------------------
resource "azurerm_virtual_machine_extension" "ama" {
  count = var.install_ama ? 1 : 0

  name                       = "AzureMonitorWindowsAgent"
  virtual_machine_id         = azurerm_windows_virtual_machine.vm.id
  publisher                  = "Microsoft.Azure.Monitor"
  type                       = "AzureMonitorWindowsAgent"
  type_handler_version       = "1.0"
  auto_upgrade_minor_version = true
  automatic_upgrade_enabled  = true

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Custom Script Extension - Configure WinRM and DNS
# -----------------------------------------------------------------------------
resource "azurerm_virtual_machine_extension" "configure" {
  count = var.configure_winrm ? 1 : 0

  name                 = "ConfigureWinRM"
  virtual_machine_id   = azurerm_windows_virtual_machine.vm.id
  publisher            = "Microsoft.Compute"
  type                 = "CustomScriptExtension"
  type_handler_version = "1.10"

  protected_settings = jsonencode({
    commandToExecute = <<-EOT
      powershell -ExecutionPolicy Bypass -Command "
        # Enable WinRM
        Enable-PSRemoting -Force -SkipNetworkProfileCheck
        Set-Item WSMan:\\localhost\\Service\\AllowUnencrypted -Value true
        Set-Item WSMan:\\localhost\\Service\\Auth\\Basic -Value true
        winrm set winrm/config/service '@{AllowUnencrypted=\"true\"}'

        # Configure firewall
        New-NetFirewallRule -Name 'WinRM-HTTP' -DisplayName 'WinRM HTTP' -Enabled True -Direction Inbound -Protocol TCP -LocalPort 5985 -Action Allow -ErrorAction SilentlyContinue

        # Set DNS
        $dnsServers = '${join(",", var.dns_servers)}'
        if ($dnsServers) {
          Set-DnsClientServerAddress -InterfaceAlias 'Ethernet' -ServerAddresses ($dnsServers -split ',')
        }
      "
    EOT
  })

  depends_on = [azurerm_virtual_machine_extension.ama]

  tags = var.tags
}
