# START HERE - Kubernetes Cluster Deployment

## Overview

This directory contains **production-grade Ansible playbooks** for deploying a highly available Kubernetes cluster on your Proxmox homelab.

**What you're deploying:**
- 3 Control Plane nodes (High Availability)
- 6 Worker nodes
- Calico CNI for networking
- containerd as container runtime
- Kubernetes v1.28

**Total deployment time:** 30-45 minutes (fully automated)

## Files in This Directory

### Core Deployment Playbooks (Run in Order)

1. **`01-k8s-prerequisites.yml`** (254 lines)
   - Disables swap permanently
   - Loads kernel modules (overlay, br_netfilter)
   - Configures sysctl for Kubernetes networking
   - Installs and configures containerd

2. **`02-k8s-install.yml`** (188 lines)
   - Adds Kubernetes apt repository
   - Installs kubeadm, kubelet, kubectl (v1.28)
   - Holds packages to prevent auto-updates
   - Enables kubelet service

3. **`03-k8s-init-cluster.yml`** (286 lines)
   - Initializes cluster on primary control plane
   - Sets up kubeconfig for admin user
   - Generates join commands for other nodes
   - Saves join tokens to files

4. **`04-k8s-install-cni.yml`** (286 lines)
   - Downloads Calico CNI manifest (v3.27.0)
   - Configures pod network CIDR
   - Applies Calico to cluster
   - Waits for Calico pods to be ready

5. **`05-k8s-join-nodes.yml`** (400 lines)
   - Joins additional control planes (controller02, controller03)
   - Joins all worker nodes (worker01-06)
   - Configures kubeconfig on control planes
   - Verifies cluster health

### Master Orchestration

- **`k8s-deploy-all.yml`** (242 lines)
  - **USE THIS FOR AUTOMATED DEPLOYMENT**
  - Runs all 5 playbooks in sequence
  - Shows progress between stages
  - Provides comprehensive summary at end
  - Supports running individual stages with tags

### Configuration Files

- **`inventory.ini`** (44 lines)
  - Ansible inventory with all node IPs
  - Kubernetes version configuration
  - Network CIDR configuration
  - SSH settings

- **`ansible.cfg`** (63 lines)
  - Ansible configuration optimized for K8s deployment
  - Timeout settings for long-running tasks
  - Performance optimizations
  - Output formatting

### Operational Tools

- **`ops-cluster-status.yml`** (495 lines)
  - Comprehensive cluster health check
  - Node status and resource usage
  - Pod status across all namespaces
  - Calico CNI status
  - Control plane component health
  - Recent events and warnings
  - Generates detailed report file

- **`verify-deployment.sh`** (372 lines)
  - **Bash script for pre/post deployment verification**
  - Pre-deployment: Tests SSH, connectivity, resources
  - Post-deployment: Verifies cluster health, pod networking
  - Color-coded output with pass/fail counts
  - Make executable: `chmod +x verify-deployment.sh`

### Documentation

- **`00-START-HERE.md`** (This file)
  - Quick start guide
  - File overview

- **`DEPLOYMENT-GUIDE.md`** (555 lines)
  - **Complete step-by-step deployment instructions**
  - Common issues and solutions
  - Post-deployment next steps
  - Useful commands reference

- **`README.md`** (526 lines)
  - **Comprehensive documentation**
  - Detailed playbook descriptions
  - Troubleshooting guide
  - Maintenance operations
  - Architecture details

## Quick Start (3 Steps)

### Step 1: Copy Files to ansible-control01

From your local machine:

```bash
# Copy all playbooks to ansible-control01
scp -r ansible-playbooks/k8s/* hermes-admin@192.168.20.50:~/ansible/k8s/

# SSH to ansible-control01
ssh hermes-admin@192.168.20.50
cd ~/ansible/k8s/
```

### Step 2: Verify Prerequisites

```bash
# Make verification script executable
chmod +x verify-deployment.sh

# Run pre-deployment checks
./verify-deployment.sh pre
```

**Fix any failures before proceeding!**

### Step 3: Deploy the Cluster

```bash
# Deploy entire cluster (automated, ~30-45 minutes)
ansible-playbook -i inventory.ini k8s-deploy-all.yml
```

That's it! The playbook will:
1. Configure all prerequisites on all nodes
2. Install Kubernetes components
3. Initialize the cluster on primary control plane
4. Install Calico CNI for networking
5. Join all additional nodes
6. Verify cluster health

## What Happens During Deployment

### Stage 1: Prerequisites (5-10 min)
- Disables swap on all nodes
- Loads kernel modules for container networking
- Configures sysctl parameters
- Installs containerd runtime

### Stage 2: Install Kubernetes (5-10 min)
- Adds Kubernetes package repository
- Installs kubeadm, kubelet, kubectl v1.28
- Holds packages to prevent auto-updates

### Stage 3: Initialize Cluster (5-10 min)
- Runs kubeadm init on k8s-controller01
- Sets up kubectl access for admin user
- Generates join commands for other nodes

### Stage 4: Install CNI (5-10 min)
- Installs Calico for pod networking
- Waits for Calico pods to be ready
- Nodes transition from NotReady to Ready

### Stage 5: Join Nodes (10-15 min)
- Joins 2 additional control planes
- Joins 6 worker nodes
- Verifies all nodes are Ready
- Confirms cluster health

## After Deployment

### Verify the Cluster

```bash
# Run post-deployment verification
./verify-deployment.sh post

# Or check cluster status
ansible-playbook -i inventory.ini ops-cluster-status.yml

# Or manually check
ssh hermes-admin@192.168.20.32
kubectl get nodes -o wide
kubectl get pods -A
```

### Expected Result

All 9 nodes should show "Ready" status:

```
NAME               STATUS   ROLES           AGE   VERSION
k8s-controller01   Ready    control-plane   15m   v1.28.x
k8s-controller02   Ready    control-plane   12m   v1.28.x
k8s-controller03   Ready    control-plane   12m   v1.28.x
k8s-worker01       Ready    <none>          10m   v1.28.x
k8s-worker02       Ready    <none>          10m   v1.28.x
k8s-worker03       Ready    <none>          10m   v1.28.x
k8s-worker04       Ready    <none>          10m   v1.28.x
k8s-worker05       Ready    <none>          10m   v1.28.x
k8s-worker06       Ready    <none>          10m   v1.28.x
```

## Common Deployment Options

### Option 1: Complete Automated Deployment (Recommended)

```bash
ansible-playbook -i inventory.ini k8s-deploy-all.yml
```

**Best for:** First-time deployment, clean installation

### Option 2: Step-by-Step Deployment

```bash
ansible-playbook -i inventory.ini 01-k8s-prerequisites.yml
ansible-playbook -i inventory.ini 02-k8s-install.yml
ansible-playbook -i inventory.ini 03-k8s-init-cluster.yml
ansible-playbook -i inventory.ini 04-k8s-install-cni.yml
ansible-playbook -i inventory.ini 05-k8s-join-nodes.yml
```

**Best for:** Learning, troubleshooting, debugging

### Option 3: Run Specific Stages (Tags)

```bash
# Run only prerequisites and installation
ansible-playbook -i inventory.ini k8s-deploy-all.yml --tags "stage1,stage2"

# Skip stages already completed
ansible-playbook -i inventory.ini k8s-deploy-all.yml --skip-tags "stage1"

# Run only CNI installation
ansible-playbook -i inventory.ini k8s-deploy-all.yml --tags cni
```

**Best for:** Re-running failed stages, updates

## Troubleshooting Quick Reference

### Nodes Show "NotReady"

**Cause:** CNI not installed or not working

**Fix:**
```bash
# Check Calico pods
kubectl get pods -n kube-system -l k8s-app=calico-node

# Re-run CNI installation if needed
ansible-playbook -i inventory.ini 04-k8s-install-cni.yml
```

### SSH Connection Failures

**Cause:** SSH keys not configured

**Fix:**
```bash
# Test SSH connectivity
for ip in 192.168.20.{32..34} 192.168.20.{40..45}; do
  echo "Testing $ip..."
  ssh -o ConnectTimeout=5 hermes-admin@$ip "hostname" || echo "FAILED"
done

# Add SSH key if needed
ssh-copy-id hermes-admin@<node-ip>
```

### Playbook Fails on Specific Task

**Solution:**
```bash
# Run with verbose output
ansible-playbook -i inventory.ini k8s-deploy-all.yml -vvv

# Check task logs on the node
ssh hermes-admin@<node-ip> "sudo journalctl -u kubelet -n 100"
```

## Next Steps After Deployment

1. **Install Metrics Server** (for resource monitoring)
   ```bash
   kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
   ```

2. **Install Ingress Controller** (Traefik or nginx)
   ```bash
   # See DEPLOYMENT-GUIDE.md for detailed instructions
   ```

3. **Configure Storage Class** (NFS provisioner)
   ```bash
   # See DEPLOYMENT-GUIDE.md for detailed instructions
   ```

4. **Deploy Test Application** (verify cluster works)
   ```bash
   kubectl create deployment nginx --image=nginx --replicas=3
   kubectl expose deployment nginx --port=80 --type=NodePort
   ```

5. **Set Up Monitoring** (Prometheus + Grafana)
   ```bash
   # See DEPLOYMENT-GUIDE.md for detailed instructions
   ```

## File Size and Complexity

| File | Lines | Purpose |
|------|-------|---------|
| `ops-cluster-status.yml` | 495 | Comprehensive status check |
| `DEPLOYMENT-GUIDE.md` | 555 | Step-by-step guide |
| `README.md` | 526 | Full documentation |
| `05-k8s-join-nodes.yml` | 400 | Join nodes playbook |
| `verify-deployment.sh` | 372 | Verification script |
| `04-k8s-install-cni.yml` | 286 | CNI installation |
| `03-k8s-init-cluster.yml` | 286 | Cluster init |
| `01-k8s-prerequisites.yml` | 254 | Prerequisites |
| `k8s-deploy-all.yml` | 242 | Master orchestration |
| `02-k8s-install.yml` | 188 | K8s installation |
| `ansible.cfg` | 63 | Ansible config |
| `inventory.ini` | 44 | Inventory |

**Total:** 3,711 lines of production-grade code and documentation

## Key Features

### Production-Ready
- Idempotent playbooks (safe to re-run)
- Comprehensive error handling
- Detailed logging and verification
- Pre and post deployment checks

### High Availability
- 3 control plane nodes (HA)
- Distributed etcd storage
- Load-balanced API server
- Fault-tolerant architecture

### Well Documented
- Extensive inline comments
- Task descriptions explain "why"
- Troubleshooting guides
- Common issue solutions

### Automated
- Single command deployment
- Progress tracking between stages
- Automatic verification
- Health checks built-in

## Support and Documentation

| Question | See File |
|----------|----------|
| How do I deploy? | `DEPLOYMENT-GUIDE.md` |
| What does each playbook do? | `README.md` |
| How do I troubleshoot? | `README.md` (Troubleshooting section) |
| What's my cluster status? | Run `ops-cluster-status.yml` |
| Pre-deployment checks? | Run `verify-deployment.sh pre` |
| Post-deployment checks? | Run `verify-deployment.sh post` |
| Need to re-run a stage? | Use tags: `--tags stage3` |

## Cluster Specifications

**Control Plane Nodes:**
- k8s-controller01: 192.168.20.32 (Primary)
- k8s-controller02: 192.168.20.33
- k8s-controller03: 192.168.20.34

**Worker Nodes:**
- k8s-worker01: 192.168.20.40
- k8s-worker02: 192.168.20.41
- k8s-worker03: 192.168.20.42
- k8s-worker04: 192.168.20.43
- k8s-worker05: 192.168.20.44
- k8s-worker06: 192.168.20.45

**Network:**
- Pod Network CIDR: 10.244.0.0/16
- Service CIDR: 10.96.0.0/12
- CNI: Calico v3.27.0

**Software:**
- Kubernetes: v1.28
- Container Runtime: containerd
- OS: Ubuntu 24.04 LTS

## Ready to Deploy?

1. **Read this file** ✓ (You're here!)
2. **Copy files to ansible-control01**
3. **Run verification:** `./verify-deployment.sh pre`
4. **Deploy:** `ansible-playbook -i inventory.ini k8s-deploy-all.yml`
5. **Verify:** `./verify-deployment.sh post`

**Questions?** See `DEPLOYMENT-GUIDE.md` and `README.md`

---

**Created:** 2025-12-16
**Version:** 1.0
**Target:** Proxmox VE 9.1.2 / Ubuntu 24.04 LTS
**Kubernetes:** v1.28
**Calico:** v3.27.0

**Good luck with your deployment!**
