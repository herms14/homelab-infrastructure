output "container_id" {
  description = "Container ID"
  value       = proxmox_lxc.container.vmid
}

output "hostname" {
  description = "Container hostname"
  value       = proxmox_lxc.container.hostname
}

output "ip_address" {
  description = "Container IP address"
  value       = var.ip_address
}
