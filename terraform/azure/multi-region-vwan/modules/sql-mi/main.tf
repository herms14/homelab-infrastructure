# =============================================================================
# SQL Managed Instance Module
# Creates SQL MI with required NSG and route table
# =============================================================================

# -----------------------------------------------------------------------------
# Network Security Group for SQL MI
# SQL MI requires specific inbound/outbound rules
# -----------------------------------------------------------------------------
resource "azurerm_network_security_group" "sqlmi" {
  name                = "nsg-sqlmi-${var.name}"
  resource_group_name = var.resource_group_name
  location            = var.location

  tags = var.tags
}

# Required NSG rules for SQL MI
resource "azurerm_network_security_rule" "allow_management_inbound" {
  name                        = "allow_management_inbound"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_ranges     = ["9000", "9003", "1438", "1440", "1452"]
  source_address_prefix       = "SqlManagement"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.sqlmi.name
}

resource "azurerm_network_security_rule" "allow_misubnet_inbound" {
  name                        = "allow_misubnet_inbound"
  priority                    = 200
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = var.subnet_address_prefix
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.sqlmi.name
}

resource "azurerm_network_security_rule" "allow_health_probe_inbound" {
  name                        = "allow_health_probe_inbound"
  priority                    = 300
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "AzureLoadBalancer"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.sqlmi.name
}

resource "azurerm_network_security_rule" "allow_tds_inbound" {
  name                        = "allow_tds_inbound"
  priority                    = 1000
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "1433"
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.sqlmi.name
}

resource "azurerm_network_security_rule" "deny_all_inbound" {
  name                        = "deny_all_inbound"
  priority                    = 4096
  direction                   = "Inbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.sqlmi.name
}

resource "azurerm_network_security_rule" "allow_management_outbound" {
  name                        = "allow_management_outbound"
  priority                    = 100
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_ranges     = ["443", "12000"]
  source_address_prefix       = "*"
  destination_address_prefix  = "AzureCloud"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.sqlmi.name
}

resource "azurerm_network_security_rule" "allow_misubnet_outbound" {
  name                        = "allow_misubnet_outbound"
  priority                    = 200
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = var.subnet_address_prefix
  destination_address_prefix  = var.subnet_address_prefix
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.sqlmi.name
}

resource "azurerm_network_security_rule" "deny_all_outbound" {
  name                        = "deny_all_outbound"
  priority                    = 4096
  direction                   = "Outbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.sqlmi.name
}

# Associate NSG with subnet
resource "azurerm_subnet_network_security_group_association" "sqlmi" {
  subnet_id                 = var.subnet_id
  network_security_group_id = azurerm_network_security_group.sqlmi.id
}

# -----------------------------------------------------------------------------
# Route Table for SQL MI
# -----------------------------------------------------------------------------
resource "azurerm_route_table" "sqlmi" {
  name                = "rt-sqlmi-${var.name}"
  resource_group_name = var.resource_group_name
  location            = var.location

  tags = var.tags
}

resource "azurerm_subnet_route_table_association" "sqlmi" {
  subnet_id      = var.subnet_id
  route_table_id = azurerm_route_table.sqlmi.id
}

# -----------------------------------------------------------------------------
# SQL Managed Instance
# -----------------------------------------------------------------------------
resource "azurerm_mssql_managed_instance" "sqlmi" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location

  license_type       = "BasePrice"
  sku_name           = var.sku_name
  storage_size_in_gb = var.storage_size_gb
  vcores             = var.vcores
  subnet_id          = var.subnet_id

  administrator_login          = var.admin_login
  administrator_login_password = var.admin_password

  public_data_endpoint_enabled = false
  minimum_tls_version          = "1.2"

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags

  depends_on = [
    azurerm_subnet_network_security_group_association.sqlmi,
    azurerm_subnet_route_table_association.sqlmi
  ]

  # SQL MI takes a long time to deploy
  timeouts {
    create = "6h"
    update = "6h"
    delete = "6h"
  }
}

# -----------------------------------------------------------------------------
# Private DNS Zone for SQL MI
# -----------------------------------------------------------------------------
resource "azurerm_private_dns_zone" "sqlmi" {
  count = var.create_private_dns_zone ? 1 : 0

  name                = "privatelink.database.windows.net"
  resource_group_name = var.resource_group_name

  tags = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "sqlmi" {
  for_each = var.create_private_dns_zone ? var.dns_zone_vnet_links : {}

  name                  = "link-${each.key}"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.sqlmi[0].name
  virtual_network_id    = each.value
  registration_enabled  = false

  tags = var.tags
}

# Private DNS A record for SQL MI
resource "azurerm_private_dns_a_record" "sqlmi" {
  count = var.create_private_dns_zone ? 1 : 0

  name                = var.name
  zone_name           = azurerm_private_dns_zone.sqlmi[0].name
  resource_group_name = var.resource_group_name
  ttl                 = 300
  records             = [azurerm_mssql_managed_instance.sqlmi.fqdn]
}
