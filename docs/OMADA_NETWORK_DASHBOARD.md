# Omada Network Dashboard Setup Guide

This guide explains how to set up the comprehensive Omada Network dashboard for Glance.

## Overview

The Omada Network Dashboard combines metrics from:
- **TP-Link Omada SDN** - Devices, clients, traffic, APs, switches, PoE
- **OPNsense Firewall** - Gateway status, firewall rules, connections
- **Speedtest Tracker** - Internet speed tests (download, upload, ping)

## Dashboard Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 📊 OVERVIEW                                                                   │
├───────┬───────┬───────┬───────┬───────┬───────┬───────┬───────────────────────┤
│Total  │Wired  │Wireless│Uptime │Storage│Upgrade│      WiFi Mode Pie Chart     │
│Clients│ Blue  │  Pink  │Purple │ Gauge │Needed │           (Donut)            │
├───────┴───────┴───────┴───────┴───────┴───────┴───────────────────────────────┤
│ 🖥️ DEVICE HEALTH                                                              │
├─────────────────┬─────────────────┬─────────────────────┬─────────────────────┤
│  Gateway CPU    │ Gateway Memory  │   Switch CPU Usage  │    AP CPU Usage     │
│    (Gauge)      │    (Gauge)      │    (Bar Gauge)      │    (Bar Gauge)      │
├─────────────────┴─────────────────┼─────────────────────┴─────────────────────┤
│         Device Uptimes (Stat - all devices)                                   │
├───────────────────────────────────────────────────────────────────────────────┤
│ 📶 WIFI SIGNAL QUALITY                                                        │
├───────────────────────────────────┬───────────────────────────────────────────┤
│  Client Signal Strength (RSSI)    │    Signal-to-Noise Ratio (SNR)            │
│  Top 15 clients, -100 to -20 dBm  │    Top 15 clients, 0 to 60 dB             │
├───────────────────────────────────┴───────────────────────────────────────────┤
│                    WiFi Signal Over Time (Time Series)                        │
├───────────────────────────────────────────────────────────────────────────────┤
│ 🔌 SWITCH PORT STATUS                                                         │
├───────────────────────────────────────────────────────────────────────────────┤
│              Port Link Status (UP/DOWN for all ports)                         │
├───────────────────────────────────┬───────────────────────────────────────────┤
│      Port Link Speeds (Mbps)      │     Port Traffic RX/TX (Time Series)      │
├───────────────────────────────────┴───────────────────────────────────────────┤
│ ⚡ POE POWER USAGE                                                            │
├─────────────────┬─────────────────┬───────────────────────────────────────────┤
│  Total PoE Power│  PoE Remaining  │         PoE Power Per Port                │
│    (Gauge)      │   (Stat+Area)   │         (Bar Gauge)                       │
├─────────────────┴─────────────────┴───────────────────────────────────────────┤
│ 📈 TRAFFIC ANALYSIS                                                           │
├───────────────────────────────────┬───────────────────────────────────────────┤
│   Client Connection Trend         │   Top 10 Clients by Traffic (Bar Gauge)   │
│   (Total/Wired/Wireless)          │                                           │
├───────────────────────────────────┼───────────────────────────────────────────┤
│   Device Download Traffic         │   Device Upload Traffic                   │
│   (Time Series)                   │   (Time Series)                           │
├───────────────────────────────────┼───────────────────────────────────────────┤
│   Client TX Rate (Bar Gauge)      │   Client RX Rate (Bar Gauge)              │
├───────────────────────────────────┴───────────────────────────────────────────┤
│ 📋 CLIENT DETAILS                                                             │
├───────────────────────────────────────────────────────────────────────────────┤
│              All Connected Clients (Table)                                    │
│  Client | IP | MAC | VLAN | Port | Mode | SSID | AP | Vendor | WiFi | Activity│
└───────────────────────────────────────────────────────────────────────────────┘
```

**Grafana UID**: `omada-network`
**Glance Iframe Height**: 2200px
**Dashboard JSON**: `temp-omada-full-dashboard.json`
**Dashboard Version**: 3 (PROTECTED - Do not modify without permission)

## Prerequisites

| Component | Status | Port | Host |
|-----------|--------|------|------|
| Omada Controller | OC300 | 443 | 192.168.0.103 |
| OPNsense Firewall | Active | 9198 | 192.168.91.30 |
| Speedtest Tracker | Active | 3000 | 192.168.40.10 |
| Prometheus | Active | 9090 | 192.168.40.10 |
| Grafana | Active | 3030 | 192.168.40.10 |

## Step 1: Create Omada Viewer User

1. Log into Omada Controller at https://192.168.0.103
2. Go to **Settings > Admin** (or Global Settings > Admins)
3. Click **Add Admin**
4. Configure:
   - **Username**: `claude-reader`
   - **Password**: `&FtwLsK#6PGDbJyA`
   - **Role**: **Viewer** (read-only access)
5. Save the user

## Step 2: Deploy Omada Exporter

SSH to the Ansible controller and run:

```bash
# Set the Omada password
export OMADA_PASSWORD='&FtwLsK#6PGDbJyA'

# Deploy the exporter
cd ~/ansible
ansible-playbook monitoring/deploy-omada-exporter.yml
```

Or deploy manually on docker-vm-utilities01:

```bash
ssh hermes-admin@192.168.40.10

# Create directory
sudo mkdir -p /opt/omada-exporter
cd /opt/omada-exporter

# Create docker-compose.yml
sudo tee docker-compose.yml << 'EOF'
services:
  omada-exporter:
    image: ghcr.io/charlie-haley/omada_exporter:latest
    container_name: omada-exporter
    restart: unless-stopped
    ports:
      - "9202:9202"
    environment:
      OMADA_HOST: "https://192.168.0.103"
      OMADA_USER: "claude-reader"
      OMADA_PASS: "&FtwLsK#6PGDbJyA"
      OMADA_SITE: "Default"
      OMADA_INSECURE: "true"
      LOG_LEVEL: "warn"
EOF

# Deploy
sudo docker compose up -d

# Verify metrics are being exported
curl http://localhost:9202/metrics | head -50
```

## Step 3: Update Prometheus Configuration

Add the Omada scrape job to Prometheus:

```bash
ssh hermes-admin@192.168.40.10

# Edit prometheus config
sudo nano /opt/monitoring/prometheus/prometheus.yml
```

Add to `scrape_configs`:

```yaml
  - job_name: 'omada'
    static_configs:
      - targets: ['192.168.40.10:9202']
        labels:
          site: 'Default'

  - job_name: 'speedtest'
    metrics_path: /api/speedtest/latest/prometheus
    static_configs:
      - targets: ['192.168.40.10:3000']
    scrape_interval: 5m
```

Reload Prometheus:

```bash
curl -X POST http://localhost:9090/-/reload
```

## Step 4: Deploy Grafana Dashboard

```bash
# Set Grafana API key
export GRAFANA_API_KEY='your_grafana_api_key'

# Deploy COMPREHENSIVE dashboard (recommended)
cd ~/ansible
ansible-playbook monitoring/deploy-omada-full-dashboard.yml

# OR deploy simpler version
ansible-playbook monitoring/deploy-omada-network-dashboard.yml
```

### Comprehensive Dashboard Includes:
- **Device Health**: Gateway/Switch/AP CPU and Memory gauges
- **WiFi Signal Quality**: RSSI and SNR bar gauges, signal over time
- **Switch Port Status**: Link status, speeds, RX/TX traffic
- **PoE Power Usage**: Total power, remaining, per-port usage
- **Traffic Analysis**: Client trends, top clients, TX/RX rates
- **Client Details**: Full table with all client information

## Step 5: Update Glance Network Tab

The Network tab will embed the new dashboard. You can update it automatically:

```bash
# Automatic update via Ansible
cd ~/ansible
ansible-playbook monitoring/update-glance-network-tab.yml
```

Or manually update the Glance configuration to point to the new dashboard URL:

```
https://grafana.hrmsmrflrii.xyz/d/omada-network/omada-network-overview?orgId=1&kiosk&theme=transparent&refresh=30s&from=now-1h&to=now
```

**Recommended Iframe Height**: 1900px (comprehensive dashboard is tall)

## Dashboard Panels

### Row 1: Device Summary
| Panel | Metric | Color |
|-------|--------|-------|
| Total Devices | `count(omada_device_uptime_seconds)` | Blue |
| Gateway | Device count by type=gateway | Green |
| Switches | Device count by type=switch | Purple |
| Access Points | Device count by type=ap | Cyan |
| Total Clients | `omada_client_connected_total` | Green |
| Wired Clients | Clients with connection_mode=wired | Amber |
| Wireless Clients | Clients with connection_mode=wireless | Pink |
| Total Traffic | Sum of all client traffic | Blue |

### Row 2: Gateway & ISP
| Panel | Metric |
|-------|--------|
| Gateway CPU | `omada_device_cpu_percentage{device_type="gateway"}` |
| Gateway Memory | `omada_device_mem_percentage{device_type="gateway"}` |
| Gateway Utilization | Time series of CPU and Memory |

### Row 3: Client Connection Trend
| Panel | Metric |
|-------|--------|
| Client Trend | Time series of total, wired, wireless clients |
| Download Speed | Speedtest download (Mbps) |
| Upload Speed | Speedtest upload (Mbps) |
| Ping | Speedtest latency (ms) |
| Jitter | Speedtest jitter (ms) |

### Row 4: Traffic & Switches
| Panel | Metric |
|-------|--------|
| Network Traffic (WAN) | OPNsense WAN interface rx/tx |
| Switch Traffic (Top 5) | Top switches by traffic |
| PoE Power Usage | PoE watts per switch |

### Row 5: APs & WiFi
| Panel | Metric |
|-------|--------|
| Top APs by Client Count | Clients per AP |
| Top APs by Traffic | Traffic per AP |
| Clients by SSID | Pie chart of SSID distribution |

### Row 6: OPNsense Firewall
| Panel | Metric |
|-------|--------|
| OPNsense Gateway | Gateway status |
| Services Running | Running service count |
| Firewall Blocked | Blocked packet count |
| Firewall Pass/Block Rate | Time series |
| TCP Connections | Established connections |
| DNS Queries | Unbound queries (30m) |
| DNS Blocked | Blocked DNS queries (30m) |

## Metrics Not Available

Due to Omada API limitations, these metrics from the Omada UI are NOT available via the exporter:

| Feature | Reason |
|---------|--------|
| ISP Load (latency/throughput) | Not exposed by Omada API |
| Gateway Alerts (errors/warnings) | Not exposed by Omada API |
| Application/DPI Categories | Deep Packet Inspection not exposed |
| Top 20 Applications by traffic | DPI data not exposed |

For DPI/Application data, continue using the native Omada Controller UI.

## Troubleshooting

### Exporter not returning metrics

```bash
# Check container logs
docker logs omada-exporter

# Test connectivity to Omada
curl -k https://192.168.0.103

# Verify credentials work
# Try logging into Omada web UI with claude-reader
```

### Prometheus not scraping

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.job=="omada")'

# Check for scrape errors
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.job=="omada") | .lastError'
```

### Missing client metrics

Some Omada Controller versions have API changes. Check the exporter GitHub for known issues:
https://github.com/charlie-haley/omada_exporter/issues

## File Locations

| File | Location |
|------|----------|
| Omada Exporter | `/opt/omada-exporter/docker-compose.yml` (on ansible-controller01) |
| Prometheus Config | `/opt/monitoring/prometheus/prometheus.yml` |
| Dashboard JSON | `temp-omada-full-dashboard.json` |
| Dashboard Ansible (Full) | `ansible-playbooks/monitoring/deploy-omada-full-dashboard.yml` |
| Dashboard Ansible (Simple) | `ansible-playbooks/monitoring/deploy-omada-network-dashboard.yml` |
| Glance Update Ansible | `ansible-playbooks/monitoring/update-glance-network-tab.yml` |
| Exporter Ansible | `ansible-playbooks/monitoring/deploy-omada-exporter.yml` |

## References

- [omada_exporter GitHub](https://github.com/charlie-haley/omada_exporter)
- [Grafana Dashboard ID 20854](https://grafana.com/grafana/dashboards/20854-omada-overview/)
- [Omada SDN API](https://www.tp-link.com/us/support/faq/3231/)

---

# Tutorial: How This Dashboard Was Built

This section documents the complete process of scraping Omada network data and building the Grafana dashboard.

## Part 1: Understanding the Data Source

### What is Omada SDN?

TP-Link Omada SDN (Software Defined Networking) is a centralized management platform for:
- **Gateway/Router** (ER605, ER7206, etc.)
- **Managed Switches** (SG3210, SG2008P, etc.)
- **Access Points** (EAP610, EAP603, EAP225, etc.)

The Omada Controller (OC300 hardware or software) manages all devices and exposes an API.

### Available Metrics from Omada Exporter

The `omada_exporter` project by Charlie Haley scrapes the Omada Controller API and exposes metrics in Prometheus format.

**Device Metrics:**
```
omada_device_uptime_seconds{device="DeviceName", device_type="gateway|switch|ap"}
omada_device_cpu_percentage{device="DeviceName", device_type="..."}
omada_device_mem_percentage{device="DeviceName", device_type="..."}
omada_device_poe_remain_watts{device="SwitchName"}
omada_device_need_upgrade{device="DeviceName"}
```

**Controller Metrics:**
```
omada_controller_uptime_seconds
omada_controller_storage_used_bytes
omada_controller_storage_available_bytes
```

**Client Metrics:**
```
omada_client_connected_total{connection_mode="wired|wireless", wifi_mode="5GHz|2.4GHz"}
omada_client_rssi_dbm{client="ClientName"}
omada_client_snr_dbm{client="ClientName"}
omada_client_tx_rate{client="ClientName"}
omada_client_rx_rate{client="ClientName"}
omada_client_traffic_down_bytes{client="ClientName"}
omada_client_traffic_up_bytes{client="ClientName"}
omada_client_download_activity_bytes{client="ClientName", ip="...", mac="...", ...}
```

**Switch Port Metrics:**
```
omada_port_link_status{device="SwitchName", port="1"}  # 0=DOWN, 1=UP
omada_port_link_speed_mbps{device="SwitchName", port="1"}
omada_port_power_watts{device="SwitchName", port="1"}
omada_port_link_rx{device="SwitchName", port="1"}  # bytes counter
omada_port_link_tx{device="SwitchName", port="1"}  # bytes counter
```

## Part 2: Setting Up Data Collection

### Step 1: Create Read-Only Omada User

```
Controller → Settings → Admin → Add Admin
Username: claude-reader
Role: Viewer (read-only, cannot modify anything)
```

### Step 2: Deploy the Exporter

The exporter runs as a Docker container that periodically polls the Omada API:

```yaml
# /opt/omada-exporter/docker-compose.yml
services:
  omada-exporter:
    image: ghcr.io/charlie-haley/omada_exporter:latest
    container_name: omada-exporter
    restart: unless-stopped
    ports:
      - "9202:9202"
    environment:
      OMADA_HOST: "https://192.168.0.103"
      OMADA_USER: "claude-reader"
      OMADA_PASS: "your-password"
      OMADA_SITE: "Default"
      OMADA_INSECURE: "true"  # Skip TLS verification for self-signed cert
```

### Step 3: Verify Metrics Export

```bash
curl http://192.168.20.30:9202/metrics | grep omada_
```

Example output:
```
omada_device_uptime_seconds{device="ER605",device_type="gateway"} 1234567
omada_client_connected_total{connection_mode="wireless",wifi_mode="5GHz"} 8
omada_port_link_status{device="SG3210",port="1"} 1
```

### Step 4: Configure Prometheus Scraping

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'omada'
    static_configs:
      - targets: ['192.168.20.30:9202']
    scrape_interval: 30s
```

## Part 3: Building the Dashboard

### Dashboard JSON Structure

Grafana dashboards are JSON documents with this structure:

```json
{
  "dashboard": {
    "uid": "unique-identifier",
    "title": "Dashboard Title",
    "panels": [
      {
        "id": 1,
        "type": "stat|gauge|timeseries|table|bargauge|piechart",
        "title": "Panel Title",
        "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
        "targets": [
          {"expr": "prometheus_query_here", "legendFormat": "{{label}}"}
        ],
        "fieldConfig": {...},
        "options": {...}
      }
    ]
  },
  "overwrite": true
}
```

### Panel Types Used

| Type | Use Case | Example |
|------|----------|---------|
| `stat` | Single value with background color | Total Clients, Device Uptimes |
| `gauge` | Circular gauge with thresholds | CPU%, Memory%, PoE Power |
| `bargauge` | Horizontal bars with gradient | Client RSSI, Switch CPU |
| `timeseries` | Line charts over time | Signal Over Time, Traffic |
| `table` | Tabular data | Port Status, Client List |
| `piechart` | Distribution visualization | WiFi Mode Distribution |

### Key PromQL Queries

**Total connected clients:**
```promql
sum(omada_client_connected_total)
```

**Wireless clients only:**
```promql
sum(omada_client_connected_total{connection_mode="wireless"})
```

**Top 15 clients by signal strength:**
```promql
topk(15, omada_client_rssi_dbm)
```

**Port traffic rate (bytes/sec):**
```promql
rate(omada_port_link_rx[5m])
```

**Device uptime by type:**
```promql
omada_device_uptime_seconds{device_type="gateway"}
```

### Color Thresholds

WiFi Signal (RSSI) thresholds:
```json
"thresholds": {
  "steps": [
    {"color": "#ef4444", "value": null},      // Red: < -70 dBm (weak)
    {"color": "#f59e0b", "value": -70},        // Yellow: -70 to -50 (good)
    {"color": "#22c55e", "value": -50}         // Green: > -50 dBm (excellent)
  ]
}
```

### Grid Positioning

Grafana uses a 24-column grid:
```json
"gridPos": {
  "h": 4,    // Height in grid units
  "w": 6,    // Width (6 = 1/4 of screen)
  "x": 0,    // X position (0-23)
  "y": 0     // Y position (row)
}
```

## Part 4: Deploying the Dashboard

### Method 1: Grafana API

```bash
curl -X POST "http://192.168.40.10:3030/api/dashboards/db" \
  -H "Content-Type: application/json" \
  -u admin:admin \
  -d @temp-omada-full-dashboard.json
```

### Method 2: Ansible Playbook

```yaml
# deploy-omada-full-dashboard.yml
- name: Deploy dashboard to Grafana
  uri:
    url: "{{ grafana_url }}/api/dashboards/db"
    method: POST
    headers:
      Authorization: "Bearer {{ grafana_api_key }}"
    body: "{{ lookup('file', dashboard_file) | from_json | to_json }}"
    body_format: json
```

## Part 5: Design Decisions

### Why Pi-hole Style Uptime Boxes?

The original design showed all device uptimes in a single horizontal stat panel, which was hard to read. We changed to individual colored boxes (like Pi-hole's dashboard) for:
- Better visibility of each device
- Clear device identification
- Consistent color coding per device type

### Why Table for Port Status?

The original stat visualization for port status showed "UP" and "DOWN" labels but:
- No context about which switch/port
- No speed information
- No PoE power data

A table provides:
- Switch name
- Port number
- Status with color (green=UP, red=DOWN)
- Link speed with color coding
- PoE power consumption

### Why Increased Heights for WiFi Panels?

Signal quality panels need more vertical space because:
- 15 clients with bar gauges need room
- Client names can be long
- Time series needs legend table

## Part 6: Maintenance Notes

### Protected Status

This dashboard is **PROTECTED** and should not be modified without explicit permission.

Files involved:
- `temp-omada-full-dashboard.json` - Dashboard definition
- `ansible-playbooks/monitoring/deploy-omada-full-dashboard.yml` - Deployment
- `ansible-playbooks/monitoring/update-glance-network-tab.yml` - Glance integration

### Version History

| Version | Date | Changes |
|---------|------|---------|
| 1 | Dec 25, 2025 | Initial simple dashboard |
| 2 | Dec 26, 2025 | Added comprehensive panels |
| 3 | Dec 26, 2025 | Fixed uptimes (Pi-hole style), increased WiFi heights, table for ports |

### Updating the Dashboard

If changes are needed in the future:

1. Edit `temp-omada-full-dashboard.json`
2. Increment version number
3. Deploy via API or Ansible
4. Update Glance iframe height if dashboard height changed
5. Document changes in this file and CHANGELOG.md
