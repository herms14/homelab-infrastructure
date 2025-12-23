# Configuration Files

Service configuration files for the homelab stack.

## Directory Structure

```
configs/
├── glance/          # Glance dashboard
│   ├── glance.yml   # Main configuration
│   └── custom-themes.css  # Custom styling
├── traefik/         # Traefik proxy
│   ├── traefik.yml  # Static configuration
│   └── dynamic/     # Dynamic configuration
│       └── services.yml
└── prometheus/      # Prometheus monitoring
    └── prometheus.yml  # Scrape configuration
```

## Glance Dashboard

### glance.yml
Main configuration file defining:
- Pages and columns
- Widget configurations
- Embedded iframes (Grafana, services)
- Theme settings

### custom-themes.css
Custom styling for:
- Theme colors and variants
- Iframe scrollbar hiding
- Component customization

## Traefik

### traefik.yml
Static configuration:
- Entry points (http, https, ping)
- Certificate resolvers (Let's Encrypt)
- Providers (file, docker)
- OpenTelemetry tracing

### dynamic/services.yml
Dynamic configuration:
- Service routers
- Middlewares (auth, headers)
- TLS certificates

## Prometheus

### prometheus.yml
Scrape configuration:
- Target definitions
- Job configurations
- Scrape intervals

### Scrape Targets

| Job | Target | Metrics |
|-----|--------|---------|
| prometheus | localhost:9090 | Self metrics |
| traefik | 192.168.40.20:8082 | Proxy metrics |
| docker-stats-utilities | 192.168.40.10:9417 | Container metrics |
| docker-stats-media | 192.168.40.11:9417 | Container metrics |
| synology | 192.168.20.31 (via SNMP) | NAS metrics |
| otel-collector | 192.168.40.10:8888 | Tracing metrics |

## Deployment

Copy configs to appropriate locations:

```bash
# Glance
scp -r glance/* hermes-admin@192.168.40.10:/opt/glance/config/

# Traefik
scp -r traefik/* hermes-admin@192.168.40.20:/opt/traefik/config/

# Prometheus
scp prometheus/prometheus.yml hermes-admin@192.168.40.10:/opt/monitoring/prometheus/
```

Restart services after configuration changes:

```bash
docker restart glance
docker restart traefik
docker restart prometheus
```
