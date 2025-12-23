#!/usr/bin/env python3
"""
Validates service definition YAML file.
Location: /opt/gitlab-runner/scripts/validate_service.py
"""

import sys
import yaml
import json
from pathlib import Path

REQUIRED_FIELDS = {
    'service': ['name', 'display_name', 'description'],
    'deployment': ['target_host', 'port', 'container_port', 'image']
}

VALID_HOSTS = [
    'docker-vm-utilities01',
    'docker-vm-media01',
    'traefik-vm01',
    'authentik-vm01',
    'immich-vm01',
    'gitlab-vm01'
]

HOST_IPS = {
    'docker-vm-utilities01': '192.168.40.10',
    'docker-vm-media01': '192.168.40.11',
    'traefik-vm01': '192.168.40.20',
    'authentik-vm01': '192.168.40.21',
    'immich-vm01': '192.168.40.22',
    'gitlab-vm01': '192.168.40.23'
}

def validate_service(file_path: str) -> dict:
    """Validate and parse service definition."""
    with open(file_path, 'r') as f:
        config = yaml.safe_load(f)

    errors = []

    # Validate required sections
    for section, fields in REQUIRED_FIELDS.items():
        if section not in config:
            errors.append(f"Missing required section: {section}")
            continue
        for field in fields:
            if field not in config[section]:
                errors.append(f"Missing required field: {section}.{field}")

    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    # Validate target host
    target_host = config['deployment']['target_host']
    if target_host not in VALID_HOSTS:
        print(f"Invalid target_host: {target_host}")
        print(f"Valid hosts: {', '.join(VALID_HOSTS)}")
        sys.exit(1)

    # Auto-fill target_ip if not provided
    if 'target_ip' not in config['deployment']:
        config['deployment']['target_ip'] = HOST_IPS[target_host]

    # Set defaults
    config.setdefault('traefik', {'enabled': True})
    config.setdefault('dns', {'enabled': True})
    config.setdefault('watchtower', {'enabled': True})
    config.setdefault('authentik', {'enabled': False})
    config.setdefault('notifications', {'discord': {'enabled': True}})

    # Set default subdomain
    if config['traefik'].get('enabled', True):
        config['traefik'].setdefault('subdomain', config['service']['name'])
        config['traefik'].setdefault('domain', f"{config['traefik']['subdomain']}.hrmsmrflrii.xyz")

    # Set default DNS hostname
    if config['dns'].get('enabled', True):
        config['dns'].setdefault('hostname', config['service']['name'])
        config['dns'].setdefault('ip', '192.168.40.20')  # Traefik IP

    # Set default Watchtower container name
    if config['watchtower'].get('enabled', True):
        config['watchtower'].setdefault('container_name', config['service']['name'])

    # Set default install path
    config['deployment'].setdefault('install_path', f"/opt/{config['service']['name']}")

    print("Service definition validated successfully!")
    print(f"  Service: {config['service']['name']}")
    print(f"  Target: {config['deployment']['target_host']} ({config['deployment']['target_ip']})")
    print(f"  Image: {config['deployment']['image']}")
    print(f"  Domain: {config['traefik'].get('domain', 'N/A')}")

    # Write parsed config for other stages
    with open('service_parsed.json', 'w') as f:
        json.dump(config, f, indent=2)

    return config

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: validate_service.py <service.yml>")
        sys.exit(1)
    validate_service(sys.argv[1])
