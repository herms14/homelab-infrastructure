# Service Onboarding Workflow

This document explains the automated service onboarding checker - a system that verifies new services are properly configured across all infrastructure components.

## What This System Does

When you deploy a new service to your homelab, there are several things that need to be set up:

1. **Virtual Machine** - The server where the service runs
2. **Configuration Scripts** - Instructions for setting up the service
3. **Domain Name** - A friendly URL like `jellyfin.hrmsmrflrii.xyz`
4. **Reverse Proxy** - Routes traffic from the internet to your service
5. **SSL Certificate** - Secures connections with HTTPS (the padlock icon)
6. **Single Sign-On** - Optional login protection via Authentik
7. **Documentation** - Written instructions for managing the service

The Service Onboarding Checker automatically verifies each of these components and reports the status in Discord.

## How to Use

### Discord Commands

Access these commands in the `new-service-onboarding-workflow` Discord channel:

| Command | What It Does |
|---------|--------------|
| `/onboard jellyfin` | Check if a specific service (like Jellyfin) is fully configured |
| `/onboard-all` | Check all services and show a complete status table |
| `/onboard-services` | List all discovered services |

### Daily Automatic Report

Every day at **9:00 AM Eastern**, the bot automatically posts a summary of all services to the Discord channel. This helps you catch any configuration issues early.

### CI/CD Integration

When you deploy a new service using the GitLab CI/CD pipeline, the system automatically runs an onboarding check and posts the results to Discord. This happens after the "notify" stage of the deployment.

## Understanding the Status Table

When you run `/onboard-all`, you'll see a table like this:

```
Service         | TF  | Ans | DNS | Traf | SSL | Auth | Docs
----------------|-----|-----|-----|------|-----|------|-----
jellyfin        |  ✓  |  ✓  |  ✓  |   ✓  |  ✓  |   ✓  |   ✓
n8n             |  ✓  |  ✗  |  ✓  |   ✓  |  ✓  |   -  |   ✓
new-service     |  ✗  |  ✗  |  ✓  |   ✓  |  ✓  |   ✗  |   ✗
```

### Column Meanings

| Column | Full Name | What It Checks |
|--------|-----------|----------------|
| **TF** | Terraform | Is there a VM definition in `main.tf`? |
| **Ans** | Ansible | Is there a deployment playbook for this service? |
| **DNS** | DNS | Does the domain name resolve correctly? |
| **Traf** | Traefik | Is there a reverse proxy route configured? |
| **SSL** | SSL/TLS | Is HTTPS enabled with a Let's Encrypt certificate? |
| **Auth** | Authentik | Is single sign-on protection configured? (optional) |
| **Docs** | Documentation | Is the service documented in `docs/SERVICES.md`? |

### Status Values

- **✓** = Configured correctly
- **✗** = Needs attention
- **-** = Not applicable (Authentik only - some services don't need SSO)

### Core Requirements

The three core requirements that **must** be configured for any service:
1. **DNS** - The domain name must resolve
2. **Traefik** - Traffic must be routed to the service
3. **SSL** - HTTPS must be enabled for security

If any of these are missing, the service won't be accessible from the web.

## How It Works (Technical Details)

### Architecture Overview

```
                                    +------------------+
                                    |   Discord Bot    |
                                    | (Update Manager) |
                                    +--------+---------+
                                             |
              +------------------------------+------------------------------+
              |                              |                              |
    +---------v----------+       +-----------v-----------+      +-----------v-----------+
    | Check Terraform    |       | Check Traefik Config  |      | Check Authentik API   |
    | (SSH to ansible)   |       | (SSH to traefik host) |      | (REST API call)       |
    +--------------------+       +-----------------------+      +-----------------------+
              |                              |                              |
    +---------v----------+       +-----------v-----------+      +-----------v-----------+
    | Check Ansible      |       | Check SSL Config      |      | Check Documentation   |
    | (SSH to ansible)   |       | (Parse YAML)          |      | (SSH to ansible)      |
    +--------------------+       +-----------------------+      +-----------------------+
              |                              |
    +---------v----------+                   |
    | Check DNS          |                   |
    | (OPNsense API or   |<------------------+
    |  DNS resolution)   |
    +--------------------+
```

### Check Methods

Each check uses a different method to verify configuration:

#### 1. Terraform Check
- **Method**: SSH to the Ansible controller and search `main.tf` for the service name
- **What it looks for**: A VM group definition containing the service name
- **Location**: `~/tf-proxmox/main.tf` on the Ansible controller

#### 2. Ansible Check
- **Method**: SSH to the Ansible controller and search recursively for service references
- **What it looks for**: A folder like `~/ansible/jellyfin/` or service name in any playbook
- **Location**: `~/ansible/` on the Ansible controller (searches all subdirectories)

#### 3. DNS Check
- **Method**: Query the OPNsense API (if credentials available) or perform DNS lookup
- **What it looks for**: A host override record for `servicename.hrmsmrflrii.xyz`
- **Fallback**: If no API credentials, uses standard DNS resolution

#### 4. Traefik Check
- **Method**: SSH to the Traefik host and parse the services configuration
- **What it looks for**: A router definition in the YAML config
- **Location**: `/opt/traefik/config/dynamic/services.yml` on traefik-vm01

#### 5. SSL Check
- **Method**: Parse the Traefik config for TLS settings
- **What it looks for**: `tls.certResolver: letsencrypt` in the router config
- **Location**: Same as Traefik check

#### 6. Authentik Check
- **Method**: Call the Authentik API to search for applications
- **What it looks for**: An application with a slug matching the service name
- **API Endpoint**: `http://192.168.40.21:9000/api/v3/core/applications/`

#### 7. Documentation Check
- **Method**: SSH to the Ansible controller and search the docs file
- **What it looks for**: The service name mentioned in `docs/SERVICES.md`
- **Location**: `~/tf-proxmox/docs/SERVICES.md`

## Configuration

### Environment Variables

The Update Manager container uses these environment variables:

| Variable | Purpose | Example |
|----------|---------|---------|
| `DISCORD_TOKEN` | Bot authentication token | `MTQ1MjEy...` |
| `DISCORD_CHANNEL_ID` | Channel for update notifications | `1452117559179739208` |
| `ONBOARD_CHANNEL_ID` | Channel for onboarding reports | `1452141884809154581` |
| `OPNSENSE_API_KEY` | OPNsense API authentication (optional) | `your-api-key` |
| `OPNSENSE_API_SECRET` | OPNsense API secret (optional) | `your-api-secret` |
| `AUTHENTIK_TOKEN` | Authentik API token (optional) | `your-token` |
| `SSH_KEY_PATH` | Path to SSH key for remote checks | `/root/.ssh/homelab_ed25519` |

### Adding API Credentials

To enable full functionality, you need to add API credentials to the `.env` file on docker-vm-utilities01:

```bash
ssh hermes-admin@192.168.40.10
sudo nano /opt/update-manager/.env
```

Add these lines with your actual credentials:
```
OPNSENSE_API_KEY=your_opnsense_api_key
OPNSENSE_API_SECRET=your_opnsense_api_secret
AUTHENTIK_TOKEN=your_authentik_api_token
```

Then restart the container:
```bash
cd /opt/update-manager
sudo docker compose restart
```

### Getting API Credentials

#### OPNsense API Key
1. Log into OPNsense web interface
2. Go to **System > Access > Users**
3. Edit your user and click **+ Add API Key**
4. Save the key and secret securely

#### Authentik API Token
1. Log into Authentik Admin Interface
2. Go to **Directory > Tokens and App passwords**
3. Click **Create** and select **API Token**
4. Copy the token value

## Troubleshooting

### Bot Not Responding

1. Check container is running:
   ```bash
   ssh hermes-admin@192.168.40.10 "docker ps | grep update-manager"
   ```

2. Check container logs:
   ```bash
   ssh hermes-admin@192.168.40.10 "docker logs update-manager --tail 50"
   ```

3. Test health endpoint:
   ```bash
   ssh hermes-admin@192.168.40.10 "curl http://localhost:5050/health"
   ```

### Slash Commands Not Showing

Discord slash commands can take up to an hour to sync globally. If commands aren't appearing:

1. Check the logs for "Slash commands synced" message
2. Try typing `/` in the channel and waiting a few seconds
3. Restart the container: `sudo docker compose restart`

### Checks Returning Wrong Status

If a check is returning incorrect results:

1. **Terraform Check**: Verify the service name matches exactly in `main.tf`
2. **Ansible Check**: Ensure the playbook folder/file exists and is named correctly
3. **DNS Check**: Test DNS resolution manually: `nslookup servicename.hrmsmrflrii.xyz`
4. **Traefik Check**: Verify the router name in `services.yml`
5. **Authentik Check**: Confirm the application slug matches the service name

### SSH Connection Issues

The bot uses SSH to check remote servers. If SSH checks are failing:

1. Verify SSH key exists: `ls -la /root/.ssh/homelab_ed25519`
2. Test SSH manually: `ssh -i /root/.ssh/homelab_ed25519 hermes-admin@192.168.40.20`
3. Check SSH key permissions: Should be `600` for the private key

## Files and Locations

| Component | Location |
|-----------|----------|
| Update Manager Bot | `/opt/update-manager/` on docker-vm-utilities01 (192.168.40.10) |
| Docker Compose | `/opt/update-manager/docker-compose.yml` |
| Environment File | `/opt/update-manager/.env` |
| CI/CD Script | `/opt/gitlab-runner/scripts/notify_discord.py` on gitlab-runner-vm01 |
| Traefik Config | `/opt/traefik/config/dynamic/services.yml` on traefik-vm01 |
| Service Documentation | `docs/SERVICES.md` in the tf-proxmox repository |

## Related Documentation

- [CICD.md](./CICD.md) - GitLab CI/CD pipeline for automated deployments
- [WATCHTOWER.md](./WATCHTOWER.md) - Container update management
- [SERVICES.md](./SERVICES.md) - List of deployed services
- [ANSIBLE.md](./ANSIBLE.md) - Ansible automation playbooks
