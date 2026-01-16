# =============================================================================
# Log Analytics Module
# Creates LAW with DCE/DCR for regional monitoring
# =============================================================================

# -----------------------------------------------------------------------------
# Log Analytics Workspace (Regional)
# -----------------------------------------------------------------------------
resource "azurerm_log_analytics_workspace" "law" {
  name                = var.workspace_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = var.retention_days

  internet_ingestion_enabled = true
  internet_query_enabled     = true

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Data Collection Endpoint (DCE)
# -----------------------------------------------------------------------------
resource "azurerm_monitor_data_collection_endpoint" "dce" {
  name                = "dce-${var.workspace_name}"
  resource_group_name = var.resource_group_name
  location            = var.location
  kind                = "Windows"

  public_network_access_enabled = true

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Data Collection Rule - Windows Events (Regional Monitoring)
# -----------------------------------------------------------------------------
resource "azurerm_monitor_data_collection_rule" "windows_events" {
  name                        = "dcr-windows-events-${var.region_code}"
  resource_group_name         = var.resource_group_name
  location                    = var.location
  data_collection_endpoint_id = azurerm_monitor_data_collection_endpoint.dce.id

  destinations {
    log_analytics {
      workspace_resource_id = azurerm_log_analytics_workspace.law.id
      name                  = "regional-law"
    }
  }

  data_flow {
    streams      = ["Microsoft-Event"]
    destinations = ["regional-law"]
  }

  data_sources {
    windows_event_log {
      name    = "system-events"
      streams = ["Microsoft-Event"]
      x_path_queries = [
        "System!*[System[(Level=1 or Level=2 or Level=3)]]",
        "Application!*[System[(Level=1 or Level=2 or Level=3)]]"
      ]
    }
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Data Collection Rule - Windows Security Events (for Sentinel)
# -----------------------------------------------------------------------------
resource "azurerm_monitor_data_collection_rule" "windows_security" {
  count = var.sentinel_workspace_id != null ? 1 : 0

  name                        = "dcr-windows-security-${var.region_code}"
  resource_group_name         = var.resource_group_name
  location                    = var.location
  data_collection_endpoint_id = azurerm_monitor_data_collection_endpoint.dce.id

  destinations {
    log_analytics {
      workspace_resource_id = var.sentinel_workspace_id
      name                  = "sentinel-law"
    }
  }

  data_flow {
    streams      = ["Microsoft-SecurityEvent"]
    destinations = ["sentinel-law"]
  }

  data_sources {
    windows_event_log {
      name    = "security-events"
      streams = ["Microsoft-SecurityEvent"]
      x_path_queries = [
        # Authentication events
        "Security!*[System[(EventID=4624 or EventID=4625 or EventID=4634 or EventID=4647 or EventID=4648)]]",
        # Privileged operations
        "Security!*[System[(EventID=4672 or EventID=4673 or EventID=4674)]]",
        # Account management
        "Security!*[System[(EventID=4720 or EventID=4722 or EventID=4724 or EventID=4726 or EventID=4738)]]",
        # Group changes
        "Security!*[System[(EventID=4728 or EventID=4729 or EventID=4732 or EventID=4733 or EventID=4756 or EventID=4757)]]",
        # Kerberos
        "Security!*[System[(EventID=4768 or EventID=4769 or EventID=4771 or EventID=4776)]]",
        # Audit log cleared
        "Security!*[System[(EventID=1102)]]",
        # Process creation
        "Security!*[System[(EventID=4688)]]",
        # Policy changes
        "Security!*[System[(EventID=4719)]]"
      ]
    }
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# Update Management Solution
# -----------------------------------------------------------------------------
resource "azurerm_log_analytics_solution" "updates" {
  solution_name         = "Updates"
  workspace_name        = azurerm_log_analytics_workspace.law.name
  workspace_resource_id = azurerm_log_analytics_workspace.law.id
  resource_group_name   = var.resource_group_name
  location              = var.location

  plan {
    publisher = "Microsoft"
    product   = "OMSGallery/Updates"
  }
}
