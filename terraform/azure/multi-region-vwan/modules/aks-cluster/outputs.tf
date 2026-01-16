# =============================================================================
# AKS Cluster Module Outputs
# =============================================================================

output "cluster_id" {
  description = "AKS cluster ID"
  value       = azurerm_kubernetes_cluster.aks.id
}

output "cluster_name" {
  description = "AKS cluster name"
  value       = azurerm_kubernetes_cluster.aks.name
}

output "cluster_fqdn" {
  description = "Private FQDN of the AKS cluster"
  value       = azurerm_kubernetes_cluster.aks.private_fqdn
}

output "kube_config" {
  description = "Kubeconfig for cluster access"
  value       = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive   = true
}

output "kubelet_identity" {
  description = "Kubelet identity"
  value = {
    client_id   = azurerm_kubernetes_cluster.aks.kubelet_identity[0].client_id
    object_id   = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
    resource_id = azurerm_kubernetes_cluster.aks.kubelet_identity[0].user_assigned_identity_id
  }
}

output "node_resource_group" {
  description = "Resource group for AKS nodes"
  value       = azurerm_kubernetes_cluster.aks.node_resource_group
}

output "oidc_issuer_url" {
  description = "OIDC issuer URL for workload identity"
  value       = azurerm_kubernetes_cluster.aks.oidc_issuer_url
}
