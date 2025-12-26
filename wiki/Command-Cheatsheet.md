# Command Cheatsheet

> **TL;DR**: Quick reference for commonly used commands across Terraform, Ansible, Docker, Proxmox, and Kubernetes.

## Terraform Commands

### Basic Operations

| Command | Description |
|---------|-------------|
| `terraform init` | Initialize working directory, download providers |
| `terraform plan` | Preview changes without applying |
| `terraform apply` | Apply changes to infrastructure |
| `terraform destroy` | Destroy all managed resources |
| `terraform fmt` | Format configuration files |
| `terraform validate` | Validate configuration syntax |

### State Management

| Command | Description |
|---------|-------------|
| `terraform state list` | List all resources in state |
| `terraform state show <resource>` | Show resource details |
| `terraform state rm <resource>` | Remove resource from state |
| `terraform refresh` | Sync state with real infrastructure |
| `terraform import <resource> <id>` | Import existing resource |

### Targeting

```bash
# Apply specific resource
terraform apply -target=module.vms["ansible-controller01"]

# Destroy specific resource
terraform destroy -target=module.vms["test-vm"]

# Plan with target
terraform plan -target=module.lxc
```

### Variables

```bash
# Pass variable
terraform apply -e "vm_count=5"

# Use variable file
terraform apply -var-file="prod.tfvars"

# Auto-approve
terraform apply -auto-approve
```

---

## Ansible Commands

### Playbooks

| Command | Description |
|---------|-------------|
| `ansible-playbook playbook.yml` | Run playbook |
| `ansible-playbook playbook.yml -l host` | Limit to specific host |
| `ansible-playbook playbook.yml --check` | Dry run |
| `ansible-playbook playbook.yml --diff` | Show file changes |
| `ansible-playbook playbook.yml -v` | Verbose output |
| `ansible-playbook playbook.yml -vvv` | Debug output |

### Ad-Hoc Commands

```bash
# Ping all hosts
ansible all -m ping

# Run command on all hosts
ansible all -a "uptime"

# Run command on specific group
ansible docker_hosts -a "docker ps"

# Install package
ansible all -m apt -a "name=htop state=present" -b

# Copy file
ansible all -m copy -a "src=./file dest=/tmp/file"

# Restart service
ansible docker_hosts -m systemd -a "name=docker state=restarted" -b
```

### Inventory

```bash
# List all hosts
ansible-inventory --list

# Show host variables
ansible-inventory --host hostname

# Graph structure
ansible-inventory --graph
```

### Vault

```bash
# Create encrypted file
ansible-vault create secrets.yml

# Edit encrypted file
ansible-vault edit secrets.yml

# View encrypted file
ansible-vault view secrets.yml

# Run with vault
ansible-playbook playbook.yml --ask-vault-pass
```

---

## Docker Commands

### Container Management

| Command | Description |
|---------|-------------|
| `docker ps` | List running containers |
| `docker ps -a` | List all containers |
| `docker start <name>` | Start container |
| `docker stop <name>` | Stop container |
| `docker restart <name>` | Restart container |
| `docker rm <name>` | Remove container |
| `docker logs <name>` | View logs |
| `docker logs -f <name>` | Follow logs |
| `docker exec -it <name> bash` | Shell into container |

### Images

| Command | Description |
|---------|-------------|
| `docker images` | List images |
| `docker pull <image>` | Pull image |
| `docker rmi <image>` | Remove image |
| `docker image prune` | Remove unused images |

### Docker Compose

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# Restart services
docker compose restart

# View logs
docker compose logs -f

# Pull latest images
docker compose pull

# Recreate containers
docker compose up -d --force-recreate

# Build and start
docker compose up -d --build
```

### Cleanup

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Remove everything unused
docker system prune -a
```

---

## Proxmox Commands

### VM Management

| Command | Description |
|---------|-------------|
| `qm list` | List all VMs |
| `qm start <vmid>` | Start VM |
| `qm shutdown <vmid>` | Graceful shutdown |
| `qm stop <vmid>` | Force stop |
| `qm reboot <vmid>` | Reboot VM |
| `qm config <vmid>` | Show VM config |
| `qm clone <source> <target>` | Clone VM |
| `qm template <vmid>` | Convert to template |

### Container Management

| Command | Description |
|---------|-------------|
| `pct list` | List all containers |
| `pct start <vmid>` | Start container |
| `pct stop <vmid>` | Stop container |
| `pct enter <vmid>` | Enter container shell |
| `pct config <vmid>` | Show config |
| `pct exec <vmid> -- <cmd>` | Execute command |

### Storage

| Command | Description |
|---------|-------------|
| `pvesm status` | List storage pools |
| `pvesm list <storage>` | List storage content |
| `pvesm alloc <storage> <vmid> <name> <size>` | Allocate disk |

### Cluster

| Command | Description |
|---------|-------------|
| `pvecm status` | Cluster status |
| `pvecm nodes` | List nodes |
| `pvesh get /cluster/resources --type node` | Node resources |

### Templates

```bash
# Update template list
pveam update

# List available
pveam available

# Download template
pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst

# List downloaded
pveam list local
```

---

## Kubernetes Commands

### Cluster Info

| Command | Description |
|---------|-------------|
| `kubectl cluster-info` | Cluster information |
| `kubectl get nodes` | List nodes |
| `kubectl get pods -A` | All pods (all namespaces) |
| `kubectl get svc -A` | All services |

### Pod Operations

```bash
# List pods
kubectl get pods

# Describe pod
kubectl describe pod <name>

# Pod logs
kubectl logs <pod>
kubectl logs -f <pod>

# Execute in pod
kubectl exec -it <pod> -- bash

# Delete pod
kubectl delete pod <name>
```

### Deployments

```bash
# List deployments
kubectl get deployments

# Scale deployment
kubectl scale deployment <name> --replicas=3

# Rollout status
kubectl rollout status deployment/<name>

# Rollback
kubectl rollout undo deployment/<name>
```

### Apply/Delete Resources

```bash
# Apply manifest
kubectl apply -f manifest.yml

# Delete resource
kubectl delete -f manifest.yml

# Delete by name
kubectl delete deployment <name>
```

---

## SSH Commands

### Basic Connection

```bash
# Connect to host
ssh hermes-admin@192.168.20.30

# With specific key
ssh -i ~/.ssh/id_ed25519 hermes-admin@192.168.20.30

# Execute command
ssh hermes-admin@192.168.20.30 "uptime"
```

### Key Management

```bash
# Generate key
ssh-keygen -t ed25519 -C "comment"

# Copy key to host
ssh-copy-id user@host

# List keys in agent
ssh-add -l

# Add key to agent
ssh-add ~/.ssh/id_ed25519
```

### SSH Config

**~/.ssh/config**:
```
Host ansible
    HostName 192.168.20.30
    User hermes-admin
    IdentityFile ~/.ssh/id_ed25519

Host proxmox
    HostName 192.168.20.21
    User root
    IdentityFile ~/.ssh/id_ed25519
```

Usage: `ssh ansible`

---

## Network Commands

### Connectivity

```bash
# Ping host
ping -c 4 192.168.20.30

# Trace route
traceroute 192.168.20.30

# Test port
nc -zv 192.168.20.30 22

# DNS lookup
nslookup photos.hrmsmrflrii.xyz 192.168.91.30
dig @192.168.91.30 photos.hrmsmrflrii.xyz
```

### Network Info

```bash
# Show interfaces
ip addr

# Show routes
ip route

# Show listening ports
ss -tlnp

# Show connections
ss -tunap
```

### curl

```bash
# GET request
curl https://photos.hrmsmrflrii.xyz

# With headers
curl -I https://photos.hrmsmrflrii.xyz

# POST JSON
curl -X POST -H "Content-Type: application/json" \
     -d '{"key":"value"}' https://api.example.com

# With auth
curl -u user:pass https://api.example.com
```

---

## File Operations

### Navigation

```bash
# List files
ls -la

# Change directory
cd /path/to/dir

# Print working directory
pwd

# Find files
find /path -name "*.yml"
```

### File Manipulation

```bash
# View file
cat file.txt

# View with line numbers
cat -n file.txt

# Edit file
nano file.txt
vim file.txt

# Copy
cp source dest

# Move
mv source dest

# Delete
rm file.txt
rm -rf directory/
```

### Permissions

```bash
# Change permissions
chmod 755 file
chmod +x script.sh

# Change owner
chown user:group file

# Recursive
chown -R user:group directory/
```

---

## Quick Reference

### Common Paths

| Path | Description |
|------|-------------|
| `/opt/traefik/` | Traefik configuration |
| `/opt/arr-stack/` | Arr stack (docker-vm-media01) |
| `~/ansible/` | Ansible playbooks (controller) |
| `/etc/pve/` | Proxmox configuration |
| `/var/lib/vz/` | Proxmox local storage |
| `/mnt/pve/VMDisks/` | NFS VM storage |

### Service Ports

| Service | Port |
|---------|------|
| SSH | 22 |
| HTTP | 80 |
| HTTPS | 443 |
| Proxmox | 8006 |
| Jellyfin | 8096 |
| Traefik Dashboard | 8080 |
| Authentik | 9000 |

### Default Credentials

See `CREDENTIALS.md` in the repository root.

---

*Keep this cheatsheet handy. Print it if needed.*
