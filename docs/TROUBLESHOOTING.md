# Troubleshooting Guide

> Part of the [Proxmox Infrastructure Documentation](../CLAUDE.md)

This guide documents resolved issues and common problems organized by category for quick reference.

---

## Table of Contents

- [Proxmox Cluster Issues](#proxmox-cluster-issues)
- [Kubernetes Issues](#kubernetes-issues)
- [Authentication Issues](#authentication-issues)
- [Container & Docker Issues](#container--docker-issues)
- [Service-Specific Issues](#service-specific-issues)
- [Network Issues](#network-issues)
- [Common Issues](#common-issues)
- [Diagnostic Commands](#diagnostic-commands)

---

## Proxmox Cluster Issues

### Corosync SIGSEGV Crash

**Resolved**: December 2025

**Symptoms**:
- `corosync.service` fails to start with `status=11/SEGV`
- Logs stop at: `Initializing transport (Kronosnet)`
- Node cannot join cluster
- Reinstalling corosync alone doesn't fix it

**Root Cause**: Broken or mismatched NSS crypto stack (`libnss3`) caused Corosync to segfault during encrypted cluster transport initialization.

**Why It Happened**:
- Corosync uses kronosnet (knet) for cluster networking
- knet loads a crypto plugin (`crypto_nss`)
- The plugin relies on NSS crypto libraries (`libnss3`)
- Corrupted or mismatched library versions caused the crash

**Diagnosis**:
```bash
# 1. Validate configuration (should pass)
corosync -t

# 2. Install debug tools
apt install systemd-coredump gdb strace

# 3. After crash, analyze core dump
coredumpctl info corosync
```

**Stack trace showed failure in**: `PK11_CipherOp` -> `libnss3.so` -> `crypto_nss.so` -> `libknet.so`

**Resolution**:
```bash
apt install --reinstall -y \
  libnss3 libnss3-tools \
  libknet1t64 libnozzle1t64 \
  corosync libcorosync-common4
```

**Verification**:
```bash
systemctl start corosync
systemctl status corosync
pvecm status
journalctl -u corosync | grep crypto_nss
```

**Prevention**: Keep all nodes package-consistent with `apt update && apt full-upgrade -y`. Avoid partial upgrades.

---

### Node Showing Question Mark / Unhealthy Status

**Resolved**: December 2025

**Symptoms**:
- Question mark icon in Proxmox web UI
- "NR" (Not Ready) status in cluster membership

**Diagnosis**:
```bash
ping 192.168.20.22
ssh root@192.168.20.22 "pvecm status"
ssh root@192.168.20.22 "pvesh get /cluster/resources --type node"
```

**Resolution**:
1. If shutdown in progress: `shutdown -c` (may fail if too late)
2. If shutdown completed: Power on via physical access, IPMI, or WoL
3. If "NR" persists:
   ```bash
   ssh root@192.168.20.22 "systemctl restart pve-cluster && systemctl restart corosync"
   ```

**Verification**:
```bash
ssh root@192.168.20.22 "pvesh get /cluster/resources --type node"
ssh root@192.168.20.22 "pvecm status"
```

---

### Cloud-init VM Boot Failure - UEFI/BIOS Mismatch

**Resolved**: December 2025

**Symptoms**:
- VM creates successfully via Terraform
- Console stops at: `Btrfs loaded, zoned=yes, fsverity=yes`
- Boot hangs before cloud-init
- VM unreachable via SSH/ping

**Root Cause**: UEFI/BIOS boot mode mismatch between template and Terraform config.

**Resolution**: Update `modules/linux-vm/main.tf`:
```hcl
bios    = "ovmf"
machine = "q35"

efidisk {
  storage           = var.storage
  efitype           = "4m"
  pre_enrolled_keys = true
}

scsihw = "virtio-scsi-single"
```

**Lesson**: Always verify template boot mode with `qm config <vmid>` before deploying.

---

## Kubernetes Issues

### kubectl Connection Refused on Secondary Controllers

**Resolved**: December 20, 2025

**Symptoms**: On non-primary Kubernetes controllers (controller02, controller03):
```
E1220 15:24:01.489681    5376 memcache.go:265] couldn't get current server API group list
The connection to the server localhost:8080 was refused - did you specify the right host or port?
```

**Root Cause**: The kubeconfig file (`~/.kube/config`) was not set up on non-primary controller nodes. `kubeadm init` only sets up kubeconfig on the primary controller.

**Fix**:
```bash
# Copy from primary to secondary controllers
ssh hermes-admin@192.168.20.32 "cat ~/.kube/config" | ssh hermes-admin@192.168.20.33 "mkdir -p ~/.kube && cat > ~/.kube/config && chmod 600 ~/.kube/config"
ssh hermes-admin@192.168.20.32 "cat ~/.kube/config" | ssh hermes-admin@192.168.20.34 "mkdir -p ~/.kube && cat > ~/.kube/config && chmod 600 ~/.kube/config"
```

**Verification**:
```bash
for ip in 192.168.20.32 192.168.20.33 192.168.20.34; do
  echo "=== $ip ==="
  ssh hermes-admin@$ip "kubectl get nodes --no-headers | head -3"
done
```

**Prevention**: Add kubeconfig distribution to Kubernetes Ansible playbook post-deployment tasks.

---

### Kubelet Health Endpoint Not Accessible Externally (Glance Monitoring)

**Resolved**: December 22, 2025

**Symptoms**:
- Glance dashboard shows K8s workers as "ERROR" (red)
- K8s controllers show OK (green)
- Workers are actually healthy, just not reachable from Glance monitoring

**Root Cause**: By default, kubelet binds its health endpoint (`/healthz`) to `127.0.0.1:10248`, making it inaccessible from external monitoring tools like Glance running on a different host.

**Diagnosis**:
```bash
# Check kubelet bind address
ssh hermes-admin@192.168.20.40 "cat /var/lib/kubelet/config.yaml | grep healthzBindAddress"
# Output: healthzBindAddress: 127.0.0.1

# Verify kubelet only listens on localhost
ssh hermes-admin@192.168.20.40 "ss -tlnp | grep 10248"
# Output: LISTEN 127.0.0.1:10248 (only localhost)

# Test external access fails
curl -s --connect-timeout 3 http://192.168.20.40:10248/healthz
# Timeout or connection refused
```

**Fix**:
```bash
# Update all worker nodes to bind healthz to 0.0.0.0
for ip in 192.168.20.40 192.168.20.41 192.168.20.42 192.168.20.43 192.168.20.44 192.168.20.45; do
  echo "=== $ip ==="
  ssh hermes-admin@$ip "sudo sed -i 's/healthzBindAddress: 127.0.0.1/healthzBindAddress: 0.0.0.0/' /var/lib/kubelet/config.yaml && sudo systemctl restart kubelet"
done
```

**Verification**:
```bash
# Verify kubelet now listens on all interfaces
ssh hermes-admin@192.168.20.40 "ss -tlnp | grep 10248"
# Output: LISTEN *:10248 (all interfaces)

# Test external access works
for ip in 192.168.20.40 192.168.20.41 192.168.20.42 192.168.20.43 192.168.20.44 192.168.20.45; do
  echo -n "$ip: "
  curl -s --connect-timeout 3 http://$ip:10248/healthz
done
# All should return: ok
```

**Prevention**: Add kubelet healthz bind address configuration to Kubernetes Ansible deployment playbook.

---

## Authentication Issues

### Authentik ForwardAuth "Not Found" Error

**Resolved**: December 21, 2025

**Symptoms**: When accessing services protected by Authentik ForwardAuth (Grafana, Prometheus, Jaeger), users receive a "not found" error instead of being redirected to login.

**Root Cause**: The Authentik **Embedded Outpost had no providers assigned**. Proxy providers and applications were created, but never bound to the outpost that handles ForwardAuth requests from Traefik.

**Diagnosis**:
```bash
ssh hermes-admin@192.168.40.21 "sudo docker exec authentik-server ak shell -c \"
from authentik.outposts.models import Outpost
outpost = Outpost.objects.get(name='authentik Embedded Outpost')
print(f'Providers: {list(outpost.providers.values_list(\"name\", flat=True))}')
\""
# Empty list = problem
```

**Fix**:
```bash
ssh hermes-admin@192.168.40.21 "sudo docker exec authentik-server ak shell -c \"
from authentik.providers.proxy.models import ProxyProvider
from authentik.outposts.models import Outpost

providers = list(ProxyProvider.objects.all())
outpost = Outpost.objects.get(name='authentik Embedded Outpost')
for p in providers:
    outpost.providers.add(p)
outpost.save()
print(f'Added {len(providers)} providers to outpost')
\""
```

**Verification**:
```bash
# Should return 302 (redirect to login)
curl -s -k -o /dev/null -w "%{http_code}" https://grafana.hrmsmrflrii.xyz
```

**Prevention**:
1. Always assign new proxy providers to the Embedded Outpost in Authentik Admin UI
2. Include outpost assignment in blueprints
3. Verify outpost has providers assigned before testing

---

## Container & Docker Issues

### Watchtower TLS Handshake Error

**Resolved**: December 2025

**Symptoms**: Watchtower logs show:
```
tls: first record does not look like a TLS handshake
```

**Root Cause**: Using `generic://` instead of `generic+http://` in webhook URL causes HTTPS connection to HTTP endpoint.

**Fix**: Update `WATCHTOWER_NOTIFICATION_URL` in docker-compose.yml:
```yaml
# Wrong
WATCHTOWER_NOTIFICATION_URL: "generic://192.168.40.10:5050/webhook"

# Correct
WATCHTOWER_NOTIFICATION_URL: "generic+http://192.168.40.10:5050/webhook"
```

Then restart: `cd /opt/watchtower && sudo docker compose restart`

---

### Update Manager SSH Key Not Accessible

**Resolved**: December 2025

**Symptoms**: Discord bot returns `❌ Update failed: Could not find compose directory`

**Root Cause**: SSH key not present on utilities host or not mounted in container.

**Fix**:
```bash
# Copy SSH key to host
scp ~/.ssh/homelab_ed25519 hermes-admin@192.168.40.10:/home/hermes-admin/.ssh/
ssh hermes-admin@192.168.40.10 "chmod 600 /home/hermes-admin/.ssh/homelab_ed25519"

# Restart container
ssh hermes-admin@192.168.40.10 "cd /opt/update-manager && sudo docker compose restart"
```

**Verification**:
```bash
ssh hermes-admin@192.168.40.10 "docker exec update-manager ssh -i /root/.ssh/homelab_ed25519 -o StrictHostKeyChecking=no hermes-admin@192.168.40.11 hostname"
```

---

### Docker Build Cache Issues

**Resolved**: December 2025

**Symptoms**: Code changes not reflected after container rebuild.

**Root Cause**: Docker caches build layers.

**Fix**: Force rebuild with no cache:
```bash
sudo docker compose down && sudo docker compose build --no-cache && sudo docker compose up -d
```

---

## Service-Specific Issues

### Immich Container Restart Loop - Missing Directory Structure

**Resolved**: December 21, 2025

**Symptoms**:
- Immich container status shows "Restarting"
- Logs show: `Failed to read: "<UPLOAD_LOCATION>/encoded-video/.immich"`
- Container never becomes healthy

**Root Cause**: When pointing Immich to a new empty NFS share, the required directory structure with `.immich` marker files doesn't exist. Immich performs system integrity checks on startup.

**Diagnosis**:
```bash
ssh hermes-admin@192.168.40.22 "sudo docker logs immich-server --tail 30 2>&1 | grep -i error"
```

**Fix**:
```bash
ssh hermes-admin@192.168.40.22 "for dir in thumbs upload backups library profile encoded-video; do \
  sudo mkdir -p /mnt/immich-uploads/\$dir && \
  sudo touch /mnt/immich-uploads/\$dir/.immich; \
done"

ssh hermes-admin@192.168.40.22 "cd /opt/immich && sudo docker compose restart immich-server"
```

**Verification**:
```bash
ssh hermes-admin@192.168.40.22 "sudo docker ps --filter name=immich-server --format '{{.Status}}'"
# Should show "Up X seconds (healthy)" after ~30 seconds
```

**Prevention**: The Ansible playbook now includes tasks to create the directory structure automatically.

---

### Immich External Library Not Visible

**Resolved**: December 21, 2025

**Symptoms**:
- Immich UI shows "Click to upload your first photo"
- NFS mounts working on host but photos not visible in Immich

**Root Cause**: Docker volume mappings missing from docker-compose.yml. The container couldn't see the mounted directories.

**Diagnosis**:
```bash
# Check if container can see external library
ssh hermes-admin@192.168.40.22 "sudo docker exec immich-server ls /usr/src/app/external/ 2>&1"
# Returns "No such file or directory" if mapping missing
```

**Fix**: Update `/opt/immich/docker-compose.yml` volumes section:
```yaml
volumes:
  - /mnt/immich-uploads:/usr/src/app/upload
  - /mnt/synology-photos:/usr/src/app/external/synology:ro
```

Then restart:
```bash
ssh hermes-admin@192.168.40.22 "cd /opt/immich && sudo docker compose down && sudo docker compose up -d"
```

**Verification**:
```bash
ssh hermes-admin@192.168.40.22 "sudo docker exec immich-server ls /usr/src/app/external/synology/ | head -3"
```

---

### Immich Bad Gateway - NFS Mounts Not Mounted After Boot

**Resolved**: December 21, 2025

**Symptoms**:
- Browser shows "Bad Gateway" when accessing https://photos.hrmsmrflrii.xyz
- Immich container in restart loop with status "health: starting"
- Logs show: `Failed to read: "<UPLOAD_LOCATION>/encoded-video/.immich"`
- `microservices worker exited with code 1`

**Root Cause**: After VM reboot, NFS mounts (`/mnt/immich-uploads`, `/mnt/synology-photos`) did not mount automatically despite being in `/etc/fstab`. Immich's storage integrity check fails when the upload directory is empty or inaccessible.

**Diagnosis**:
```bash
# Check if NFS mounts are active
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "mount | grep nfs"
# Empty output = mounts missing

# Check upload directory
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "ls -la /mnt/immich-uploads/"
# If empty or shows local disk, mount is missing

# Check container logs for storage errors
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "docker logs immich-server --tail 30 2>&1 | grep -i 'error\|failed'"
```

**Fix**:
```bash
# Step 1: Mount all NFS shares from fstab
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "sudo mount -a"

# Step 2: Verify mounts are active
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "mount | grep -E 'immich|synology'"

# Step 3: Verify upload directory has content
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "ls -la /mnt/immich-uploads/"

# Step 4: Restart Immich server container
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "cd /opt/immich && docker compose restart immich-server"
```

**Verification**:
```bash
# Wait 30 seconds for health check, then verify
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep immich"
# Should show "Up X seconds (healthy)"

# Test API endpoint
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "curl -s -o /dev/null -w '%{http_code}' http://localhost:2283/api/server/ping"
# Should return 200
```

**Prevention** (Implemented on immich-vm01):

Create a systemd service that mounts NFS before Docker starts:

```bash
# Create the service file
cat << 'EOF' | sudo tee /etc/systemd/system/mount-nfs-before-docker.service
[Unit]
Description=Mount NFS shares before Docker
After=network-online.target remote-fs.target
Before=docker.service
Wants=network-online.target
RequiresMountsFor=/mnt

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/bin/sleep 5
ExecStart=/bin/mount -a
ExecStart=/bin/bash -c 'mount | grep -q immich-uploads && echo NFS mounts ready || (echo NFS mount failed && exit 1)'

[Install]
WantedBy=multi-user.target docker.service
EOF

# Enable the service
sudo systemctl daemon-reload
sudo systemctl enable mount-nfs-before-docker.service
```

This ensures NFS mounts are ready before Docker containers start, preventing the "Bad Gateway" issue after reboots or migrations.

**Note**: If SSH to 192.168.40.22 times out from your workstation, use ProxyJump through a Proxmox node:
```bash
ssh -o ProxyJump=root@192.168.20.20 hermes-admin@192.168.40.22 "<command>"
```

---

### GitLab Unsupported Config Value (grafana)

**Resolved**: December 20, 2025

**Symptoms**: GitLab container restart loop with:
```
FATAL: Mixlib::Config::UnknownConfigOptionError: Reading unsupported config value grafana.
```

**Root Cause**: GitLab removed bundled Grafana support. The `grafana['enable'] = false` line is deprecated.

**Fix**: Remove `grafana['enable'] = false` from GITLAB_OMNIBUS_CONFIG in `/opt/gitlab/docker-compose.yml`:
```bash
cd /opt/gitlab && sudo docker compose down && sudo docker compose up -d
```

**Verification**:
```bash
docker ps --filter name=gitlab
docker exec gitlab gitlab-ctl status
```

**Prevention**: Review GitLab release notes for deprecated options before updates.

---

### Glance Dashboard "Migration should take around 5 minutes" Message

**Resolved**: December 22, 2025

**Symptoms**:
- Accessing https://glance.hrmsmrflrii.xyz shows "Migration should take around 5 minutes"
- Dashboard never loads, stuck on migration message
- Container logs show: `!!! WARNING !!! The default location of glance.yml in the Docker image has changed starting from v0.7.0.`

**Root Cause**: Glance v0.7.0 changed the config file location from `/app/glance.yml` (single file mount) to `/app/config/` (directory mount). The old docker-compose.yml was using the deprecated single-file mount format.

**Diagnosis**:
```bash
ssh hermes-admin@192.168.40.10 "docker logs glance 2>&1 | head -10"
# Look for: "The default location of glance.yml in the Docker image has changed"
```

**Fix**:
```bash
# Update docker-compose.yml to use directory mount format
ssh hermes-admin@192.168.40.10 "cat > /opt/glance/docker-compose.yml << 'EOF'
services:
  glance:
    image: glanceapp/glance:latest
    container_name: glance
    restart: unless-stopped
    ports:
      - 8080:8080
    volumes:
      - ./config:/app/config
      - ./assets:/app/assets:ro
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro
    environment:
      - TZ=America/New_York
EOF"

# Restart the container
ssh hermes-admin@192.168.40.10 "cd /opt/glance && sudo docker compose down && sudo docker compose up -d"
```

**Key Changes**:
- Volume mount changed from `./glance.yml:/app/glance.yml` to `./config:/app/config`
- Config file must be at `/opt/glance/config/glance.yml` (not `/opt/glance/glance.yml`)
- Assets directory must also be mounted if `assets-path` is configured

**Verification**:
```bash
# Check logs for successful startup
ssh hermes-admin@192.168.40.10 "docker logs glance 2>&1"
# Should show: "Starting server on :8080"

# Test dashboard access
curl -s -o /dev/null -w "%{http_code}" https://glance.hrmsmrflrii.xyz
# Should return 200
```

**Prevention**:
- Monitor Glance release notes for breaking changes
- Ansible playbook `ansible-playbooks/glance/deploy-glance-dashboard.yml` has been updated to use the v0.7.0+ format
- See: https://github.com/glanceapp/glance/blob/main/docs/v0.7.0-upgrade.md

---

### Glance Service Health Showing ERROR for Traefik

**Resolved**: December 22, 2025

**Symptoms**: Glance dashboard shows Traefik as "ERROR" even though Traefik is running fine.

**Root Cause**: Glance was configured to use `http://192.168.40.20:8080/api/overview` which doesn't exist because Traefik's API is not exposed on port 8080 (insecure mode disabled).

**Fix**:
1. Enable Traefik ping endpoint on a dedicated entrypoint:
```bash
# Update traefik.yml to add ping entrypoint
ssh hermes-admin@192.168.40.20 "sudo cat >> /opt/traefik/config/traefik.yml << 'EOF'
ping:
  entryPoint: traefik
EOF"

# Add traefik entrypoint to entryPoints section:
#   traefik:
#     address: ":8082"

# Update docker-compose.yml to expose port 8082
# ports:
#   - "8082:8082"

# Restart Traefik
ssh hermes-admin@192.168.40.20 "cd /opt/traefik && sudo docker compose restart"
```

2. Update Glance config to use ping endpoint:
```bash
ssh hermes-admin@192.168.40.10 "sudo sed -i 's|url: http://192.168.40.20:8080/api/overview|url: http://192.168.40.20:8082/ping|' /opt/glance/config/glance.yml"
```

**Verification**:
```bash
curl -s http://192.168.40.20:8082/ping
# Should return: OK
```

---

### Glance Service Health Showing ERROR for GitLab

**Resolved**: December 22, 2025

**Symptoms**: Glance dashboard shows GitLab as "ERROR" or "Not Found".

**Root Cause**: Multiple issues:
1. GitLab's health endpoints (`/-/health`, `/-/readiness`) are restricted by `monitoring_whitelist` (default: localhost only)
2. DNS resolution fails on docker-vm-utilities01 for `gitlab.hrmsmrflrii.xyz`

**Fix**:
1. Use direct HTTP URL that returns 200:
```bash
ssh hermes-admin@192.168.40.10 "sudo sed -i 's|url: http://192.168.40.23/-/health|url: http://192.168.40.23/users/sign_in|' /opt/glance/config/glance.yml"
```

Note: Using `/users/sign_in` returns 200 without requiring health endpoint access.

**Alternative (if health endpoint needed)**:
```bash
# Enable monitoring from infrastructure network
ssh hermes-admin@192.168.40.23 "sudo docker exec gitlab sh -c \"echo \\\"gitlab_rails['monitoring_whitelist'] = ['127.0.0.0/8', '::1/128', '192.168.40.0/24', '192.168.20.0/24']\\\" >> /etc/gitlab/gitlab.rb\""
ssh hermes-admin@192.168.40.23 "sudo docker exec gitlab gitlab-ctl reconfigure"
```

**Verification**:
```bash
ssh hermes-admin@192.168.40.10 "curl -s -o /dev/null -w '%{http_code}' http://192.168.40.23/users/sign_in"
# Should return: 200
```

---

## Network Issues

### VLAN-Aware Bridge Missing

**Symptoms**: `QEMU exited with code 1` on VM deployment

**Root Cause**: Node missing VLAN-aware bridge configuration.

**Fix**: Configure `/etc/network/interfaces`:
```bash
auto vmbr0
iface vmbr0 inet static
    address 192.168.20.XX/24
    gateway 192.168.20.1
    bridge-ports nic0
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 2-4094
```

Then: `ifreload -a` or reboot.

**Verify**:
```bash
ip -d link show vmbr0 | grep vlan_filtering
# Should show "vlan_filtering 1"
```

---

### NFS Mount Failures

**Diagnosis**:
```bash
showmount -e 192.168.20.31
df -h | grep nfs
mount -t nfs 192.168.20.31:/volume2/ProxmoxCluster-VMDisks /mnt/test
```

**Common Fixes**:
- Ensure NFS service running on NAS
- Check firewall rules (NFS ports 111, 2049)
- Verify export permissions include Proxmox node IPs
- For stale mounts: `umount -l /mnt/stale && mount -a`

---

## Common Issues

### Connection Refused Errors

**Symptom**: `dial tcp 192.168.20.21:8006: connectex: No connection could be made`

**Cause**: Proxmox API temporarily unavailable

**Solution**: Wait and retry, or check node status:
```bash
ssh root@192.168.20.21 "systemctl status pveproxy"
```

---

### Template Not Found (LXC)

**Symptom**: `template 'local:vztmpl/...' does not exist`

**Solution**:
```bash
ssh root@<node> "pveam update && pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
```

---

### Tainted Terraform Resources

**Symptom**: Resources marked as tainted

**Solution**: Run `terraform apply` to recreate properly

---

### Terraform State Lock

**Symptom**: Terraform state is locked

**Solution**:
1. Ensure no other terraform operations running
2. Force unlock if needed (caution): `terraform force-unlock <lock-id>`

---

## Diagnostic Commands

### Terraform
```bash
terraform state list
terraform state show <resource>
terraform refresh
terraform validate
terraform fmt
```

### Proxmox
```bash
pvecm status
pvesh get /cluster/resources --type node
qm config <vmid>
pct config <ctid>
systemctl status pve-cluster corosync pveproxy
journalctl -xeu corosync
coredumpctl info corosync
```

### Kubernetes
```bash
kubectl get nodes
kubectl get pods -A
kubectl describe node <node>
kubectl logs -n <namespace> <pod>
```

### Ansible
```bash
ansible all -m ping
ansible <host> -m setup
```

### Network
```bash
ip -d link show vmbr0 | grep vlan_filtering
bridge link show
ip route show
```

### Docker/Watchtower
```bash
docker logs <container> --tail 50
docker exec <container> <command>
ssh hermes-admin@192.168.40.10 "docker logs update-manager --tail 50"
ssh hermes-admin@192.168.40.11 "docker logs watchtower --tail 50"
```

### Authentik
```bash
# List providers
ssh hermes-admin@192.168.40.21 "sudo docker exec authentik-server ak shell -c \"
from authentik.providers.proxy.models import ProxyProvider
for p in ProxyProvider.objects.all():
    print(p.name)
\""

# Check outpost providers
ssh hermes-admin@192.168.40.21 "sudo docker exec authentik-server ak shell -c \"
from authentik.outposts.models import Outpost
outpost = Outpost.objects.get(name='authentik Embedded Outpost')
print(f'Providers: {outpost.providers.count()}')
\""
```

---

### Immich

```bash
# Check container health
ssh hermes-admin@192.168.40.22 "sudo docker ps --filter name=immich --format 'table {{.Names}}\t{{.Status}}'"

# View Immich logs
ssh hermes-admin@192.168.40.22 "sudo docker logs immich-server --tail 50"

# Verify NFS mounts
ssh hermes-admin@192.168.40.22 "mount | grep -E 'synology|immich'"

# Check container volume access
ssh hermes-admin@192.168.40.22 "sudo docker exec immich-server ls /usr/src/app/external/synology/ | head -5"
ssh hermes-admin@192.168.40.22 "sudo docker exec immich-server ls /usr/src/app/upload/"

# Test API health
ssh hermes-admin@192.168.40.22 "curl -s http://localhost:2283/api/server/ping"
```

---

## Related Documentation

- [Proxmox](./PROXMOX.md) - Cluster configuration
- [Networking](./NETWORKING.md) - Network configuration
- [Terraform](./TERRAFORM.md) - Deployment configuration
- [Services](./SERVICES.md) - Docker services
- [Application Configurations](./APPLICATION_CONFIGURATIONS.md) - Detailed app setup guides
- [Ansible](./ANSIBLE.md) - Automation playbooks
