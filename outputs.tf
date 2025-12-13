# Output definitions

output "vm_summary" {
  description = "Summary of all created VMs"
  value = {
    for key, vm in module.vms : key => {
      name = vm.vm_name
      id   = vm.vm_id
      ip   = vm.ip_address
    }
  }
}

output "vm_ips" {
  description = "Map of VM names to IP addresses"
  value = {
    for key, vm in module.vms : vm.vm_name => vm.ip_address
  }
}
