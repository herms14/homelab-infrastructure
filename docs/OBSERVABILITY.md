# Observability Stack

> Part of the [Proxmox Infrastructure Documentation](../CLAUDE.md)

End-to-end request visibility using OpenTelemetry, Jaeger, Prometheus, and Grafana.

## Architecture Overview

### Request Flow

```
┌──────────┐    ┌───────────────┐    ┌─────────┐    ┌─────────────┐
│  Client  │───▶│    Traefik    │───▶│Authentik│───▶│   Backend   │
│ (Browser)│    │ (TLS + Routing)│    │ForwardAuth│   │     App     │
└──────────┘    └───────────────┘    └─────────┘    └─────────────┘
```

### Trace Flow

```
┌─────────────┐     ┌─────────────────┐     ┌────────┐     ┌─────────┐
│   Traefik   │────▶│  OTEL Collector │────▶│ Jaeger │────▶│ Grafana │
│ (OTLP HTTP) │     │   (receiver,    │     │ (OTLP) │     │ (trace  │
└─────────────┘     │   processor,    │     │        │     │  view)  │
                    │   exporter)     │     └────────┘     └─────────┘
┌─────────────┐     │                 │
│ Backend App │────▶│                 │
│ (OTLP gRPC) │     └─────────────────┘
└─────────────┘
```

### Metrics Flow

```
┌─────────────┐                      ┌────────────┐     ┌─────────┐
│   Traefik   │◀─────────scrape──────│ Prometheus │────▶│ Grafana │
│  :8082/     │                      │            │     │         │
│  metrics    │                      └────────────┘     └─────────┘
└─────────────┘                            ▲
                                           │
┌─────────────┐                            │
│OTEL Collector│◀──────────────────────────┘
│ :8888/:8889 │
└─────────────┘
```

## Components

### OpenTelemetry Collector

**Host**: docker-vm-utilities01 (192.168.40.10)
**Image**: otel/opentelemetry-collector-contrib:0.91.0

| Port | Protocol | Purpose |
|------|----------|---------|
| 4317 | gRPC | OTLP trace/metrics receiver |
| 4318 | HTTP | OTLP trace/metrics receiver |
| 8888 | HTTP | Collector internal metrics |
| 8889 | HTTP | Prometheus exporter (pipeline metrics) |
| 13133 | HTTP | Health check |

**Pipeline Configuration**:
- **Receivers**: OTLP (gRPC + HTTP)
- **Processors**: memory_limiter, attributes (sanitization), resource, batch
- **Exporters**: otlp/jaeger, prometheus, debug

### Jaeger

**Host**: docker-vm-utilities01 (192.168.40.10)
**Image**: jaegertracing/all-in-one:1.53
**URL**: https://jaeger.hrmsmrflrii.xyz (protected by Authentik)

| Port | Purpose |
|------|---------|
| 16686 | Web UI |
| 4317 | OTLP gRPC receiver |
| 14269 | Metrics endpoint |

**Storage**: In-memory (50,000 traces max)

### Demo Application

**Host**: docker-vm-utilities01 (192.168.40.10)
**URL**: https://demo.hrmsmrflrii.xyz (protected by Authentik)
**Port**: 8080

Instrumented Python/Flask application demonstrating multi-span traces:
- Simulated database queries
- Simulated cache lookups
- Simulated external API calls

### Traefik (Updated)

**Additional Configuration**:
- OpenTelemetry tracing enabled (exports to OTEL Collector)
- Prometheus metrics endpoint on port 8082
- Access logs with trace correlation headers

## Deployment

### Prerequisites

1. Monitoring stack deployed (`deploy-monitoring-stack.yml`)
2. Traefik running (`deploy-traefik-ssl.yml`)
3. Authentik configured with ForwardAuth

### Deployment Order

```bash
# 1. Update monitoring stack (adds Jaeger datasource, scrape configs)
ansible-playbook monitoring/deploy-monitoring-stack.yml

# 2. Deploy observability stack (OTEL Collector, Jaeger, demo app)
ansible-playbook monitoring/deploy-observability-stack.yml

# 3. Update Traefik with OTEL tracing and observability routes
ansible-playbook traefik/deploy-traefik-ssl.yml

# 4. Configure DNS (if not already done)
# Add: jaeger.hrmsmrflrii.xyz, demo.hrmsmrflrii.xyz -> 192.168.40.20
```

### File Locations

| Component | Location |
|-----------|----------|
| Observability stack | `/opt/observability/` |
| OTEL Collector config | `/opt/observability/otel-collector/otel-collector-config.yaml` |
| Demo app | `/opt/observability/demo-app/` |
| Traefik config | `/opt/traefik/config/traefik.yml` |
| Prometheus config | `/opt/monitoring/prometheus/prometheus.yml` |
| Grafana datasources | `/opt/monitoring/grafana/provisioning/datasources/` |

## Usage

### Viewing Traces

1. Navigate to https://jaeger.hrmsmrflrii.xyz
2. Authenticate via Authentik
3. Select **Service**: `traefik` or `demo-app`
4. Click **Find Traces**
5. Click on a trace to see the span waterfall

### Generating Test Traffic

```bash
# Direct test (bypassing auth)
curl http://192.168.40.10:8080/health
curl http://192.168.40.10:8080/api/data

# Through Traefik (requires auth)
# Open in browser: https://demo.hrmsmrflrii.xyz/api/data

# Generate load for visible traces
for i in {1..20}; do
  curl -s https://demo.hrmsmrflrii.xyz/api/data > /dev/null
  sleep 0.5
done
```

### Demo App Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Simple response with user info |
| `/api/data` | Complex operation with cache, DB, external API spans |
| `/api/slow` | Intentionally slow (1-3s) for latency testing |
| `/api/error` | Random failures for error trace testing |
| `/health` | Health check |
| `/metrics` | Prometheus metrics |

### Grafana Dashboards

**Traefik Observability Dashboard**:
- Request rate (req/s)
- P95 latency
- Error rate %
- Active services count
- Requests by service
- P95 latency by service
- Requests by status code

**Access**: https://grafana.hrmsmrflrii.xyz → Dashboards → Traefik Observability

### Prometheus Queries

```promql
# Total request rate
sum(rate(traefik_service_requests_total[5m]))

# P95 latency
histogram_quantile(0.95, sum(rate(traefik_service_request_duration_seconds_bucket[5m])) by (le))

# Error rate percentage
sum(rate(traefik_service_requests_total{code=~"5.."}[5m])) / sum(rate(traefik_service_requests_total[5m])) * 100

# Requests by service
sum(rate(traefik_service_requests_total[5m])) by (service)

# OTEL Collector received spans
rate(otelcol_receiver_accepted_spans[5m])

# OTEL Collector dropped spans
rate(otelcol_processor_dropped_spans[5m])
```

## Verification

### Check OTEL Collector

```bash
# Health check
curl http://192.168.40.10:13133

# Metrics
curl http://192.168.40.10:8888/metrics | head -20
```

### Check Traefik Tracing

```bash
# Verify OTEL config in logs
ssh hermes-admin@192.168.40.20 "docker logs traefik 2>&1 | grep -i otel"

# Check metrics endpoint
curl http://192.168.40.20:8082/metrics | head -20
```

### Check Jaeger

```bash
# Health check
curl http://192.168.40.10:14269

# Check for services in Jaeger
curl http://192.168.40.10:16686/api/services
```

### Check Prometheus Targets

```bash
# View target status
curl -s http://192.168.40.10:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

## Troubleshooting

### No Traces Appearing in Jaeger

1. **Check OTEL Collector is running**:
   ```bash
   ssh hermes-admin@192.168.40.10 "docker logs otel-collector --tail 50"
   ```

2. **Verify Traefik can reach OTEL Collector**:
   ```bash
   ssh hermes-admin@192.168.40.20 "curl -v http://192.168.40.10:4318/v1/traces"
   ```

3. **Check Traefik logs for trace errors**:
   ```bash
   ssh hermes-admin@192.168.40.20 "docker logs traefik 2>&1 | grep -i error"
   ```

### Prometheus Not Scraping Targets

1. **Check target status**:
   ```bash
   curl http://192.168.40.10:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health != "up")'
   ```

2. **Verify network connectivity**:
   ```bash
   # From docker-utilities host
   curl http://192.168.40.20:8082/metrics
   ```

### Demo App Not Starting

1. **Check container logs**:
   ```bash
   ssh hermes-admin@192.168.40.10 "docker logs demo-app"
   ```

2. **Verify OTEL Collector is healthy**:
   ```bash
   ssh hermes-admin@192.168.40.10 "docker ps | grep otel"
   ```

## Security Considerations

### Authentication

All observability endpoints are protected by Authentik ForwardAuth:
- https://jaeger.hrmsmrflrii.xyz
- https://prometheus.hrmsmrflrii.xyz
- https://grafana.hrmsmrflrii.xyz
- https://demo.hrmsmrflrii.xyz

### Network Isolation

- OTLP ports (4317, 4318) are exposed for internal services only
- Jaeger UI is only accessible via Traefik (with auth)
- Prometheus internal metrics not exposed externally

### Data Sanitization

OTEL Collector processors remove sensitive headers:
- `http.request.header.authorization`
- `http.request.header.cookie`

## Maintenance

### Log Retention

| Component | Retention |
|-----------|-----------|
| Docker logs | 10MB per container, 3 files |
| Prometheus | 30 days or 10GB |
| Jaeger | 50,000 traces (in-memory) |

### Updating Components

```bash
# Update observability stack
ssh hermes-admin@192.168.40.10 "cd /opt/observability && docker compose pull && docker compose up -d"

# Update monitoring stack
ssh hermes-admin@192.168.40.10 "cd /opt/monitoring && docker compose pull && docker compose up -d"
```

### Backup Considerations

- Prometheus data: `/opt/monitoring/prometheus/data/`
- Grafana dashboards: Exported as JSON or provisioned via files
- Jaeger: In-memory, no persistent backup needed

## Synology NAS Monitoring

The monitoring stack includes SNMP-based monitoring for the Synology NAS (192.168.20.31).

### Components

| Component | Purpose |
|-----------|---------|
| SNMP Exporter | Collects SNMP metrics from Synology NAS |
| Prometheus | Scrapes SNMP exporter on synology job |
| Grafana | Synology NAS dashboard |
| Glance | Embedded Grafana dashboard on Storage page |

### Metrics Collected

| Category | Metrics |
|----------|---------|
| Disk Health | SMART status, temperature, health status |
| Storage | RAID total/free/used, volume usage |
| CPU | Processor load per core, system stats |
| Memory | Total, available, cached, buffer |
| System | Status, temperature, fan status |

### Prerequisites

SNMP must be enabled on the Synology NAS:

1. Log into DSM at http://192.168.20.31:5000
2. Go to **Control Panel** → **Terminal & SNMP** → **SNMP** tab
3. Enable **SNMPv1, SNMPv2c service**
4. Set Community: `homelab`
5. Click **Apply**

### Verification

```bash
# Test SNMP connectivity
curl "http://192.168.40.10:9116/snmp?target=192.168.20.31&module=synology"

# Check Prometheus target
curl -s http://192.168.40.10:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="synology")'
```

### Dashboard URLs

| Dashboard | URL |
|-----------|-----|
| Grafana (full) | https://grafana.hrmsmrflrii.xyz/d/synology-nas/synology-nas |
| Grafana (kiosk) | http://192.168.40.10:3030/d/synology-nas/synology-nas?kiosk |
| Glance (embedded) | https://glance.hrmsmrflrii.xyz → Storage page |

## Related Documentation

- [Services](./SERVICES.md) - Service deployment details
- [Networking](./NETWORKING.md) - Service URLs and routing
- [Forward Auth Setup](./FORWARD_AUTH_SETUP.md) - Authentik SSO configuration
- [Ansible](./ANSIBLE.md) - Playbook documentation
