#!/usr/bin/env python3
"""
Configures Traefik reverse proxy for the service.
Location: /opt/gitlab-runner/scripts/configure_traefik.py
"""

import sys
import yaml
import subprocess
import tempfile
import os

TRAEFIK_HOST = "192.168.40.20"
TRAEFIK_USER = "hermes-admin"
TRAEFIK_CONFIG = "/opt/traefik/config/dynamic/services.yml"
SSH_KEY = os.environ.get('SSH_KEY_PATH', '/home/gitlab-runner/.ssh/homelab_ed25519')


def run_ssh_command(command: str) -> str:
    """Run a command via SSH on Traefik host."""
    result = subprocess.run(
        ['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
         f'{TRAEFIK_USER}@{TRAEFIK_HOST}', command],
        capture_output=True, text=True, check=True
    )
    return result.stdout


def configure_traefik(service_file: str):
    """Add service to Traefik dynamic configuration."""
    with open(service_file, 'r') as f:
        config = yaml.safe_load(f)

    if not config.get('traefik', {}).get('enabled', True):
        print("Traefik configuration disabled, skipping...")
        return

    service = config['service']
    deployment = config['deployment']
    traefik = config.get('traefik', {})
    authentik = config.get('authentik', {})

    service_name = service['name']
    domain = traefik.get('domain', f"{service_name}.hrmsmrflrii.xyz")
    backend_url = f"http://{deployment['target_ip']}:{deployment['port']}"

    # Read current Traefik config
    current_yaml = run_ssh_command(f'cat {TRAEFIK_CONFIG}')
    current_config = yaml.safe_load(current_yaml)

    # Backup current config
    with open('traefik_backup.yml', 'w') as f:
        f.write(current_yaml)
    print("Created backup: traefik_backup.yml")

    # Ensure structure exists
    if 'http' not in current_config:
        current_config['http'] = {}
    if 'routers' not in current_config['http']:
        current_config['http']['routers'] = {}
    if 'services' not in current_config['http']:
        current_config['http']['services'] = {}

    # Add router
    router_config = {
        'rule': f'Host(`{domain}`)',
        'service': service_name,
        'entryPoints': traefik.get('entrypoints', ['websecure']),
        'tls': {
            'certResolver': 'letsencrypt'
        }
    }

    # Add Authentik middleware if SSO enabled
    if authentik.get('enabled') and authentik.get('method') == 'forward_auth':
        router_config['middlewares'] = ['authentik']

    current_config['http']['routers'][service_name] = router_config

    # Add service
    current_config['http']['services'][service_name] = {
        'loadBalancer': {
            'servers': [{'url': backend_url}]
        }
    }

    # Write updated config
    updated_yaml = yaml.dump(current_config, default_flow_style=False, sort_keys=False)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write(updated_yaml)
        temp_file = f.name

    # Upload to Traefik host
    subprocess.run(
        ['scp', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
         temp_file, f'{TRAEFIK_USER}@{TRAEFIK_HOST}:{TRAEFIK_CONFIG}'],
        check=True
    )
    os.unlink(temp_file)

    print(f"Traefik configured for {service_name}")
    print(f"  Domain: {domain}")
    print(f"  Backend: {backend_url}")
    print("Traefik will auto-reload configuration")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: configure_traefik.py <service.yml>")
        sys.exit(1)
    configure_traefik(sys.argv[1])
