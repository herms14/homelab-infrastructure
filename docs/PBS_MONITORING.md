# Proxmox Backup Server (PBS) Monitoring

This document covers the setup and configuration of Prometheus monitoring for Proxmox Backup Server.

## Overview

PBS monitoring provides visibility into:
- Backup job status (success/failure)
- Datastore storage usage
- Snapshot counts per datastore
- PBS host resource utilization (CPU, memory, load)

## Architecture

```
+------------------+     +------------------+     +------------------+
|       PBS        |     |   PBS Exporter   |     |    Prometheus    |
| 192.168.20.50    |<--->| 192.168.40.13    |<--->| 192.168.40.13    |
| LXC 100 (node03) |     | Port 9101        |     | Port 9090        |
+------------------+     +------------------+     +------------------+
                                                         |
                                                         v
                                              +------------------+
                                              |     Grafana      |
                                              | 192.168.40.13    |
                                              | Port 3030        |
                                              +------------------+
                                                         |
                                                         v
                                              +------------------+
                                              |      Glance      |
                                              | 192.168.40.12    |
                                              | Backup Page      |
                                              +------------------+
```

## Components

### PBS Server (LXC 100)

| Property | Value |
|----------|-------|
| Host | 192.168.20.50 |
| Node | node03 |
| Web UI | https://192.168.20.50:8007 |
| Version | 3.4 |

### Datastores

| Datastore | Storage Type | Capacity | Purpose |
|-----------|-------------|----------|---------|
| `daily` | Kingston 1TB NVMe | ~1TB | Daily backups (fast restore) |
| `main` | Seagate 4TB HDD | ~4TB | Weekly/monthly backups |

### PBS Exporter

| Property | Value |
|----------|-------|
| Container | `pbs-exporter` |
| Image | `ghcr.io/natrontech/pbs-exporter:latest` |
| Host | docker-vm-core-utilities01 (192.168.40.13) |
| Port | 9101 (external) -> 10019 (internal) |
| Config | `/opt/pbs-exporter/docker-compose.yml` |

## Configuration

### PBS API Token

The exporter authenticates using a PBS API token:

```
User: backup@pbs
Token Name: pve
Token ID: backup@pbs!pve
```

### Docker Compose Configuration

Location: `/opt/pbs-exporter/docker-compose.yml`

```yaml
services:
  pbs-exporter:
    image: ghcr.io/natrontech/pbs-exporter:latest
    container_name: pbs-exporter
    restart: unless-stopped
    environment:
      PBS_ENDPOINT: "https://192.168.20.50:8007"
      PBS_USERNAME: "backup@pbs"
      PBS_API_TOKEN_NAME: "pve"
      PBS_API_TOKEN: "<token-secret>"
      PBS_INSECURE: "true"
      PBS_TIMEOUT: "30s"
    ports:
      - "9101:10019"
    networks:
      - monitoring_monitoring

networks:
  monitoring_monitoring:
    external: true
```

### Prometheus Scrape Configuration

Added to `/opt/monitoring/prometheus/prometheus.yml`:

```yaml
  - job_name: 'pbs'
    static_configs:
      - targets: ['192.168.40.13:9101']
        labels:
          instance: 'pbs-lxc100'
    scrape_interval: 60s
```

## Available Metrics

### Connection Status

| Metric | Description |
|--------|-------------|
| `pbs_up` | 1 if exporter can connect to PBS, 0 otherwise |
| `pbs_version` | PBS version info (labels: version, release, repoid) |

### Datastore Storage

| Metric | Description | Labels |
|--------|-------------|--------|
| `pbs_size` | Total size of datastore in bytes | datastore |
| `pbs_used` | Used bytes in datastore | datastore |
| `pbs_available` | Available bytes in datastore | datastore |

### Backup Snapshots

| Metric | Description | Labels |
|--------|-------------|--------|
| `pbs_snapshot_count` | Number of backup snapshots | datastore, namespace |

### Host Metrics

| Metric | Description |
|--------|-------------|
| `pbs_host_cpu_usage` | CPU usage (0-1) |
| `pbs_host_io_wait` | IO wait percentage |
| `pbs_host_memory_total` | Total memory bytes |
| `pbs_host_memory_used` | Used memory bytes |
| `pbs_host_memory_free` | Free memory bytes |
| `pbs_host_load1` | 1-minute load average |
| `pbs_host_load5` | 5-minute load average |
| `pbs_host_load15` | 15-minute load average |
| `pbs_host_uptime` | Uptime in seconds |
| `pbs_host_disk_total` | Root disk total bytes |
| `pbs_host_disk_used` | Root disk used bytes |
| `pbs_host_disk_available` | Root disk available bytes |
| `pbs_host_swap_total` | Total swap bytes |
| `pbs_host_swap_used` | Used swap bytes |
| `pbs_host_swap_free` | Free swap bytes |

## Grafana Dashboard

| Property | Value |
|----------|-------|
| Dashboard | PBS Backup Status |
| UID | `pbs-backup-status` |
| URL | https://grafana.hrmsmrflrii.xyz/d/pbs-backup-status |
| JSON | `dashboards/pbs-backup-status.json` |

### Dashboard Sections

1. **PBS Status Overview** - Connection status, version, uptime, CPU, memory, load
2. **Datastore Storage** - Pie charts and gauges showing storage usage per datastore
3. **Backup Snapshots** - Snapshot counts for daily and main datastores
4. **Storage Usage Over Time** - Time series of storage usage
5. **PBS Host Metrics** - CPU, memory, and load graphs

## Glance Integration

The Backup page in Glance displays:
- Embedded Grafana dashboard (PBS Backup Status)
- Monitor widget for PBS server health
- Quick links to PBS Web UI and Grafana

Access: https://glance.hrmsmrflrii.xyz → Backup tab

## Useful PromQL Queries

### Storage Usage Percentage

```promql
pbs_used{datastore="daily"} / pbs_size{datastore="daily"} * 100
```

### Total Backup Count

```promql
sum(pbs_snapshot_count)
```

### PBS Memory Usage Percentage

```promql
pbs_host_memory_used / pbs_host_memory_total * 100
```

## Troubleshooting

### Exporter Not Connecting (pbs_up = 0)

1. Check exporter logs:
   ```bash
   docker logs pbs-exporter
   ```

2. Verify PBS API access:
   ```bash
   curl -sk -H 'Authorization: PBSAPIToken=backup@pbs!pve:<secret>' \
     https://192.168.20.50:8007/api2/json/version
   ```

3. Common issues:
   - Wrong API token format (user@realm!tokenname:secret)
   - Network connectivity between exporter and PBS
   - TLS certificate issues (use PBS_INSECURE=true for self-signed)

### No Metrics in Prometheus

1. Check Prometheus targets:
   ```bash
   curl -s 'http://localhost:9090/api/v1/targets' | grep pbs
   ```

2. Test metrics endpoint:
   ```bash
   curl -s http://192.168.40.13:9101/metrics | grep pbs_up
   ```

### Dashboard Shows No Data

1. Verify Prometheus datasource in Grafana
2. Check time range (metrics only available after first scrape)
3. Verify metric names match the exporter output

## Maintenance

### Updating PBS Exporter

```bash
cd /opt/pbs-exporter
docker compose pull
docker compose up -d
```

### Verifying Metrics Collection

```bash
# Check exporter is running
docker ps | grep pbs

# Check metrics endpoint
curl -s http://localhost:9101/metrics | grep -i pbs

# Verify Prometheus scrape
curl -s 'http://localhost:9090/api/v1/query?query=pbs_up'
```

## Administration Notes (Updated January 12, 2026)

### Root Password

| Field | Value |
|-------|-------|
| Username | `root` (select "Linux PAM" realm) |
| Password | `NewPBS2025` |

> **Note**: Enter `root` in username field (not `root@pam`). The realm dropdown automatically adds the `@pam` suffix.

### ACL Permissions

To ensure daily backups work properly, the following ACL permissions must be set:

```bash
# Add DatastoreBackup permission for API token on daily datastore
pvesh create /access/acl --path /datastore/daily --role DatastoreBackup --token 'backup@pbs!pve'

# Add DatastoreBackup permission for user on daily datastore (for non-token access)
pvesh create /access/acl --path /datastore/daily --role DatastoreBackup --userid 'backup@pbs'
```

| Principal | Path | Role |
|-----------|------|------|
| `backup@pbs` | `/` | Audit |
| `backup@pbs` | `/datastore/main` | DatastoreAdmin |
| `backup@pbs` | `/datastore/daily` | DatastoreAdmin |
| `backup@pbs!pve` | `/datastore/main` | DatastoreAdmin |
| `backup@pbs!pve` | `/datastore/daily` | DatastoreBackup |

### Subscription Nag Removal

To remove the "No valid subscription" popup:

```bash
# SSH to PBS container via node03
ssh root@192.168.20.22

# Enter the LXC container
pct exec 100 -- bash

# Edit the proxmoxlib.js file
nano /usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js

# Find this line:
if (res === null || res === undefined || !res || res.data.status.toLowerCase() !== 'active') {

# Change to (flip the condition):
if (res === null || res === undefined || !res || res.data.status.toLowerCase() === 'active') {

# Clear browser cache or use incognito to verify
```

### Orphaned Backup Cleanup

If backup errors show "missing blob files" in logs, check for incomplete snapshots:

```bash
# On PBS container, check for orphaned temp files
find /backup /backup-ssd -name "*.tmp_fidx" 2>/dev/null

# Check for snapshots missing index.json.blob
for dir in /backup*/*/vm/*/; do
  if [[ -d "$dir" ]]; then
    for snap in "$dir"*/; do
      if [[ -d "$snap" && ! -f "$snap/index.json.blob" ]]; then
        echo "Incomplete: $snap"
      fi
    done
  fi
done

# Remove incomplete snapshots (after verification)
# rm -rf /path/to/incomplete/snapshot
```

## Drive Health Monitoring (Added January 12, 2026)

SMART health monitoring for PBS storage drives is provided via a custom API on node03.

### SMART Health API

| Property | Value |
|----------|-------|
| Host | node03 (192.168.20.22) |
| Port | 9101 |
| Endpoint | `http://192.168.20.22:9101/health` |
| Service | `smart-health-api.service` |

### Monitored Drives

| Drive | Device | Datastore |
|-------|--------|-----------|
| Seagate 4TB HDD | `/dev/sda` | main |
| Kingston 1TB NVMe | `/dev/nvme1n1` | daily |

### API Response

```json
{
  "drives": [
    {
      "device": "/dev/sda",
      "name": "Seagate 4TB HDD",
      "datastore": "main",
      "healthy": true,
      "status": "PASSED"
    },
    {
      "device": "/dev/nvme1n1",
      "name": "Kingston 1TB NVMe",
      "datastore": "daily",
      "healthy": true,
      "status": "PASSED"
    }
  ]
}
```

### Service Files

**Script Location**: `/opt/smart-health-api/smart-health.py`

```python
#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import json

DRIVES = [
    {"device": "/dev/sda", "name": "Seagate 4TB HDD", "datastore": "main"},
    {"device": "/dev/nvme1n1", "name": "Kingston 1TB NVMe", "datastore": "daily"}
]

# Uses smartctl -H -j to check SMART health status
# Returns JSON with healthy boolean and status string
```

**Systemd Service**: `/etc/systemd/system/smart-health-api.service`

```bash
# Enable and start the service
systemctl enable smart-health-api
systemctl start smart-health-api

# Check status
systemctl status smart-health-api
curl http://localhost:9101/health
```

### Glance Integration

The Drive Health Status widget is displayed on the Glance Backup page:

```yaml
- type: custom-api
  title: Drive Health Status
  cache: 5m
  url: http://192.168.20.22:9101/health
  template: |
    # Uses Go templating to display drive status with color indicators
    # Green for healthy, Red for failed
```

## NAS Backup Status API (Added January 12, 2026)

A custom API that monitors the PBS-to-NAS backup sync status and lists all backups stored on the Synology NAS.

### API Overview

| Property | Value |
|----------|-------|
| Host | docker-vm-core-utilities01 (192.168.40.13) |
| Port | 9102 |
| Container | `nas-backup-status-api` |
| Config | `/opt/nas-backup-status-api/` |

### Endpoints

| Endpoint | Description | Response |
|----------|-------------|----------|
| `/status` | Sync status and datastore sizes | `{"status": "success", "last_sync": "...", "main_size": "20G", "daily_size": "38G"}` |
| `/backups` | List of all backups on NAS | `{"backups": [...], "total_count": 14, "vm_count": 7, "ct_count": 7}` |
| `/health` | Health check | `{"status": "healthy"}` |

### Status Response Fields

| Field | Description |
|-------|-------------|
| `status` | `success`, `running`, `failed`, or `unknown` |
| `last_sync` | Timestamp of last successful sync |
| `main_size` | Size of main datastore on NAS (e.g., "20G") |
| `daily_size` | Size of daily datastore on NAS (e.g., "38G") |
| `nas_target` | NAS mount path |
| `schedule` | Sync schedule (Daily at 2:00 AM) |

### Backups Response Fields

| Field | Description |
|-------|-------------|
| `backups` | Array of backup objects |
| `total_count` | Total number of backed up VMs/CTs |
| `vm_count` | Number of VMs with backups |
| `ct_count` | Number of CTs with backups |

Each backup object contains:
- `vmid`: VM/CT ID
- `type`: "VM" or "CT"
- `datastore`: "main" or "daily"
- `last_backup`: Timestamp of most recent backup

### How It Works

1. API runs on docker-vm-core-utilities01 in a Docker container
2. Uses SSH to query PBS server (192.168.20.50) for:
   - Lock file status (determines if sync is running)
   - Log file for last sync time and status
   - NAS mount directories for backup listing
3. Reads datastore sizes from log file (faster than `du -sh` over NFS)

### Deployment

```bash
ansible-playbook glance/deploy-nas-backup-status-api.yml
```

Or manual deployment:

```bash
ssh hermes-admin@192.168.40.13
cd /opt/nas-backup-status-api
docker compose up -d --build
```

### Glance Integration

Two widgets on the Backup page use this API:

1. **NAS Backup Sync** - Shows sync status with color indicator
2. **Backups on NAS** - Lists all protected VMs/CTs with backup dates

### SSH Requirements

The API container needs SSH access to PBS:
- SSH key mounted at `/root/.ssh/homelab_ed25519`
- PBS must have the public key in `/root/.ssh/authorized_keys`

### Troubleshooting

```bash
# Test API
curl http://192.168.40.13:9102/status
curl http://192.168.40.13:9102/backups

# Check container logs
docker logs nas-backup-status-api

# Verify SSH connectivity
ssh -i ~/.ssh/homelab_ed25519 root@192.168.20.50 "echo 'SSH OK'"
```

## References

- [PBS Exporter GitHub](https://github.com/natrontech/pbs-exporter)
- [Proxmox Backup Server Documentation](https://pbs.proxmox.com/docs/)
- [PBS API Documentation](https://pbs.proxmox.com/docs/api-viewer/index.html)
