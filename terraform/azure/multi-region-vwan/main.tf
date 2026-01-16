# =============================================================================
# Multi-Region Azure Infrastructure with VWAN
# Root Module - Orchestrates all components
# =============================================================================
# Deploy from: ubuntu-deploy-vm (10.90.10.5)
#   cd /opt/terraform/multi-region-vwan
#   terraform init
#   terraform plan -out=tfplan
#   terraform apply tfplan
# =============================================================================

# -----------------------------------------------------------------------------
# Local Variables
# -----------------------------------------------------------------------------
locals {
  # Combine all tags
  common_tags = merge(var.tags, {
    DeployedBy = "Terraform"
    DeployedOn = timestamp()
  })

  # DNS servers (domain controllers)
  dns_servers = var.domain_controllers
}

# -----------------------------------------------------------------------------
# Resource Groups
# -----------------------------------------------------------------------------
resource "azurerm_resource_group" "vwan" {
  name     = "rg-vwan-prod"
  location = var.regions.primary
  tags     = local.common_tags
}

resource "azurerm_resource_group" "app_servers_sea" {
  name     = "rg-app-servers-prod-sea"
  location = var.regions.primary
  tags     = local.common_tags
}

resource "azurerm_resource_group" "file_servers_sea" {
  name     = "rg-file-servers-prod-sea"
  location = var.regions.primary
  tags     = local.common_tags
}

resource "azurerm_resource_group" "servers_eastasia" {
  name     = "rg-servers-prod-eas"
  location = var.regions.secondary
  tags     = local.common_tags
}

# -----------------------------------------------------------------------------
# Virtual WAN
# -----------------------------------------------------------------------------
module "vwan" {
  source = "./modules/vwan"

  vwan_name                   = var.vwan_name
  resource_group_name         = azurerm_resource_group.vwan.name
  location_primary            = var.regions.primary
  location_secondary          = var.regions.secondary
  hub_sea_address_prefix      = var.vwan_hub_sea_address_prefix
  hub_eastasia_address_prefix = var.vwan_hub_eastasia_address_prefix
  onprem_vpn_site_name        = var.onprem_vpn_site_name
  onprem_public_ip            = var.onprem_public_ip
  onprem_address_spaces       = var.onprem_address_spaces
  vpn_shared_key              = var.vpn_shared_key

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# Spoke VNets - Southeast Asia
# -----------------------------------------------------------------------------
module "vnet_app_servers_sea" {
  source = "./modules/spoke-vnet"

  vnet_name           = var.vnet_app_servers_sea.name
  resource_group_name = azurerm_resource_group.app_servers_sea.name
  location            = var.regions.primary
  address_space       = var.vnet_app_servers_sea.address_space
  subnets             = var.vnet_app_servers_sea.subnets
  dns_servers         = local.dns_servers

  vwan_hub_id                = module.vwan.hub_sea_id
  vwan_route_table_id        = module.vwan.hub_sea_default_route_table_id
  propagated_route_table_ids = [module.vwan.hub_sea_default_route_table_id, module.vwan.hub_eastasia_default_route_table_id]

  tags = local.common_tags
}

module "vnet_file_servers_sea" {
  source = "./modules/spoke-vnet"

  vnet_name           = var.vnet_file_servers_sea.name
  resource_group_name = azurerm_resource_group.file_servers_sea.name
  location            = var.regions.primary
  address_space       = var.vnet_file_servers_sea.address_space
  subnets             = var.vnet_file_servers_sea.subnets
  dns_servers         = local.dns_servers

  vwan_hub_id                = module.vwan.hub_sea_id
  vwan_route_table_id        = module.vwan.hub_sea_default_route_table_id
  propagated_route_table_ids = [module.vwan.hub_sea_default_route_table_id, module.vwan.hub_eastasia_default_route_table_id]

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# Connect Existing Identity VNet to VWAN Hub
# -----------------------------------------------------------------------------
resource "azurerm_virtual_hub_connection" "identity_vnet" {
  name                      = "conn-identity-vnet"
  virtual_hub_id            = module.vwan.hub_sea_id
  remote_virtual_network_id = var.existing_identity_vnet_id

  internet_security_enabled = true
}

# -----------------------------------------------------------------------------
# Spoke VNet - East Asia
# -----------------------------------------------------------------------------
module "vnet_servers_eastasia" {
  source = "./modules/spoke-vnet"

  vnet_name           = var.vnet_servers_eastasia.name
  resource_group_name = azurerm_resource_group.servers_eastasia.name
  location            = var.regions.secondary
  address_space       = var.vnet_servers_eastasia.address_space
  subnets             = var.vnet_servers_eastasia.subnets
  dns_servers         = local.dns_servers

  vwan_hub_id                = module.vwan.hub_eastasia_id
  vwan_route_table_id        = module.vwan.hub_eastasia_default_route_table_id
  propagated_route_table_ids = [module.vwan.hub_sea_default_route_table_id, module.vwan.hub_eastasia_default_route_table_id]

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# Log Analytics - Regional Monitoring
# -----------------------------------------------------------------------------
module "law_sea" {
  source = "./modules/log-analytics"

  workspace_name        = var.law_sea_name
  resource_group_name   = azurerm_resource_group.app_servers_sea.name
  location              = var.regions.primary
  region_code           = "sea"
  retention_days        = var.law_retention_days
  sentinel_workspace_id = var.existing_sentinel_law_id

  tags = local.common_tags
}

module "law_eastasia" {
  source = "./modules/log-analytics"

  workspace_name        = var.law_eastasia_name
  resource_group_name   = azurerm_resource_group.servers_eastasia.name
  location              = var.regions.secondary
  region_code           = "eas"
  retention_days        = var.law_retention_days
  sentinel_workspace_id = var.existing_sentinel_law_id

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# Windows VMs - Southeast Asia (App Servers)
# -----------------------------------------------------------------------------
module "vms_app_servers_sea" {
  source   = "./modules/windows-vm"
  for_each = var.vms_sea_app_servers

  vm_name             = each.value.name
  resource_group_name = azurerm_resource_group.app_servers_sea.name
  location            = var.regions.primary
  subnet_id           = module.vnet_app_servers_sea.subnet_ids["snet-app-servers"]
  private_ip_address  = each.value.ip_address
  vm_size             = coalesce(each.value.size, var.vm_size_default)
  admin_username      = var.vm_admin_username
  admin_password      = var.vm_admin_password
  dns_servers         = local.dns_servers
  data_disks          = each.value.data_disks

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# Windows VMs - Southeast Asia (File Servers)
# -----------------------------------------------------------------------------
module "vms_file_servers_sea" {
  source   = "./modules/windows-vm"
  for_each = var.vms_sea_file_servers

  vm_name             = each.value.name
  resource_group_name = azurerm_resource_group.file_servers_sea.name
  location            = var.regions.primary
  subnet_id           = module.vnet_file_servers_sea.subnet_ids["snet-file-servers"]
  private_ip_address  = each.value.ip_address
  vm_size             = coalesce(each.value.size, var.vm_size_default)
  admin_username      = var.vm_admin_username
  admin_password      = var.vm_admin_password
  dns_servers         = local.dns_servers
  data_disks          = each.value.data_disks

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# Windows VMs - East Asia
# -----------------------------------------------------------------------------
module "vms_eastasia" {
  source   = "./modules/windows-vm"
  for_each = var.vms_eastasia_servers

  vm_name             = each.value.name
  resource_group_name = azurerm_resource_group.servers_eastasia.name
  location            = var.regions.secondary
  subnet_id           = module.vnet_servers_eastasia.subnet_ids[each.value.subnet]
  private_ip_address  = each.value.ip_address
  vm_size             = coalesce(each.value.size, var.vm_size_default)
  admin_username      = var.vm_admin_username
  admin_password      = var.vm_admin_password
  dns_servers         = local.dns_servers
  data_disks          = each.value.data_disks

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# DCR Associations - SEA VMs to Regional LAW
# -----------------------------------------------------------------------------
resource "azurerm_monitor_data_collection_rule_association" "sea_app_servers" {
  for_each = module.vms_app_servers_sea

  name                    = "dcra-${each.value.vm_name}-events"
  target_resource_id      = each.value.vm_id
  data_collection_rule_id = module.law_sea.dcr_windows_events_id
}

resource "azurerm_monitor_data_collection_rule_association" "sea_file_servers" {
  for_each = module.vms_file_servers_sea

  name                    = "dcra-${each.value.vm_name}-events"
  target_resource_id      = each.value.vm_id
  data_collection_rule_id = module.law_sea.dcr_windows_events_id
}

# DCR Associations - SEA VMs to Sentinel
resource "azurerm_monitor_data_collection_rule_association" "sea_app_servers_security" {
  for_each = module.vms_app_servers_sea

  name                    = "dcra-${each.value.vm_name}-security"
  target_resource_id      = each.value.vm_id
  data_collection_rule_id = module.law_sea.dcr_windows_security_id
}

resource "azurerm_monitor_data_collection_rule_association" "sea_file_servers_security" {
  for_each = module.vms_file_servers_sea

  name                    = "dcra-${each.value.vm_name}-security"
  target_resource_id      = each.value.vm_id
  data_collection_rule_id = module.law_sea.dcr_windows_security_id
}

# -----------------------------------------------------------------------------
# DCR Associations - East Asia VMs
# -----------------------------------------------------------------------------
resource "azurerm_monitor_data_collection_rule_association" "eastasia_servers" {
  for_each = module.vms_eastasia

  name                    = "dcra-${each.value.vm_name}-events"
  target_resource_id      = each.value.vm_id
  data_collection_rule_id = module.law_eastasia.dcr_windows_events_id
}

resource "azurerm_monitor_data_collection_rule_association" "eastasia_servers_security" {
  for_each = module.vms_eastasia

  name                    = "dcra-${each.value.vm_name}-security"
  target_resource_id      = each.value.vm_id
  data_collection_rule_id = module.law_eastasia.dcr_windows_security_id
}

# -----------------------------------------------------------------------------
# AKS Cluster - East Asia (Conditional)
# -----------------------------------------------------------------------------
module "aks" {
  source = "./modules/aks-cluster"
  count  = var.deploy_aks ? 1 : 0

  cluster_name               = var.aks_cluster_name
  resource_group_name        = azurerm_resource_group.servers_eastasia.name
  location                   = var.regions.secondary
  kubernetes_version         = var.aks_kubernetes_version
  vnet_id                    = module.vnet_servers_eastasia.vnet_id
  node_subnet_id             = module.vnet_servers_eastasia.subnet_ids["snet-aks-nodes"]
  system_node_count          = var.aks_system_node_count
  system_node_size           = var.vm_size_aks_system
  user_node_count            = var.aks_user_node_count
  user_node_size             = var.vm_size_aks_user
  service_cidr               = var.aks_service_cidr
  dns_service_ip             = var.aks_dns_service_ip
  log_analytics_workspace_id = module.law_eastasia.workspace_id

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# SQL Managed Instance - East Asia (Conditional)
# -----------------------------------------------------------------------------
module "sqlmi" {
  source = "./modules/sql-mi"
  count  = var.deploy_sqlmi ? 1 : 0

  name                  = var.sqlmi_name
  resource_group_name   = azurerm_resource_group.servers_eastasia.name
  location              = var.regions.secondary
  subnet_id             = module.vnet_servers_eastasia.subnet_ids["snet-sqlmi"]
  subnet_address_prefix = var.vnet_servers_eastasia.subnets["snet-sqlmi"].address_prefix
  sku_name              = var.sqlmi_sku
  vcores                = var.sqlmi_vcores
  storage_size_gb       = var.sqlmi_storage_gb
  admin_login           = var.sqlmi_admin_login
  admin_password        = var.sqlmi_admin_password

  dns_zone_vnet_links = {
    "servers-eastasia" = module.vnet_servers_eastasia.vnet_id
    "app-servers-sea"  = module.vnet_app_servers_sea.vnet_id
    "file-servers-sea" = module.vnet_file_servers_sea.vnet_id
  }

  tags = local.common_tags
}
