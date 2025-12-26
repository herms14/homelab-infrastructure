# Prerequisites

> **TL;DR**: You need Proxmox installed on at least one server, Terraform and Ansible on your workstation, and some basic networking knowledge.

## What You Need

Before starting, make sure you have the following ready.

---

## Hardware Requirements

### Minimum Setup (Learning/Testing)

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Servers** | 1 | 3 (for clustering) |
| **CPU** | 4 cores | 8+ cores per node |
| **RAM** | 16 GB | 32+ GB per node |
| **Storage** | 256 GB SSD | 500+ GB SSD + NAS |
| **Network** | 1 Gbps | 2.5+ Gbps |

### This Project's Hardware

| Node | CPU | RAM | Storage | Role |
|------|-----|-----|---------|------|
| node01 | 8 cores | 32 GB | 500 GB NVMe | Primary VM host |
| node02 | 8 cores | 32 GB | 500 GB NVMe | Secondary host |
| node03 | 8 cores | 32 GB | 500 GB NVMe | Kubernetes |
| NAS | N/A | N/A | 8 TB | Synology storage |

---

## Software Requirements

### On Your Proxmox Servers

| Software | Version | How to Get It |
|----------|---------|---------------|
| Proxmox VE | 8.0+ (we use 9.1.2) | [Download ISO](https://www.proxmox.com/en/downloads) |

**Installation**: Boot from the ISO and follow the installer. It takes about 10 minutes.

[Screenshot: Proxmox installation complete screen]

### On Your Workstation (Where You Run Commands)

| Software | Version | Installation |
|----------|---------|--------------|
| **Terraform** | 1.5+ | See below |
| **Ansible** | 2.15+ | See below |
| **Git** | Any | `apt install git` or download from git-scm.com |
| **SSH Client** | Any | Built into Linux/Mac, use PuTTY on Windows |

#### Installing Terraform

**What is Terraform?** A tool that creates infrastructure (VMs, networks, etc.) from code files.

```bash
# On Ubuntu/Debian
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

**What each command does**:
- Line 1: Downloads HashiCorp's signing key (proves the software is genuine)
- Line 2: Adds HashiCorp's package repository to your system
- Line 3: Updates package list and installs Terraform

**Verify installation**:
```bash
terraform version
# Should show: Terraform v1.x.x
```

#### Installing Ansible

**What is Ansible?** A tool that configures servers (installs software, edits files, etc.) automatically.

```bash
# On Ubuntu/Debian
sudo apt update
sudo apt install ansible

# Or with pip (any OS)
pip install ansible
```

**Verify installation**:
```bash
ansible --version
# Should show: ansible [core 2.x.x]
```

---

## Network Requirements

### Basic Setup

| Requirement | Details |
|-------------|---------|
| **Static IPs** | Your Proxmox nodes need static IP addresses |
| **DHCP Range** | Know which IPs are available for VMs |
| **DNS Server** | Either your router or a dedicated server (OPNsense) |
| **Internet Access** | For downloading packages and updates |

### This Project's Network

| VLAN | Network | Purpose |
|------|---------|---------|
| VLAN 20 | 192.168.20.0/24 | Infrastructure (Proxmox, K8s) |
| VLAN 40 | 192.168.40.0/24 | Application services |

**Don't have VLANs?** You can use a single network - just adjust the IP addresses.

---

## Accounts & Credentials

### Proxmox API Access

You'll need a Proxmox API token for Terraform to create VMs.

#### Creating an API Token

1. Log into Proxmox web UI (https://your-proxmox-ip:8006)

2. Navigate to: **Datacenter → Permissions → API Tokens**

3. Click **Add**:
   - **User**: Select your user (e.g., `root@pam`)
   - **Token ID**: Give it a name (e.g., `terraform`)
   - **Privilege Separation**: Uncheck this

4. Click **Add** and **copy the token secret** (shown only once!)

[Screenshot: Proxmox API token creation dialog]

**Save these values** (you'll need them later):
```
Token ID: root@pam!terraform
Secret: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### SSH Keys

SSH keys let you log into servers without typing passwords.

#### Generating an SSH Key

```bash
# Generate a new key pair
ssh-keygen -t ed25519 -C "your-email@example.com"
```

**What this does**:
- `-t ed25519`: Uses the Ed25519 algorithm (modern, secure)
- `-C "..."`: Adds a comment to identify the key

**When prompted**:
- **File location**: Press Enter for default (`~/.ssh/id_ed25519`)
- **Passphrase**: Optional but recommended for security

**Your keys**:
- `~/.ssh/id_ed25519` - Private key (never share this!)
- `~/.ssh/id_ed25519.pub` - Public key (this goes on servers)

**View your public key**:
```bash
cat ~/.ssh/id_ed25519.pub
# Output: ssh-ed25519 AAAA... your-email@example.com
```

---

## Optional: NAS Storage

For production use, network storage is highly recommended.

### Supported Options

| Type | Examples | Notes |
|------|----------|-------|
| **Synology NAS** | DS920+, DS1621+ | Used in this project |
| **TrueNAS** | TrueNAS Core/Scale | Free, powerful |
| **DIY NAS** | Any Linux + NFS | More work, more control |

### NAS Configuration

Your NAS should have:
- **NFS shares** enabled
- **Static IP** address
- **Proper permissions** for Proxmox to access shares

---

## Knowledge Prerequisites

### What You Should Know

| Topic | Level Needed | Quick Refresher |
|-------|-------------|-----------------|
| **Linux Command Line** | Basic | Navigate directories, edit files |
| **SSH** | Basic | Connect to remote servers |
| **Networking** | Basic | IP addresses, subnets, ports |
| **YAML/JSON** | Helpful | Data format used in configs |

### Quick Linux Refresher

```bash
# Navigate directories
cd /path/to/directory    # Change directory
ls -la                   # List files with details
pwd                      # Print current directory

# View and edit files
cat file.txt            # View file contents
nano file.txt           # Edit file (Ctrl+X to save/exit)
vim file.txt            # Edit file (press i to edit, :wq to save)

# Run commands as root
sudo command            # Run single command as root
sudo -i                 # Become root user

# SSH to a server
ssh user@192.168.1.100  # Connect to server
```

---

## Checklist

Before proceeding, confirm you have:

- [ ] At least one server with Proxmox VE installed
- [ ] Terraform installed on your workstation
- [ ] Ansible installed on your workstation
- [ ] Proxmox API token created and saved
- [ ] SSH key generated
- [ ] Network information documented (IP ranges, gateway, DNS)
- [ ] (Optional) NAS with NFS configured

---

## Next Steps

**Ready?** Continue to [Architecture Overview](Architecture-Overview) to see how everything fits together.

**Need to install Proxmox first?** See the [Proxmox Cluster](Proxmox-Cluster) guide.

---

*All commands are explained. If something is unclear, check the [Glossary](Glossary).*
