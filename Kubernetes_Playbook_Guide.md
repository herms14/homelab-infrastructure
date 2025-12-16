# Kubernetes Playbook Guide for Learners

## Table of Contents
1. [Introduction](#introduction)
2. [Kubernetes Architecture Basics](#kubernetes-architecture-basics)
3. [Prerequisites Playbook Explained](#prerequisites-playbook-explained)
4. [Installation Playbook Explained](#installation-playbook-explained)
5. [Cluster Initialization Explained](#cluster-initialization-explained)
6. [CNI Installation Explained](#cni-installation-explained)
7. [Node Join Playbook Explained](#node-join-playbook-explained)
8. [Complete Deployment Flow](#complete-deployment-flow)
9. [Learning Resources](#learning-resources)

---

## Introduction

This guide explains every aspect of the Ansible playbooks used to deploy a production-grade Kubernetes cluster. It's designed for people learning both Kubernetes and Ansible, so we'll explain:
- **What** each task does
- **Why** it's necessary
- **How** the underlying commands work
- **What** would happen if you skipped it

### Our Cluster Architecture

We're building a **High Availability (HA) Kubernetes cluster**:
- **3 Control Plane Nodes**: Run Kubernetes management components
- **6 Worker Nodes**: Run your application containers
- **Stacked etcd**: Database runs on control plane nodes (not separate)

---

## Kubernetes Architecture Basics

Before diving into playbooks, let's understand what Kubernetes is:

### What is Kubernetes?

Kubernetes (K8s) is a **container orchestration platform**. Think of it as an operating system for your datacenter:
- **Containers**: Lightweight packages containing your application + dependencies
- **Orchestration**: Automatically managing where containers run, scaling them, and restarting failed ones

### Key Components

#### Control Plane Components (run on controller nodes)
1. **API Server**: The "front door" - all commands go through here
2. **etcd**: Database storing all cluster state (which pods are where, configurations, etc.)
3. **Scheduler**: Decides which worker node should run new containers
4. **Controller Manager**: Ensures desired state matches actual state (e.g., "I want 3 replicas" → keeps 3 running)

#### Worker Node Components
1. **kubelet**: Agent that runs on each node, manages containers on that node
2. **Container Runtime**: Actually runs containers (we use containerd)
3. **kube-proxy**: Handles networking between containers

#### Add-ons
1. **CNI (Container Network Interface)**: Enables pod-to-pod communication (we use Calico)

### How They Work Together

```
User → kubectl command → API Server → etcd (stores request)
                              ↓
                         Scheduler (picks node)
                              ↓
                         kubelet on worker (starts container)
                              ↓
                         Container Runtime (containerd runs it)
```

---

## Prerequisites Playbook Explained

**File**: `01-k8s-prerequisites.yml`

**Purpose**: Prepare the operating system to run Kubernetes. Linux needs specific configurations before Kubernetes can work properly.

### Full Playbook Breakdown

#### Task 1: Disable Swap Memory

```yaml
- name: Disable swap immediately
  command: swapoff -a
  when: ansible_swaptotal_mb > 0
```

**What it does**: Turns off swap memory right now (temporary until reboot)

**Command explained**:
- `swapoff -a`: Disable all swap partitions/files
  - `-a` = all swap devices

**Why it's required**:
- Kubernetes **requires** swap to be disabled
- **Swap** = using disk space as "fake" RAM when real RAM is full
- **Problem with swap**: Kubernetes expects predictable memory performance. If a container's memory gets swapped to disk, it becomes extremely slow and unpredictable
- Kubernetes manages memory limits itself - it doesn't want the OS interfering

**What happens if skipped**:
- kubelet will refuse to start with error: "running with swap on is not supported"

**Learning note**: The `when:` condition makes this task **idempotent** (safe to run multiple times) - it only runs if swap is actually enabled.

---

#### Task 2: Disable Swap Permanently

```yaml
- name: Remove swap entry from /etc/fstab
  lineinfile:
    path: /etc/fstab
    regexp: '^([^#].*?\sswap\s+sw\s+.*)$'
    line: '# \1'
    backrefs: yes
```

**What it does**: Comments out swap entries in /etc/fstab so swap stays disabled after reboot

**File explained**:
- `/etc/fstab`: "File System Table" - tells Linux which disks/partitions to mount at boot
- Example line: `/dev/sda2 none swap sw 0 0`

**Ansible module explained**:
- `lineinfile`: Edits a line in a file
- `regexp`: Regular expression to find the line
  - `^([^#].*?\sswap\s+sw\s+.*)$`: Find uncommented lines with "swap" and "sw"
  - `^` = start of line
  - `[^#]` = not a comment
  - `\s` = whitespace
- `backrefs: yes`: Allows using captured groups (the parentheses in regexp)
- `line: '# \1'`: Replace with `#` + original line (comments it out)

**Why not just delete it**: Commenting preserves the original configuration in case you need to reference it later.

---

#### Task 3: Load Kernel Modules Immediately

```yaml
- name: Load required kernel modules
  modprobe:
    name: "{{ item }}"
    state: present
  loop:
    - overlay
    - br_netfilter
```

**What it does**: Loads two kernel modules into memory right now

**Modules explained**:

1. **overlay**:
   - Used by container storage drivers
   - Allows layering filesystems (containers are built in layers)
   - Example: Base Ubuntu layer + App layer + Config layer = Final container
   - Without it: Containers can't create their filesystem layers

2. **br_netfilter**:
   - "Bridge netfilter" - allows iptables rules to work on bridged network traffic
   - Kubernetes uses network bridges to connect containers
   - Without it: Network policies and service routing won't work

**Command equivalent**: `modprobe overlay && modprobe br_netfilter`

**Why needed**: These modules aren't loaded by default on Ubuntu, but Kubernetes networking and storage depend on them.

---

#### Task 4: Load Kernel Modules Permanently

```yaml
- name: Ensure modules load on boot
  copy:
    dest: /etc/modules-load.d/k8s.conf
    content: |
      overlay
      br_netfilter
```

**What it does**: Creates a config file so modules load automatically on every boot

**File explained**:
- `/etc/modules-load.d/`: Directory where systemd reads module configs
- `k8s.conf`: Our custom file (name doesn't matter, `.conf` extension required)
- Contents: Just list module names, one per line

**Why separate from Task 3**:
- Task 3 loads them NOW (for immediate use)
- Task 4 loads them on NEXT BOOT (persistence)
- Both needed for a complete solution

---

#### Task 5: Configure sysctl Parameters

```yaml
- name: Set sysctl parameters for Kubernetes
  sysctl:
    name: "{{ item.name }}"
    value: "{{ item.value }}"
    state: present
    reload: yes
  loop:
    - { name: 'net.bridge.bridge-nf-call-iptables', value: '1' }
    - { name: 'net.bridge.bridge-nf-call-ip6tables', value: '1' }
    - { name: 'net.ipv4.ip_forward', value: '1' }
```

**What it does**: Changes Linux kernel networking parameters

**sysctl explained**:
- **sysctl** = "system control" - interface to modify kernel parameters at runtime
- Parameters stored in `/proc/sys/` virtual filesystem
- Command equivalent: `sysctl -w net.ipv4.ip_forward=1`

**Parameters explained**:

1. **net.bridge.bridge-nf-call-iptables = 1**
   - Makes bridged IPv4 traffic go through iptables rules
   - **iptables** = Linux firewall that routes/filters network packets
   - Kubernetes uses iptables for service load balancing
   - Example: Traffic to service IP `10.96.0.1` → iptables routes it to actual pod IP `10.244.1.5`
   - Without it: Services won't work, pods can't communicate

2. **net.bridge.bridge-nf-call-ip6tables = 1**
   - Same as above but for IPv6 traffic
   - Future-proofs your cluster for IPv6

3. **net.ipv4.ip_forward = 1**
   - Enables IP forwarding (routing traffic between network interfaces)
   - Linux by default doesn't forward packets between interfaces (acts like an endpoint, not a router)
   - Kubernetes nodes need to forward traffic between pods, so they need to act as routers
   - Without it: Pods on different nodes can't talk to each other

**Why reload: yes**: Applies changes immediately without reboot

**Persistence**: These settings are also written to `/etc/sysctl.d/k8s.conf` automatically by the sysctl module.

---

#### Task 6: Install containerd

```yaml
- name: Install containerd and dependencies
  apt:
    name:
      - containerd
      - apt-transport-https
      - ca-certificates
      - curl
      - gnupg
    state: present
    update_cache: yes
```

**What it does**: Installs the container runtime and helper tools

**Packages explained**:

1. **containerd**:
   - The container runtime - actually runs containers
   - Think of it as the "engine" that starts/stops containers
   - Kubernetes talks to containerd via CRI (Container Runtime Interface)
   - Alternative: Docker (but containerd is lighter and designed for Kubernetes)

2. **apt-transport-https**:
   - Allows `apt` package manager to download packages over HTTPS
   - Needed to securely download Kubernetes packages from Google's repository

3. **ca-certificates**:
   - "Certificate Authority certificates"
   - Trusted root certificates for verifying HTTPS connections
   - Without it: Can't verify if download sources are legitimate

4. **curl**:
   - Command-line tool for downloading files (used to fetch GPG keys)

5. **gnupg**:
   - "GNU Privacy Guard" - handles encryption and digital signatures
   - Used to verify package authenticity

**update_cache: yes**: Runs `apt update` first to refresh package lists

---

#### Task 7: Create containerd Configuration Directory

```yaml
- name: Create containerd configuration directory
  file:
    path: /etc/containerd
    state: directory
    mode: '0755'
```

**What it does**: Creates `/etc/containerd/` directory if it doesn't exist

**Parameters explained**:
- `state: directory`: Ensure it's a directory (not a file)
- `mode: '0755'`: Permission bits
  - `7` (owner) = read+write+execute
  - `5` (group) = read+execute
  - `5` (others) = read+execute
  - Standard for config directories

**Why needed**: Next task writes config to this directory.

---

#### Task 8: Generate Default containerd Config

```yaml
- name: Generate default containerd configuration
  shell: containerd config default > /etc/containerd/config.toml
  args:
    creates: /etc/containerd/config.toml
```

**What it does**: Creates containerd's configuration file with default settings

**Command breakdown**:
- `containerd config default`: Outputs default config to stdout
- `>`: Redirects output to file
- `/etc/containerd/config.toml`: Config file location
  - TOML = "Tom's Obvious Minimal Language" (config file format)

**args.creates**: Only runs if file doesn't exist (idempotency)

**Why needed**: Containerd needs configuration before it can start.

---

#### Task 9: Configure systemd cgroup Driver

```yaml
- name: Configure containerd to use systemd cgroup driver
  lineinfile:
    path: /etc/containerd/config.toml
    regexp: '^\s*SystemdCgroup\s*='
    line: '            SystemdCgroup = true'
    insertafter: '^\s*\[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options\]'
```

**What it does**: Changes containerd config to use systemd for cgroup management

**What are cgroups?**
- **Control Groups** = Linux kernel feature that limits/isolates resources (CPU, memory, disk I/O)
- Containers use cgroups to enforce resource limits
- Example: "This container can use max 2 CPU cores and 4GB RAM"

**Two cgroup managers**:
1. **cgroupfs**: Old default, direct filesystem interface
2. **systemd**: Modern, integrates with systemd init system

**Why systemd cgroup driver?**
- Kubernetes (kubelet) also uses cgroups to manage pods
- Problem: If kubelet uses systemd cgroups but containerd uses cgroupfs, you have TWO managers fighting for control
- Solution: Both must use the same manager (systemd is recommended by Kubernetes)
- **Without this**: Pods might not respect resource limits, unstable behavior

**Line breakdown**:
- `regexp`: Finds the SystemdCgroup line (might be commented or set to false)
- `line`: Replaces it with `SystemdCgroup = true` (indented to match TOML structure)
- `insertafter`: If line doesn't exist, add it after the [options] section

---

#### Task 10: Restart containerd

```yaml
- name: Restart containerd service
  systemd:
    name: containerd
    state: restarted
    enabled: yes
    daemon_reload: yes
```

**What it does**: Restarts containerd to apply configuration changes

**Parameters explained**:
- `state: restarted`: Stop then start the service
- `enabled: yes`: Enable to start automatically on boot
- `daemon_reload: yes`: Reload systemd manager configuration
  - systemd tracks services via unit files
  - This rereads all unit files in case they changed

**Why restart needed**: Configuration changes only take effect after restart.

---

### Prerequisites Summary

After this playbook runs, each node has:
- ✅ Swap disabled (Kubernetes requirement)
- ✅ Kernel modules loaded (overlay, br_netfilter for containers/networking)
- ✅ Network parameters configured (IP forwarding, bridge filtering)
- ✅ Container runtime installed and configured (containerd with systemd cgroups)

**Next step**: Install Kubernetes components (kubelet, kubeadm, kubectl)

---

## Installation Playbook Explained

**File**: `02-k8s-install.yml`

**Purpose**: Install Kubernetes packages on all nodes. This adds the actual Kubernetes software.

### Full Playbook Breakdown

#### Task 1: Create Keyrings Directory

```yaml
- name: Create keyrings directory
  file:
    path: /etc/apt/keyrings
    state: directory
    mode: '0755'
```

**What it does**: Creates directory to store GPG keys

**What are GPG keys?**
- **GPG** = GNU Privacy Guard, encryption/signing tool
- Package repositories sign their packages with GPG keys
- Your system verifies packages are authentic before installing
- Prevents malicious packages from being installed

**Why /etc/apt/keyrings?**:
- Modern Debian/Ubuntu standard location for repository keys
- Old location was `/etc/apt/trusted.gpg.d/` (still works but deprecated)

---

#### Task 2: Download Kubernetes GPG Key

```yaml
- name: Add Kubernetes GPG key
  get_url:
    url: https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key
    dest: /tmp/kubernetes-release.key
    mode: '0644'
```

**What it does**: Downloads the GPG key from Kubernetes package repository

**URL explained**:
- `https://pkgs.k8s.io`: Kubernetes package repository
- `core:/stable:/v1.28`: Version channel (v1.28 stable releases)
- `deb`: Debian/Ubuntu packages
- `Release.key`: GPG public key file

**Why to /tmp first**: We'll convert it to a different format in the next step.

---

#### Task 3: Convert GPG Key to Binary Format

```yaml
- name: Dearmor Kubernetes GPG key
  shell: gpg --dearmor < /tmp/kubernetes-release.key > /etc/apt/keyrings/kubernetes-apt-keyring.gpg
  args:
    creates: /etc/apt/keyrings/kubernetes-apt-keyring.gpg
```

**What it does**: Converts ASCII-armored GPG key to binary format

**Command breakdown**:
- `gpg --dearmor`: Convert ASCII key to binary
  - **ASCII-armored**: Text format (human readable, starts with `-----BEGIN PGP PUBLIC KEY BLOCK-----`)
  - **Dearmored**: Binary format (smaller, faster for computer to process)
- `<`: Read input from file
- `>`: Write output to file

**Why convert**: Modern apt requires binary format GPG keys in `/etc/apt/keyrings/`.

---

#### Task 4: Add Kubernetes Repository

```yaml
- name: Add Kubernetes apt repository
  apt_repository:
    repo: "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /"
    state: present
    filename: kubernetes
```

**What it does**: Adds Kubernetes package repository to apt sources

**Repository line explained**:
```
deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /
```

Breaking it down:
- `deb`: Type of repository (deb = Debian binary packages)
- `[signed-by=...]`: Which GPG key to use for verification
  - Only packages signed by this key will be trusted
  - Security measure against package tampering
- `https://pkgs.k8s.io/core:/stable:/v1.28/deb/`: Repository URL
  - `v1.28`: Kubernetes version 1.28.x (locks us to this minor version)
  - Prevents accidental upgrades to 1.29, 1.30, etc.
- `/`: Distribution (root of repository)

**filename: kubernetes**: Creates `/etc/apt/sources.list.d/kubernetes.list`

**Why separate repo**: Ubuntu's default repos don't have Kubernetes or have old versions.

---

#### Task 5: Update Package Cache

```yaml
- name: Update apt cache
  apt:
    update_cache: yes
```

**What it does**: Runs `apt update` to refresh package lists

**Why needed**:
- After adding new repository, apt doesn't know what packages are available
- `apt update` downloads package indexes from all repositories
- Without it: Next step won't find kubeadm/kubelet/kubectl

**What it downloads**:
- Package names, versions, dependencies
- NOT the actual packages (that comes in next step)

---

#### Task 6: Install Kubernetes Packages

```yaml
- name: Install Kubernetes packages
  apt:
    name:
      - kubelet
      - kubeadm
      - kubectl
    state: present
    update_cache: no
```

**What it does**: Installs the three core Kubernetes packages

**Packages explained**:

1. **kubelet**:
   - **The node agent** - runs on EVERY node (control plane + workers)
   - Responsibilities:
     - Registers node with cluster
     - Watches API server for pods assigned to this node
     - Starts/stops containers via containerd
     - Reports pod status back to API server
     - Mounts volumes into containers
     - Runs health checks (liveness/readiness probes)
   - **Analogy**: Like a property manager who maintains a building based on the landlord's instructions
   - Without it: Node can't join cluster, can't run pods

2. **kubeadm**:
   - **Cluster bootstrapping tool**
   - Responsibilities:
     - Initializes control plane (`kubeadm init`)
     - Joins nodes to cluster (`kubeadm join`)
     - Generates certificates for secure communication
     - Sets up control plane components (API server, scheduler, controller manager)
   - **Analogy**: Like an installer wizard that sets up a new system
   - Only used during cluster setup, not needed for daily operations
   - Without it: Manual cluster setup is extremely complex (100+ steps)

3. **kubectl**:
   - **Command-line client** (pronounced "kube-control" or "kube-cuttle")
   - Responsibilities:
     - Talks to API server
     - Deploys applications
     - Inspects cluster state
     - Manages resources
   - Example commands:
     - `kubectl get pods`: List all pods
     - `kubectl apply -f app.yaml`: Deploy application
     - `kubectl logs my-pod`: View pod logs
   - **Analogy**: Like a remote control for your cluster
   - Without it: Can't interact with cluster (except via API directly)

**Why all three?**
- Control plane nodes: Need all three
- Worker nodes: Technically only need kubelet, but installing all three is standard practice
  - Useful for debugging on workers
  - Allows promoting worker to control plane later

---

#### Task 7: Hold Kubernetes Packages

```yaml
- name: Hold Kubernetes packages at current version
  dpkg_selections:
    name: "{{ item }}"
    selection: hold
  loop:
    - kubelet
    - kubeadm
    - kubectl
```

**What it does**: Prevents automatic upgrades of Kubernetes packages

**apt-mark hold explained**:
- **Normal behavior**: `apt upgrade` updates all packages
- **With hold**: Package is skipped during `apt upgrade`
- Command equivalent: `apt-mark hold kubelet kubeadm kubectl`

**Why hold Kubernetes packages?**
- **Kubernetes upgrades must be done carefully**:
  - Control plane nodes upgraded first
  - Worker nodes upgraded one at a time
  - Version skew policies (control plane can only be 1 minor version ahead)
- **Automatic upgrades would break the cluster**:
  - Imagine worker upgraded to 1.29 but control plane still 1.28
  - Or control plane components upgraded out of order
  - Could cause downtime or data loss
- **Manual upgrade process**:
  1. Upgrade control plane node 1 (`kubeadm upgrade apply`)
  2. Upgrade other control plane nodes (`kubeadm upgrade node`)
  3. Upgrade worker nodes one by one (`kubeadm upgrade node`)
  4. Each upgrade includes draining pods first

**How to upgrade later**:
```bash
apt-mark unhold kubelet kubeadm kubectl
apt update
apt install -y kubelet=1.29.0-00 kubeadm=1.29.0-00 kubectl=1.29.0-00
apt-mark hold kubelet kubeadm kubectl
```

---

#### Task 8: Start and Enable kubelet

```yaml
- name: Enable and start kubelet service
  systemd:
    name: kubelet
    enabled: yes
    state: started
```

**What it does**: Starts kubelet service and configures it to start on boot

**Parameters**:
- `enabled: yes`: Create symlink in systemd to start on boot
- `state: started`: Start the service now

**Why start kubelet before cluster init?**
- kubelet service will start but fail with error: "no kubeconfig file"
- This is expected! Kubeconfig is created during `kubeadm init`
- After `kubeadm init`, kubelet automatically detects kubeconfig and starts working
- Starting it now ensures systemd configuration is correct

**What kubelet does before joining cluster**:
- Waits for `/etc/kubernetes/kubelet.conf` to appear
- Logs errors (this is normal)
- Once cluster is initialized, it joins automatically

---

### Installation Summary

After this playbook runs, each node has:
- ✅ Kubernetes GPG key installed (for package verification)
- ✅ Kubernetes repository added (version 1.28.x)
- ✅ kubelet, kubeadm, kubectl installed
- ✅ Packages held to prevent accidental upgrades
- ✅ kubelet service enabled and started (waiting for cluster init)

**Next step**: Initialize the cluster on the primary control plane node

---

## Cluster Initialization Explained

**File**: `03-k8s-init-cluster.yml`

**Purpose**: Create the cluster on the first control plane node and generate join commands for other nodes.

### Full Playbook Breakdown

#### Task 1: Check if Cluster Already Initialized

```yaml
- name: Check if Kubernetes is already initialized
  stat:
    path: /etc/kubernetes/admin.conf
  register: kubeadm_initialized
```

**What it does**: Checks if the cluster has already been set up

**File explained**:
- `/etc/kubernetes/admin.conf`: Kubeconfig file created by `kubeadm init`
- Contains:
  - API server address
  - Admin certificates for authentication
  - Cluster CA certificate
- If this file exists, cluster is already initialized

**Ansible register**: Saves result to variable `kubeadm_initialized`
- Can check later: `kubeadm_initialized.stat.exists` (true/false)

**Why check first**:
- Running `kubeadm init` on already-initialized node causes errors
- Makes playbook idempotent (safe to run multiple times)

---

#### Task 2: Initialize Kubernetes Cluster

```yaml
- name: Initialize Kubernetes cluster
  command: >
    kubeadm init
    --pod-network-cidr=10.244.0.0/16
    --control-plane-endpoint=192.168.20.32:6443
    --upload-certs
  when: not kubeadm_initialized.stat.exists
```

**What it does**: Creates the Kubernetes cluster on the first control plane node

**Command breakdown**:

```bash
kubeadm init
```
This single command does MANY things:

1. **Pre-flight checks**: Validates system (swap off, ports available, etc.)
2. **Generates certificates**: Creates CA + certificates for all components
   - etcd certificates
   - API server certificates
   - Service account signing keys
   - Admin client certificate
   - Certificates valid for 1 year by default
3. **Generates kubeconfig files**:
   - `/etc/kubernetes/admin.conf` (full admin access)
   - `/etc/kubernetes/kubelet.conf` (kubelet authentication)
   - `/etc/kubernetes/controller-manager.conf`
   - `/etc/kubernetes/scheduler.conf`
4. **Starts control plane containers**:
   - kube-apiserver
   - etcd
   - kube-controller-manager
   - kube-scheduler
   - These run as "static pods" (manifests in `/etc/kubernetes/manifests/`)
5. **Taints control plane node**: Marks it as `node-role.kubernetes.io/control-plane:NoSchedule`
   - Prevents regular pods from running on control plane
   - Only system pods and pods with matching tolerations can run here
6. **Waits for API server**: Ensures API server is responding
7. **Bootstraps RBAC**: Creates default roles and role bindings
8. **Creates CoreDNS**: Deploys DNS service for cluster
9. **Outputs join commands**: Shows commands to join other nodes

**Parameters explained**:

**`--pod-network-cidr=10.244.0.0/16`**:
- CIDR = "Classless Inter-Domain Routing" (IP address range notation)
- `10.244.0.0/16` = 10.244.0.0 to 10.244.255.255 (65,536 IPs)
- This is the IP range for pods (not nodes, not services)
- Each node gets a subnet from this range:
  - Node 1: 10.244.0.0/24 (256 IPs)
  - Node 2: 10.244.1.0/24 (256 IPs)
  - Node 3: 10.244.2.0/24 (256 IPs)
  - etc.
- **Why 10.244.0.0/16?**: Calico CNI default (our CNI plugin expects this)
- **Why specify it?**: Some CNI plugins need to know the range during installation
- **Important**: Must not overlap with:
  - Node network (192.168.20.0/24)
  - Service network (default 10.96.0.0/12)

**`--control-plane-endpoint=192.168.20.32:6443`**:
- Sets the API server endpoint for the cluster
- `192.168.20.32`: Primary control plane node IP
- `6443`: Kubernetes API server port (standard)
- **Why needed for HA?**:
  - In production, you'd use a load balancer IP here
  - All nodes connect to this endpoint
  - If control plane node fails, load balancer routes to another
  - For our homelab, we use the primary node IP (single point of failure, but simpler)
- **What uses this?**:
  - Worker nodes connect to this to join cluster
  - kubectl connects to this
  - Other control plane nodes connect to this

**`--upload-certs`**:
- Uploads control plane certificates to kubeadm-certs Secret
- Stored in cluster with 2-hour TTL
- **Why needed?**: Additional control plane nodes need these certificates
- **How it works**:
  1. Primary node creates certificates
  2. Encrypts them with random key
  3. Uploads to cluster (in kube-system namespace)
  4. Prints decryption key in join command
  5. Secondary control planes download and decrypt certificates
- **Without it**: You'd have to manually copy `/etc/kubernetes/pki/` to other nodes (insecure, complex)

**when condition**: Only runs if cluster not already initialized

---

#### Task 3: Create .kube Directory

```yaml
- name: Create .kube directory for root user
  file:
    path: /root/.kube
    state: directory
    mode: '0755'
```

**What it does**: Creates directory to store kubectl configuration

**Why /root/.kube?**:
- kubectl looks for config in `$HOME/.kube/config` by default
- We're running as root user, so `$HOME` = `/root`
- Standard location for user-specific kubectl config

**Mode 0755**: Owner can read/write/execute, others can read/execute

---

#### Task 4: Copy admin kubeconfig

```yaml
- name: Copy admin.conf to user's kube config
  copy:
    src: /etc/kubernetes/admin.conf
    dest: /root/.kube/config
    remote_src: yes
    owner: root
    group: root
    mode: '0600'
```

**What it does**: Copies admin credentials to kubectl's default location

**Files explained**:
- Source: `/etc/kubernetes/admin.conf` (created by kubeadm init)
- Destination: `/root/.kube/config` (where kubectl looks)
- `remote_src: yes`: Source file is on remote host (not Ansible controller)

**Mode 0600**: Only owner can read/write (keeps admin credentials secure)

**What's in this file?**:
```yaml
apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority-data: [base64 encoded CA cert]
    server: https://192.168.20.32:6443
  name: kubernetes
contexts:
- context:
    cluster: kubernetes
    user: kubernetes-admin
  name: kubernetes-admin@kubernetes
current-context: kubernetes-admin@kubernetes
users:
- name: kubernetes-admin
  user:
    client-certificate-data: [base64 encoded client cert]
    client-key-data: [base64 encoded client key]
```

**After this**, you can run:
```bash
kubectl get nodes  # Lists cluster nodes
kubectl get pods -A  # Lists all pods
```

---

#### Task 5: Wait for API Server

```yaml
- name: Wait for API server to be ready
  command: kubectl cluster-info
  register: cluster_info
  retries: 10
  delay: 10
  until: cluster_info.rc == 0
```

**What it does**: Waits until the API server is responding to requests

**kubectl cluster-info**: Shows cluster endpoint info
- Output: "Kubernetes control plane is running at https://192.168.20.32:6443"
- Exit code 0 = success, non-zero = failure

**Retry logic**:
- `retries: 10`: Try up to 10 times
- `delay: 10`: Wait 10 seconds between attempts
- `until: cluster_info.rc == 0`: Stop when return code is 0
- Maximum wait time: 100 seconds

**Why wait?**:
- API server takes 20-60 seconds to fully start
- It needs to:
  - Load certificates
  - Connect to etcd
  - Start serving HTTPS
- If we try to use kubectl too early, commands fail

---

#### Task 6: Wait for CoreDNS Pods

```yaml
- name: Wait for CoreDNS pods to be ready
  command: kubectl wait --for=condition=Ready pods -l k8s-app=kube-dns -n kube-system --timeout=300s
  register: coredns_wait
  retries: 3
  delay: 10
  until: coredns_wait.rc == 0
```

**What it does**: Waits for DNS pods to be fully running

**Command breakdown**:

```bash
kubectl wait --for=condition=Ready pods -l k8s-app=kube-dns -n kube-system --timeout=300s
```

- `kubectl wait`: Wait for a condition to be true
- `--for=condition=Ready`: Wait for "Ready" condition
  - Pods have multiple conditions: Initialized, Ready, ContainersReady, PodScheduled
  - Ready = pod is running and passing health checks
- `pods`: Resource type
- `-l k8s-app=kube-dns`: Label selector (finds CoreDNS pods)
  - All Kubernetes resources have labels (key-value pairs)
  - CoreDNS pods are labeled with `k8s-app=kube-dns`
- `-n kube-system`: Namespace
  - kube-system = system namespace for Kubernetes components
- `--timeout=300s`: Give up after 5 minutes

**Why wait for CoreDNS?**:
- Without DNS, services can't find each other
- Pods use DNS names like `my-service.default.svc.cluster.local`
- CoreDNS won't start until CNI is installed (catch-22)
- This task will fail initially, that's why we have the CNI installation playbook next

**Retry logic**: Try 3 times, wait 10 seconds between attempts

---

#### Task 7: Generate Controller Join Command

```yaml
- name: Generate join command for additional control plane nodes
  shell: |
    CERT_KEY=$(kubeadm init phase upload-certs --upload-certs 2>/dev/null | tail -1)
    JOIN_CMD=$(kubeadm token create --print-join-command 2>/dev/null)
    echo "$JOIN_CMD --control-plane --certificate-key $CERT_KEY"
  register: join_command_controllers
```

**What it does**: Creates the command other control planes use to join the cluster

**Command breakdown**:

**Line 1: Upload and get certificate key**
```bash
CERT_KEY=$(kubeadm init phase upload-certs --upload-certs 2>/dev/null | tail -1)
```
- `kubeadm init phase upload-certs`: Runs just the "upload certs" phase of kubeadm init
  - Uploads control plane certificates to cluster
  - Prints upload key at the end
- `--upload-certs`: Actually perform the upload
- `2>/dev/null`: Suppress error messages
- `tail -1`: Get last line (the certificate key)
- `CERT_KEY=`: Save to variable
- Result: `CERT_KEY=abc123def456...` (64-character hex string)

**Line 2: Generate basic join command**
```bash
JOIN_CMD=$(kubeadm token create --print-join-command 2>/dev/null)
```
- `kubeadm token create`: Creates a new bootstrap token
  - Tokens allow nodes to join cluster
  - Valid for 24 hours by default
  - Used for authentication during join
- `--print-join-command`: Output full join command
- Result: `JOIN_CMD=kubeadm join 192.168.20.32:6443 --token abc123.xyz789 --discovery-token-ca-cert-hash sha256:abc123...`

**Line 3: Combine into control plane join command**
```bash
echo "$JOIN_CMD --control-plane --certificate-key $CERT_KEY"
```
- Takes basic join command
- Adds `--control-plane`: Marks this as control plane join (not worker)
- Adds `--certificate-key`: Provides decryption key for certificates
- Final result:
  ```bash
  kubeadm join 192.168.20.32:6443 \
    --token abc123.xyz789 \
    --discovery-token-ca-cert-hash sha256:abc123... \
    --control-plane \
    --certificate-key def456...
  ```

**Why so complex?**:
- Control planes need certificates (workers don't)
- Certificates are encrypted in cluster
- Need decryption key to get certificates
- All this needs to happen securely

---

#### Task 8: Generate Worker Join Command

```yaml
- name: Generate join command for worker nodes
  command: kubeadm token create --print-join-command
  register: join_command_workers
```

**What it does**: Creates simpler command for worker nodes to join

**Command**: `kubeadm token create --print-join-command`

**Result**:
```bash
kubeadm join 192.168.20.32:6443 \
  --token abc123.xyz789 \
  --discovery-token-ca-cert-hash sha256:abc123...
```

**Simpler than control plane because**:
- No `--control-plane` flag
- No `--certificate-key` (workers don't run control plane components)
- Workers only need:
  - Token (for authentication)
  - CA cert hash (to verify API server identity)

**Token explained**:
- Format: `abc123.xyz789`
  - First part: Token ID (public)
  - Second part: Token secret (private)
- Used once during join, then node gets permanent credentials

**Discovery token CA cert hash**:
- Hash of the cluster's CA certificate
- Prevents man-in-the-middle attacks
- Node verifies API server's certificate matches this hash
- Without it: Attacker could impersonate API server and capture credentials

---

#### Task 9: Save Controller Join Command

```yaml
- name: Save controller join command locally
  local_action:
    module: copy
    content: "{{ join_command_controllers.stdout }}"
    dest: ~/ansible/k8s/join-command-controllers.sh
```

**What it does**: Saves controller join command to file on Ansible controller

**local_action**: Runs task on Ansible control machine (not remote host)

**File created**: `~/ansible/k8s/join-command-controllers.sh`

**Contents**:
```bash
kubeadm join 192.168.20.32:6443 --token abc123.xyz789 --discovery-token-ca-cert-hash sha256:abc123... --control-plane --certificate-key def456...
```

**Why save it?**:
- Used in next playbook to join additional control planes
- Human-readable backup if automation fails

---

#### Task 10: Save Worker Join Command

```yaml
- name: Save worker join command locally
  local_action:
    module: copy
    content: "{{ join_command_workers.stdout }}"
    dest: ~/ansible/k8s/join-command-workers.sh
```

**What it does**: Saves worker join command to file on Ansible controller

**File created**: `~/ansible/k8s/join-command-workers.sh`

**Contents**:
```bash
kubeadm join 192.168.20.32:6443 --token abc123.xyz789 --discovery-token-ca-cert-hash sha256:abc123...
```

**Why separate files?**:
- Different commands for control planes vs workers
- Easier to read/debug
- Can manually join nodes if needed

---

### Initialization Summary

After this playbook runs:
- ✅ Cluster created on primary control plane (k8s-controller01)
- ✅ Control plane components running (API server, scheduler, controller manager, etcd)
- ✅ kubectl configured for root user
- ✅ Join commands generated and saved
- ⚠️ CoreDNS pending (needs CNI plugin)

**Next step**: Install CNI so pods can communicate

---

## CNI Installation Explained

**File**: `04-k8s-install-cni.yml`

**Purpose**: Install Calico CNI to enable pod networking

### What is CNI?

**CNI** = Container Network Interface

**The problem**: Containers on different nodes need to talk to each other, but they're on different networks.

**Example without CNI**:
- Pod A on Node 1: IP 10.244.0.5
- Pod B on Node 2: IP 10.244.1.5
- Node 1 doesn't know how to route traffic to 10.244.1.0/24
- Pods can't communicate

**What CNI does**:
1. Assigns IP addresses to pods
2. Sets up routing between nodes
3. Configures network policies (firewalls between pods)
4. Provides DNS

**CNI options**:
- **Calico**: Feature-rich, supports network policies, good for production (our choice)
- **Flannel**: Simple, good for testing
- **Weave**: Auto-discovery, good for multi-cloud
- **Cilium**: eBPF-based, very fast, complex

### Full Playbook Breakdown

#### Task 1: Download Calico Manifest

```yaml
- name: Download Calico manifest
  get_url:
    url: "https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/calico.yaml"
    dest: /tmp/calico.yaml
    mode: '0644'
```

**What it does**: Downloads Calico installation file from GitHub

**URL explained**:
- `projectcalico/calico`: Official Calico repository
- `v3.27.0`: Calico version (stable as of 2024)
- `manifests/calico.yaml`: All-in-one installation file

**What's in calico.yaml?**:
- CustomResourceDefinitions (CRDs): New resource types (FelixConfiguration, BGPConfiguration, etc.)
- ServiceAccount: Identity for Calico pods
- RBAC: Permissions for Calico to manage networking
- DaemonSet: Ensures calico-node runs on every node
- Deployment: Runs calico-kube-controllers
- ConfigMap: Calico configuration

**Why download first?**:
- Could apply directly from URL, but downloading allows inspection/modification
- Good practice: know what you're installing

---

#### Task 2: Check for Existing CNI

```yaml
- name: Check if Calico is already installed
  command: kubectl get daemonset calico-node -n kube-system
  register: calico_check
  ignore_errors: yes
```

**What it does**: Checks if Calico is already running

**Command explained**:
- `kubectl get daemonset calico-node`: Get the calico-node DaemonSet
- `-n kube-system`: In kube-system namespace
- DaemonSet = pod that runs on every node (like kubelet but in Kubernetes)

**ignore_errors: yes**: Don't fail playbook if DaemonSet doesn't exist

**Return code**:
- 0 = DaemonSet exists (Calico installed)
- Non-zero = DaemonSet doesn't exist (Calico not installed)

---

#### Task 3: Apply Calico Manifest

```yaml
- name: Apply Calico manifest
  command: kubectl --kubeconfig=/etc/kubernetes/admin.conf apply -f /tmp/calico.yaml
  when: calico_check.rc != 0
```

**What it does**: Installs Calico into the cluster

**Command breakdown**:
- `kubectl apply`: Create or update resources
  - Declarative: "Make the cluster look like this file"
  - Can run multiple times safely (idempotent)
- `-f /tmp/calico.yaml`: From file
- `--kubeconfig=/etc/kubernetes/admin.conf`: Explicit kubeconfig (ensures we use admin credentials)

**when condition**: Only if Calico not already installed

**What happens when you run this?**:
1. kubectl reads calico.yaml
2. Sends resources to API server
3. API server stores them in etcd
4. Controllers notice new resources:
   - DaemonSet controller creates calico-node pods on each node
   - Deployment controller creates calico-kube-controllers pod
   - ServiceAccount controller creates tokens
5. Scheduler assigns pods to nodes
6. kubelet on each node starts the pods
7. Calico pods start configuring networking

---

#### Task 4: Wait for Calico Pods

```yaml
- name: Wait for Calico pods to be ready
  command: kubectl wait --for=condition=Ready pods -l k8s-app=calico-node -n kube-system --timeout=300s
  register: calico_wait
  retries: 3
  delay: 10
  until: calico_wait.rc == 0
```

**What it does**: Waits for Calico pods to start successfully

**Command explained**:
- `-l k8s-app=calico-node`: Label selector for Calico node pods
- Similar to CoreDNS wait, but for Calico

**Why wait?**:
- Calico pods take 30-60 seconds to start
- Need to:
  - Download images
  - Configure networking
  - Set up routes
- Following tasks depend on networking working

**Timeout**: 5 minutes (Calico is more complex than CoreDNS)

---

#### Task 5: Verify CoreDNS After CNI

```yaml
- name: Verify CoreDNS pods are now running
  command: kubectl wait --for=condition=Ready pods -l k8s-app=kube-dns -n kube-system --timeout=300s
```

**What it does**: Confirms CoreDNS is now running (it was pending before)

**Why now?**:
- CoreDNS pods couldn't start without CNI
- They were stuck in "Pending" state
- Needed pod IPs, but no CNI to assign them
- Now that Calico is running:
  1. Calico assigns IPs to CoreDNS pods
  2. Sets up routes for them
  3. Pods can start

**This confirms networking is fully working**

---

### CNI Summary

After this playbook runs:
- ✅ Calico CNI installed and running
- ✅ Pod-to-pod networking enabled
- ✅ Each node has calico-node pod
- ✅ CoreDNS now running
- ✅ Cluster ready for pods

**How Calico works**:
1. When pod is created:
   - kubelet asks CNI plugin for IP
   - Calico assigns IP from node's subnet
   - Calico sets up network namespace
   - Calico configures routes
2. When pod talks to another pod:
   - Packet goes to Calico veth pair
   - Calico looks up destination
   - Routes packet to correct node
   - Other node's Calico delivers to pod

**Next step**: Join additional control planes and workers

---

## Node Join Playbook Explained

**File**: `05-k8s-join-nodes.yml`

**Purpose**: Add remaining control plane nodes and all worker nodes to the cluster

### Full Playbook Breakdown

#### Play 1: Join Additional Control Plane Nodes

```yaml
- name: Join Additional Control Plane Nodes
  hosts: k8s_controllers:!k8s_primary_controller
  become: yes
```

**What it does**: Runs tasks on controller02 and controller03 (not controller01)

**Inventory selection explained**:
- `k8s_controllers`: Group containing all 3 controllers
- `:!k8s_primary_controller`: Exclude primary controller (the `!` means NOT)
- Result: Only controller02 and controller03

**Why exclude primary?**: Already initialized in previous playbook

---

#### Task 1.1: Check if Controller Already Joined

```yaml
- name: Check if node is already part of cluster
  stat:
    path: /etc/kubernetes/kubelet.conf
  register: node_joined
```

**What it does**: Checks if this node has already joined

**File explained**:
- `/etc/kubernetes/kubelet.conf`: Created when node joins
- Contains kubelet's credentials for talking to API server
- If exists = already joined

**Why check**: Safe to run playbook multiple times

---

#### Task 1.2: Read Controller Join Command

```yaml
- name: Read controller join command
  set_fact:
    join_command: "{{ lookup('file', '~/ansible/k8s/join-command-controllers.sh') }}"
  when: not node_joined.stat.exists
```

**What it does**: Loads join command from saved file

**Ansible modules used**:
- `set_fact`: Creates a variable
- `lookup('file', ...)`: Reads file contents
- File: `join-command-controllers.sh` (created in previous playbook)

**Result**: Variable `join_command` contains:
```bash
kubeadm join 192.168.20.32:6443 --token abc123.xyz789 --discovery-token-ca-cert-hash sha256:abc123... --control-plane --certificate-key def456...
```

---

#### Task 1.3: Join Control Plane

```yaml
- name: Join node to cluster as control plane
  command: "{{ join_command }}"
  when: not node_joined.stat.exists
```

**What it does**: Runs the join command to add this node as a control plane

**What happens during join**:

1. **Pre-flight checks**: Same as kubeadm init (swap, ports, etc.)

2. **Discovery**:
   - Connects to API server (192.168.20.32:6443)
   - Verifies API server cert matches CA hash
   - If mismatch = abort (prevents MITM attack)

3. **Authentication**:
   - Presents bootstrap token
   - API server validates token
   - Token is single-use for this node

4. **Download cluster info**:
   - Gets CA certificate
   - Gets cluster configuration
   - Gets component versions

5. **Download control plane certificates** (because `--control-plane` flag):
   - Downloads encrypted certificates from kubeadm-certs Secret
   - Decrypts using `--certificate-key`
   - Saves to `/etc/kubernetes/pki/`
   - Certificates include:
     - API server cert
     - API server kubelet client cert
     - Front proxy cert
     - Service account signing key

6. **Generate node certificate**:
   - Creates certificate signing request (CSR)
   - API server signs it
   - Node gets unique certificate

7. **Write kubeconfig files**:
   - `/etc/kubernetes/admin.conf`
   - `/etc/kubernetes/kubelet.conf`
   - `/etc/kubernetes/controller-manager.conf`
   - `/etc/kubernetes/scheduler.conf`

8. **Start control plane components**:
   - Creates static pod manifests in `/etc/kubernetes/manifests/`
   - kubelet detects manifests and starts pods:
     - kube-apiserver
     - etcd (joins existing etcd cluster)
     - kube-controller-manager (standby mode, primary is elected)
     - kube-scheduler (standby mode, primary is elected)

9. **Register node**:
   - kubelet registers node with cluster
   - Node appears in `kubectl get nodes`

10. **Mark as control plane**:
    - Adds label: `node-role.kubernetes.io/control-plane=`
    - Adds taint: `node-role.kubernetes.io/control-plane:NoSchedule`

**After join**: Node is fully functional control plane member

---

#### Task 1.4: Create .kube Directory

```yaml
- name: Create .kube directory
  file:
    path: /root/.kube
    state: directory
    mode: '0755'
  when: not node_joined.stat.exists
```

**Same as primary controller**: Creates directory for kubectl config

---

#### Task 1.5: Copy kubeconfig

```yaml
- name: Copy admin.conf to .kube/config
  copy:
    src: /etc/kubernetes/admin.conf
    dest: /root/.kube/config
    remote_src: yes
    owner: root
    group: root
    mode: '0600'
  when: not node_joined.stat.exists
```

**Same as primary controller**: Enables kubectl on this node

**Now you can run kubectl on any control plane node**

---

#### Play 2: Join Worker Nodes

```yaml
- name: Join Worker Nodes
  hosts: k8s_workers
  become: yes
  serial: 2
```

**What it does**: Adds all 6 worker nodes to cluster

**serial: 2**: Join 2 workers at a time
- Prevents overwhelming cluster
- If one fails, others haven't started yet (easier to debug)
- Production-ready approach

**Why serial matters**:
- Each join:
  - Creates network routes
  - Downloads images
  - Starts Calico pod
  - Registers with API server
- 6 simultaneous joins = high load on API server
- Serial = controlled rollout

---

#### Task 2.1: Check if Worker Already Joined

```yaml
- name: Check if node is already part of cluster
  stat:
    path: /etc/kubernetes/kubelet.conf
  register: node_joined
```

**Same check as control planes**: Looks for kubelet.conf

---

#### Task 2.2: Read Worker Join Command

```yaml
- name: Read worker join command
  set_fact:
    join_command: "{{ lookup('file', '~/ansible/k8s/join-command-workers.sh') }}"
  when: not node_joined.stat.exists
```

**What it does**: Loads worker join command

**File**: `join-command-workers.sh` (simpler, no --control-plane flag)

---

#### Task 2.3: Join as Worker

```yaml
- name: Join node to cluster as worker
  command: "{{ join_command }}"
  when: not node_joined.stat.exists
```

**What it does**: Runs join command to add worker node

**What happens during worker join**:

1-4. **Same as control plane**: Discovery, authentication, download cluster info, generate node cert

5. **Skip certificate download**: Workers don't need control plane certs

6. **Write kubelet config only**:
   - `/etc/kubernetes/kubelet.conf`
   - No admin.conf, controller-manager.conf, scheduler.conf

7. **Start kubelet** (no control plane components):
   - kubelet registers node with cluster
   - Starts waiting for pod assignments

8. **Calico pod starts**:
   - DaemonSet controller notices new node
   - Creates calico-node pod on this node
   - Pod starts, configures networking

9. **Mark as worker**:
   - Adds label: `node-role.kubernetes.io/worker=` (optional)
   - No taint (workers accept all pods)

**After join**: Node ready to run workloads

---

#### Task 2.4: Wait Between Batches

```yaml
- name: Wait for node to be ready before joining next batch
  command: kubectl --kubeconfig=/etc/kubernetes/admin.conf get nodes
  delegate_to: "{{ groups['k8s_primary_controller'][0] }}"
  when: not node_joined.stat.exists
```

**What it does**: Pauses between serial batches

**delegate_to**: Runs command on primary controller (not worker)
- Workers don't have kubectl configured
- Check cluster state from controller

**Why wait**: Ensures previous batch joined successfully before starting next

---

### Join Summary

After this playbook runs:
- ✅ 3 control plane nodes (HA cluster)
  - etcd running on all 3 (quorum = 2, can tolerate 1 failure)
  - API server on all 3 (load balanced)
  - Scheduler on all 3 (1 active, 2 standby)
  - Controller manager on all 3 (1 active, 2 standby)
- ✅ 6 worker nodes ready for pods
- ✅ All nodes have Calico networking
- ✅ Cluster fully operational

**High availability achieved**:
- If controller01 fails: controller02/03 handle requests
- If worker fails: Pods rescheduled to other workers
- If etcd node fails: Cluster continues with 2/3 quorum

---

## Complete Deployment Flow

### Visual Overview

```
[Prerequisites] → All nodes prepared
       ↓
[Installation] → Kubernetes packages installed
       ↓
[Init Cluster] → Primary controller creates cluster
       ↓
[Install CNI] → Networking enabled
       ↓
[Join Nodes] → Full cluster assembled
```

### Step-by-Step What Happens

**Step 1: Prerequisites (all 9 nodes in parallel)**
- System configured for containers
- Container runtime installed
- ~2 minutes per node

**Step 2: Installation (all 9 nodes in parallel)**
- Kubernetes packages installed
- kubelet started (waiting)
- ~3 minutes per node

**Step 3: Cluster Init (controller01 only)**
- Control plane created
- etcd initialized
- Certificates generated
- Join commands created
- ~3-5 minutes

**Step 4: CNI Installation (controller01 only)**
- Calico deployed
- Networking enabled
- CoreDNS starts
- ~2-3 minutes

**Step 5: Join Nodes (sequential)**
- controller02, controller03 join (parallel): ~2 minutes each
- worker01-06 join (2 at a time): ~1 minute each
- Total: ~8 minutes

**Total deployment time: ~20-25 minutes**

### Verification Commands

After deployment, verify cluster health:

```bash
# Check all nodes joined
kubectl get nodes
# Should show 9 nodes, all Ready

# Check control plane components
kubectl get pods -n kube-system
# Should see:
# - etcd-controller01/02/03
# - kube-apiserver-controller01/02/03
# - kube-scheduler-controller01/02/03
# - kube-controller-manager-controller01/02/03
# - calico-node-* (9 pods, 1 per node)
# - calico-kube-controllers
# - coredns-* (2 pods)

# Test pod scheduling
kubectl run test-nginx --image=nginx
kubectl get pod test-nginx -o wide
# Should schedule to a worker, get IP, start running

# Test pod-to-pod networking
kubectl run test-curl --image=curlimages/curl --rm -it -- curl http://<test-nginx-pod-ip>
# Should return nginx welcome page

# Test DNS
kubectl run test-dns --image=busybox --rm -it -- nslookup kubernetes.default
# Should resolve to service IP

# Test service load balancing
kubectl expose pod test-nginx --port=80
kubectl run test-service --image=curlimages/curl --rm -it -- curl http://test-nginx
# Should reach nginx via service name
```

### What You Now Have

A **production-grade Kubernetes cluster** with:

**High Availability**:
- 3 control planes (survive 1 failure)
- 6 workers (can tolerate multiple failures)
- Distributed etcd (survive 1 failure)

**Networking**:
- Pod-to-pod communication (Calico)
- Service discovery (CoreDNS)
- Network policies ready (Calico)

**Ready for**:
- Application deployments
- Load balancing (Services)
- Auto-scaling (HPA)
- Persistent storage (when configured)
- Monitoring (Prometheus)
- Logging (ELK stack)

---

## Learning Resources

### Kubernetes Concepts

**Official Docs**:
- [Kubernetes Basics](https://kubernetes.io/docs/tutorials/kubernetes-basics/)
- [Concepts](https://kubernetes.io/docs/concepts/)

**Free Courses**:
- [Kubernetes for Beginners (KodeKloud)](https://kodekloud.com/courses/kubernetes-for-the-absolute-beginners-hands-on/)
- [Introduction to Kubernetes (edX)](https://www.edx.org/course/introduction-to-kubernetes)

**Books**:
- "Kubernetes Up & Running" by Kelsey Hightower
- "The Kubernetes Book" by Nigel Poulton

### Ansible Concepts

**Official Docs**:
- [Ansible Getting Started](https://docs.ansible.com/ansible/latest/getting_started/index.html)
- [Playbook Best Practices](https://docs.ansible.com/ansible/latest/tips_tricks/ansible_tips_tricks.html)

**Free Courses**:
- [Ansible for Beginners (KodeKloud)](https://kodekloud.com/courses/ansible-for-the-absolute-beginners/)

### Hands-On Practice

**Local Kubernetes**:
- [minikube](https://minikube.sigs.k8s.io/): Single-node cluster on your laptop
- [kind](https://kind.sigs.k8s.io/): Kubernetes in Docker

**Kubernetes Challenges**:
- [Kubernetes the Hard Way](https://github.com/kelseyhightower/kubernetes-the-hard-way): Manual cluster setup
- [CKA Practice](https://killer.sh/): Certified Kubernetes Administrator practice

### Community

- [Kubernetes Slack](https://slack.k8s.io/)
- [r/kubernetes](https://reddit.com/r/kubernetes)
- [Kubernetes Forum](https://discuss.kubernetes.io/)

---

## Glossary

**API Server**: The front door to Kubernetes, all requests go through it
**CNI**: Container Network Interface - enables pod networking
**containerd**: Container runtime that actually runs containers
**Control Plane**: Management layer of Kubernetes (API, scheduler, controllers)
**CoreDNS**: DNS server for service discovery in the cluster
**DaemonSet**: Ensures a pod runs on all (or some) nodes
**Deployment**: Manages a replicated application
**etcd**: Key-value database storing all cluster state
**HA**: High Availability - can survive component failures
**Idempotent**: Safe to run multiple times, same result
**kubeadm**: Tool to bootstrap Kubernetes clusters
**kubectl**: Command-line tool to interact with Kubernetes
**kubelet**: Agent running on each node, manages containers
**Namespace**: Virtual cluster within a cluster (isolation)
**Node**: A machine (VM or physical) in the cluster
**Pod**: Smallest deployable unit, contains one or more containers
**RBAC**: Role-Based Access Control - permissions system
**Service**: Stable network endpoint for a set of pods
**Static Pod**: Pod managed by kubelet directly (not API server)
**Taint**: Marks node to repel pods (unless they tolerate it)
**Worker**: Node that runs application workloads

---

**Next Steps**:
1. Run the deployment: `ansible-playbook k8s/k8s-deploy-all.yml`
2. Verify cluster: `kubectl get nodes`
3. Deploy your first app: `kubectl create deployment hello-world --image=nginx`
4. Learn more: Read official Kubernetes tutorials

Happy learning! 🚀
