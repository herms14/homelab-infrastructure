# Controller Setup

> **TL;DR**: ansible-controller01 (192.168.20.30) is the centralized automation hub. All playbooks execute from here via SSH to target hosts.

## Controller Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ansible-controller01                                  │
│                        192.168.20.30 (VLAN 20)                              │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                          ~/ansible/                                  │   │
│   │                                                                      │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│   │  │ ansible.cfg │  │inventory.ini│  │ group_vars/ │                 │   │
│   │  │             │  │             │  │             │                 │   │
│   │  │ • SSH conf  │  │ • All hosts │  │ • k8s vars  │                 │   │
│   │  │ • Defaults  │  │ • Groups    │  │ • docker    │                 │   │
│   │  │ • Plugins   │  │ • Variables │  │ • services  │                 │   │
│   │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│   │                                                                      │   │
│   │  ┌─────────────────────────────────────────────────────────────┐   │   │
│   │  │                     Playbooks                                │   │   │
│   │  │                                                              │   │   │
│   │  │  docker/         k8s/           traefik/      opnsense/     │   │   │
│   │  │  ├── install     ├── deploy-all ├── deploy    ├── dns       │   │   │
│   │  │  └── arr-stack   └── prereqs    └── config    └── all-dns   │   │   │
│   │  │                                                              │   │   │
│   │  └─────────────────────────────────────────────────────────────┘   │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                       │                                      │
│                                       │ SSH                                  │
│                                       ▼                                      │
│   ┌───────────────────────────────────────────────────────────────────────┐ │
│   │                        Managed Hosts                                   │ │
│   │                                                                        │ │
│   │  VLAN 20: k8s-controller01-03, k8s-worker01-06                       │ │
│   │  VLAN 40: docker-vm-*, traefik-vm01, authentik-vm01, immich-vm01     │ │
│   └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Initial Controller Configuration

### Access Controller

```bash
# From workstation
ssh hermes-admin@192.168.20.30
```

### Install Ansible

```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Ansible
sudo apt install -y ansible

# Verify installation
ansible --version
```

**Expected output**:
```
ansible [core 2.16.x]
  config file = /etc/ansible/ansible.cfg
  configured module search path = ['/home/hermes-admin/.ansible/plugins/modules']
  ansible python module location = /usr/lib/python3/dist-packages/ansible
  executable location = /usr/bin/ansible
  python version = 3.12.x
```

### Directory Structure Setup

```bash
# Create ansible directory
mkdir -p ~/ansible/{docker,k8s,traefik,authentik,immich,n8n,opnsense,synology}
mkdir -p ~/ansible/{group_vars,host_vars,roles,files,templates}

# Create base files
touch ~/ansible/{ansible.cfg,inventory.ini}
```

---

## Configuration Files

### ansible.cfg

**File**: `~/ansible/ansible.cfg`

```ini
[defaults]
# Inventory file location
inventory = ./inventory.ini

# SSH user
remote_user = hermes-admin

# SSH key
private_key_file = ~/.ssh/id_ed25519

# Disable host key checking (homelab only)
host_key_checking = False

# Python interpreter
interpreter_python = /usr/bin/python3

# Parallelism
forks = 10

# Output formatting
stdout_callback = yaml

# Retry files
retry_files_enabled = False

# Gathering
gathering = smart
fact_caching = memory
fact_caching_timeout = 3600

[privilege_escalation]
become = True
become_method = sudo
become_user = root
become_ask_pass = False

[ssh_connection]
# SSH connection settings
pipelining = True
ssh_args = -o ControlMaster=auto -o ControlPersist=60s -o UserKnownHostsFile=/dev/null
```

**Key settings explained**:

| Setting | Purpose |
|---------|---------|
| `inventory` | Default inventory file |
| `remote_user` | SSH username |
| `private_key_file` | SSH private key |
| `host_key_checking = False` | Skip SSH fingerprint verification |
| `forks = 10` | Run on 10 hosts simultaneously |
| `pipelining = True` | Faster execution (fewer SSH connections) |

### SSH Key Setup

```bash
# Generate SSH key if not exists
ssh-keygen -t ed25519 -C "ansible@controller"

# Copy key to all managed hosts
ssh-copy-id hermes-admin@192.168.20.32   # k8s-controller01
ssh-copy-id hermes-admin@192.168.40.10   # docker-vm-utilities01
# ... repeat for all hosts
```

**Automated key distribution**:
```bash
# For hosts already accessible with existing key
for ip in 32 33 34 40 41 42 43 44 45; do
    ssh-copy-id hermes-admin@192.168.20.$ip
done

for ip in 10 11 20 21 22 23; do
    ssh-copy-id hermes-admin@192.168.40.$ip
done
```

---

## Inventory Configuration

### inventory.ini

**File**: `~/ansible/inventory.ini`

```ini
# =============================================================================
# Kubernetes Cluster
# =============================================================================

[k8s_controllers]
k8s-controller01 ansible_host=192.168.20.32
k8s-controller02 ansible_host=192.168.20.33
k8s-controller03 ansible_host=192.168.20.34

[k8s_workers]
k8s-worker01 ansible_host=192.168.20.40
k8s-worker02 ansible_host=192.168.20.41
k8s-worker03 ansible_host=192.168.20.42
k8s-worker04 ansible_host=192.168.20.43
k8s-worker05 ansible_host=192.168.20.44
k8s-worker06 ansible_host=192.168.20.45

[k8s:children]
k8s_controllers
k8s_workers

# =============================================================================
# Docker Hosts
# =============================================================================

[docker_hosts]
docker-vm-utilities01 ansible_host=192.168.40.10
docker-vm-media01 ansible_host=192.168.40.11

# =============================================================================
# Application Services
# =============================================================================

[services]
traefik-vm01 ansible_host=192.168.40.20
authentik-vm01 ansible_host=192.168.40.21
immich-vm01 ansible_host=192.168.40.22
gitlab-vm01 ansible_host=192.168.40.23

# =============================================================================
# Infrastructure
# =============================================================================

[logging]
linux-syslog-server01 ansible_host=192.168.40.5

# =============================================================================
# All Hosts Configuration
# =============================================================================

[all:vars]
ansible_user=hermes-admin
ansible_ssh_private_key_file=~/.ssh/id_ed25519
ansible_python_interpreter=/usr/bin/python3
```

---

## Group Variables

### all.yml

**File**: `~/ansible/group_vars/all.yml`

```yaml
---
# Common variables for all hosts

# User configuration
admin_user: hermes-admin

# DNS
dns_server: 192.168.91.30
domain: hrmsmrflrii.xyz

# NTP
ntp_servers:
  - 0.pool.ntp.org
  - 1.pool.ntp.org

# Packages to install on all hosts
common_packages:
  - curl
  - wget
  - htop
  - vim
  - git
  - jq

# Docker registry (if using private)
# docker_registry: registry.hrmsmrflrii.xyz
```

### docker_hosts.yml

**File**: `~/ansible/group_vars/docker_hosts.yml`

```yaml
---
# Docker host configuration

docker_compose_version: "2.24.0"

# Docker daemon configuration
docker_daemon_config:
  log-driver: "json-file"
  log-opts:
    max-size: "10m"
    max-file: "3"
  storage-driver: "overlay2"

# Default Docker network
docker_network_name: traefik

# Base directory for Docker apps
docker_base_dir: /opt
```

### k8s.yml

**File**: `~/ansible/group_vars/k8s.yml`

```yaml
---
# Kubernetes cluster configuration

k8s_version: "1.28"
k8s_pod_network_cidr: "10.244.0.0/16"
k8s_service_cidr: "10.96.0.0/12"

# Container runtime
container_runtime: containerd
containerd_version: "1.7"

# CNI
cni_plugin: calico
calico_version: "3.27.0"

# Control plane endpoint (for HA)
k8s_control_plane_endpoint: "192.168.20.32:6443"
```

---

## Verify Connectivity

### Ping All Hosts

```bash
cd ~/ansible
ansible all -m ping
```

**Expected output**:
```yaml
k8s-controller01 | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
docker-vm-media01 | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
# ... all hosts showing SUCCESS
```

### Test Specific Groups

```bash
# Ping only K8s nodes
ansible k8s -m ping

# Ping Docker hosts
ansible docker_hosts -m ping
```

### Gather Facts

```bash
# Get system info from all hosts
ansible all -m setup -a "filter=ansible_distribution*"
```

---

## Sync Playbooks from Repository

### Initial Clone

```bash
# Clone repository to controller
cd ~
git clone https://github.com/herms14/Proxmox-TerraformDeployments.git

# Link or copy ansible directory
ln -s ~/Proxmox-TerraformDeployments/ansible ~/ansible

# Or copy specific playbooks
cp -r ~/Proxmox-TerraformDeployments/ansible/* ~/ansible/
```

### Update Playbooks

```bash
cd ~/Proxmox-TerraformDeployments
git pull origin master
```

### Ansible Playbook for Sync

**File**: `sync-playbooks.yml`

```yaml
---
- name: Sync playbooks from Git repository
  hosts: localhost
  gather_facts: no

  tasks:
    - name: Ensure repo is cloned
      git:
        repo: https://github.com/herms14/Proxmox-TerraformDeployments.git
        dest: ~/Proxmox-TerraformDeployments
        version: master
        update: yes
        force: yes

    - name: Sync ansible directory
      synchronize:
        src: ~/Proxmox-TerraformDeployments/ansible/
        dest: ~/ansible/
        recursive: yes
        delete: no
      delegate_to: localhost
```

---

## Common Operations

### Run Playbook

```bash
cd ~/ansible

# Install Docker on all Docker hosts
ansible-playbook docker/install-docker.yml

# Deploy Arr stack
ansible-playbook docker/deploy-arr-stack.yml

# Limit to specific host
ansible-playbook docker/deploy-arr-stack.yml -l docker-vm-media01
```

### Ad-Hoc Commands

```bash
# Check uptime on all hosts
ansible all -a "uptime"

# Update all packages
ansible all -m apt -a "upgrade=dist update_cache=yes" -b

# Restart Docker on Docker hosts
ansible docker_hosts -m systemd -a "name=docker state=restarted" -b

# Check disk space
ansible all -a "df -h"
```

### Dry Run

```bash
# Preview changes without applying
ansible-playbook docker/install-docker.yml --check --diff
```

---

## Credentials Management

### Environment Variables

Set sensitive variables via environment:

```bash
# Add to ~/.bashrc
export OPNSENSE_API_KEY="your-key"
export OPNSENSE_API_SECRET="your-secret"
export CLOUDFLARE_DNS_API_TOKEN="your-token"
```

### Ansible Vault (Recommended)

```bash
# Create encrypted file
ansible-vault create ~/ansible/vault.yml

# Edit encrypted file
ansible-vault edit ~/ansible/vault.yml

# Use in playbook
ansible-playbook deploy.yml --ask-vault-pass
# Or
ansible-playbook deploy.yml --vault-password-file ~/.vault_pass
```

**vault.yml** example:
```yaml
vault_opnsense_api_key: "your-key"
vault_opnsense_api_secret: "your-secret"
vault_cloudflare_token: "your-token"
```

**Usage in playbook**:
```yaml
vars_files:
  - vault.yml

tasks:
  - name: Use secret
    uri:
      url: "https://api.example.com"
      headers:
        Authorization: "Bearer {{ vault_cloudflare_token }}"
```

---

## Troubleshooting

### SSH Connection Failed

**Error**: `UNREACHABLE`

**Diagnosis**:
```bash
# Test direct SSH
ssh hermes-admin@192.168.20.40

# Check SSH key
ssh-add -l

# Verbose ansible
ansible all -m ping -vvvv
```

**Fixes**:
- Verify SSH key is correct in ansible.cfg
- Check target host SSH service running
- Verify network connectivity

### Permission Denied (sudo)

**Error**: `Missing sudo password`

**Fix**: Ensure `ansible_become_password` or passwordless sudo:

```bash
# On target host, add to /etc/sudoers
hermes-admin ALL=(ALL) NOPASSWD: ALL
```

### Python Not Found

**Error**: `python interpreter not found`

**Fix**: Set interpreter in inventory:
```ini
[all:vars]
ansible_python_interpreter=/usr/bin/python3
```

---

## Maintenance Tasks

### Update All Systems

```bash
ansible all -m apt -a "upgrade=dist update_cache=yes" -b
```

### Reboot All (Rolling)

```yaml
---
- name: Rolling reboot
  hosts: all
  serial: 1
  tasks:
    - name: Reboot
      reboot:
        reboot_timeout: 300
```

### Check Service Status

```bash
ansible docker_hosts -m systemd -a "name=docker" -b
```

---

## What's Next?

- **[Inventory Management](Inventory-Management)** - Advanced inventory patterns
- **[Playbook Guide](Playbook-Guide)** - Production playbooks
- **[Services Overview](Services-Overview)** - Deploy services

---

*The controller is your command center. Keep it organized and secure.*
