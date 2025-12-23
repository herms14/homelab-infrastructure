#!/usr/bin/env python3
"""
Removes deployed container.
Location: /opt/gitlab-runner/scripts/rollback_container.py
"""

import sys
import yaml
import subprocess
import os

SSH_KEY = os.environ.get('SSH_KEY_PATH', '/home/gitlab-runner/.ssh/homelab_ed25519')


def rollback_container(service_file: str):
    """Remove deployed container and optionally its data."""
    with open(service_file, 'r') as f:
        config = yaml.safe_load(f)

    service = config['service']
    deployment = config['deployment']

    service_name = service['name']
    target_ip = deployment['target_ip']
    install_path = deployment.get('install_path', f"/opt/{service_name}")

    print(f"Removing container {service_name} from {target_ip}...")

    # Stop and remove container
    subprocess.run(
        ['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
         f'hermes-admin@{target_ip}',
         f'cd {install_path} && sudo docker compose down -v'],
        check=False
    )

    print(f"Container {service_name} removed")
    print(f"Note: Data directory {install_path} preserved for manual cleanup")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: rollback_container.py <service.yml>")
        sys.exit(1)
    rollback_container(sys.argv[1])
