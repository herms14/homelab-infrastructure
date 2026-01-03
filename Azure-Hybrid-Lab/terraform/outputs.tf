# =============================================================================
# Outputs - Azure Hybrid Lab
# =============================================================================

# -----------------------------------------------------------------------------
# Connectivity Outputs
# -----------------------------------------------------------------------------
output "hub_vnet_id" {
  description = "ID of the hub virtual network"
  value       = module.connectivity.hub_vnet_id
}

output "vpn_gateway_public_ip" {
  description = "Public IP of the VPN Gateway (configure on Omada ER605)"
  value       = module.connectivity.vpn_gateway_public_ip
}

output "vwan_id" {
  description = "Azure Virtual WAN ID"
  value       = module.connectivity.vwan_id
}

# -----------------------------------------------------------------------------
# Identity Outputs
# -----------------------------------------------------------------------------
output "dc_private_ips" {
  description = "Private IP addresses of Azure Domain Controllers"
  value       = module.platform_identity.dc_private_ips
}

output "key_vault_uri" {
  description = "URI of the identity Key Vault"
  value       = module.platform_identity.key_vault_uri
}

# -----------------------------------------------------------------------------
# Application Landing Zone Outputs
# -----------------------------------------------------------------------------
output "aks_cluster_name" {
  description = "Name of the AKS cluster"
  value       = module.app_lz.aks_cluster_name
}

output "aks_cluster_fqdn" {
  description = "Private FQDN of the AKS cluster"
  value       = module.app_lz.aks_cluster_fqdn
}

output "acr_login_server" {
  description = "Container registry login server"
  value       = module.app_lz.acr_login_server
}

# -----------------------------------------------------------------------------
# VPN Configuration (for Omada ER605)
# -----------------------------------------------------------------------------
output "vpn_config_for_omada" {
  description = "VPN configuration to apply on Omada ER605"
  value = {
    azure_gateway_ip  = module.connectivity.vpn_gateway_public_ip
    azure_vnet_cidrs  = concat(var.azure_hub_vnet.address_space, var.azure_spoke_vnet.address_space)
    onprem_cidr       = var.onprem_network.address_space
    shared_key        = "Set via TF_VAR or tfvars"
  }
  sensitive = true
}
