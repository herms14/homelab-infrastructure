# =============================================================================
# Multi-Region Azure Infrastructure - Outputs
# =============================================================================

# -----------------------------------------------------------------------------
# VWAN Outputs
# -----------------------------------------------------------------------------
output "vwan_id" {
  description = "Virtual WAN ID"
  value       = module.vwan.vwan_id
}

output "vwan_hub_sea_id" {
  description = "SEA VWAN Hub ID"
  value       = module.vwan.hub_sea_id
}

output "vwan_hub_eastasia_id" {
  description = "East Asia VWAN Hub ID"
  value       = module.vwan.hub_eastasia_id
}

output "vpn_gateway_public_ips" {
  description = "VPN Gateway public IPs (configure on OPNsense)"
  value       = module.vwan.vpn_gateway_sea_public_ips
}

# -----------------------------------------------------------------------------
# VNet Outputs
# -----------------------------------------------------------------------------
output "vnet_app_servers_sea_id" {
  description = "App Servers VNet ID (SEA)"
  value       = module.vnet_app_servers_sea.vnet_id
}

output "vnet_file_servers_sea_id" {
  description = "File Servers VNet ID (SEA)"
  value       = module.vnet_file_servers_sea.vnet_id
}

output "vnet_servers_eastasia_id" {
  description = "Servers VNet ID (East Asia)"
  value       = module.vnet_servers_eastasia.vnet_id
}

# -----------------------------------------------------------------------------
# VM Outputs
# -----------------------------------------------------------------------------
output "vms_sea_app_servers" {
  description = "SEA App Server VMs"
  value = { for k, v in module.vms_app_servers_sea : k => {
    name       = v.vm_name
    private_ip = v.private_ip_address
  } }
}

output "vms_sea_file_servers" {
  description = "SEA File Server VMs"
  value = { for k, v in module.vms_file_servers_sea : k => {
    name       = v.vm_name
    private_ip = v.private_ip_address
  } }
}

output "vms_eastasia" {
  description = "East Asia VMs"
  value = { for k, v in module.vms_eastasia : k => {
    name       = v.vm_name
    private_ip = v.private_ip_address
  } }
}

# -----------------------------------------------------------------------------
# Log Analytics Outputs
# -----------------------------------------------------------------------------
output "law_sea_id" {
  description = "SEA Log Analytics Workspace ID"
  value       = module.law_sea.workspace_id
}

output "law_eastasia_id" {
  description = "East Asia Log Analytics Workspace ID"
  value       = module.law_eastasia.workspace_id
}

# -----------------------------------------------------------------------------
# AKS Outputs
# -----------------------------------------------------------------------------
output "aks_cluster_name" {
  description = "AKS Cluster name"
  value       = var.deploy_aks ? module.aks[0].cluster_name : null
}

output "aks_cluster_fqdn" {
  description = "AKS Cluster private FQDN"
  value       = var.deploy_aks ? module.aks[0].cluster_fqdn : null
}

output "aks_kube_config" {
  description = "AKS kubeconfig (sensitive)"
  value       = var.deploy_aks ? module.aks[0].kube_config : null
  sensitive   = true
}

# -----------------------------------------------------------------------------
# SQL MI Outputs
# -----------------------------------------------------------------------------
output "sqlmi_fqdn" {
  description = "SQL MI FQDN"
  value       = var.deploy_sqlmi ? module.sqlmi[0].fqdn : null
}

output "sqlmi_connection_string" {
  description = "SQL MI connection string (without password)"
  value       = var.deploy_sqlmi ? module.sqlmi[0].connection_string : null
}

# -----------------------------------------------------------------------------
# Ansible Inventory Helper
# -----------------------------------------------------------------------------
output "ansible_inventory" {
  description = "Ansible inventory snippet"
  value       = <<-EOT
# Generated Ansible inventory for multi-region Azure infrastructure
# Add to ansible/inventory/azure-multiregion.yml

all:
  vars:
    ansible_user: ${var.vm_admin_username}
    ansible_connection: winrm
    ansible_winrm_transport: ntlm
    ansible_port: 5985

  children:
    sea_app_servers:
      hosts:
%{for k, v in module.vms_app_servers_sea~}
        ${v.vm_name}:
          ansible_host: ${v.private_ip_address}
%{endfor~}

    sea_file_servers:
      hosts:
%{for k, v in module.vms_file_servers_sea~}
        ${v.vm_name}:
          ansible_host: ${v.private_ip_address}
%{endfor~}

    eastasia_servers:
      hosts:
%{for k, v in module.vms_eastasia~}
        ${v.vm_name}:
          ansible_host: ${v.private_ip_address}
%{endfor~}
  EOT
}
