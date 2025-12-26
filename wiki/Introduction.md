# Introduction

> **TL;DR**: This is a complete homelab infrastructure running on Proxmox, managed with Terraform and Ansible, hosting 22+ services with automatic SSL.

## What is This Project?

This project is a fully documented homelab infrastructure that runs on three physical servers using Proxmox VE (a free, open-source virtualization platform). Think of it as your own mini data center at home.

### In Plain English

Imagine you want to run your own:
- Photo backup service (like Google Photos, but you own it)
- Movie/TV show library (like Netflix, but with your own content)
- Password manager, file storage, and other services

Instead of paying monthly fees to companies and trusting them with your data, you run everything yourself. This project shows you exactly how to do that.

## Who is This For?

### Perfect For You If:

- **You're curious about homelabs** and want to see a real, working example
- **You value privacy** and want to self-host services
- **You're learning DevOps** and want hands-on experience with:
  - Virtualization (Proxmox)
  - Infrastructure as Code (Terraform)
  - Configuration Management (Ansible)
  - Containerization (Docker)
  - Container Orchestration (Kubernetes)
  - Reverse Proxies (Traefik)
  - SSL Certificates (Let's Encrypt)
- **You have some spare hardware** and want to put it to good use

### What You Should Know

This documentation assumes you:
- Are comfortable with the command line (terminal)
- Have basic Linux knowledge (navigating directories, editing files)
- Can follow technical instructions

No prior experience with Proxmox, Terraform, or Ansible is required - we explain everything!

## What's Included?

### Hardware (3 Physical Servers)

| Node | Role | What Runs on It |
|------|------|-----------------|
| node01 | Primary VM host | Ansible controller |
| node02 | Secondary host | Application services |
| node03 | Kubernetes host | 9-node K8s cluster |

### Virtual Machines (17 Total)

Think of virtual machines (VMs) as "computers inside your computer." Each VM runs its own operating system and applications, completely isolated from others.

| VM Group | Count | Purpose |
|----------|-------|---------|
| Ansible Controller | 1 | Manages all other VMs |
| Kubernetes Controllers | 3 | Run the Kubernetes control plane |
| Kubernetes Workers | 6 | Run containerized applications |
| Application Services | 7 | Docker hosts, Traefik, databases |

### Services (22+ Applications)

| Category | Services | What They Do |
|----------|----------|--------------|
| **Reverse Proxy** | Traefik | Routes traffic to services, handles SSL |
| **Identity** | Authentik | Single sign-on for all services |
| **Media** | Jellyfin, Radarr, Sonarr, Lidarr, Prowlarr, Bazarr, Overseerr, Jellyseerr, Tdarr, Autobrr | Media library and automation |
| **Photos** | Immich | Photo/video backup (Google Photos alternative) |
| **Documents** | Paperless-ngx | Scan, organize, and search documents |
| **DevOps** | GitLab | Code hosting and CI/CD |
| **Automation** | n8n | Workflow automation (like Zapier) |
| **Dashboard** | Glance | Homelab overview dashboard |

## How is Everything Connected?

```
Internet → Router → OPNsense Firewall → Proxmox Cluster → Services
                         ↓
                  Internal DNS
                  (*.hrmsmrflrii.xyz)
                         ↓
                    Traefik
                  (SSL termination)
                         ↓
              ┌────────────────────┐
              │   Your Services    │
              │                    │
              │  photos.domain     │
              │  gitlab.domain     │
              │  jellyfin.domain   │
              │  ...and more       │
              └────────────────────┘
```

### Key Concepts

1. **All traffic goes through Traefik**: One entry point for everything
2. **SSL everywhere**: Every service has HTTPS (green padlock)
3. **Internal DNS**: Services have nice names like `photos.hrmsmrflrii.xyz`
4. **Infrastructure as Code**: Everything is defined in files, not clicked through UIs

## Why Terraform and Ansible?

### Without These Tools (The Hard Way)

1. Log into Proxmox web UI
2. Click "Create VM"
3. Fill out 20+ form fields
4. Click through wizards
5. Repeat for each VM
6. Manually configure each VM after creation
7. Forget what you did 6 months later

### With Terraform + Ansible (The Smart Way)

```bash
# Create all 17 VMs with one command
terraform apply

# Configure all VMs automatically
ansible-playbook site.yml
```

Benefits:
- **Reproducible**: Run the same command, get the same result
- **Documented**: The code IS the documentation
- **Version controlled**: Track every change in Git
- **Fast recovery**: Disaster? Redeploy everything in minutes

## What Will You Learn?

By exploring this documentation, you'll understand:

1. **Virtualization**: How Proxmox creates and manages VMs
2. **Networking**: VLANs, IP addressing, DNS, routing
3. **Storage**: NFS, storage pools, data organization
4. **Automation**: Terraform for infrastructure, Ansible for configuration
5. **Containers**: Docker, Docker Compose, orchestration
6. **Security**: SSL certificates, firewalls, authentication
7. **Self-hosting**: Running popular services yourself

## Ready to Start?

**Next**: [Prerequisites](Prerequisites) - What you need before diving in

---

## Quick Links

- [Architecture Overview](Architecture-Overview) - See the big picture
- [Quick Start](Quick-Start) - Deploy something now
- [Services Overview](Services-Overview) - What's running

---

*This documentation is written for beginners. Every command is explained.*
