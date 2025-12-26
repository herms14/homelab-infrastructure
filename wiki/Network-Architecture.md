# Network Architecture

> **TL;DR**: Two VLANs separate infrastructure (VLAN 20) from services (VLAN 40), with OPNsense providing DNS and firewall services.

## Network Overview

```
                                    Internet
                                        │
                                        ▼
                              ┌─────────────────┐
                              │   ISP Router    │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │    OPNsense     │
                              │   Firewall      │
                              │ 192.168.91.30   │
                              │                 │
                              │ • DNS Server    │
                              │ • DHCP          │
                              │ • Firewall      │
                              │ • Routing       │
                              └────────┬────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
    ┌─────────▼─────────┐    ┌────────▼────────┐    ┌─────────▼─────────┐
    │     VLAN 20       │    │  Management     │    │     VLAN 40       │
    │  Infrastructure   │    │  (Untagged)     │    │    Services       │
    │ 192.168.20.0/24   │    │                 │    │ 192.168.40.0/24   │
    │                   │    │                 │    │                   │
    │ • Proxmox nodes   │    │ • OPNsense      │    │ • Docker hosts    │
    │ • Kubernetes      │    │                 │    │ • Application VMs │
    │ • Ansible         │    │                 │    │ • Traefik         │
    │ • NAS             │    │                 │    │                   │
    └───────────────────┘    └─────────────────┘    └───────────────────┘
```

---

## What are VLANs?

### Simple Explanation

A **VLAN** (Virtual Local Area Network) is like having separate networks on the same physical cables. Instead of buying separate switches for different purposes, you use VLAN tags to keep traffic separate.

**Analogy**: Think of VLANs like colored lanes on a highway. All cars use the same road, but they can only switch between lanes at designated points (routers/firewalls).

### Why Use VLANs?

| Benefit | How It Helps |
|---------|--------------|
| **Security** | Services can't directly attack infrastructure |
| **Organization** | Easy to know what's where by IP address |
| **Traffic Control** | Firewall rules between VLANs |
| **Broadcast Isolation** | Reduces network noise |

---

## VLAN Configuration

### VLAN 20 - Infrastructure

**Purpose**: Core infrastructure that runs everything else

| Setting | Value |
|---------|-------|
| **Network** | 192.168.20.0/24 |
| **Gateway** | 192.168.20.1 |
| **DNS** | 192.168.91.30 (OPNsense) |
| **VLAN Tag** | 20 (or untagged on access ports) |
| **Usable IPs** | 192.168.20.2 - 192.168.20.254 |

**What's on VLAN 20**:
- Proxmox cluster nodes (192.168.20.20-22)
- Synology NAS (192.168.20.31)
- Ansible controller (192.168.20.30)
- Kubernetes cluster (192.168.20.32-45)

### VLAN 40 - Services

**Purpose**: Application services that users access

| Setting | Value |
|---------|-------|
| **Network** | 192.168.40.0/24 |
| **Gateway** | 192.168.40.1 |
| **DNS** | 192.168.91.30 (OPNsense) |
| **VLAN Tag** | 40 |
| **Usable IPs** | 192.168.40.2 - 192.168.40.254 |

**What's on VLAN 40**:
- Traefik reverse proxy (192.168.40.20)
- Docker hosts (192.168.40.10-11)
- Authentik SSO (192.168.40.21)
- Immich photos (192.168.40.22)
- GitLab (192.168.40.23)

---

## Physical Network Setup

### Switch Configuration

Your managed switch must support VLANs. Key settings:

```
Port 1 (OPNsense):     Trunk - VLANs 20, 40 (tagged)
Port 2 (Proxmox node01): Trunk - VLANs 20, 40 (tagged)
Port 3 (Proxmox node02): Trunk - VLANs 20, 40 (tagged)
Port 4 (Proxmox node03): Trunk - VLANs 20, 40 (tagged)
Port 5 (Synology NAS):  Access - VLAN 20 (untagged)
```

**Terminology**:
- **Trunk port**: Carries multiple VLANs (tagged traffic)
- **Access port**: Carries one VLAN (untagged traffic)
- **Tagged**: Packets have VLAN ID in header
- **Untagged**: Packets have no VLAN ID (native VLAN)

[Screenshot: Switch VLAN configuration page]

### Proxmox Bridge Configuration

Each Proxmox node needs a VLAN-aware bridge.

**File**: `/etc/network/interfaces` on each node

```bash
# Loopback interface
auto lo
iface lo inet loopback

# Physical interface (connected to switch trunk port)
auto nic0
iface nic0 inet manual

# VLAN-aware bridge
auto vmbr0
iface vmbr0 inet static
    address 192.168.20.XX/24    # Replace XX with node number (20, 21, 22)
    gateway 192.168.20.1
    bridge-ports nic0
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes       # CRITICAL: Enables VLAN filtering
    bridge-vids 2-4094          # CRITICAL: Allowed VLAN range

source /etc/network/interfaces.d/*
```

**What each line does**:
| Line | Purpose |
|------|---------|
| `auto nic0` | Bring up physical interface at boot |
| `iface nic0 inet manual` | Don't assign IP to physical interface |
| `auto vmbr0` | Bring up bridge at boot |
| `address 192.168.20.XX/24` | Node's IP address |
| `gateway 192.168.20.1` | Default route to OPNsense |
| `bridge-ports nic0` | Physical NIC attached to bridge |
| `bridge-vlan-aware yes` | Enable VLAN tagging on bridge |
| `bridge-vids 2-4094` | Allow VLAN IDs 2 through 4094 |

### Apply Network Changes

```bash
# Method 1: Reload without reboot
ifreload -a

# Method 2: Reboot (safer for major changes)
reboot
```

### Verify VLAN Configuration

```bash
# Check VLAN filtering is enabled
ip -d link show vmbr0 | grep vlan_filtering
```

**Expected output**:
```
vlan_filtering 1
```

If you see `vlan_filtering 0`, VLANs are NOT working.

---

## VM Network Configuration

### Assigning VMs to VLANs

When creating or editing a VM:

**For VLAN 20 (Infrastructure)**:
```
Bridge: vmbr0
VLAN Tag: (leave empty or enter 20)
```

**For VLAN 40 (Services)**:
```
Bridge: vmbr0
VLAN Tag: 40
```

[Screenshot: VM network settings in Proxmox]

### Terraform Configuration

In `main.tf`, VLAN is set per VM group:

```hcl
# VLAN 20 - No tag needed (native VLAN)
k8s-controllers = {
  vlan_tag = null
  gateway  = "192.168.20.1"
  # ...
}

# VLAN 40 - Explicit tag required
docker-hosts = {
  vlan_tag = 40
  gateway  = "192.168.40.1"
  # ...
}
```

---

## OPNsense Firewall

### Role in Network

OPNsense acts as:
1. **Router**: Routes traffic between VLANs
2. **Firewall**: Controls what traffic is allowed
3. **DNS Server**: Resolves internal hostnames
4. **DHCP Server**: Assigns IPs (if needed)

### Accessing OPNsense

| Method | Address |
|--------|---------|
| Web UI | https://192.168.91.30 |
| SSH | `ssh root@192.168.91.30` |

### VLAN Interfaces in OPNsense

OPNsense has separate interfaces for each VLAN:

| Interface | Network | Role |
|-----------|---------|------|
| LAN | 192.168.91.0/24 | Management |
| VLAN20 | 192.168.20.0/24 | Infrastructure gateway |
| VLAN40 | 192.168.40.0/24 | Services gateway |

[Screenshot: OPNsense interfaces page]

### Default Firewall Rules

| Rule | From | To | Action |
|------|------|-----|--------|
| Allow VLAN20 → Internet | 192.168.20.0/24 | Any | Allow |
| Allow VLAN40 → Internet | 192.168.40.0/24 | Any | Allow |
| Allow VLAN20 → VLAN40 | 192.168.20.0/24 | 192.168.40.0/24 | Allow |
| Allow VLAN40 → VLAN20 | 192.168.40.0/24 | 192.168.20.0/24 | Allow |
| Block all other | Any | Any | Block |

**Note**: Inter-VLAN traffic must pass through OPNsense, allowing firewall inspection.

---

## DNS Configuration

### Internal DNS with OPNsense

OPNsense runs **Unbound** DNS server, providing:
- Local hostname resolution (`*.hrmsmrflrii.xyz`)
- External DNS forwarding (Cloudflare 1.1.1.1)

### How DNS Resolution Works

```
1. VM requests: "photos.hrmsmrflrii.xyz"
          │
          ▼
2. Query sent to: 192.168.91.30 (OPNsense)
          │
          ▼
3. Unbound checks local overrides
          │
          ├─► Found locally: Return 192.168.40.20 (Traefik)
          │
          └─► Not found: Forward to Cloudflare (1.1.1.1)
```

### Viewing DNS Records

```bash
# Test DNS resolution
nslookup photos.hrmsmrflrii.xyz 192.168.91.30

# Expected output:
Server:         192.168.91.30
Address:        192.168.91.30#53

Name:   photos.hrmsmrflrii.xyz
Address: 192.168.40.20
```

See [DNS Configuration](DNS-Configuration) for managing DNS records.

---

## Traffic Flow Examples

### Example 1: User Accessing Jellyfin

```
User's Device (192.168.40.50)
         │
         │ 1. DNS Query: "jellyfin.hrmsmrflrii.xyz"
         ▼
    OPNsense (192.168.91.30)
         │
         │ 2. Response: 192.168.40.20 (Traefik)
         ▼
User's Device
         │
         │ 3. HTTPS Request to 192.168.40.20:443
         ▼
    Traefik (192.168.40.20)
         │
         │ 4. Proxy to 192.168.40.11:8096
         ▼
    docker-vm-media01 (192.168.40.11)
         │
         │ 5. Jellyfin responds
         ▼
    (Response flows back)
```

### Example 2: Kubernetes Pod Accessing Internet

```
K8s Pod (10.244.x.x)
         │
         │ 1. Request to external API
         ▼
K8s Worker Node (192.168.20.4x)
         │
         │ 2. NAT to node IP
         ▼
    OPNsense (192.168.20.1)
         │
         │ 3. NAT to public IP, route to internet
         ▼
    Internet
```

### Example 3: Cross-VLAN Communication

```
Ansible Controller (192.168.20.30, VLAN 20)
         │
         │ 1. SSH to docker-vm-media01
         ▼
    OPNsense (routes between VLANs)
         │
         │ 2. Traffic allowed by firewall rule
         ▼
docker-vm-media01 (192.168.40.11, VLAN 40)
```

---

## Network Debugging

### Test Connectivity

```bash
# Ping gateway
ping 192.168.20.1

# Ping another VLAN
ping 192.168.40.20

# Ping external
ping 1.1.1.1

# Ping by hostname
ping jellyfin.hrmsmrflrii.xyz
```

### Check Routing

```bash
# View routing table
ip route

# Expected output:
default via 192.168.20.1 dev eth0
192.168.20.0/24 dev eth0 proto kernel scope link src 192.168.20.30
```

### Check DNS Resolution

```bash
# Query specific DNS server
nslookup google.com 192.168.91.30

# Check DNS server in use
cat /etc/resolv.conf
```

### Capture Network Traffic

```bash
# On Proxmox node, capture VLAN 40 traffic
tcpdump -i vmbr0 vlan 40

# Capture traffic to specific host
tcpdump -i eth0 host 192.168.40.20
```

---

## Common Issues

### VMs Can't Get IP / No Network

**Symptoms**:
- VM boots but has no network
- DHCP times out
- Can't ping gateway

**Causes & Fixes**:

1. **VLAN not configured on bridge**
   ```bash
   # Check VLAN filtering
   ip -d link show vmbr0 | grep vlan_filtering
   # Must show: vlan_filtering 1
   ```

2. **Wrong VLAN tag on VM**
   - Check VM network settings
   - VLAN 20 VMs: No tag or tag 20
   - VLAN 40 VMs: Tag 40

3. **Switch not configured for VLANs**
   - Verify switch port is trunk mode
   - Check allowed VLANs on port

### Can't Reach Other VLAN

**Symptoms**:
- Can ping same VLAN
- Can't ping other VLAN
- Can't reach internet

**Causes & Fixes**:

1. **Firewall blocking traffic**
   - Check OPNsense firewall rules
   - Look for block rules

2. **No route to other VLAN**
   ```bash
   # Check default gateway
   ip route | grep default
   # Should show: default via 192.168.XX.1
   ```

3. **OPNsense interface down**
   - Check OPNsense web UI
   - Verify VLAN interface is up

### DNS Not Resolving

**Symptoms**:
- `ping 1.1.1.1` works
- `ping google.com` fails

**Fixes**:
```bash
# Check DNS server
cat /etc/resolv.conf
# Should contain: nameserver 192.168.91.30

# Test DNS directly
nslookup google.com 192.168.91.30
```

---

## IP Address Quick Reference

### VLAN 20 Allocation

| Range | Purpose |
|-------|---------|
| 192.168.20.1 | Gateway (OPNsense) |
| 192.168.20.20-22 | Proxmox nodes |
| 192.168.20.30-31 | Management (Ansible, NAS) |
| 192.168.20.32-39 | K8s control plane |
| 192.168.20.40-99 | K8s workers |
| 192.168.20.100-199 | LXC containers |
| 192.168.20.200-254 | Reserved |

### VLAN 40 Allocation

| Range | Purpose |
|-------|---------|
| 192.168.40.1 | Gateway (OPNsense) |
| 192.168.40.5-9 | Logging/monitoring |
| 192.168.40.10-19 | Docker hosts |
| 192.168.40.20-39 | Application services |
| 192.168.40.40-99 | Future services |
| 192.168.40.100-199 | DHCP (if used) |

See [IP Address Map](IP-Address-Map) for complete allocation.

---

## What's Next?

- **[DNS Configuration](DNS-Configuration)** - Managing OPNsense DNS
- **[Storage Architecture](Storage-Architecture)** - NFS and storage setup
- **[SSL Certificates](SSL-Certificates)** - HTTPS for all services

---

*Good network architecture is invisible when it works.*
