# Disaster Recovery Guide

> **Complete Rebuild Documentation** - Step-by-step guide to rebuild the entire homelab infrastructure from scratch.

Last Updated: December 20, 2025

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Network Infrastructure](#phase-1-network-infrastructure)
3. [Phase 2: Storage Infrastructure](#phase-2-storage-infrastructure)
4. [Phase 3: Proxmox Cluster](#phase-3-proxmox-cluster)
5. [Phase 4: VM Templates](#phase-4-vm-templates)
6. [Phase 5: Terraform Deployment](#phase-5-terraform-deployment)
7. [Phase 6: Ansible Configuration](#phase-6-ansible-configuration)
8. [Phase 7: Kubernetes Cluster](#phase-7-kubernetes-cluster)
9. [Phase 8: Docker Services](#phase-8-docker-services)
10. [Phase 9: DNS and SSL](#phase-9-dns-and-ssl)
11. [Phase 10: Verification](#phase-10-verification)
12. [Recovery Time Estimates](#recovery-time-estimates)
13. [Backup Recommendations](#backup-recommendations)

---

## Prerequisites

### Hardware Requirements

| Component | Specification | Quantity |
|-----------|---------------|----------|
| Proxmox Nodes | 64GB+ RAM, 8+ cores, 500GB+ SSD | 3 |
| NAS | Synology DS920+ or equivalent | 1 |
| Router/Firewall | OPNsense-compatible device | 1 |
| Network Switch | Managed, VLAN-capable | 1 |

### Software/Accounts Required

- Proxmox VE 9.x ISO
- Ubuntu 24.04 Server ISO
- OPNsense ISO (latest stable)
- Domain name with Cloudflare DNS (hrmsmrflrii.xyz)
- Cloudflare API token for DNS-01 challenge
- GitHub account for repository access

### Documentation to Have Ready

- This repository: `tf-proxmox`
- SSH keys (or generate new ones)
- All service credentials from password manager

---

## Phase 1: Network Infrastructure

### 1.1 OPNsense Firewall Setup

**Estimated Time: 1-2 hours**

#### Install OPNsense

1. Boot from OPNsense ISO
2. Run installer with default options
3. Set root password
4. Configure initial network interfaces

#### Configure Interfaces

```
WAN Interface: igb0 (or first NIC)
  - DHCP or Static IP from ISP
  - Gateway: ISP provided

LAN Interface: igb1 (or second NIC)
  - IP: 192.168.91.30/24
  - No gateway (this is the gateway for internal networks)
```

#### Create VLANs

Navigate to: **Interfaces > Other Types > VLAN**

| VLAN ID | Parent | Description | Interface IP |
|---------|--------|-------------|--------------|
| 20 | igb1 | Kubernetes Infrastructure | 192.168.20.1/24 |
| 40 | igb1 | Services & Management | 192.168.40.1/24 |

#### Assign VLAN Interfaces

1. Go to **Interfaces > Assignments**
2. Add each VLAN as a new interface
3. Enable each interface and assign IPs:
   - VLAN20: 192.168.20.1/24
   - VLAN40: 192.168.40.1/24

#### Configure DHCP (Optional)

Navigate to: **Services > ISC DHCPv4**

For VLAN 20:
```
Range: 192.168.20.200 - 192.168.20.254
Gateway: 192.168.20.1
DNS: 192.168.91.30
```

For VLAN 40:
```
Range: 192.168.40.200 - 192.168.40.254
Gateway: 192.168.40.1
DNS: 192.168.91.30
```

#### Firewall Rules

Navigate to: **Firewall > Rules > [Each Interface]**

**VLAN20 Rules:**
```
Action: Pass
Protocol: Any
Source: VLAN20 net
Destination: Any
Description: Allow all from VLAN20
```

**VLAN40 Rules:**
```
Action: Pass
Protocol: Any
Source: VLAN40 net
Destination: Any
Description: Allow all from VLAN40
```

**Inter-VLAN Routing:**
```
Action: Pass
Protocol: Any
Source: VLAN20 net
Destination: VLAN40 net
Description: Allow VLAN20 to VLAN40

Action: Pass
Protocol: Any
Source: VLAN40 net
Destination: VLAN20 net
Description: Allow VLAN40 to VLAN20
```

#### Configure Unbound DNS

Navigate to: **Services > Unbound DNS > General**

```
Enable: Yes
Listen Port: 53
Network Interfaces: All
DNSSEC: Enable
DNS Query Forwarding: Enable (use Cloudflare 1.1.1.1)
```

#### DNS Host Overrides

Navigate to: **Services > Unbound DNS > Host Overrides**

Add all service DNS records pointing to Traefik (192.168.40.20):

| Host | Domain | IP Address |
|------|--------|------------|
| traefik | hrmsmrflrii.xyz | 192.168.40.20 |
| proxmox | hrmsmrflrii.xyz | 192.168.40.20 |
| node01 | hrmsmrflrii.xyz | 192.168.40.20 |
| node02 | hrmsmrflrii.xyz | 192.168.40.20 |
| node03 | hrmsmrflrii.xyz | 192.168.40.20 |
| auth | hrmsmrflrii.xyz | 192.168.40.20 |
| photos | hrmsmrflrii.xyz | 192.168.40.20 |
| gitlab | hrmsmrflrii.xyz | 192.168.40.20 |
| jellyfin | hrmsmrflrii.xyz | 192.168.40.20 |
| radarr | hrmsmrflrii.xyz | 192.168.40.20 |
| sonarr | hrmsmrflrii.xyz | 192.168.40.20 |
| lidarr | hrmsmrflrii.xyz | 192.168.40.20 |
| prowlarr | hrmsmrflrii.xyz | 192.168.40.20 |
| bazarr | hrmsmrflrii.xyz | 192.168.40.20 |
| overseerr | hrmsmrflrii.xyz | 192.168.40.20 |
| jellyseerr | hrmsmrflrii.xyz | 192.168.40.20 |
| tdarr | hrmsmrflrii.xyz | 192.168.40.20 |
| autobrr | hrmsmrflrii.xyz | 192.168.40.20 |
| paperless | hrmsmrflrii.xyz | 192.168.40.20 |
| glance | hrmsmrflrii.xyz | 192.168.40.20 |
| n8n | hrmsmrflrii.xyz | 192.168.40.20 |
| speedtest | hrmsmrflrii.xyz | 192.168.40.20 |

### 1.2 Network Switch Configuration

Configure managed switch with VLAN trunk ports:

```
Port 1-8: Access VLAN 20 (Proxmox nodes)
Port 9-16: Access VLAN 40 (Services)
Port 24: Trunk (all VLANs) to OPNsense
```

---

## Phase 2: Storage Infrastructure

### 2.1 Synology NAS Configuration

**Estimated Time: 1-2 hours**

#### Initial Setup

1. Install DSM 7.x via web interface
2. Create storage pool (RAID 5/6 recommended)
3. Create volume on storage pool

#### Create Shared Folders

Navigate to: **Control Panel > Shared Folder**

| Folder Name | Path | Purpose |
|-------------|------|---------|
| ProxmoxCluster-VMDisks | /volume2/ProxmoxCluster-VMDisks | VM disk images |
| ProxmoxCluster-ISOs | /volume2/ProxmoxCluster-ISOs | ISO files |
| Proxmox-LXCs | /volume2/Proxmox-LXCs | LXC configs |
| Proxmox-Media | /volume2/Proxmox-Media | Media files |
| ProxmoxData | /volume2/ProxmoxData | Application data |

#### Configure NFS Permissions

Navigate to: **Control Panel > Shared Folder > [folder] > NFS Permissions**

For each folder, add rule:
```
Server/IP: 192.168.20.0/24
Privilege: Read/Write
Squash: Map root to admin
Security: sys
Enable async: Yes
Allow non-privileged ports: Yes
```

Repeat for 192.168.40.0/24 subnet.

#### Create Media Directory Structure

```bash
# SSH to NAS or use File Station
mkdir -p /volume2/Proxmox-Media/Movies
mkdir -p /volume2/Proxmox-Media/Series
mkdir -p /volume2/Proxmox-Media/Music
mkdir -p /volume2/Proxmox-Media/Downloads

# Set permissions
chmod -R 777 /volume2/Proxmox-Media
```

---

## Phase 3: Proxmox Cluster

### 3.1 Install Proxmox VE on All Nodes

**Estimated Time: 2-3 hours**

#### Node Installation (Repeat for each node)

1. Boot from Proxmox VE ISO
2. Select target disk for installation
3. Configure network:

**Node01:**
```
IP: 192.168.20.20/24
Gateway: 192.168.20.1
DNS: 192.168.91.30
Hostname: node01.hrmsmrflrii.xyz
```

**Node02:**
```
IP: 192.168.20.21/24
Gateway: 192.168.20.1
DNS: 192.168.91.30
Hostname: node02.hrmsmrflrii.xyz
```

**Node03:**
```
IP: 192.168.20.22/24
Gateway: 192.168.20.1
DNS: 192.168.91.30
Hostname: node03.hrmsmrflrii.xyz
```

### 3.2 Configure VLAN-Aware Bridge

**CRITICAL: Must be done on ALL nodes**

SSH to each node and edit `/etc/network/interfaces`:

```bash
auto lo
iface lo inet loopback

auto nic0
iface nic0 inet manual

auto vmbr0
iface vmbr0 inet static
    address 192.168.20.XX/24   # XX = 20, 21, or 22
    gateway 192.168.20.1
    bridge-ports nic0
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes      # CRITICAL
    bridge-vids 2-4094         # CRITICAL

source /etc/network/interfaces.d/*
```

Apply changes:
```bash
ifreload -a
# OR reboot
reboot
```

Verify:
```bash
ip -d link show vmbr0 | grep vlan_filtering
# Should show: vlan_filtering 1
```

### 3.3 Create Proxmox Cluster

**On Node01 (Primary):**
```bash
pvecm create homelab-cluster
```

**On Node02 and Node03:**
```bash
pvecm add 192.168.20.20
```

**Verify Cluster:**
```bash
pvecm status
```

Expected output:
```
Cluster information
-------------------
Name:             homelab-cluster
Config Version:   3
Transport:        knet
Secure auth:      on

Quorum information
------------------
Date:             [current date]
Quorum provider:  corosync_votequorum
Nodes:            3
Node ID:          0x00000001
Ring ID:          1.XXX
Quorate:          Yes

Votequorum information
----------------------
Expected votes:   3
Highest expected: 3
Total votes:      3
Quorum:           2
Flags:            Quorate
```

### 3.4 Configure Storage in Proxmox

Navigate to: **Datacenter > Storage > Add > NFS**

**VMDisks Storage:**
```
ID: VMDisks
Server: 192.168.20.31
Export: /volume2/ProxmoxCluster-VMDisks
Content: Disk image, Container
Nodes: All
```

**ISOs Storage:**
```
ID: ISOs
Server: 192.168.20.31
Export: /volume2/ProxmoxCluster-ISOs
Content: ISO image, Container template
Nodes: All
```

### 3.5 Configure Manual NFS Mounts

On each Proxmox node, edit `/etc/fstab`:

```bash
192.168.20.31:/volume2/Proxmox-LXCs   /mnt/nfs/lxcs   nfs  defaults,_netdev  0  0
192.168.20.31:/volume2/Proxmox-Media  /mnt/nfs/media  nfs  defaults,_netdev  0  0
```

Create mount points and mount:
```bash
mkdir -p /mnt/nfs/lxcs /mnt/nfs/media
mount -a
df -h | grep /mnt/nfs
```

### 3.6 Create API Token for Terraform

Navigate to: **Datacenter > Permissions > API Tokens > Add**

```
User: root@pam
Token ID: tf
Privilege Separation: Unchecked (full permissions)
```

Save the token secret - you'll need it for Terraform!

---

## Phase 4: VM Templates

### 4.1 Download Ubuntu Cloud Image

```bash
# On node01
cd /var/lib/vz/template/iso
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
```

### 4.2 Create Cloud-Init Template

```bash
# Create VM
qm create 9000 --name "tpl-ubuntuv24.04-v1" --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0

# Import cloud image to VM
qm importdisk 9000 /var/lib/vz/template/iso/noble-server-cloudimg-amd64.img VMDisks

# Attach disk
qm set 9000 --scsihw virtio-scsi-single --scsi0 VMDisks:vm-9000-disk-0

# Add cloud-init drive
qm set 9000 --ide2 VMDisks:cloudinit

# Set boot order
qm set 9000 --boot order=scsi0

# Enable UEFI
qm set 9000 --bios ovmf --machine q35
qm set 9000 --efidisk0 VMDisks:1,efitype=4m,pre-enrolled-keys=1

# Enable QEMU agent
qm set 9000 --agent enabled=1

# Set cloud-init defaults
qm set 9000 --ciuser hermes-admin
qm set 9000 --sshkeys ~/.ssh/authorized_keys
qm set 9000 --ipconfig0 ip=dhcp

# Convert to template
qm template 9000
```

### 4.3 Create Shared Template

Repeat the process for `tpl-ubuntu-shared-v1` (ID 9001) with same configuration.

---

## Phase 5: Terraform Deployment

### 5.1 Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/tf-proxmox.git
cd tf-proxmox
```

### 5.2 Create terraform.tfvars

```hcl
# Proxmox API Configuration
proxmox_api_url  = "https://192.168.20.21:8006/api2/json"
proxmox_user     = "root@pam!tf"
proxmox_password = "YOUR_TOKEN_SECRET"

# Cloud-init Configuration
ci_user        = "hermes-admin"
ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAby7br+5MzyDus2fi2UFjUBZvGucN40Gxa29bgUTbfz hermes@homelab"
```

### 5.3 Initialize and Apply Terraform

```bash
# Initialize
terraform init

# Plan
terraform plan -out=recovery.tfplan

# Apply
terraform apply recovery.tfplan
```

### 5.4 Verify VM Deployment

```bash
# Check all VMs are created
terraform output vm_summary

# Verify connectivity
for ip in 192.168.20.30 192.168.20.32 192.168.20.33 192.168.20.34 192.168.20.40 192.168.20.41 192.168.20.42 192.168.20.43 192.168.20.44 192.168.20.45 192.168.40.5 192.168.40.10 192.168.40.11 192.168.40.20 192.168.40.21 192.168.40.22 192.168.40.23; do
  echo -n "$ip: "
  timeout 3 ssh -o StrictHostKeyChecking=no hermes-admin@$ip "hostname" 2>/dev/null || echo "UNREACHABLE"
done
```

---

## Phase 6: Ansible Configuration

### 6.1 Setup Ansible Controller

SSH to ansible-controller01 (192.168.20.30):

```bash
# Install Ansible
sudo apt update
sudo apt install -y python3-pip python3-venv
python3 -m pip install --user ansible ansible-core

# Create ansible directory
mkdir -p ~/ansible
cd ~/ansible
```

### 6.2 Create Inventory File

Create `~/ansible/inventory.ini`:

```ini
# Ansible Inventory for Homelab Infrastructure

[all:vars]
ansible_user=hermes-admin
ansible_ssh_common_args='-o StrictHostKeyChecking=accept-new'

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

[kubernetes:children]
k8s_controllers
k8s_workers

[docker_utilities]
docker-vm-utilities01 ansible_host=192.168.40.10

[docker_media]
docker-vm-media01 ansible_host=192.168.40.11

[docker_hosts:children]
docker_utilities
docker_media

[reverse_proxy]
traefik-vm01 ansible_host=192.168.40.20

[identity_management]
authentik-vm01 ansible_host=192.168.40.21

[media_services]
immich-vm01 ansible_host=192.168.40.22

[devops]
gitlab-vm01 ansible_host=192.168.40.23

[logging]
linux-syslog-server01 ansible_host=192.168.40.5
```

### 6.3 Create Ansible Configuration

Create `~/ansible/ansible.cfg`:

```ini
[defaults]
inventory = inventory.ini
host_key_checking = False
retry_files_enabled = False
log_path = ansible.log

[ssh_connection]
ssh_args = -o ControlMaster=auto -o ControlPersist=60s
pipelining = True
```

### 6.4 Generate SSH Key

```bash
ssh-keygen -t ed25519 -C "ansible@homelab" -f ~/.ssh/id_ed25519 -N ""

# Copy to all hosts
for ip in 192.168.20.32 192.168.20.33 192.168.20.34 192.168.20.40 192.168.20.41 192.168.20.42 192.168.20.43 192.168.20.44 192.168.20.45 192.168.40.5 192.168.40.10 192.168.40.11 192.168.40.20 192.168.40.21 192.168.40.22 192.168.40.23; do
  ssh-copy-id -o StrictHostKeyChecking=no hermes-admin@$ip
done
```

### 6.5 Test Connectivity

```bash
ansible all -m ping
```

---

## Phase 7: Kubernetes Cluster

### 7.1 Copy Kubernetes Playbooks

Copy the `k8s/` directory from the repository to `~/ansible/k8s/` on ansible-controller01.

### 7.2 Deploy Kubernetes

```bash
cd ~/ansible

# Deploy full cluster
ansible-playbook k8s/k8s-deploy-all.yml
```

This will:
1. Install container runtime (containerd)
2. Install kubeadm, kubelet, kubectl
3. Initialize primary controller
4. Join secondary controllers for HA
5. Join worker nodes
6. Install Calico CNI

### 7.3 Verify Cluster

```bash
# On any controller
kubectl get nodes
kubectl get pods -A
```

Expected output:
```
NAME               STATUS   ROLES           AGE   VERSION
k8s-controller01   Ready    control-plane   10m   v1.28.15
k8s-controller02   Ready    control-plane   8m    v1.28.15
k8s-controller03   Ready    control-plane   6m    v1.28.15
k8s-worker01       Ready    <none>          4m    v1.28.15
k8s-worker02       Ready    <none>          4m    v1.28.15
k8s-worker03       Ready    <none>          4m    v1.28.15
k8s-worker04       Ready    <none>          4m    v1.28.15
k8s-worker05       Ready    <none>          4m    v1.28.15
k8s-worker06       Ready    <none>          4m    v1.28.15
```

---

## Phase 8: Docker Services

### 8.1 Install Docker on All Docker Hosts

```bash
ansible-playbook docker/install-docker.yml
```

### 8.2 Deploy Traefik Reverse Proxy

```bash
ansible-playbook traefik/deploy-traefik.yml
```

Verify: http://192.168.40.20:8080

### 8.3 Deploy Authentik

```bash
ansible-playbook authentik/deploy-authentik.yml
```

Initial setup: http://192.168.40.21:9000/if/flow/initial-setup/

### 8.4 Deploy Immich

```bash
ansible-playbook immich/deploy-immich.yml
```

Access: http://192.168.40.22:2283

### 8.5 Deploy GitLab

```bash
ansible-playbook gitlab/deploy-gitlab.yml
```

Get initial password:
```bash
ssh hermes-admin@192.168.40.23 "sudo docker exec gitlab grep 'Password:' /etc/gitlab/initial_root_password"
```

### 8.6 Deploy Arr Media Stack

```bash
ansible-playbook docker/deploy-arr-stack.yml
```

Services will be available at:
- Jellyfin: http://192.168.40.11:8096
- Radarr: http://192.168.40.11:7878
- Sonarr: http://192.168.40.11:8989
- And others...

### 8.7 Deploy n8n

```bash
ansible-playbook n8n/deploy-n8n.yml
```

Access: http://192.168.40.10:5678

---

## Phase 9: DNS and SSL

### 9.1 Configure Cloudflare DNS

In Cloudflare dashboard for hrmsmrflrii.xyz:

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | @ | Your Public IP | Yes |
| A | * | Your Public IP | Yes |

### 9.2 Create Cloudflare API Token

1. Go to Cloudflare Dashboard > Profile > API Tokens
2. Create Token with Zone:DNS:Edit permissions
3. Save token for Traefik configuration

### 9.3 Configure Traefik for SSL

SSH to traefik-vm01 and edit `/opt/traefik/config/traefik.yml`:

```yaml
certificatesResolvers:
  letsencrypt:
    acme:
      email: your-email@example.com
      storage: /etc/traefik/certs/acme.json
      dnsChallenge:
        provider: cloudflare
        delayBeforeCheck: 10
        resolvers:
          - "1.1.1.1:53"
          - "8.8.8.8:53"
```

Create `.env` file:
```bash
CF_API_EMAIL=your-email@example.com
CF_DNS_API_TOKEN=your-cloudflare-token
```

Restart Traefik:
```bash
cd /opt/traefik && sudo docker compose restart
```

### 9.4 Verify SSL

```bash
curl -I https://traefik.hrmsmrflrii.xyz
```

Should return 200 with valid certificate.

---

## Phase 10: Verification

### 10.1 Infrastructure Verification Checklist

```bash
#!/bin/bash
# Save as verify-infrastructure.sh

echo "=== Network Verification ==="
ping -c 1 192.168.91.30 && echo "OPNsense: OK" || echo "OPNsense: FAIL"
ping -c 1 192.168.20.31 && echo "NAS: OK" || echo "NAS: FAIL"

echo ""
echo "=== Proxmox Cluster ==="
ssh root@192.168.20.21 "pvecm status | grep -E 'Quorate|Nodes'"

echo ""
echo "=== Kubernetes Cluster ==="
ssh hermes-admin@192.168.20.32 "kubectl get nodes --no-headers | wc -l" | xargs echo "Nodes:"
ssh hermes-admin@192.168.20.32 "kubectl get nodes --no-headers | grep -c Ready" | xargs echo "Ready:"

echo ""
echo "=== Docker Services ==="
for svc in "192.168.40.20:8080 Traefik" "192.168.40.21:9000 Authentik" "192.168.40.22:2283 Immich" "192.168.40.23:80 GitLab" "192.168.40.11:8096 Jellyfin" "192.168.40.10:5678 n8n"; do
  ip=$(echo $svc | cut -d' ' -f1)
  name=$(echo $svc | cut -d' ' -f2)
  curl -s -o /dev/null -w "%{http_code}" http://$ip | grep -qE "200|302|301" && echo "$name: OK" || echo "$name: FAIL"
done

echo ""
echo "=== SSL Verification ==="
for url in traefik proxmox auth photos gitlab jellyfin n8n; do
  curl -sk -o /dev/null -w "%{http_code}" https://${url}.hrmsmrflrii.xyz | grep -qE "200|302|301" && echo "$url: OK" || echo "$url: FAIL"
done
```

### 10.2 Service Health Check

| Service | URL | Expected Status |
|---------|-----|-----------------|
| Traefik Dashboard | https://traefik.hrmsmrflrii.xyz | 200 |
| Proxmox | https://proxmox.hrmsmrflrii.xyz | 200/302 |
| Authentik | https://auth.hrmsmrflrii.xyz | 200/302 |
| Immich | https://photos.hrmsmrflrii.xyz | 200/302 |
| GitLab | https://gitlab.hrmsmrflrii.xyz | 200/302 |
| Jellyfin | https://jellyfin.hrmsmrflrii.xyz | 200/302 |
| n8n | https://n8n.hrmsmrflrii.xyz | 200/302 |

---

## Recovery Time Estimates

| Phase | Estimated Time | Dependencies |
|-------|---------------|--------------|
| Network Infrastructure | 1-2 hours | Hardware ready |
| Storage Infrastructure | 1-2 hours | Network ready |
| Proxmox Cluster | 2-3 hours | Network, Storage ready |
| VM Templates | 30 minutes | Proxmox ready |
| Terraform Deployment | 30-45 minutes | Templates ready |
| Ansible Configuration | 30 minutes | VMs running |
| Kubernetes Cluster | 45-60 minutes | Ansible ready |
| Docker Services | 2-3 hours | All infra ready |
| DNS and SSL | 30-60 minutes | Services running |
| **Total Estimated Time** | **8-12 hours** | |

---

## Backup Recommendations

### Critical Data to Backup

| Data | Location | Backup Method | Frequency |
|------|----------|---------------|-----------|
| Terraform State | Local + Remote | Git + S3/Cloud | Every change |
| Ansible Playbooks | Git repo | GitHub | Every change |
| VM Templates | Proxmox | Snapshot/Export | Monthly |
| Service Configs | /opt/* on VMs | Rsync to NAS | Daily |
| Database Backups | Various | pg_dump/mysqldump | Daily |
| Media Files | NAS | External backup | Weekly |
| SSL Certificates | Traefik acme.json | Copy to backup | Weekly |
| OPNsense Config | OPNsense | Built-in backup | Weekly |
| Proxmox Config | /etc/pve | Built-in backup | Weekly |

### Backup Commands

```bash
# Proxmox backup
vzdump 100 --storage VMDisks --mode snapshot

# OPNsense backup (via API)
curl -k -u "key:secret" https://192.168.91.30/api/core/backup/download/this

# Service config backup
rsync -avz hermes-admin@192.168.40.10:/opt/ /backup/docker-utilities/
rsync -avz hermes-admin@192.168.40.11:/opt/ /backup/docker-media/
rsync -avz hermes-admin@192.168.40.20:/opt/ /backup/traefik/
```

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Main infrastructure documentation
- [INVENTORY.md](./INVENTORY.md) - Current deployment inventory
- [SERVICES.md](./SERVICES.md) - Service configuration details
- [NETWORKING.md](./NETWORKING.md) - Network architecture
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common issues and fixes

---

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-20 | Claude | Initial DR documentation |
