# Forward Auth Setup Guide

> Part of the [Proxmox Infrastructure Documentation](../CLAUDE.md)

This document describes how to add Authentik forward auth protection to new services.

## Overview

Forward auth protects services by requiring authentication through Authentik before accessing the service. Users authenticate once (via Google SSO or username/password) and can access all protected services.

## Architecture

```
User -> Traefik -> Authentik (auth check) -> Service
                      |
                      v
                Google OAuth (optional)
```

## Configuration Files

| Component | File Location | Purpose |
|-----------|--------------|---------|
| Authentik Blueprint | `/opt/authentik/blueprints/custom/forward-auth-services.yaml` | Defines providers & applications |
| Traefik Dynamic Config | `/opt/traefik/config/dynamic/services.yml` | Routes with forwardAuth middleware |

## Adding a New Service

### Step 1: Add to Authentik Blueprint

SSH to Authentik server and edit the blueprint:

```bash
ssh hermes-admin@192.168.40.21
sudo nano /opt/authentik/blueprints/custom/forward-auth-services.yaml
```

Add these entries for your new service (replace `myservice` with your service name):

```yaml
  # MyService
  - model: authentik_providers_proxy.proxyprovider
    id: myservice-provider
    identifiers:
      name: myservice-provider
    attrs:
      name: myservice-provider
      mode: forward_single
      external_host: https://myservice.hrmsmrflrii.xyz
      authorization_flow: !Find [authentik_flows.flow, [slug, default-provider-authorization-implicit-consent]]
      invalidation_flow: !Find [authentik_flows.flow, [slug, default-provider-invalidation-flow]]
      access_token_validity: hours=24

  - model: authentik_core.application
    id: myservice-app
    identifiers:
      slug: myservice
    attrs:
      name: My Service
      slug: myservice
      provider: !Find [authentik_providers_proxy.proxyprovider, [name, myservice-provider]]
      meta_launch_url: https://myservice.hrmsmrflrii.xyz
      policy_engine_mode: any
```

Apply the blueprint:

```bash
cd /opt/authentik
sudo docker compose exec server ak apply_blueprint /blueprints/custom/custom/forward-auth-services.yaml
```

### Step 2: Add to Traefik Configuration

SSH to Traefik server and edit the dynamic config:

```bash
ssh hermes-admin@192.168.40.20
sudo nano /opt/traefik/config/dynamic/services.yml
```

Add router with `authentik-auth` middleware:

```yaml
http:
  routers:
    myservice:
      rule: "Host(`myservice.hrmsmrflrii.xyz`)"
      service: myservice
      entryPoints:
        - websecure
      middlewares:
        - authentik-auth  # This enables forward auth
      tls:
        certResolver: letsencrypt

  services:
    myservice:
      loadBalancer:
        servers:
          - url: "http://192.168.40.XX:PORT"
```

Traefik auto-reloads the config (no restart needed).

### Step 3: Add DNS Record

Add the DNS record in OPNsense or your DNS provider:
- `myservice.hrmsmrflrii.xyz` -> `192.168.40.20` (Traefik IP)

## Services Without Forward Auth

Some services have their own authentication or should not use forward auth:

| Service | Reason |
|---------|--------|
| Authentik | Is the auth provider itself |
| Proxmox nodes | Internal infrastructure, separate auth |
| GitLab | Has native OAuth/OIDC support |
| Immich | Has native OAuth/OIDC support |

For these, omit the `middlewares: - authentik-auth` line in Traefik config.

## Protected Services (Current)

### Infrastructure & Monitoring

| Service | URL | Protected |
|---------|-----|-----------|
| Traefik Dashboard | traefik.hrmsmrflrii.xyz | Yes |
| Uptime Kuma | uptime.hrmsmrflrii.xyz | Yes |
| Prometheus | prometheus.hrmsmrflrii.xyz | Yes |
| Grafana | grafana.hrmsmrflrii.xyz | Yes |

### Observability (Tracing)

| Service | URL | Protected |
|---------|-----|-----------|
| Jaeger | jaeger.hrmsmrflrii.xyz | Yes |
| Demo App | demo.hrmsmrflrii.xyz | Yes |

### Media Services

| Service | URL | Protected |
|---------|-----|-----------|
| Jellyfin | jellyfin.hrmsmrflrii.xyz | Yes |
| Radarr | radarr.hrmsmrflrii.xyz | Yes |
| Sonarr | sonarr.hrmsmrflrii.xyz | Yes |
| Lidarr | lidarr.hrmsmrflrii.xyz | Yes |
| Prowlarr | prowlarr.hrmsmrflrii.xyz | Yes |
| Bazarr | bazarr.hrmsmrflrii.xyz | Yes |
| Overseerr | overseerr.hrmsmrflrii.xyz | Yes |
| Jellyseerr | jellyseerr.hrmsmrflrii.xyz | Yes |
| Tdarr | tdarr.hrmsmrflrii.xyz | Yes |
| Autobrr | autobrr.hrmsmrflrii.xyz | Yes |

### Utility Services

| Service | URL | Protected |
|---------|-----|-----------|
| n8n | n8n.hrmsmrflrii.xyz | Yes |
| Paperless | paperless.hrmsmrflrii.xyz | Yes |
| Glance | glance.hrmsmrflrii.xyz | Yes |
| Speed Test | speedtest.hrmsmrflrii.xyz | Yes |

## Troubleshooting

### 401 Unauthorized from Traefik

Check Authentik is reachable from Traefik:

```bash
ssh hermes-admin@192.168.40.20
curl -I http://192.168.40.21:9000/outpost.goauthentik.io/auth/traefik
```

### Application Not Found in Authentik

Verify the application exists:

```bash
ssh hermes-admin@192.168.40.21
cd /opt/authentik
sudo docker compose exec server ak shell -c "from authentik.core.models import Application; print([a.slug for a in Application.objects.all()])"
```

### Blueprint Not Applying

Check blueprint status:

```bash
sudo docker compose exec server ak shell -c "from authentik.blueprints.models import BlueprintInstance; print([(b.name, b.status) for b in BlueprintInstance.objects.all()])"
```

Re-apply manually:

```bash
sudo docker compose exec server ak apply_blueprint /blueprints/custom/custom/forward-auth-services.yaml
```

## Google OAuth Configuration

Google OAuth is configured as a source in Authentik:
- **Client ID**: Configured in `/opt/authentik/blueprints/custom/google-oauth.yaml`
- **Redirect URI**: `https://auth.hrmsmrflrii.xyz/source/oauth/callback/google/`

Users can sign in with Google on the Authentik login page.

## Related Documentation

- [Services](./SERVICES.md) - Service deployment details
- [Networking](./NETWORKING.md) - DNS and URL configuration
- [Ansible](./ANSIBLE.md) - Automation playbooks
