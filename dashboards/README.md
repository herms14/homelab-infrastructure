# Grafana Dashboards

Pre-configured Grafana dashboards for homelab monitoring.

## Dashboards

| Dashboard | UID | Description |
|-----------|-----|-------------|
| Proxmox Compute | `proxmox-compute` | Proxmox cluster metrics |
| Container Monitoring | `containers-modern` | Docker container metrics |
| Synology NAS | `synology-nas` | NAS health and storage |
| Traefik | `traefik-observability` | Reverse proxy metrics |

## Import Instructions

### Manual Import

1. Open Grafana (https://grafana.hrmsmrflrii.xyz)
2. Go to Dashboards > Import
3. Upload JSON file or paste contents
4. Select data sources
5. Click Import

### Provisioned Import

Copy dashboards to Grafana provisioning directory:

```bash
cp grafana/*.json /opt/monitoring/grafana/dashboards/
docker restart grafana
```

## Dashboard Features

### Proxmox Compute
- Node status and resource usage
- VM/LXC metrics
- Storage pool utilization
- Network traffic

### Container Monitoring
- Per-container CPU/memory usage
- Bar gauge visualization
- Sorted by utilization (highest first)
- Split by host (utilities/media)

### Synology NAS
- RAID health and status
- Disk temperatures
- Storage utilization
- System metrics

## Customization

Dashboards use variables for flexibility:
- `$datasource` - Prometheus data source
- `$host` - Filter by hostname
- `$interval` - Time aggregation

## Embedding in Glance

Use kiosk mode URLs for embedding:

```
https://grafana.hrmsmrflrii.xyz/d/UID/name?kiosk&theme=transparent&refresh=30s
```
