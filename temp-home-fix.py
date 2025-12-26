import yaml

with open("/opt/glance/config/glance.yml", "r") as f:
    config = yaml.safe_load(f)

# Enhanced Home page with comprehensive monitoring
home_page = {
    "name": "Home",
    "columns": [
        {
            "size": "small",
            "widgets": [
                {
                    "type": "clock",
                    "hour-format": "24h",
                    "timezone": "Asia/Manila"
                },
                {
                    "type": "weather",
                    "location": "Manila, Philippines",
                    "units": "metric",
                    "hour-format": "24h"
                },
                {
                    "type": "calendar",
                    "first-day-of-week": "monday"
                },
                {
                    "type": "bookmarks",
                    "title": "Infrastructure",
                    "groups": [
                        {
                            "title": "Management",
                            "links": [
                                {"title": "Authentik", "url": "https://auth.hrmsmrflrii.xyz", "icon": "si:authentik"},
                                {"title": "Omada Cloud", "url": "https://omada.tplinkcloud.com", "icon": "si:tplink"},
                                {"title": "Proxmox", "url": "https://proxmox.hrmsmrflrii.xyz", "icon": "si:proxmox"},
                                {"title": "Traefik", "url": "https://traefik.hrmsmrflrii.xyz", "icon": "si:traefikproxy"},
                                {"title": "OPNsense", "url": "https://192.168.91.30", "icon": "si:opnsense"},
                                {"title": "Portainer", "url": "https://portainer.hrmsmrflrii.xyz", "icon": "si:portainer"},
                                {"title": "Synology NAS", "url": "https://192.168.10.31:5001", "icon": "si:synology"}
                            ]
                        }
                    ]
                },
                {
                    "type": "bookmarks",
                    "title": "Services",
                    "groups": [
                        {
                            "title": "Media",
                            "links": [
                                {"title": "Jellyfin", "url": "https://jellyfin.hrmsmrflrii.xyz", "icon": "si:jellyfin"},
                                {"title": "Radarr", "url": "https://radarr.hrmsmrflrii.xyz", "icon": "si:radarr"},
                                {"title": "Sonarr", "url": "https://sonarr.hrmsmrflrii.xyz", "icon": "si:sonarr"},
                                {"title": "Lidarr", "url": "https://lidarr.hrmsmrflrii.xyz", "icon": "si:lidarr"},
                                {"title": "Prowlarr", "url": "https://prowlarr.hrmsmrflrii.xyz", "icon": "si:prowlarr"},
                                {"title": "Bazarr", "url": "https://bazarr.hrmsmrflrii.xyz", "icon": "si:bazarr"},
                                {"title": "Jellyseerr", "url": "https://jellyseerr.hrmsmrflrii.xyz", "icon": "si:jellyseerr"},
                                {"title": "Tdarr", "url": "https://tdarr.hrmsmrflrii.xyz", "icon": "si:tdarr"}
                            ]
                        },
                        {
                            "title": "Downloads",
                            "links": [
                                {"title": "Deluge", "url": "https://deluge.hrmsmrflrii.xyz", "icon": "si:deluge"},
                                {"title": "SABnzbd", "url": "https://sabnzbd.hrmsmrflrii.xyz", "icon": "si:sabnzbd"}
                            ]
                        },
                        {
                            "title": "Productivity",
                            "links": [
                                {"title": "GitLab", "url": "https://gitlab.hrmsmrflrii.xyz", "icon": "si:gitlab"},
                                {"title": "Immich", "url": "https://photos.hrmsmrflrii.xyz", "icon": "si:immich"},
                                {"title": "n8n", "url": "https://n8n.hrmsmrflrii.xyz", "icon": "si:n8n"},
                                {"title": "Paperless", "url": "https://paperless.hrmsmrflrii.xyz", "icon": "si:paperlessngx"}
                            ]
                        },
                        {
                            "title": "Monitoring",
                            "links": [
                                {"title": "Uptime Kuma", "url": "https://uptime.hrmsmrflrii.xyz", "icon": "si:uptimekuma"},
                                {"title": "Prometheus", "url": "https://prometheus.hrmsmrflrii.xyz", "icon": "si:prometheus"},
                                {"title": "Grafana", "url": "https://grafana.hrmsmrflrii.xyz", "icon": "si:grafana"},
                                {"title": "Jaeger", "url": "https://jaeger.hrmsmrflrii.xyz", "icon": "si:jaeger"},
                                {"title": "Speedtest", "url": "https://speedtest.hrmsmrflrii.xyz", "icon": "si:speedtest"}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "size": "full",
            "widgets": [
                {
                    "type": "custom-api",
                    "title": "Hermes Miraflor II Life Progress",
                    "cache": "1h",
                    "url": "http://192.168.40.10:5051/progress",
                    "template": '''<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 10px;">
  <div style="text-align: center; margin-bottom: 15px;">
    <span style="color: #f87171; font-weight: 600; font-size: 18px;">{{ .JSON.Int "remaining_days" | formatNumber }}</span>
    <span style="color: #888; font-size: 14px;"> days remaining until age {{ .JSON.Int "target_age" }}</span>
  </div>
  <div style="display: flex; align-items: center; margin-bottom: 12px;">
    <span style="width: 60px; font-weight: bold; color: #f87171;">Year</span>
    <div style="flex: 1; height: 24px; background: #333; border-radius: 4px; position: relative; margin: 0 15px; overflow: hidden;">
      <div style="width: {{ .JSON.Float "year" }}%; height: 100%; background: linear-gradient(90deg, #ef4444, #f87171); border-radius: 4px;"></div>
    </div>
    <span style="width: 50px; text-align: right; font-weight: 500;">{{ .JSON.Float "year" | printf "%.0f" }}%</span>
  </div>
  <div style="display: flex; align-items: center; margin-bottom: 12px;">
    <span style="width: 60px; font-weight: bold; color: #facc15;">Month</span>
    <div style="flex: 1; height: 24px; background: #333; border-radius: 4px; position: relative; margin: 0 15px; overflow: hidden;">
      <div style="width: {{ .JSON.Float "month" }}%; height: 100%; background: linear-gradient(90deg, #eab308, #facc15); border-radius: 4px;"></div>
    </div>
    <span style="width: 50px; text-align: right; font-weight: 500;">{{ .JSON.Float "month" | printf "%.0f" }}%</span>
  </div>
  <div style="display: flex; align-items: center; margin-bottom: 12px;">
    <span style="width: 60px; font-weight: bold; color: #4ade80;">Day</span>
    <div style="flex: 1; height: 24px; background: #333; border-radius: 4px; position: relative; margin: 0 15px; overflow: hidden;">
      <div style="width: {{ .JSON.Float "day" }}%; height: 100%; background: linear-gradient(90deg, #22c55e, #4ade80); border-radius: 4px;"></div>
    </div>
    <span style="width: 50px; text-align: right; font-weight: 500;">{{ .JSON.Float "day" | printf "%.0f" }}%</span>
  </div>
  <div style="display: flex; align-items: center; margin-bottom: 15px;">
    <span style="width: 60px; font-weight: bold; color: #4ade80;">Life</span>
    <div style="flex: 1; height: 24px; background: #333; border-radius: 4px; position: relative; margin: 0 15px; overflow: hidden;">
      <div style="width: {{ .JSON.Float "life" }}%; height: 100%; background: linear-gradient(90deg, #22c55e, #4ade80); border-radius: 4px;"></div>
    </div>
    <span style="width: 50px; text-align: right; font-weight: 500;">{{ .JSON.Float "life" | printf "%.0f" }}%</span>
  </div>
  <div style="text-align: center; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px;">
    <em style="color: #aaa; font-size: 13px; line-height: 1.5;">"{{ .JSON.String "quote" }}"</em>
  </div>
</div>'''
                },
                {
                    "type": "custom-api",
                    "title": "GitHub Contributions",
                    "cache": "6h",
                    "url": "https://api.github.com/users/herms14",
                    "template": '''<div style="text-align: center; padding: 10px;">
  <img src="https://ghchart.rshah.org/40c463/herms14" alt="GitHub Contributions" style="width: 100%; border-radius: 8px; filter: invert(1) hue-rotate(180deg);">
  <div style="margin-top: 10px; color: #a6adc8; font-size: 12px;">
    <span style="color: #a6e3a1; font-weight: bold;">{{ .JSON.Int "public_repos" }}</span> repos |
    <span style="color: #89b4fa; font-weight: bold;">{{ .JSON.Int "followers" }}</span> followers |
    <span style="color: #fab387; font-weight: bold;">{{ .JSON.Int "following" }}</span> following
  </div>
</div>'''
                },
                {
                    "type": "monitor",
                    "title": "Proxmox Cluster",
                    "cache": "1m",
                    "sites": [
                        {"title": "Node 01", "url": "https://192.168.20.20:8006", "icon": "si:proxmox", "allow-insecure": True},
                        {"title": "Node 02", "url": "https://192.168.20.21:8006", "icon": "si:proxmox", "allow-insecure": True},
                        {"title": "Node 03", "url": "https://192.168.20.22:8006", "icon": "si:proxmox", "allow-insecure": True}
                    ]
                },
                {
                    "type": "monitor",
                    "title": "Storage",
                    "cache": "1m",
                    "sites": [
                        {"title": "Synology NAS (VLAN 20)", "url": "https://192.168.20.31:5001", "icon": "si:synology", "allow-insecure": True},
                        {"title": "Synology NAS (VLAN 10)", "url": "https://192.168.10.31:5001", "icon": "si:synology", "allow-insecure": True}
                    ]
                },
                {
                    "type": "monitor",
                    "title": "Core Services",
                    "cache": "1m",
                    "sites": [
                        {"title": "Traefik", "url": "http://192.168.40.20:8082/ping", "icon": "si:traefikproxy"},
                        {"title": "Authentik", "url": "http://192.168.40.21:9000/-/health/ready/", "icon": "si:authentik"},
                        {"title": "GitLab", "url": "http://192.168.40.23:80", "icon": "si:gitlab"},
                        {"title": "Immich", "url": "http://192.168.40.22:2283", "icon": "si:immich"},
                        {"title": "n8n", "url": "http://192.168.40.10:5678/healthz", "icon": "si:n8n"},
                        {"title": "Paperless", "url": "http://192.168.40.10:8000", "icon": "si:paperlessngx"}
                    ]
                },
                {
                    "type": "monitor",
                    "title": "Media Services",
                    "cache": "1m",
                    "sites": [
                        {"title": "Jellyfin", "url": "http://192.168.40.11:8096/health", "icon": "si:jellyfin"},
                        {"title": "Radarr", "url": "http://192.168.40.11:7878/ping", "icon": "si:radarr"},
                        {"title": "Sonarr", "url": "http://192.168.40.11:8989/ping", "icon": "si:sonarr"},
                        {"title": "Lidarr", "url": "http://192.168.40.11:8686/ping", "icon": "si:lidarr"},
                        {"title": "Prowlarr", "url": "http://192.168.40.11:9696/ping", "icon": "si:prowlarr"},
                        {"title": "Bazarr", "url": "http://192.168.40.11:6767/ping", "icon": "si:bazarr"},
                        {"title": "Jellyseerr", "url": "http://192.168.40.11:5055", "icon": "si:jellyseerr"},
                        {"title": "Tdarr", "url": "http://192.168.40.11:8265", "icon": "si:tdarr"},
                        {"title": "Deluge", "url": "http://192.168.40.11:8112", "icon": "si:deluge"},
                        {"title": "SABnzbd", "url": "http://192.168.40.11:8081", "icon": "si:sabnzbd"}
                    ]
                },
                {
                    "type": "monitor",
                    "title": "Monitoring Stack",
                    "cache": "1m",
                    "sites": [
                        {"title": "Uptime Kuma", "url": "http://192.168.40.10:3001", "icon": "si:uptimekuma"},
                        {"title": "Prometheus", "url": "http://192.168.40.10:9090/-/healthy", "icon": "si:prometheus"},
                        {"title": "Grafana", "url": "http://192.168.40.10:3030/api/health", "icon": "si:grafana"},
                        {"title": "Jaeger", "url": "http://192.168.40.10:16686", "icon": "si:jaeger"},
                        {"title": "Glance", "url": "http://192.168.40.10:8080", "icon": "mdi:view-dashboard"},
                        {"title": "Speedtest", "url": "http://192.168.40.10:3000", "icon": "si:speedtest"}
                    ]
                },
                {
                    "type": "monitor",
                    "title": "Kubernetes Control Plane",
                    "cache": "1m",
                    "sites": [
                        {"title": "Controller 01", "url": "https://192.168.20.32:6443/healthz", "icon": "si:kubernetes", "allow-insecure": True},
                        {"title": "Controller 02", "url": "https://192.168.20.33:6443/healthz", "icon": "si:kubernetes", "allow-insecure": True},
                        {"title": "Controller 03", "url": "https://192.168.20.34:6443/healthz", "icon": "si:kubernetes", "allow-insecure": True}
                    ]
                },
                {
                    "type": "monitor",
                    "title": "Kubernetes Workers",
                    "cache": "1m",
                    "sites": [
                        {"title": "Worker 01", "url": "http://192.168.20.40:10248/healthz", "icon": "si:kubernetes"},
                        {"title": "Worker 02", "url": "http://192.168.20.41:10248/healthz", "icon": "si:kubernetes"},
                        {"title": "Worker 03", "url": "http://192.168.20.42:10248/healthz", "icon": "si:kubernetes"},
                        {"title": "Worker 04", "url": "http://192.168.20.43:10248/healthz", "icon": "si:kubernetes"},
                        {"title": "Worker 05", "url": "http://192.168.20.44:10248/healthz", "icon": "si:kubernetes"},
                        {"title": "Worker 06", "url": "http://192.168.20.45:10248/healthz", "icon": "si:kubernetes"}
                    ]
                }
            ]
        },
        {
            "size": "small",
            "widgets": [
                {
                    "type": "markets",
                    "title": "Crypto",
                    "markets": [
                        {"symbol": "BTC-USD", "name": "Bitcoin"},
                        {"symbol": "ETH-USD", "name": "Ethereum"},
                        {"symbol": "XRP-USD", "name": "XRP"},
                        {"symbol": "BNB-USD", "name": "BNB"},
                        {"symbol": "ADA-USD", "name": "Cardano"}
                    ]
                },
                {
                    "type": "markets",
                    "title": "Stocks",
                    "markets": [
                        {"symbol": "MSFT", "name": "Microsoft"},
                        {"symbol": "AAPL", "name": "Apple"},
                        {"symbol": "ORCL", "name": "Oracle"},
                        {"symbol": "NVDA", "name": "Nvidia"},
                        {"symbol": "GOOGL", "name": "Google"},
                        {"symbol": "TSLA", "name": "Tesla"},
                        {"symbol": "NFLX", "name": "Netflix"},
                        {"symbol": "AMZN", "name": "Amazon"}
                    ]
                },
                {
                    "type": "rss",
                    "title": "Tech News",
                    "style": "horizontal-cards",
                    "feeds": [
                        {"url": "https://www.reddit.com/r/homelab/.rss", "title": "r/homelab"},
                        {"url": "https://www.reddit.com/r/selfhosted/.rss", "title": "r/selfhosted"}
                    ],
                    "limit": 5
                }
            ]
        }
    ]
}

# Update the Home page
for i, page in enumerate(config["pages"]):
    if page.get("name") == "Home":
        config["pages"][i] = home_page
        break

with open("/opt/glance/config/glance.yml", "w") as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False, indent=2)

print("Home page updated with calendar, NAS monitoring, and split Kubernetes sections")
