output "vm_id" {
  description = "ID of the created VM"
  value       = proxmox_vm_qemu.linux_vm.id
}

output "vm_name" {
  description = "Name of the created VM"
  value       = proxmox_vm_qemu.linux_vm.name
}

output "ip_address" {
  description = "IP address of the VM"
  value       = var.ip_address
}
