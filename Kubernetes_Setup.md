# Kubernetes Cluster Setup Documentation

## Table of Contents
- [Overview](#overview)
- [Infrastructure](#infrastructure)
- [Prerequisites](#prerequisites)
- [Setup Process](#setup-process)
- [Ansible Playbooks Explained](#ansible-playbooks-explained)
- [Deployment Steps](#deployment-steps)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Post-Installation](#post-installation)

---

## Overview

This document provides comprehensive documentation for deploying a production-grade Kubernetes cluster on Proxmox VMs using Ansible automation.

**Cluster Specifications:**
- **Control Plane**: 3 nodes (High Availability)
- **Worker Nodes**: 6 nodes
- **Total Nodes**: 9
- **Container Runtime**: containerd
- **CNI Plugin**: Calico
- **Kubernetes Version**: 1.28.x (configurable)

**Management:**
- **Ansible Controller**: ansible-controller01 (192.168.20.30)
- **Automation Tool**: Ansible
- **Authentication**: SSH key-based

---

## Infrastructure

### Kubernetes Cluster Nodes

| Node | IP Address | Role | Resources | VM ID | Host |
|------|------------|------|-----------|-------|------|
| k8s-controller01 | 192.168.20.32 | Control Plane (Primary) | 2 CPU, 4GB RAM, 20GB | 110 | node03 |
| k8s-controller02 | 192.168.20.33 | Control Plane | 2 CPU, 4GB RAM, 20GB | 105 | node03 |
| k8s-controller03 | 192.168.20.34 | Control Plane | 2 CPU, 4GB RAM, 20GB | 104 | node03 |
| k8s-worker01 | 192.168.20.40 | Worker | 2 CPU, 4GB RAM, 20GB | 112 | node03 |
| k8s-worker02 | 192.168.20.41 | Worker | 2 CPU, 4GB RAM, 20GB | 101 | node03 |
| k8s-worker03 | 192.168.20.42 | Worker | 2 CPU, 4GB RAM, 20GB | 115 | node03 |
| k8s-worker04 | 192.168.20.43 | Worker | 2 CPU, 4GB RAM, 20GB | 116 | node03 |
| k8s-worker05 | 192.168.20.44 | Worker | 2 CPU, 4GB RAM, 20GB | 118 | node03 |
| k8s-worker06 | 192.168.20.45 | Worker | 2 CPU, 4GB RAM, 20GB | 117 | node03 |

### Network Configuration
- **VLAN**: 20 (192.168.20.0/24)
- **Gateway**: 192.168.20.1
- **DNS**: 192.168.20.1
- **Pod Network CIDR**: 10.244.0.0/16 (Calico)
- **Service CIDR**: 10.96.0.0/12 (Kubernetes default)

---

## Prerequisites

### 1. Infrastructure Requirements

**All VMs must be:**
- Running Ubuntu 24.04 LTS
- Accessible via SSH from ansible-controller01
- Have hermes-admin user with sudo privileges
- Have SSH keys configured for passwordless access

### 2. SSH Key Configuration

**For New VMs (not yet configured):**

SSH keys must be added to allow ansible-controller01 to manage the nodes:

```bash
# ansible-controller01's public key:
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILNaYM/nUFmslKMJ77SIuiT/1CQot2NbtBTP8zdXP2d6 hermes-admin@ansible-controller01

# Add to each K8s node:
ssh hermes-admin@<node-ip> "echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILNaYM/nUFmslKMJ77SIuiT/1CQot2NbtBTP8zdXP2d6 hermes-admin@ansible-controller01' >> ~/.ssh/authorized_keys"
```

**Example - Add key to all nodes:**
```bash
for ip in 192.168.20.32 192.168.20.33 192.168.20.34 192.168.20.40 192.168.20.41 192.168.20.42 192.168.20.43 192.168.20.44 192.168.20.45; do
  echo "Configuring $ip..."
  ssh hermes-admin@$ip "echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILNaYM/nUFmslKMJ77SIuiT/1CQot2NbtBTP8zdXP2d6 hermes-admin@ansible-controller01' >> ~/.ssh/authorized_keys"
done
```

### 3. Verify Ansible Connectivity

From ansible-controller01:
```bash
cd ~/ansible
ansible kubernetes -m ping
```

**Expected output:** All nodes should return `pong`.

---

## Setup Process

The Kubernetes cluster setup is automated through 5 Ansible playbooks located at `~/ansible/k8s/` on ansible-controller01:

1. **01-k8s-prerequisites.yml** - System configuration
2. **02-k8s-install.yml** - Install Kubernetes packages
3. **03-k8s-init-cluster.yml** - Initialize cluster
4. **04-k8s-install-cni.yml** - Install networking (Calico)
5. **05-k8s-join-nodes.yml** - Join all nodes
6. **k8s-deploy-all.yml** - Master playbook (runs all above)

---

## Ansible Playbooks Explained

### Playbook 1: `01-k8s-prerequisites.yml`

**Purpose:** Prepare all nodes for Kubernetes installation by configuring system requirements.

**What it does:**

1. **Disables Swap**
   - **Why:** Kubernetes requires swap to be disabled for proper memory management
   - **Commands:**
     ```bash
     swapoff -a  # Disable swap immediately
     ```
   - **Config:** Removes swap entries from `/etc/fstab` to persist across reboots

2. **Loads Kernel Modules**
   - **Why:** Required for container networking and overlay filesystems
   - **Modules:**
     - `overlay` - Overlay filesystem for container layers
     - `br_netfilter` - Bridge netfilter for iptables to see bridged traffic
   - **Commands:**
     ```bash
     modprobe overlay
     modprobe br_netfilter
     ```
   - **Config:** Creates `/etc/modules-load.d/k8s.conf` to load modules on boot

3. **Configures sysctl Parameters**
   - **Why:** Enable IP forwarding and bridge traffic filtering for Kubernetes networking
   - **Parameters:**
     ```bash
     net.bridge.bridge-nf-call-iptables = 1   # Allow iptables to see bridged traffic
     net.bridge.bridge-nf-call-ip6tables = 1  # Same for IPv6
     net.ipv4.ip_forward = 1                  # Enable IP forwarding
     ```
   - **Config:** Creates `/etc/sysctl.d/k8s.conf` and applies with `sysctl --system`

4. **Installs containerd**
   - **Why:** Kubernetes needs a container runtime; containerd is lightweight and production-ready
   - **Packages:** `containerd`, `runc`
   - **Commands:**
     ```bash
     apt install -y containerd runc
     ```

5. **Configures containerd**
   - **Why:** Default config doesn't work with Kubernetes; need systemd cgroup driver
   - **Steps:**
     - Generate default config: `containerd config default > /etc/containerd/config.toml`
     - Modify to use systemd cgroup driver (matches kubelet)
     - Restart containerd service
   - **Config file:** `/etc/containerd/config.toml`
     ```toml
     [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
       SystemdCgroup = true  # Critical for Kubernetes compatibility
     ```

**Run this playbook:**
```bash
cd ~/ansible
ansible-playbook k8s/01-k8s-prerequisites.yml
```

---

### Playbook 2: `02-k8s-install.yml`

**Purpose:** Install Kubernetes packages (kubeadm, kubelet, kubectl) on all nodes.

**What it does:**

1. **Adds Kubernetes APT Repository**
   - **Why:** Get official Kubernetes packages with security updates
   - **Commands:**
     ```bash
     # Add GPG key
     curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | \
       gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

     # Add repository
     echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] \
       https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /" | \
       tee /etc/apt/sources.list.d/kubernetes.list

     apt update
     ```

2. **Installs Kubernetes Packages**
   - **Packages:**
     - `kubeadm` - Cluster bootstrapping tool
     - `kubelet` - Node agent that runs on every node
     - `kubectl` - Command-line tool for cluster management
   - **Commands:**
     ```bash
     apt install -y kubelet kubeadm kubectl
     ```

3. **Holds Package Versions**
   - **Why:** Prevent automatic upgrades that could break the cluster
   - **Commands:**
     ```bash
     apt-mark hold kubelet kubeadm kubectl
     ```
   - **To upgrade later:** Run `apt-mark unhold`, upgrade, then `apt-mark hold` again

4. **Enables kubelet Service**
   - **Why:** Ensure kubelet starts on boot (will wait for cluster join)
   - **Commands:**
     ```bash
     systemctl enable kubelet
     ```

**Run this playbook:**
```bash
cd ~/ansible
ansible-playbook k8s/02-k8s-install.yml
```

---

### Playbook 3: `03-k8s-init-cluster.yml`

**Purpose:** Initialize the Kubernetes cluster on the primary control plane node.

**What it does:**

1. **Initializes First Control Plane**
   - **Where:** k8s-controller01 (192.168.20.32)
   - **Why:** Bootstraps the cluster, creates certificates, starts control plane components
   - **Command:**
     ```bash
     kubeadm init \
       --pod-network-cidr=10.244.0.0/16 \
       --control-plane-endpoint=192.168.20.32:6443 \
       --upload-certs
     ```
   - **Parameters explained:**
     - `--pod-network-cidr`: IP range for pod networking (Calico default)
     - `--control-plane-endpoint`: API server endpoint for HA
     - `--upload-certs`: Uploads certificates to cluster for other control planes to join

2. **Sets Up kubeconfig**
   - **Why:** Allows kubectl to authenticate to the cluster
   - **Commands:**
     ```bash
     mkdir -p /home/hermes-admin/.kube
     cp /etc/kubernetes/admin.conf /home/hermes-admin/.kube/config
     chown hermes-admin:hermes-admin /home/hermes-admin/.kube/config
     chmod 600 /home/hermes-admin/.kube/config
     ```
   - **File:** `~/.kube/config` contains cluster connection info and admin credentials

3. **Generates Join Commands**
   - **Why:** Other nodes need these commands to join the cluster securely
   - **For Control Planes:**
     ```bash
     kubeadm token create --print-join-command \
       --certificate-key $(kubeadm init phase upload-certs --upload-certs 2>/dev/null | tail -1)
     ```
     - Includes certificate key for control plane components

   - **For Workers:**
     ```bash
     kubeadm token create --print-join-command
     ```
     - Basic join command without control plane certs

4. **Saves Join Commands**
   - **Location:** `~/ansible/k8s/join-command-controllers.sh`
   - **Location:** `~/ansible/k8s/join-command-workers.sh`
   - **Why:** Used by playbook 5 to join nodes automatically

**Run this playbook:**
```bash
cd ~/ansible
ansible-playbook k8s/03-k8s-init-cluster.yml
```

**After running, verify:**
```bash
ssh hermes-admin@192.168.20.32 "kubectl get nodes"
```

---

### Playbook 4: `04-k8s-install-cni.yml`

**Purpose:** Install Calico CNI (Container Network Interface) for pod networking.

**What it does:**

1. **Downloads Calico Manifest**
   - **Why:** Calico provides networking and network policy for Kubernetes
   - **Command:**
     ```bash
     curl -O https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/calico.yaml
     ```

2. **Applies Calico to Cluster**
   - **Why:** Enables pod-to-pod communication across nodes
   - **Command:**
     ```bash
     kubectl apply -f calico.yaml
     ```
   - **What it creates:**
     - calico-node DaemonSet (runs on every node)
     - calico-kube-controllers Deployment
     - NetworkPolicy CRDs

3. **Waits for Calico Pods**
   - **Why:** Ensure networking is ready before joining more nodes
   - **Command:**
     ```bash
     kubectl wait --for=condition=Ready pods --all -n kube-system \
       -l k8s-app=calico-node --timeout=300s
     ```

4. **Verifies Node Status**
   - **Why:** Nodes should move from "NotReady" to "Ready" once CNI is installed
   - **Command:**
     ```bash
     kubectl get nodes
     ```
   - **Expected:** Controller node(s) should show "Ready" status

**Run this playbook:**
```bash
cd ~/ansible
ansible-playbook k8s/04-k8s-install-cni.yml
```

---

### Playbook 5: `05-k8s-join-nodes.yml`

**Purpose:** Join remaining control plane nodes and all worker nodes to the cluster.

**What it does:**

1. **Joins Additional Control Planes**
   - **Targets:** k8s-controller02, k8s-controller03
   - **Why:** Creates HA control plane (3 nodes can tolerate 1 failure)
   - **Command:** Reads from `join-command-controllers.sh`
     ```bash
     kubeadm join 192.168.20.32:6443 --token <token> \
       --discovery-token-ca-cert-hash sha256:<hash> \
       --control-plane --certificate-key <cert-key>
     ```
   - **Wait time:** 15 seconds between nodes to allow cluster to stabilize

2. **Joins Worker Nodes**
   - **Targets:** k8s-worker01 through k8s-worker06
   - **Why:** Provide compute capacity for running application workloads
   - **Command:** Reads from `join-command-workers.sh`
     ```bash
     kubeadm join 192.168.20.32:6443 --token <token> \
       --discovery-token-ca-cert-hash sha256:<hash>
     ```
   - **Serial execution:** Joins 2 workers at a time to avoid overwhelming cluster

3. **Verifies All Nodes**
   - **Command:**
     ```bash
     kubectl get nodes
     ```
   - **Expected:** 9 nodes total, all in "Ready" state
   - **Validation:** Playbook fails if less than 9 nodes are ready

**Run this playbook:**
```bash
cd ~/ansible
ansible-playbook k8s/05-k8s-join-nodes.yml
```

---

### Master Playbook: `k8s-deploy-all.yml`

**Purpose:** Orchestrate complete cluster deployment from scratch.

**What it does:**
- Runs all 5 playbooks in sequence
- Provides status messages between stages
- Displays completion message with next steps

**Run full deployment:**
```bash
cd ~/ansible
ansible-playbook k8s/k8s-deploy-all.yml
```

**Execution time:** Approximately 15-20 minutes for full deployment.

---

## Deployment Steps

### Step 1: Ensure All VMs Are Running

**Check VM status:**
```bash
# From local machine
for ip in 192.168.20.{32..34} 192.168.20.{40..45}; do
  ping -c 1 -W 1 $ip > /dev/null 2>&1 && echo "$ip: UP" || echo "$ip: DOWN"
done
```

**Start VMs if needed:**
```bash
# From Proxmox node03
ssh root@192.168.20.22
for vmid in 110 105 104 112 101 115 116 118 117; do
  qm start $vmid
done
```

**Wait for VMs to boot:** ~60 seconds for cloud-init to complete.

### Step 2: Configure SSH Access

**Add ansible-controller01's SSH key to all K8s nodes:**
```bash
# From local machine
PUBKEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILNaYM/nUFmslKMJ77SIuiT/1CQot2NbtBTP8zdXP2d6 hermes-admin@ansible-controller01"

for ip in 192.168.20.{32..34} 192.168.20.{40..45}; do
  echo "Configuring $ip..."
  ssh hermes-admin@$ip "echo '$PUBKEY' >> ~/.ssh/authorized_keys"
done
```

### Step 3: Verify Ansible Connectivity

**SSH to ansible-controller01:**
```bash
ssh hermes-admin@192.168.20.30
cd ~/ansible
```

**Test connectivity to all K8s nodes:**
```bash
ansible kubernetes -m ping
```

**Expected output:** All 9 nodes should return SUCCESS/pong.

**If nodes are unreachable:**
- Verify VMs are running
- Check SSH keys are configured
- Test manual SSH: `ssh hermes-admin@192.168.20.32`

### Step 4: Run Prerequisites Playbook

**Configure system requirements on all nodes:**
```bash
ansible-playbook k8s/01-k8s-prerequisites.yml
```

**What to watch for:**
- Swap disabled successfully
- Kernel modules loaded
- Containerd installed and running
- No errors about missing packages

**Execution time:** ~3-5 minutes

### Step 5: Install Kubernetes Packages

**Install kubeadm, kubelet, kubectl:**
```bash
ansible-playbook k8s/02-k8s-install.yml
```

**What to watch for:**
- Repository added successfully
- All packages installed
- Packages held at current version
- Kubelet enabled

**Verify manually (optional):**
```bash
ansible kubernetes -a "kubeadm version"
ansible kubernetes -a "kubelet --version"
```

**Execution time:** ~2-3 minutes

### Step 6: Initialize Cluster

**Bootstrap the cluster on primary control plane:**
```bash
ansible-playbook k8s/03-k8s-init-cluster.yml
```

**What to watch for:**
- Cluster initialization successful
- Join commands generated and saved
- Control plane components healthy

**Critical files created:**
- `~/ansible/k8s/join-command-controllers.sh` - For joining control planes
- `~/ansible/k8s/join-command-workers.sh` - For joining workers

**Verify cluster is initialized:**
```bash
ssh hermes-admin@192.168.20.32 "kubectl get nodes"
```

**Expected:** One node (k8s-controller01) in "NotReady" state (CNI not yet installed).

**Execution time:** ~3-4 minutes

### Step 7: Install CNI (Calico)

**Deploy Calico networking:**
```bash
ansible-playbook k8s/04-k8s-install-cni.yml
```

**What to watch for:**
- Calico manifest applied
- Calico pods starting
- Node changes to "Ready" state

**Verify Calico is running:**
```bash
ssh hermes-admin@192.168.20.32 "kubectl get pods -n kube-system -l k8s-app=calico-node"
```

**Expected:** Calico pods in "Running" state.

**Execution time:** ~2-3 minutes

### Step 8: Join All Nodes

**Add remaining control planes and all workers:**
```bash
ansible-playbook k8s/05-k8s-join-nodes.yml
```

**What to watch for:**
- Control planes join successfully (2 nodes)
- Workers join successfully (6 nodes)
- All nodes become "Ready"

**Verify all nodes joined:**
```bash
ssh hermes-admin@192.168.20.32 "kubectl get nodes"
```

**Expected:** 9 nodes total, all in "Ready" state.

**Execution time:** ~5-7 minutes

### Step 9: Complete Deployment (Alternative)

**Instead of steps 4-8, run master playbook:**
```bash
ansible-playbook k8s/k8s-deploy-all.yml
```

This runs all playbooks in sequence automatically.

---

## Verification

### Cluster Health Checks

**1. Check all nodes are ready:**
```bash
ssh hermes-admin@192.168.20.32 "kubectl get nodes"
```

**Expected output:**
```
NAME               STATUS   ROLES           AGE   VERSION
k8s-controller01   Ready    control-plane   10m   v1.28.x
k8s-controller02   Ready    control-plane   8m    v1.28.x
k8s-controller03   Ready    control-plane   8m    v1.28.x
k8s-worker01       Ready    <none>          6m    v1.28.x
k8s-worker02       Ready    <none>          6m    v1.28.x
k8s-worker03       Ready    <none>          6m    v1.28.x
k8s-worker04       Ready    <none>          6m    v1.28.x
k8s-worker05       Ready    <none>          6m    v1.28.x
k8s-worker06       Ready    <none>          6m    v1.28.x
```

**2. Check system pods are running:**
```bash
ssh hermes-admin@192.168.20.32 "kubectl get pods -n kube-system"
```

**Expected:** All pods in "Running" status, including:
- coredns (2 replicas)
- etcd (on control planes)
- kube-apiserver (on control planes)
- kube-controller-manager (on control planes)
- kube-proxy (on all nodes)
- kube-scheduler (on control planes)
- calico-node (on all nodes)
- calico-kube-controllers (1 replica)

**3. Check cluster info:**
```bash
ssh hermes-admin@192.168.20.32 "kubectl cluster-info"
```

**Expected:**
```
Kubernetes control plane is running at https://192.168.20.32:6443
CoreDNS is running at https://192.168.20.32:6443/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
```

**4. Verify control plane HA:**
```bash
ssh hermes-admin@192.168.20.32 "kubectl get pods -n kube-system -l component=kube-apiserver"
```

**Expected:** 3 API server pods (one per control plane).

**5. Test pod networking:**
```bash
ssh hermes-admin@192.168.20.32 "kubectl run test-pod --image=nginx --rm -it --restart=Never -- curl -I localhost"
```

**Expected:** HTTP 200 response from nginx.

### Component Status

**Check component health:**
```bash
ssh hermes-admin@192.168.20.32 "kubectl get componentstatuses"
```

**Note:** This command is deprecated but still useful for quick health check.

**Check control plane pods:**
```bash
ssh hermes-admin@192.168.20.32 "kubectl get pods -n kube-system -o wide | grep -E 'NAME|kube-apiserver|etcd|kube-controller|kube-scheduler'"
```

### Network Verification

**Check Calico status:**
```bash
ssh hermes-admin@192.168.20.32 "kubectl get pods -n kube-system -l k8s-app=calico-node -o wide"
```

**Expected:** One calico-node pod per node (9 total).

**Verify pod CIDR:**
```bash
ssh hermes-admin@192.168.20.32 "kubectl cluster-info dump | grep -m 1 cluster-cidr"
```

**Expected:** `--cluster-cidr=10.244.0.0/16`

---

## Troubleshooting

### Issue: VMs Not Responding to Ping

**Symptoms:**
- Cannot ping K8s nodes from local machine
- VMs show as DOWN

**Diagnosis:**
```bash
# Check VM status on Proxmox
ssh root@192.168.20.22 "qm list | grep k8s"
```

**Solution:**
```bash
# Start VMs that are stopped
ssh root@192.168.20.22 "qm start <vmid>"

# Start all K8s VMs
for vmid in 110 105 104 112 101 115 116 118 117; do
  ssh root@192.168.20.22 "qm start $vmid"
done

# Wait 60 seconds for boot
sleep 60
```

### Issue: SSH Connection Refused

**Symptoms:**
- `ssh: connect to host X.X.X.X port 22: Connection refused`

**Diagnosis:**
```bash
# Ping the host
ping -c 2 192.168.20.32

# Check if VM is running
ssh root@192.168.20.22 "qm status <vmid>"
```

**Solution:**
```bash
# If VM is stopped, start it
ssh root@192.168.20.22 "qm start <vmid>"

# If VM is running, wait for cloud-init (can take 60-90 seconds)
sleep 60

# If still failing, check VM console via Proxmox web UI
```

### Issue: Ansible Ping Fails (Permission Denied)

**Symptoms:**
```
192.168.20.32 | UNREACHABLE! => {
    "msg": "Failed to connect: Permission denied (publickey)"
}
```

**Diagnosis:**
```bash
# Test manual SSH
ssh hermes-admin@192.168.20.32 "hostname"

# Check if ansible-controller01 key is in authorized_keys
ssh hermes-admin@192.168.20.32 "cat ~/.ssh/authorized_keys | grep ansible-controller01"
```

**Solution:**
```bash
# Add ansible-controller01's public key to the node
PUBKEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILNaYM/nUFmslKMJ77SIuiT/1CQot2NbtBTP8zdXP2d6 hermes-admin@ansible-controller01"
ssh hermes-admin@192.168.20.32 "echo '$PUBKEY' >> ~/.ssh/authorized_keys"

# Verify
ansible kubernetes -m ping
```

### Issue: Swap Not Disabled

**Symptoms:**
```
[ERROR Swap]: running with swap on is not supported. Please disable swap
```

**Diagnosis:**
```bash
# Check if swap is enabled
ssh hermes-admin@192.168.20.32 "swapon --show"
```

**Solution:**
```bash
# Disable swap immediately
ssh hermes-admin@192.168.20.32 "sudo swapoff -a"

# Remove from fstab to persist
ssh hermes-admin@192.168.20.32 "sudo sed -i '/\sswap\s/d' /etc/fstab"

# Verify
ssh hermes-admin@192.168.20.32 "swapon --show"  # Should be empty
```

### Issue: containerd Not Running

**Symptoms:**
```
[ERROR CRI]: container runtime is not running
```

**Diagnosis:**
```bash
ssh hermes-admin@192.168.20.32 "sudo systemctl status containerd"
```

**Solution:**
```bash
# Restart containerd
ssh hermes-admin@192.168.20.32 "sudo systemctl restart containerd"

# Enable on boot
ssh hermes-admin@192.168.20.32 "sudo systemctl enable containerd"

# Verify
ssh hermes-admin@192.168.20.32 "sudo systemctl is-active containerd"
```

### Issue: kubeadm init Fails

**Symptoms:**
- Cluster initialization hangs or fails
- Error messages about ports in use

**Diagnosis:**
```bash
# Check if cluster is already initialized
ssh hermes-admin@192.168.20.32 "sudo ls /etc/kubernetes/admin.conf"

# Check required ports
ssh hermes-admin@192.168.20.32 "sudo netstat -tulpn | grep -E '6443|2379|2380|10250|10259|10257'"
```

**Solution:**
```bash
# If cluster partially initialized, reset
ssh hermes-admin@192.168.20.32 "sudo kubeadm reset -f"

# Clean up
ssh hermes-admin@192.168.20.32 "sudo rm -rf /etc/kubernetes/ ~/.kube/"

# Re-run initialization playbook
ansible-playbook k8s/03-k8s-init-cluster.yml
```

### Issue: Nodes Stay in NotReady State

**Symptoms:**
- Nodes show "NotReady" after joining
- Pods stuck in "Pending" state

**Diagnosis:**
```bash
# Check node status
ssh hermes-admin@192.168.20.32 "kubectl get nodes"

# Check kubelet logs
ssh hermes-admin@192.168.20.40 "sudo journalctl -u kubelet -f"

# Check if CNI is installed
ssh hermes-admin@192.168.20.32 "kubectl get pods -n kube-system -l k8s-app=calico-node"
```

**Solution:**
```bash
# If CNI not installed, run CNI playbook
ansible-playbook k8s/04-k8s-install-cni.yml

# If CNI pods not running, check their logs
ssh hermes-admin@192.168.20.32 "kubectl logs -n kube-system -l k8s-app=calico-node --tail=50"

# Restart kubelet on problematic node
ssh hermes-admin@192.168.20.40 "sudo systemctl restart kubelet"
```

### Issue: Control Plane Nodes Fail to Join

**Symptoms:**
- Error: "certificate-key" not found
- Join command fails with authentication error

**Diagnosis:**
```bash
# Check if join command file exists
ls -l ~/ansible/k8s/join-command-controllers.sh

# Check certificate upload
ssh hermes-admin@192.168.20.32 "sudo kubeadm token list"
```

**Solution:**
```bash
# Regenerate join command with new certificate key
ssh hermes-admin@192.168.20.32 "sudo kubeadm init phase upload-certs --upload-certs"

# Create new join command
ssh hermes-admin@192.168.20.32 "sudo kubeadm token create --print-join-command --certificate-key \$(sudo kubeadm init phase upload-certs --upload-certs 2>/dev/null | tail -1)" > ~/ansible/k8s/join-command-controllers.sh

# Re-run join playbook
ansible-playbook k8s/05-k8s-join-nodes.yml
```

### Issue: Calico Pods CrashLoopBackOff

**Symptoms:**
- Calico pods restarting repeatedly
- Networking not working

**Diagnosis:**
```bash
# Check Calico pod status
ssh hermes-admin@192.168.20.32 "kubectl get pods -n kube-system -l k8s-app=calico-node"

# Check logs
ssh hermes-admin@192.168.20.32 "kubectl logs -n kube-system -l k8s-app=calico-node --tail=100"
```

**Solution:**
```bash
# Delete Calico and reinstall
ssh hermes-admin@192.168.20.32 "kubectl delete -f /tmp/calico.yaml"

# Wait for cleanup
sleep 30

# Reinstall
ansible-playbook k8s/04-k8s-install-cni.yml
```

### Issue: Worker Nodes Can't Pull Images

**Symptoms:**
- Pods stuck in "ImagePullBackOff"
- containerd errors in kubelet logs

**Diagnosis:**
```bash
# Check containerd config
ssh hermes-admin@192.168.20.40 "sudo cat /etc/containerd/config.toml | grep SystemdCgroup"

# Test image pull
ssh hermes-admin@192.168.20.40 "sudo ctr image pull docker.io/library/nginx:latest"
```

**Solution:**
```bash
# Ensure SystemdCgroup is true
ssh hermes-admin@192.168.20.40 "sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml"

# Restart containerd
ssh hermes-admin@192.168.20.40 "sudo systemctl restart containerd"

# Restart kubelet
ssh hermes-admin@192.168.20.40 "sudo systemctl restart kubelet"
```

---

## Post-Installation

### Access Cluster from ansible-controller01

**Copy kubeconfig:**
```bash
# From ansible-controller01
mkdir -p ~/.kube
scp hermes-admin@192.168.20.32:~/.kube/config ~/.kube/config

# Test access
kubectl get nodes
```

### Access Cluster from Local Machine

**Copy kubeconfig:**
```bash
# From local machine
mkdir -p ~/.kube
scp hermes-admin@192.168.20.32:~/.kube/config ~/.kube/config

# Verify
kubectl get nodes
```

### Deploy Sample Application

**1. Create a test deployment:**
```bash
kubectl create deployment nginx --image=nginx --replicas=3
```

**2. Expose as a service:**
```bash
kubectl expose deployment nginx --port=80 --type=NodePort
```

**3. Check deployment:**
```bash
kubectl get pods -o wide
kubectl get svc nginx
```

**4. Access the application:**
```bash
# Get NodePort
NODE_PORT=$(kubectl get svc nginx -o jsonpath='{.spec.ports[0].nodePort}')

# Access via any node IP
curl http://192.168.20.40:$NODE_PORT
```

### Install Kubernetes Dashboard (Optional)

**1. Deploy dashboard:**
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml
```

**2. Create admin user:**
```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: admin-user
  namespace: kubernetes-dashboard
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: admin-user
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- kind: ServiceAccount
  name: admin-user
  namespace: kubernetes-dashboard
EOF
```

**3. Get access token:**
```bash
kubectl -n kubernetes-dashboard create token admin-user
```

**4. Access dashboard:**
```bash
kubectl proxy
```

Open browser: http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/

### Install Metrics Server (Recommended)

**For resource monitoring (kubectl top):**
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Patch for insecure TLS (homelab only)
kubectl patch deployment metrics-server -n kube-system --type='json' -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'
```

**Verify:**
```bash
kubectl top nodes
kubectl top pods -A
```

### Backup etcd (Important!)

**Create backup script:**
```bash
cat > ~/backup-etcd.sh <<'EOF'
#!/bin/bash
BACKUP_DIR=/home/hermes-admin/etcd-backups
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d-%H%M%S)

sudo ETCDCTL_API=3 etcdctl snapshot save $BACKUP_DIR/etcd-backup-$DATE.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

echo "Backup saved to: $BACKUP_DIR/etcd-backup-$DATE.db"

# Keep only last 7 days
find $BACKUP_DIR -name "etcd-backup-*.db" -mtime +7 -delete
EOF

chmod +x ~/backup-etcd.sh
```

**Run on any control plane:**
```bash
ssh hermes-admin@192.168.20.32 "bash ~/backup-etcd.sh"
```

**Schedule with cron (on control plane):**
```bash
ssh hermes-admin@192.168.20.32 "crontab -l | { cat; echo '0 2 * * * ~/backup-etcd.sh'; } | crontab -"
```

### Upgrade Cluster (Future)

**When new Kubernetes version is available:**

1. Upgrade control planes first (one at a time)
2. Upgrade worker nodes (can drain and upgrade in batches)
3. Follow official upgrade guide: https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/

---

## Summary

You now have a production-grade, highly-available Kubernetes cluster with:

- ✅ 3 control plane nodes (HA configuration)
- ✅ 6 worker nodes (compute capacity)
- ✅ containerd container runtime
- ✅ Calico CNI for networking
- ✅ Automated deployment via Ansible
- ✅ Comprehensive documentation

**Quick Reference Commands:**

```bash
# Check cluster health
kubectl get nodes
kubectl get pods -A
kubectl cluster-info

# Deploy application
kubectl create deployment myapp --image=nginx
kubectl expose deployment myapp --port=80 --type=NodePort

# Scale deployment
kubectl scale deployment myapp --replicas=5

# View logs
kubectl logs <pod-name>

# Execute in pod
kubectl exec -it <pod-name> -- /bin/bash

# Delete resources
kubectl delete deployment myapp
kubectl delete svc myapp
```

**For more information:**
- Kubernetes Documentation: https://kubernetes.io/docs/
- Calico Documentation: https://docs.tigera.io/calico/latest/
- kubectl Cheat Sheet: https://kubernetes.io/docs/reference/kubectl/cheatsheet/

---

**Document Version:** 1.0
**Last Updated:** December 16, 2025
**Author:** Homelab Infrastructure Team
**Cluster Name:** Production K8s Cluster
