# Kubernetes

> **TL;DR**: Production-grade 9-node Kubernetes cluster with 3 HA control plane nodes and 6 workers, deployed via Ansible automation.

## Cluster Status

| Component | Status | Details |
|-----------|--------|---------|
| **Cluster** | Deployed | December 19, 2025 |
| **Version** | v1.28.15 | Kubernetes stable |
| **CNI** | Calico v3.27.0 | Pod networking |
| **Control Plane** | 3 nodes | High Availability |
| **Workers** | 6 nodes | Application workloads |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster Architecture                           │
│                    VLAN 20 (192.168.20.0/24)                                │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                    Control Plane (HA)                                │   │
│   │                                                                      │   │
│   │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
│   │   │ controller01 │  │ controller02 │  │ controller03 │             │   │
│   │   │ 192.168.20.32│  │ 192.168.20.33│  │ 192.168.20.34│             │   │
│   │   │              │  │              │  │              │             │   │
│   │   │ • API Server │  │ • API Server │  │ • API Server │             │   │
│   │   │ • etcd       │  │ • etcd       │  │ • etcd       │             │   │
│   │   │ • Scheduler  │  │ • Scheduler  │  │ • Scheduler  │             │   │
│   │   │ • Controller │  │ • Controller │  │ • Controller │             │   │
│   │   └──────────────┘  └──────────────┘  └──────────────┘             │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                │                                             │
│                    ┌───────────┴───────────┐                                │
│                    │   Calico CNI          │                                │
│                    │   Pod Network:        │                                │
│                    │   10.244.0.0/16       │                                │
│                    └───────────┬───────────┘                                │
│                                │                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                       Worker Nodes                                   │   │
│   │                                                                      │   │
│   │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │   │
│   │  │worker01 │  │worker02 │  │worker03 │  │worker04 │  │worker05 │   │   │
│   │  │ .20.40  │  │ .20.41  │  │ .20.42  │  │ .20.43  │  │ .20.44  │   │   │
│   │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │   │
│   │                                                                      │   │
│   │              ┌─────────┐                                            │   │
│   │              │worker06 │                                            │   │
│   │              │ .20.45  │                                            │   │
│   │              └─────────┘                                            │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Node Reference

### Control Plane Nodes

| Hostname | IP Address | Role | Resources | Proxmox Node |
|----------|------------|------|-----------|--------------|
| k8s-controller01 | 192.168.20.32 | Control Plane (Primary) | 2 CPU, 4GB RAM | node01 |
| k8s-controller02 | 192.168.20.33 | Control Plane | 2 CPU, 4GB RAM | node01 |
| k8s-controller03 | 192.168.20.34 | Control Plane | 2 CPU, 4GB RAM | node01 |

### Worker Nodes

| Hostname | IP Address | Role | Resources | Proxmox Node |
|----------|------------|------|-----------|--------------|
| k8s-worker01 | 192.168.20.40 | Worker | 2 CPU, 4GB RAM | node01 |
| k8s-worker02 | 192.168.20.41 | Worker | 2 CPU, 4GB RAM | node01 |
| k8s-worker03 | 192.168.20.42 | Worker | 2 CPU, 4GB RAM | node01 |
| k8s-worker04 | 192.168.20.43 | Worker | 2 CPU, 4GB RAM | node01 |
| k8s-worker05 | 192.168.20.44 | Worker | 2 CPU, 4GB RAM | node01 |
| k8s-worker06 | 192.168.20.45 | Worker | 2 CPU, 4GB RAM | node01 |

---

## Network Configuration

| Parameter | Value |
|-----------|-------|
| **VLAN** | 20 |
| **Node Network** | 192.168.20.0/24 |
| **Gateway** | 192.168.20.1 |
| **Pod Network CIDR** | 10.244.0.0/16 |
| **Service CIDR** | 10.96.0.0/12 |
| **API Server Endpoint** | https://192.168.20.32:6443 |

---

## Quick Access

### From Your Workstation

```bash
# Copy kubeconfig
mkdir -p ~/.kube
scp hermes-admin@192.168.20.32:~/.kube/config ~/.kube/config

# Verify access
kubectl get nodes
```

### From Ansible Controller

```bash
# SSH to controller
ssh hermes-admin@192.168.20.30

# Copy kubeconfig (if not already done)
mkdir -p ~/.kube
scp hermes-admin@192.168.20.32:~/.kube/config ~/.kube/config

# Use kubectl
kubectl get nodes
```

---

## Cluster Health Commands

### Check Nodes

```bash
# All nodes
kubectl get nodes

# Detailed view
kubectl get nodes -o wide

# Node conditions
kubectl describe nodes | grep -A5 "Conditions:"
```

### Check System Pods

```bash
# All system pods
kubectl get pods -n kube-system

# Control plane components
kubectl get pods -n kube-system | grep -E 'etcd|apiserver|controller|scheduler'

# Calico pods
kubectl get pods -n kube-system -l k8s-app=calico-node
```

### Cluster Info

```bash
# Basic cluster info
kubectl cluster-info

# Detailed dump
kubectl cluster-info dump
```

---

## Deployment Operations

### Deploy Application

```bash
# Create deployment
kubectl create deployment nginx --image=nginx --replicas=3

# Expose as service
kubectl expose deployment nginx --port=80 --type=NodePort

# Check status
kubectl get pods -o wide
kubectl get svc nginx

# Access via NodePort
NODE_PORT=$(kubectl get svc nginx -o jsonpath='{.spec.ports[0].nodePort}')
curl http://192.168.20.40:$NODE_PORT
```

### Scale Application

```bash
# Scale up
kubectl scale deployment nginx --replicas=5

# Scale down
kubectl scale deployment nginx --replicas=2
```

### Delete Application

```bash
kubectl delete deployment nginx
kubectl delete svc nginx
```

---

## Troubleshooting

### Node Not Ready

```bash
# Check node conditions
kubectl describe node <node-name> | grep -A10 "Conditions:"

# Check kubelet on the node
ssh hermes-admin@<node-ip> "sudo systemctl status kubelet"
ssh hermes-admin@<node-ip> "sudo journalctl -u kubelet --tail=50"

# Restart kubelet
ssh hermes-admin@<node-ip> "sudo systemctl restart kubelet"
```

### Pod Issues

```bash
# Check pod status
kubectl describe pod <pod-name>

# View pod logs
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # Previous container logs

# Execute in pod
kubectl exec -it <pod-name> -- /bin/bash
```

### Network Issues

```bash
# Check Calico status
kubectl get pods -n kube-system -l k8s-app=calico-node -o wide

# View Calico logs
kubectl logs -n kube-system -l k8s-app=calico-node --tail=50

# Test DNS
kubectl run test-dns --image=busybox:1.28 --rm -it --restart=Never -- nslookup kubernetes
```

---

## Ansible Playbooks

Located at `~/ansible/k8s/` on ansible-controller01:

| Playbook | Purpose |
|----------|---------|
| `01-k8s-prerequisites.yml` | System config, containerd |
| `02-k8s-install.yml` | Install kubeadm, kubelet, kubectl |
| `03-k8s-init-cluster.yml` | Initialize control plane |
| `04-k8s-install-cni.yml` | Install Calico CNI |
| `05-k8s-join-nodes.yml` | Join nodes to cluster |
| `k8s-deploy-all.yml` | Run all playbooks |

### Redeploy Cluster (if needed)

```bash
# SSH to ansible controller
ssh hermes-admin@192.168.20.30

# Reset cluster (WARNING: destroys cluster!)
ansible kubernetes -b -a "kubeadm reset -f"

# Redeploy
cd ~/ansible
ansible-playbook k8s/k8s-deploy-all.yml
```

---

## Maintenance

### Backup etcd

```bash
# On a control plane node
ssh hermes-admin@192.168.20.32

# Create backup
sudo ETCDCTL_API=3 etcdctl snapshot save /tmp/etcd-backup.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# Copy backup locally
scp hermes-admin@192.168.20.32:/tmp/etcd-backup.db ./
```

### Drain Node for Maintenance

```bash
# Mark node unschedulable and evict pods
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Perform maintenance...

# Make node schedulable again
kubectl uncordon <node-name>
```

### Upgrade Cluster

Follow official Kubernetes upgrade guide:
https://kubernetes.io/docs/tasks/administer-cluster/kubeadm/kubeadm-upgrade/

---

## External Traefik Integration

Kubernetes services are exposed through the external Traefik reverse proxy (192.168.40.20) using NodePort services.

### Architecture

```
Internet → Cloudflare → Traefik (192.168.40.20) → K8s NodePort → K8s Service → Pods
                              ↓
                        All 6 Workers
                        (.40, .41, .42, .43, .44, .45)
```

### How It Works

1. **K8s Service**: Deploy with `type: NodePort` to expose on all worker nodes
2. **Traefik Config**: Route hostname to NodePort across all workers (load balanced)
3. **OPNsense DNS**: Resolve hostname to Traefik IP (192.168.40.20)
4. **Let's Encrypt**: Traefik automatically obtains SSL certificates

### Example: Expose a Service

**Step 1: Deploy in Kubernetes**

```bash
# Create deployment
kubectl create deployment my-app --image=nginx --replicas=2

# Expose as NodePort
kubectl expose deployment my-app --port=80 --type=NodePort

# Get the NodePort
kubectl get svc my-app
# Example output: my-app NodePort 10.96.x.x 80:31234/TCP
```

**Step 2: Configure Traefik**

Create `/opt/traefik/config/dynamic/my-app.yml`:

```yaml
http:
  routers:
    my-app:
      rule: "Host(`my-app.hrmsmrflrii.xyz`)"
      service: my-app
      entryPoints:
        - websecure
      tls:
        certResolver: letsencrypt

  services:
    my-app:
      loadBalancer:
        servers:
          - url: "http://192.168.20.40:31234"  # Replace 31234 with actual NodePort
          - url: "http://192.168.20.41:31234"
          - url: "http://192.168.20.42:31234"
          - url: "http://192.168.20.43:31234"
          - url: "http://192.168.20.44:31234"
          - url: "http://192.168.20.45:31234"
```

**Step 3: Add DNS Record**

Add `my-app.hrmsmrflrii.xyz → 192.168.40.20` in OPNsense Unbound DNS.

### Current K8s Services via Traefik

| Service | URL | NodePort | Status |
|---------|-----|----------|--------|
| nginx-test | https://k8s-test.hrmsmrflrii.xyz | 31938 | Active |

### Test Service Directly

```bash
# Test via Traefik with Host header (bypass DNS)
curl -sk -H 'Host: k8s-test.hrmsmrflrii.xyz' https://192.168.40.20

# Test NodePort directly
curl http://192.168.20.40:31938
```

### Traefik Config Location

K8s service configurations are stored on traefik-vm01:

```
/opt/traefik/config/dynamic/k8s-services.yml
```

---

## What's Next?

- **[Services Overview](Services-Overview)** - Deploy services on the cluster
- **[Traefik](Traefik)** - Ingress controller configuration
- **[Command Cheatsheet](Command-Cheatsheet)** - kubectl quick reference

---

*Kubernetes cluster: production-grade infrastructure for containerized workloads.*
