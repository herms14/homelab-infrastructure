# Inventory Management

> **TL;DR**: Inventory defines what Ansible manages. Use groups for logical organization, group_vars for shared settings, and host_vars for host-specific configuration.

## Inventory Types

### INI Format

**File**: `inventory.ini`

```ini
[webservers]
web1 ansible_host=192.168.40.10
web2 ansible_host=192.168.40.11

[databases]
db1 ansible_host=192.168.40.20

[webservers:vars]
http_port=80

[all:vars]
ansible_user=hermes-admin
```

### YAML Format

**File**: `inventory.yml`

```yaml
all:
  vars:
    ansible_user: hermes-admin
  children:
    webservers:
      hosts:
        web1:
          ansible_host: 192.168.40.10
        web2:
          ansible_host: 192.168.40.11
      vars:
        http_port: 80
    databases:
      hosts:
        db1:
          ansible_host: 192.168.40.20
```

---

## Production Inventory

### Full inventory.ini

```ini
# =============================================================================
# VLAN 20 - Infrastructure (192.168.20.0/24)
# =============================================================================

# Kubernetes Control Plane
[k8s_controllers]
k8s-controller01 ansible_host=192.168.20.32 k8s_role=primary
k8s-controller02 ansible_host=192.168.20.33 k8s_role=secondary
k8s-controller03 ansible_host=192.168.20.34 k8s_role=secondary

# Kubernetes Workers
[k8s_workers]
k8s-worker01 ansible_host=192.168.20.40
k8s-worker02 ansible_host=192.168.20.41
k8s-worker03 ansible_host=192.168.20.42
k8s-worker04 ansible_host=192.168.20.43
k8s-worker05 ansible_host=192.168.20.44
k8s-worker06 ansible_host=192.168.20.45

# Combined Kubernetes group
[k8s:children]
k8s_controllers
k8s_workers

# =============================================================================
# VLAN 40 - Services (192.168.40.0/24)
# =============================================================================

# Docker Container Hosts
[docker_hosts]
docker-vm-utilities01 ansible_host=192.168.40.10 docker_role=utilities
docker-vm-media01 ansible_host=192.168.40.11 docker_role=media

# Application Services (each runs dedicated service)
[traefik]
traefik-vm01 ansible_host=192.168.40.20

[authentik]
authentik-vm01 ansible_host=192.168.40.21

[immich]
immich-vm01 ansible_host=192.168.40.22

[gitlab]
gitlab-vm01 ansible_host=192.168.40.23

# Combined services group
[services:children]
traefik
authentik
immich
gitlab

# =============================================================================
# Infrastructure Services
# =============================================================================

[logging]
linux-syslog-server01 ansible_host=192.168.40.5

# =============================================================================
# Logical Groupings
# =============================================================================

# All hosts requiring Docker
[docker_required:children]
docker_hosts
authentik
immich

# All VLAN 20 hosts
[vlan20:children]
k8s

# All VLAN 40 hosts
[vlan40:children]
docker_hosts
services
logging

# =============================================================================
# Global Variables
# =============================================================================

[all:vars]
ansible_user=hermes-admin
ansible_ssh_private_key_file=~/.ssh/id_ed25519
ansible_python_interpreter=/usr/bin/python3
```

---

## Group Variables

### Directory Structure

```
group_vars/
├── all.yml                 # All hosts
├── k8s.yml                 # All K8s nodes
├── k8s_controllers.yml     # K8s control plane only
├── k8s_workers.yml         # K8s workers only
├── docker_hosts.yml        # Docker hosts
├── services.yml            # Application services
├── vlan20.yml              # VLAN 20 network settings
└── vlan40.yml              # VLAN 40 network settings
```

### all.yml

```yaml
---
# Global variables for all managed hosts

# User configuration
admin_user: hermes-admin

# Network
dns_servers:
  - 192.168.91.30
ntp_servers:
  - 0.pool.ntp.org
  - 1.pool.ntp.org

# Domain
domain: hrmsmrflrii.xyz

# Common packages
common_packages:
  - curl
  - wget
  - htop
  - vim
  - git
  - jq
  - ca-certificates
  - gnupg

# SSH configuration
ssh_port: 22
ssh_permit_root: "no"
ssh_password_auth: "no"

# Timezone
timezone: America/New_York
```

### k8s.yml

```yaml
---
# Kubernetes cluster configuration

# Version
k8s_version: "1.28"
k8s_minor_version: "1.28.5"

# Network
k8s_pod_network_cidr: "10.244.0.0/16"
k8s_service_cidr: "10.96.0.0/12"
k8s_dns_domain: "cluster.local"

# Control plane
k8s_control_plane_endpoint: "192.168.20.32"
k8s_control_plane_port: 6443

# Container runtime
container_runtime: containerd
containerd_version: "1.7"

# CNI
cni_plugin: calico
calico_version: "3.27.0"

# Kubelet configuration
kubelet_extra_args:
  - "--cgroup-driver=systemd"
```

### k8s_controllers.yml

```yaml
---
# K8s control plane specific

# etcd
etcd_data_dir: /var/lib/etcd

# API server
kube_apiserver_admission_plugins:
  - NodeRestriction
  - PodSecurity

# Controller manager
kube_controller_manager_extra_args: {}
```

### docker_hosts.yml

```yaml
---
# Docker host configuration

# Docker
docker_edition: "ce"
docker_version: ""  # Latest
docker_compose_version: "2.24.0"

# Docker daemon
docker_daemon_config:
  log-driver: "json-file"
  log-opts:
    max-size: "10m"
    max-file: "3"
  storage-driver: "overlay2"
  default-address-pools:
    - base: "172.17.0.0/16"
      size: 24

# Directories
docker_base_dir: /opt
docker_data_dir: /var/lib/docker

# Network
docker_networks:
  - name: traefik
    driver: bridge
```

### vlan20.yml

```yaml
---
# VLAN 20 network configuration

network_vlan: 20
network_cidr: "192.168.20.0/24"
network_gateway: "192.168.20.1"
network_dns: "192.168.91.30"
network_domain: "hrmsmrflrii.xyz"
```

### vlan40.yml

```yaml
---
# VLAN 40 network configuration

network_vlan: 40
network_cidr: "192.168.40.0/24"
network_gateway: "192.168.40.1"
network_dns: "192.168.91.30"
network_domain: "hrmsmrflrii.xyz"

# Traefik reverse proxy
traefik_ip: "192.168.40.20"
```

---

## Host Variables

### Directory Structure

```
host_vars/
├── k8s-controller01.yml
├── docker-vm-media01.yml
└── traefik-vm01.yml
```

### k8s-controller01.yml

```yaml
---
# Primary K8s controller

k8s_role: primary
k8s_init_cluster: true

# etcd
etcd_initial_cluster_state: "new"
```

### docker-vm-media01.yml

```yaml
---
# Media Docker host

# NFS mounts
nfs_mounts:
  - src: "192.168.20.31:/volume2/Proxmox-Media"
    dest: "/mnt/media"
    opts: "defaults,_netdev"
    fstype: "nfs"

# Docker stacks
docker_stacks:
  - name: arr-stack
    compose_dir: /opt/arr-stack

# Services running
services_running:
  - jellyfin
  - radarr
  - sonarr
  - lidarr
  - prowlarr
  - bazarr
  - overseerr
  - jellyseerr
  - tdarr
  - autobrr
```

### traefik-vm01.yml

```yaml
---
# Traefik reverse proxy

traefik_version: "v3.0"
traefik_dashboard_enabled: true
traefik_api_insecure: false

# SSL
acme_email: "admin@example.com"
acme_provider: cloudflare

# Entrypoints
traefik_entrypoints:
  web:
    address: ":80"
  websecure:
    address: ":443"
```

---

## Dynamic Inventory

### Pattern Matching

```bash
# All hosts
ansible all -m ping

# Single host
ansible k8s-controller01 -m ping

# Group
ansible k8s_workers -m ping

# Multiple groups (union)
ansible 'docker_hosts:services' -m ping

# Intersection
ansible 'k8s:&k8s_controllers' -m ping

# Exclusion
ansible 'k8s:!k8s_workers' -m ping

# Regex
ansible '~k8s-worker0[1-3]' -m ping
```

### Patterns in Playbooks

```yaml
---
- name: Deploy to web tier
  hosts: webservers:!webservers_maintenance
  tasks:
    - name: Deploy application
      # ...

- name: Database maintenance
  hosts: databases:&production
  tasks:
    - name: Backup database
      # ...
```

---

## Group Hierarchies

### Parent/Child Groups

```ini
[production:children]
prod_web
prod_db
prod_cache

[staging:children]
stage_web
stage_db

[web:children]
prod_web
stage_web

[databases:children]
prod_db
stage_db
```

### Variable Inheritance

Variables cascade through group hierarchies:

1. `all` group vars
2. Parent group vars
3. Child group vars
4. Host vars

**Example**:
```
all:
  ansible_user: admin
    └── k8s:
        k8s_version: 1.28
          └── k8s_controllers:
              k8s_role: controller
                └── k8s-controller01:
                    k8s_init: true
```

Host `k8s-controller01` has all four variables.

---

## Listing Inventory

### List Hosts

```bash
# All hosts
ansible-inventory --list

# Specific group
ansible k8s --list-hosts

# Graph view
ansible-inventory --graph

# Output:
@all:
  |--@k8s:
  |  |--@k8s_controllers:
  |  |  |--k8s-controller01
  |  |  |--k8s-controller02
  |  |  |--k8s-controller03
  |  |--@k8s_workers:
  |  |  |--k8s-worker01
  |  |  |--k8s-worker02
  ...
```

### Show Host Variables

```bash
# All variables for host
ansible-inventory --host k8s-controller01

# Output as YAML
ansible-inventory --host k8s-controller01 --yaml
```

---

## Inventory Validation

### Check for Errors

```bash
# Validate inventory syntax
ansible-inventory --list > /dev/null

# Test connectivity
ansible all -m ping

# Gather facts to verify access
ansible all -m setup -a "filter=ansible_hostname"
```

### Common Errors

**Duplicate host**:
```
[WARNING]: Found variable using reserved name: ansible_host
```

**Missing host**:
```
[WARNING]: Could not match supplied host pattern, ignoring: nonexistent
```

**Variable conflict**:
```
[WARNING]: While constructing a mapping from..., found a duplicate dict key
```

---

## Best Practices

### Naming Conventions

```ini
# Pattern: service-type-number
k8s-controller01      # Not: controller1, k8s_controller_01
docker-vm-media01     # Not: docker-media, dockermedia01

# Groups: plural, lowercase, underscores
[k8s_controllers]     # Not: k8s-controllers, K8sControllers
[docker_hosts]        # Not: docker-host, DockerHosts
```

### Organization

- One inventory file for small environments
- Split inventories for large environments (dev/staging/prod)
- Use `group_vars/` and `host_vars/` directories
- Document group purposes with comments

### Security

- Don't store secrets in inventory files
- Use `ansible-vault` for sensitive variables
- Keep inventory in version control (without secrets)

---

## Multiple Environments

### Directory Structure

```
inventories/
├── production/
│   ├── hosts.ini
│   ├── group_vars/
│   └── host_vars/
├── staging/
│   ├── hosts.ini
│   ├── group_vars/
│   └── host_vars/
└── development/
    ├── hosts.ini
    ├── group_vars/
    └── host_vars/
```

### Usage

```bash
# Production
ansible-playbook -i inventories/production/hosts.ini playbook.yml

# Staging
ansible-playbook -i inventories/staging/hosts.ini playbook.yml
```

---

## What's Next?

- **[Playbook Guide](Playbook-Guide)** - Production playbooks
- **[Controller Setup](Controller-Setup)** - Ansible controller
- **[Services Overview](Services-Overview)** - Deploy services

---

*Well-organized inventory makes automation manageable at scale.*
