# Kubernetes Cluster Deployment with Ansible

This directory contains production-grade Ansible playbooks for deploying a highly available Kubernetes cluster on Proxmox VMs.

## Cluster Architecture

**Control Plane (HA):**
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

**Network Configuration:**
- Pod Network CIDR: 10.244.0.0/16
- Service CIDR: 10.96.0.0/12
- CNI: Calico v3.27.0
- Container Runtime: containerd

**Kubernetes Version:**
- v1.28 (latest stable at time of writing)

## Prerequisites

### On Ansible Control Node (ansible-control01)

1. Ansible installed (2.14 or later recommended):
```bash
sudo apt update
sudo apt install -y ansible
ansible --version
```

2. SSH key access to all cluster nodes:
```bash
# Verify SSH access to all nodes
for ip in 192.168.20.{32..34} 192.168.20.{40..45}; do
  echo "Testing $ip..."
  ssh -o ConnectTimeout=5 hermes-admin@$ip "hostname" || echo "FAILED: $ip"
done
```

3. Python3 on all target nodes (usually pre-installed on Ubuntu 24.04)

### On Target Nodes (All Kubernetes Nodes)

- Ubuntu 24.04 LTS (or compatible)
- Minimum 2 CPU cores (4 recommended for control plane)
- Minimum 2GB RAM (8GB recommended for control plane)
- Network connectivity between all nodes
- Unique hostnames and MAC addresses
- Disabled swap (handled by playbook)

## File Structure

```
k8s/
├── inventory.ini                    # Ansible inventory file
├── 01-k8s-prerequisites.yml         # System prerequisites
├── 02-k8s-install.yml               # Kubernetes components installation
├── 03-k8s-init-cluster.yml          # Cluster initialization
├── 04-k8s-install-cni.yml           # Calico CNI installation
├── 05-k8s-join-nodes.yml            # Join nodes to cluster
├── k8s-deploy-all.yml               # Master orchestration playbook
└── README.md                        # This file
```

## Playbook Descriptions

### 01-k8s-prerequisites.yml
**Purpose:** Prepares all nodes for Kubernetes installation

**What it does:**
- Disables swap permanently (required by kubelet)
- Loads kernel modules (overlay, br_netfilter)
- Configures sysctl parameters for networking
- Installs and configures containerd runtime
- Verifies all configurations

**Runtime:** ~5-10 minutes

### 02-k8s-install.yml
**Purpose:** Installs Kubernetes components on all nodes

**What it does:**
- Adds Kubernetes apt repository (pkgs.k8s.io)
- Installs kubeadm, kubelet, kubectl (v1.28)
- Holds packages to prevent auto-updates
- Enables kubelet service
- Verifies installations

**Runtime:** ~5-10 minutes

### 03-k8s-init-cluster.yml
**Purpose:** Initializes the Kubernetes cluster

**What it does:**
- Runs kubeadm init on primary control plane
- Configures kubeconfig for root and admin user
- Generates join commands for control planes and workers
- Saves join commands to /tmp/ for other playbooks
- Verifies cluster initialization

**Runtime:** ~5-10 minutes

**Note:** Nodes will show "NotReady" until CNI is installed (Stage 4)

### 04-k8s-install-cni.yml
**Purpose:** Installs Calico Container Network Interface

**What it does:**
- Downloads Calico manifest (v3.27.0)
- Configures pod network CIDR
- Applies Calico to cluster
- Waits for Calico pods to be ready
- Verifies networking is functional

**Runtime:** ~5-10 minutes

**Important:** After this stage, nodes should transition to "Ready" status

### 05-k8s-join-nodes.yml
**Purpose:** Joins all nodes to the cluster

**What it does:**
- Joins additional control planes (controller02, controller03)
- Joins all worker nodes (worker01-06)
- Configures kubeconfig on control planes
- Waits for all nodes to be Ready
- Verifies cluster health

**Runtime:** ~10-15 minutes

### k8s-deploy-all.yml
**Purpose:** Master playbook that runs all stages sequentially

**What it does:**
- Orchestrates complete cluster deployment
- Runs all 5 playbooks in correct order
- Displays progress between stages
- Provides final deployment summary

**Runtime:** ~30-45 minutes total

## Quick Start

### Option 1: Complete Deployment (Recommended)

Deploy the entire cluster in one command:

```bash
# Navigate to playbook directory
cd ~/ansible/k8s/

# Run complete deployment
ansible-playbook -i inventory.ini k8s-deploy-all.yml
```

This will:
1. Configure prerequisites on all nodes
2. Install Kubernetes components
3. Initialize the cluster
4. Install Calico CNI
5. Join all nodes
6. Verify cluster health

### Option 2: Step-by-Step Deployment

Run each playbook individually for more control:

```bash
cd ~/ansible/k8s/

# Stage 1: Prerequisites
ansible-playbook -i inventory.ini 01-k8s-prerequisites.yml

# Stage 2: Install Kubernetes
ansible-playbook -i inventory.ini 02-k8s-install.yml

# Stage 3: Initialize cluster
ansible-playbook -i inventory.ini 03-k8s-init-cluster.yml

# Stage 4: Install CNI
ansible-playbook -i inventory.ini 04-k8s-install-cni.yml

# Stage 5: Join nodes
ansible-playbook -i inventory.ini 05-k8s-join-nodes.yml
```

### Option 3: Run Specific Stages

Use tags to run specific stages:

```bash
# Run only prerequisites and installation
ansible-playbook -i inventory.ini k8s-deploy-all.yml --tags "stage1,stage2"

# Run only CNI installation
ansible-playbook -i inventory.ini k8s-deploy-all.yml --tags cni

# Skip prerequisites (if already done)
ansible-playbook -i inventory.ini k8s-deploy-all.yml --skip-tags prerequisites
```

## Post-Deployment Verification

After deployment completes, verify the cluster:

### 1. SSH to Primary Control Plane
```bash
ssh hermes-admin@192.168.20.32
```

### 2. Check Node Status
```bash
kubectl get nodes -o wide
```

Expected output:
```
NAME               STATUS   ROLES           AGE   VERSION
k8s-controller01   Ready    control-plane   10m   v1.28.x
k8s-controller02   Ready    control-plane   8m    v1.28.x
k8s-controller03   Ready    control-plane   8m    v1.28.x
k8s-worker01       Ready    <none>          5m    v1.28.x
k8s-worker02       Ready    <none>          5m    v1.28.x
k8s-worker03       Ready    <none>          5m    v1.28.x
k8s-worker04       Ready    <none>          5m    v1.28.x
k8s-worker05       Ready    <none>          5m    v1.28.x
k8s-worker06       Ready    <none>          5m    v1.28.x
```

### 3. Check System Pods
```bash
kubectl get pods -n kube-system
```

All pods should be in "Running" or "Completed" status.

### 4. Check Cluster Info
```bash
kubectl cluster-info
```

### 5. Check Calico Status
```bash
kubectl get pods -n kube-system -l k8s-app=calico-node
```

Should show calico-node pods running on all 9 nodes.

### 6. Test Pod Creation
```bash
# Create a test deployment
kubectl create deployment nginx --image=nginx --replicas=3

# Check deployment
kubectl get deployments
kubectl get pods -o wide

# Clean up
kubectl delete deployment nginx
```

## Troubleshooting

### Nodes Show "NotReady"

**Check kubelet logs:**
```bash
ssh hermes-admin@<node-ip>
sudo journalctl -u kubelet -f
```

**Check Calico pods:**
```bash
kubectl logs -n kube-system -l k8s-app=calico-node
```

**Common causes:**
- CNI not installed yet (run 04-k8s-install-cni.yml)
- Network connectivity issues between nodes
- Firewall blocking required ports
- containerd not running: `sudo systemctl status containerd`

### Join Command Expired

Join tokens expire after 24 hours. To regenerate:

**On primary control plane (k8s-controller01):**
```bash
# For control plane nodes
kubeadm token create --print-join-command

# Get certificate key for control plane
kubeadm init phase upload-certs --upload-certs

# For worker nodes
kubeadm token create --print-join-command
```

### Pod Network Issues

**Check Calico installation:**
```bash
kubectl get pods -n kube-system -l k8s-app=calico-node -o wide
kubectl describe pod -n kube-system -l k8s-app=calico-node
```

**Verify network configuration:**
```bash
kubectl get ippool -o yaml
```

**Check node network:**
```bash
# On each node
sudo ip addr show
sudo ip route show
```

### kubelet Not Starting

**Check kubelet status:**
```bash
sudo systemctl status kubelet
sudo journalctl -u kubelet -n 100 --no-pager
```

**Common issues:**
- Swap not disabled: `sudo swapoff -a`
- Configuration missing: Check /var/lib/kubelet/config.yaml
- Port conflicts: Check if port 10250 is available

### Unable to Connect to API Server

**Check API server pods:**
```bash
kubectl get pods -n kube-system -l component=kube-apiserver
```

**Check API server logs:**
```bash
sudo journalctl -u kube-apiserver -f
```

**Verify API server is listening:**
```bash
sudo netstat -tlnp | grep 6443
```

## Required Firewall Ports

If using firewall rules, ensure these ports are open:

### Control Plane Nodes
- 6443: Kubernetes API server
- 2379-2380: etcd server client API
- 10250: Kubelet API
- 10251: kube-scheduler
- 10252: kube-controller-manager
- 179: Calico BGP

### Worker Nodes
- 10250: Kubelet API
- 30000-32767: NodePort Services
- 179: Calico BGP

### All Nodes
- UDP 4789: Calico VXLAN (if using VXLAN mode)
- TCP 5473: Calico Typha (if using Typha)

## Maintenance Operations

### View Join Commands
```bash
# On ansible-control01 or primary control plane
cat /tmp/kubeadm-join-control-plane.sh
cat /tmp/kubeadm-join-worker.sh
```

### Remove a Node from Cluster
```bash
# Drain node (evict pods)
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Delete node from cluster
kubectl delete node <node-name>

# On the node itself, reset kubeadm
sudo kubeadm reset
sudo rm -rf /etc/kubernetes /var/lib/kubelet /var/lib/etcd
```

### Upgrade Kubernetes Version

**Note:** Cluster upgrades must be done carefully and in specific order.

1. Update inventory.ini with new version
2. Upgrade control planes one at a time
3. Upgrade worker nodes
4. Refer to official Kubernetes upgrade documentation

### Backup etcd

**On control plane node:**
```bash
sudo ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key
```

## Next Steps After Deployment

### 1. Install Ingress Controller
```bash
# Option 1: Traefik
kubectl apply -f https://raw.githubusercontent.com/traefik/traefik/v2.10/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml
kubectl apply -f https://raw.githubusercontent.com/traefik/traefik/v2.10/docs/content/reference/dynamic-configuration/kubernetes-crd-rbac.yml

# Option 2: nginx-ingress
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/baremetal/deploy.yaml
```

### 2. Install Metrics Server
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# For self-signed certs, add --kubelet-insecure-tls flag to metrics-server deployment
```

### 3. Configure Storage Classes

Example NFS storage class:
```bash
# Install NFS provisioner
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
helm install nfs-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  --set nfs.server=192.168.20.31 \
  --set nfs.path=/volume2/ProxmoxCluster-K8s
```

### 4. Install Monitoring Stack

```bash
# Add Prometheus Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install kube-prometheus-stack (Prometheus + Grafana + Alertmanager)
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace
```

### 5. Set Up GitOps (Optional)

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

## Playbook Idempotency

All playbooks are designed to be idempotent - they can be run multiple times safely:

- If prerequisites are already configured, they will be skipped
- If Kubernetes is already installed, installation will be skipped
- If cluster is already initialized, init will be skipped
- If nodes are already joined, join will be skipped

This allows you to:
- Re-run playbooks after failures
- Add new nodes to existing cluster
- Verify cluster configuration

## Additional Resources

### Kubernetes Documentation
- Official Docs: https://kubernetes.io/docs/
- kubectl Cheat Sheet: https://kubernetes.io/docs/reference/kubectl/cheatsheet/
- kubeadm Documentation: https://kubernetes.io/docs/reference/setup-tools/kubeadm/

### Calico Documentation
- Official Docs: https://docs.tigera.io/calico/latest/about/
- Troubleshooting: https://docs.tigera.io/calico/latest/operations/troubleshoot/

### Community Resources
- Kubernetes Slack: https://slack.k8s.io/
- Stack Overflow: https://stackoverflow.com/questions/tagged/kubernetes
- Reddit: https://www.reddit.com/r/kubernetes/

## Support

For issues specific to these playbooks:
1. Check the troubleshooting section above
2. Review playbook logs for error messages
3. Verify all prerequisites are met
4. Check connectivity between nodes

For Kubernetes-specific issues:
1. Consult official Kubernetes documentation
2. Check component logs (kubelet, kube-apiserver, etc.)
3. Verify resource availability (CPU, memory, disk)

## License

These playbooks are provided as-is for homelab and learning purposes.

## Authors

Created for Proxmox homelab Kubernetes cluster deployment.

---

**Last Updated:** 2025-12-16
**Kubernetes Version:** v1.28
**Calico Version:** v3.27.0
