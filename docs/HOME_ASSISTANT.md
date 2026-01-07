# Home Assistant

> Part of the [Proxmox Infrastructure Documentation](../CLAUDE.md)

## Overview

Home Assistant provides smart home automation with device control, energy monitoring, and automations.

| Property | Value |
|----------|-------|
| **LXC ID** | 206 |
| **Hostname** | homeassistant-lxc |
| **Node** | node01 |
| **IP** | 192.168.40.25 |
| **URL** | https://ha.hrmsmrflrii.xyz |
| **Port** | 8123 |
| **Version** | Home Assistant Container (stable) |
| **Deployed** | January 7, 2026 |

## Features

### Device Control (vs Glance which is read-only)
- Toggle lights and plugs directly
- Adjust brightness/color of smart bulbs
- Control Samsung TV (power, volume, input)
- PTZ camera control for Tapo cameras

### Energy Monitoring
- **Rate**: 14.32 PHP per kWh
- Per-device power consumption (W)
- Daily/monthly energy usage (kWh)
- Cost tracking in PHP

### Automations
- Motion-activated lights
- Scheduled scenes
- Energy alerts
- Away mode
- TV auto-off

### Scenes
- Movie Mode
- Sleep Mode
- Work Mode
- Away Mode

## Device Inventory

### Tapo Devices (TP-Link)

| Type | Model | Features |
|------|-------|----------|
| Energy Plugs | P110 | Power monitoring, scheduling |
| Basic Plugs | P100/P105 | On/off control |
| Smart Bulbs | L530/L510 | Color, dimming |
| Cameras | C200/C210 | Pan/tilt, motion detection |

### Samsung SmartThings

| Device | Features |
|--------|----------|
| Smart TV | Power, volume, input, media |

## Configuration

### Directory Structure

```
/opt/homeassistant/
├── docker-compose.yml
└── config/
    ├── configuration.yaml
    ├── automations.yaml
    ├── scripts.yaml
    ├── scenes.yaml
    ├── themes/
    └── packages/
        └── energy_monitoring.yaml
```

### Docker Compose

```yaml
services:
  homeassistant:
    container_name: homeassistant
    image: ghcr.io/home-assistant/home-assistant:stable
    restart: unless-stopped
    privileged: true
    network_mode: host
    security_opt:
      - apparmor=unconfined
    volumes:
      - /opt/homeassistant/config:/config
      - /etc/localtime:/etc/localtime:ro
      - /run/dbus:/run/dbus:ro
    environment:
      - TZ=Asia/Manila
```

### Trusted Proxies

Configured in `configuration.yaml` for Traefik reverse proxy:

```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 192.168.40.20  # Traefik LXC
    - 192.168.40.0/24  # Services VLAN
    - 172.17.0.0/16  # Docker network
```

## Energy Dashboard

### Utility Meters

| Meter | Cycle | Purpose |
|-------|-------|---------|
| `energy_*_daily` | Daily | Daily consumption per device |
| `energy_*_monthly` | Monthly | Monthly consumption per device |
| `total_energy_daily` | Daily | Total daily consumption |
| `total_energy_monthly` | Monthly | Total monthly consumption |

### Cost Sensors

| Sensor | Formula |
|--------|---------|
| `*_daily_cost` | daily_energy * 14.32 PHP |
| `*_monthly_cost` | monthly_energy * 14.32 PHP |
| `total_daily_cost` | total_daily * 14.32 PHP |
| `total_monthly_cost` | total_monthly * 14.32 PHP |

## Management

### View Logs

```bash
ssh hermes-admin@192.168.40.25 "docker logs homeassistant --tail 50"
```

### Restart

```bash
ssh hermes-admin@192.168.40.25 "cd /opt/homeassistant && docker compose restart"
```

### Update

```bash
ssh hermes-admin@192.168.40.25 "cd /opt/homeassistant && docker compose pull && docker compose up -d"
```

### Access via LXC

```bash
ssh root@192.168.20.20 "pct exec 206 -- docker logs homeassistant --tail 50"
```

## Setup Guide

### 1. Initial Onboarding

1. Access https://ha.hrmsmrflrii.xyz
2. Create admin account
3. Set location and time zone
4. Complete onboarding wizard

### 2. Install HACS

```bash
ssh hermes-admin@192.168.40.25 "docker exec -it homeassistant bash"
# Inside container:
wget -O - https://get.hacs.xyz | bash -
```

Restart Home Assistant, then:
1. Settings > Devices & Services > Add Integration
2. Search "HACS" and install
3. Authorize with GitHub account

### 3. Install Tapo Integration

1. HACS > Integrations > Search "Tapo"
2. Install "Tapo Controller"
3. Restart Home Assistant
4. Settings > Devices & Services > Add Integration > Tapo
5. Enter Tapo account credentials
6. Devices will be auto-discovered

### 4. Configure Energy Dashboard

1. Settings > Dashboards > Energy
2. Add grid consumption sensors
3. Add device consumption sensors
4. Configure cost tracking

### 5. Samsung TV Integration

1. Settings > Devices & Services > Add Integration
2. Search "Samsung Smart TV"
3. Follow pairing instructions on TV

## Ansible Playbooks

| Playbook | Purpose |
|----------|---------|
| `homeassistant/deploy-homeassistant.yml` | Deploy Home Assistant container |
| `homeassistant/configure-energy-dashboard.yml` | Configure energy monitoring |

### Deploy

```bash
cd ~/ansible
ansible-playbook homeassistant/deploy-homeassistant.yml
```

### Configure Energy

```bash
cd ~/ansible
ansible-playbook homeassistant/configure-energy-dashboard.yml
```

## Troubleshooting

### Container won't start

```bash
# Check Docker logs
ssh hermes-admin@192.168.40.25 "docker logs homeassistant"

# Verify AppArmor is disabled
ssh hermes-admin@192.168.40.25 "docker inspect homeassistant | grep -i apparmor"
```

### Can't access via Traefik

1. Verify DNS: `nslookup ha.hrmsmrflrii.xyz`
2. Check Traefik logs: `docker logs traefik`
3. Verify trusted_proxies in configuration.yaml

### Tapo devices not discovered

1. Ensure devices are on same network
2. Check Tapo app account credentials
3. Restart integration

### WebSocket connection fails

Add to `configuration.yaml`:

```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 192.168.40.20
```

## Related Documentation

- [Inventory](./INVENTORY.md) - Infrastructure inventory
- [Networking](./NETWORKING.md) - VLAN configuration
- [Glance](./GLANCE.md) - Dashboard comparison
- [Traefik](./FORWARD_AUTH_SETUP.md) - Reverse proxy setup

---

*Created: January 7, 2026*
*Container: Home Assistant Container (stable)*
