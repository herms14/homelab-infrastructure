# Kubernetes Cluster Deployment Guide

## Quick Reference

**Cluster:** 3 Control Planes + 6 Workers = 9 Nodes Total
**Target:** ansible-control01 (192.168.20.50)
**Deployment Time:** ~30-45 minutes
**Kubernetes Version:** v1.28

## Pre-Deployment Checklist

Before deploying the cluster, ensure:

- [ ] All 9 VMs are deployed and running (3 control planes + 6 workers)
- [ ] All VMs have Ubuntu 24.04 LTS installed
- [ ] All VMs are accessible via SSH with key authentication
- [ ] Network connectivity between all nodes is working
- [ ] Ansible is installed on ansible-control01
- [ ] You have the playbooks in `~/ansible/k8s/` directory

## Step-by-Step Deployment

### Step 1: Copy Playbooks to ansible-control01

From your local machine:

```bash
# Copy all playbooks to ansible-control01
scp -r ansible-playbooks/k8s/* hermes-admin@192.168.20.50:~/ansible/k8s/

# SSH to ansible-control01
ssh hermes-admin@192.168.20.50
```

### Step 2: Verify Playbooks and Inventory

```bash
cd ~/ansible/k8s/

# List all files
ls -lah

# Review inventory file
cat inventory.ini

# Verify Ansible configuration
cat ansible.cfg
```

### Step 3: Run Pre-Deployment Verification

```bash
# Make verification script executable
chmod +x verify-deployment.sh

# Run pre-deployment checks
./verify-deployment.sh pre
```

This will verify:
- SSH connectivity to all nodes
- Python3 availability
- Network connectivity between nodes
- System resources (CPU, RAM)
- Unique hostnames

**Important:** Fix any failures before proceeding!

### Step 4: Deploy the Cluster

Choose one of these deployment methods:

#### Option A: Complete Automated Deployment (Recommended)

```bash
# Deploy entire cluster in one command
ansible-playbook -i inventory.ini k8s-deploy-all.yml
```

This runs all 5 stages automatically with progress updates between each stage.

#### Option B: Step-by-Step Deployment

```bash
# Stage 1: Prerequisites
ansible-playbook -i inventory.ini 01-k8s-prerequisites.yml

# Stage 2: Install Kubernetes
ansible-playbook -i inventory.ini 02-k8s-install.yml

# Stage 3: Initialize Cluster
ansible-playbook -i inventory.ini 03-k8s-init-cluster.yml

# Stage 4: Install CNI (Calico)
ansible-playbook -i inventory.ini 04-k8s-install-cni.yml

# Stage 5: Join Nodes
ansible-playbook -i inventory.ini 05-k8s-join-nodes.yml
```

Use this method if you want more control or need to troubleshoot between stages.

#### Option C: Run Specific Stages (Using Tags)

```bash
# Run only specific stages
ansible-playbook -i inventory.ini k8s-deploy-all.yml --tags "stage1,stage2"

# Skip stages already completed
ansible-playbook -i inventory.ini k8s-deploy-all.yml --skip-tags "stage1"
```

### Step 5: Post-Deployment Verification

```bash
# Run post-deployment checks
./verify-deployment.sh post
```

This verifies:
- Cluster is accessible
- All 9 nodes are Ready
- Control plane components are running
- Calico CNI is functional
- System pods are running
- Pod networking works

### Step 6: Check Cluster Status

```bash
# Run comprehensive status check
ansible-playbook -i inventory.ini ops-cluster-status.yml
```

This generates a detailed report showing:
- Node status
- Pod status
- System components
- Calico status
- Recent events
- Resource usage (if metrics-server installed)

Or manually check:

```bash
# SSH to primary control plane
ssh hermes-admin@192.168.20.32

# Check nodes
kubectl get nodes -o wide

# Check all pods
kubectl get pods -A

# Check cluster info
kubectl cluster-info
```

## Expected Output

### Successful Node Status

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

All nodes should show:
- STATUS: Ready
- AGE: Should show time since node joined

### System Pods

All pods in kube-system namespace should be Running:

```bash
kubectl get pods -n kube-system
```

Look for:
- calico-node pods (9 total - one per node)
- calico-kube-controllers (1-3 pods)
- coredns pods (2 pods)
- etcd pods (3 pods - one per control plane)
- kube-apiserver pods (3 pods)
- kube-controller-manager pods (3 pods)
- kube-proxy pods (9 total - one per node)
- kube-scheduler pods (3 pods)

## Common Issues and Solutions

### Issue: Nodes Show "NotReady"

**Cause:** CNI (Calico) not installed or not working

**Solution:**
```bash
# Check Calico pods
kubectl get pods -n kube-system -l k8s-app=calico-node

# If Calico pods are not running, re-run CNI installation
ansible-playbook -i inventory.ini 04-k8s-install-cni.yml

# Check Calico logs
kubectl logs -n kube-system -l k8s-app=calico-node
```

### Issue: Join Command Expired

**Cause:** Join tokens expire after 24 hours

**Solution:**
```bash
# SSH to primary control plane
ssh hermes-admin@192.168.20.32

# Generate new join command
kubeadm token create --print-join-command

# For control plane nodes, also get certificate key
kubeadm init phase upload-certs --upload-certs
```

### Issue: SSH Connection Failures

**Cause:** SSH keys not configured or network issues

**Solution:**
```bash
# Test SSH to each node
for ip in 192.168.20.{32..34} 192.168.20.{40..45}; do
  echo "Testing $ip..."
  ssh -o ConnectTimeout=5 hermes-admin@$ip "hostname" || echo "FAILED: $ip"
done

# Add SSH keys if needed
ssh-copy-id hermes-admin@<node-ip>
```

### Issue: Playbook Hangs on kubeadm init

**Cause:** Timeout too short or network issues

**Solution:**
```bash
# The playbook has a 600-second (10 minute) timeout
# If it still times out, check:

# 1. Network connectivity
ping 192.168.20.32

# 2. Required ports are open (6443, 2379-2380, 10250-10252)
# 3. containerd is running
ssh hermes-admin@192.168.20.32 "sudo systemctl status containerd"

# 4. Check kubelet logs
ssh hermes-admin@192.168.20.32 "sudo journalctl -u kubelet -f"
```

### Issue: Pods Stuck in "Pending"

**Cause:** Nodes not Ready or resource constraints

**Solution:**
```bash
# Check node status
kubectl get nodes

# Check pod details
kubectl describe pod <pod-name> -n <namespace>

# Check resource usage
kubectl top nodes  # Requires metrics-server

# Check events
kubectl get events -A --sort-by='.lastTimestamp'
```

## Timeline for Deployment

### Typical Deployment Timeline

| Stage | Playbook | Duration | Description |
|-------|----------|----------|-------------|
| 0 | Verification | 2-3 min | Pre-deployment checks |
| 1 | Prerequisites | 5-10 min | System preparation, containerd |
| 2 | Install | 5-10 min | Kubernetes packages |
| 3 | Init | 5-10 min | Cluster initialization |
| 4 | CNI | 5-10 min | Calico installation |
| 5 | Join | 10-15 min | Join all nodes |
| **Total** | | **30-45 min** | Complete deployment |

### Progress Indicators

Each playbook displays:
- Task descriptions explaining what's happening
- Success/failure indicators
- Verification steps
- Summary at completion

Watch for:
- ✓ Green checkmarks = Success
- ✗ Red X = Failure (review error message)
- ⚠ Yellow warning = Attention needed

## Post-Deployment Next Steps

### 1. Install Metrics Server

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# For self-signed certs, patch the deployment:
kubectl patch deployment metrics-server -n kube-system --type='json' -p='[
  {
    "op": "add",
    "path": "/spec/template/spec/containers/0/args/-",
    "value": "--kubelet-insecure-tls"
  }
]'

# Verify metrics are working
kubectl top nodes
kubectl top pods -A
```

### 2. Install Ingress Controller

Choose one:

**Option A: Traefik (Recommended for homelab)**
```bash
kubectl apply -f https://raw.githubusercontent.com/traefik/traefik/v2.10/docs/content/reference/dynamic-configuration/kubernetes-crd-definition-v1.yml
kubectl apply -f https://raw.githubusercontent.com/traefik/traefik/v2.10/docs/content/reference/dynamic-configuration/kubernetes-crd-rbac.yml
```

**Option B: nginx-ingress**
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/baremetal/deploy.yaml
```

### 3. Configure Storage Class

Set up NFS provisioner for persistent storage:

```bash
# Install NFS CSI driver
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/

helm install nfs-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
  --set nfs.server=192.168.20.31 \
  --set nfs.path=/volume2/ProxmoxCluster-K8s \
  --set storageClass.defaultClass=true

# Verify storage class
kubectl get storageclass
```

### 4. Deploy Test Application

Test the cluster with a simple nginx deployment:

```bash
# Create deployment
kubectl create deployment nginx-test --image=nginx --replicas=3

# Expose as service
kubectl expose deployment nginx-test --port=80 --type=NodePort

# Check deployment
kubectl get deployments
kubectl get pods -o wide
kubectl get services

# Test access (use NodePort shown in services)
curl http://192.168.20.40:<NodePort>

# Cleanup
kubectl delete deployment nginx-test
kubectl delete service nginx-test
```

### 5. Set Up Monitoring (Optional)

Install Prometheus and Grafana:

```bash
# Add Prometheus Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install kube-prometheus-stack
kubectl create namespace monitoring

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false

# Access Grafana (default credentials: admin/prom-operator)
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
```

## File Reference

| File | Purpose |
|------|---------|
| `inventory.ini` | Ansible inventory with all node IPs |
| `ansible.cfg` | Ansible configuration |
| `01-k8s-prerequisites.yml` | System preparation |
| `02-k8s-install.yml` | Install Kubernetes components |
| `03-k8s-init-cluster.yml` | Initialize cluster |
| `04-k8s-install-cni.yml` | Install Calico CNI |
| `05-k8s-join-nodes.yml` | Join nodes to cluster |
| `k8s-deploy-all.yml` | Master orchestration playbook |
| `ops-cluster-status.yml` | Comprehensive status check |
| `verify-deployment.sh` | Pre/post deployment verification |
| `README.md` | Detailed documentation |
| `DEPLOYMENT-GUIDE.md` | This file |

## Useful Commands Reference

### Cluster Management

```bash
# View cluster info
kubectl cluster-info
kubectl get nodes -o wide
kubectl get pods -A

# View specific namespace
kubectl get all -n kube-system

# Describe resources
kubectl describe node <node-name>
kubectl describe pod <pod-name> -n <namespace>

# View logs
kubectl logs <pod-name> -n <namespace>
kubectl logs -f <pod-name> -n <namespace>  # Follow logs

# Execute commands in pod
kubectl exec -it <pod-name> -n <namespace> -- /bin/bash
```

### Cluster Status

```bash
# Check component health
kubectl get componentstatuses

# View events
kubectl get events -A --sort-by='.lastTimestamp'

# Check resource usage (requires metrics-server)
kubectl top nodes
kubectl top pods -A
```

### Node Management

```bash
# Cordon node (prevent new pods)
kubectl cordon <node-name>

# Drain node (evict pods)
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Uncordon node (allow pods)
kubectl uncordon <node-name>

# Delete node from cluster
kubectl delete node <node-name>
```

## Support and Troubleshooting

### Getting Help

1. **Check README.md** - Comprehensive documentation and troubleshooting
2. **Run status check** - `ansible-playbook -i inventory.ini ops-cluster-status.yml`
3. **Check logs** - Review kubelet, containerd, and pod logs
4. **Kubernetes docs** - https://kubernetes.io/docs/

### Debug Mode

Run playbooks with verbose output:

```bash
# Verbose mode (-v, -vv, -vvv for increasing verbosity)
ansible-playbook -i inventory.ini k8s-deploy-all.yml -vvv

# Check mode (dry run)
ansible-playbook -i inventory.ini k8s-deploy-all.yml --check
```

### Log Locations

On each node:

- **kubelet logs:** `sudo journalctl -u kubelet -f`
- **containerd logs:** `sudo journalctl -u containerd -f`
- **Pod logs:** `kubectl logs <pod-name> -n <namespace>`
- **System logs:** `/var/log/syslog`

## Maintenance

### Backup kubeconfig

```bash
# From primary control plane
scp hermes-admin@192.168.20.32:~/.kube/config ~/.kube/config-k8s-homelab

# Test backup
kubectl --kubeconfig ~/.kube/config-k8s-homelab get nodes
```

### Backup etcd

```bash
# SSH to control plane
ssh hermes-admin@192.168.20.32

# Create etcd snapshot
sudo ETCDCTL_API=3 etcdctl snapshot save /tmp/etcd-snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# Download snapshot
exit
scp hermes-admin@192.168.20.32:/tmp/etcd-snapshot.db ./etcd-backup-$(date +%Y%m%d).db
```

## Additional Resources

- **Kubernetes Documentation:** https://kubernetes.io/docs/
- **Calico Documentation:** https://docs.tigera.io/calico/latest/about/
- **kubectl Cheat Sheet:** https://kubernetes.io/docs/reference/kubectl/cheatsheet/
- **Ansible Documentation:** https://docs.ansible.com/

---

**Deployment Guide Version:** 1.0
**Last Updated:** 2025-12-16
**Target Kubernetes Version:** v1.28
**Target Platform:** Proxmox VE 9.1.2 / Ubuntu 24.04 LTS
