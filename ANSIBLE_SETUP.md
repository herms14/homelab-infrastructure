# Ansible Configuration for Homelab Infrastructure

## Overview
Ansible controller configured to manage all VMs in the homelab infrastructure.

**Controller**: ansible-controller01 (192.168.20.30)
**User**: hermes-admin
**Authentication**: SSH key-based
**Total Managed Hosts**: 16 VMs (9 active, 7 offline)

## Managed Hosts

### ✅ Active and Reachable (9 VMs)
- k8s-controller02 (192.168.20.33)
- k8s-controller03 (192.168.20.34)
- linux-syslog-server01 (192.168.40.5)
- docker-vm-utilities01 (192.168.40.10)
- docker-vm-media01 (192.168.40.11)
- traefik-vm01 (192.168.40.20)
- authentik-vm01 (192.168.40.21)
- immich-vm01 (192.168.40.22)
- gitlab-vm01 (192.168.40.23)

### ⚠️ Offline (7 VMs)
- k8s-controller01 (192.168.20.32)
- k8s-worker01 (192.168.20.40)
- k8s-worker02 (192.168.20.41)
- k8s-worker03 (192.168.20.42)
- k8s-worker04 (192.168.20.43)
- k8s-worker05 (192.168.20.44)
- k8s-worker06 (192.168.20.45)

**Note**: When these VMs are started, you'll need to add the SSH key:
```bash
ssh hermes-admin@<vm-ip> "echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILNaYM/nUFmslKMJ77SIuiT/1CQot2NbtBTP8zdXP2d6 hermes-admin@ansible-controller01' >> ~/.ssh/authorized_keys"
```

## Inventory Structure

The inventory is organized into logical groups:

- **kubernetes**: All Kubernetes nodes
  - k8s_controllers: Control plane nodes
  - k8s_workers: Worker nodes
- **docker_hosts**: Docker VMs
  - docker_utilities
  - docker_media
- **application_services**: Application VMs
  - reverse_proxy (Traefik)
  - identity_management (Authentik)
  - media_services (Immich)
  - devops (GitLab)
- **logging**: Logging infrastructure
- **vlan20**: All VLAN 20 hosts
- **vlan40**: All VLAN 40 hosts
- **managed_vms**: All managed hosts (parent group)

## Common Commands

### Test connectivity
```bash
ansible all -m ping
ansible kubernetes -m ping
ansible vlan40 -m ping
```

### Run ad-hoc commands
```bash
# Check uptime
ansible all -a uptime

# Check disk usage
ansible all -a 'df -h'

# Check memory
ansible all -a 'free -h'
```

### List hosts in groups
```bash
ansible kubernetes --list-hosts
ansible docker_hosts --list-hosts
ansible managed_vms --list-hosts
```

### Run playbooks
```bash
ansible-playbook ping-all.yml
ansible-playbook gather-facts.yml
ansible-playbook update-systems.yml  # Requires sudo
```

### Deploy Kubernetes Cluster
```bash
# Deploy complete production-grade Kubernetes cluster
cd ~/ansible
ansible-playbook k8s/k8s-deploy-all.yml

# Or run individual playbooks step-by-step:
ansible-playbook k8s/01-k8s-prerequisites.yml
ansible-playbook k8s/02-k8s-install.yml
ansible-playbook k8s/03-k8s-init-cluster.yml
ansible-playbook k8s/04-k8s-install-cni.yml
ansible-playbook k8s/05-k8s-join-nodes.yml
```

See [Kubernetes_Setup.md](./Kubernetes_Setup.md) for complete Kubernetes deployment documentation.

## Files

### General Playbooks
- **inventory.ini**: Host inventory with groups
- **ansible.cfg**: Ansible configuration
- **ping-all.yml**: Test connectivity playbook
- **gather-facts.yml**: Gather system information
- **update-systems.yml**: Update all systems
- **ansible.log**: Ansible execution log

### Kubernetes Playbooks (~/ansible/k8s/)
- **k8s-deploy-all.yml**: Master playbook - deploys complete K8s cluster
- **01-k8s-prerequisites.yml**: System prerequisites (swap, kernel modules, containerd)
- **02-k8s-install.yml**: Install Kubernetes packages (kubeadm, kubelet, kubectl)
- **03-k8s-init-cluster.yml**: Initialize cluster on primary controller
- **04-k8s-install-cni.yml**: Install Calico CNI for pod networking
- **05-k8s-join-nodes.yml**: Join additional controllers and workers to cluster

## Notes

- SSH host key checking is disabled for convenience
- Facts are cached for 24 hours to improve performance
- Logs are written to ansible.log in the current directory
- Privilege escalation (sudo) is configured but not enabled by default
