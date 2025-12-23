#!/usr/bin/env python3
"""
Registers service with Watchtower/Update Manager.
Location: /opt/gitlab-runner/scripts/register_watchtower.py
"""

import sys
import yaml
import subprocess
import re
import os

UPDATE_MANAGER_HOST = "192.168.40.10"
UPDATE_MANAGER_USER = "hermes-admin"
UPDATE_MANAGER_FILE = "/opt/update-manager/update_manager.py"
SSH_KEY = os.environ.get('SSH_KEY_PATH', '/home/gitlab-runner/.ssh/homelab_ed25519')


def run_ssh_command(command: str, check: bool = True) -> str:
    """Run a command via SSH on Update Manager host."""
    result = subprocess.run(
        ['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
         f'{UPDATE_MANAGER_USER}@{UPDATE_MANAGER_HOST}', command],
        capture_output=True, text=True, check=check
    )
    return result.stdout


def register_watchtower(service_file: str):
    """Add service to Update Manager CONTAINER_HOSTS dict."""
    with open(service_file, 'r') as f:
        config = yaml.safe_load(f)

    if not config.get('watchtower', {}).get('enabled', True):
        print("Watchtower registration disabled, skipping...")
        return

    service = config['service']
    deployment = config['deployment']
    watchtower = config.get('watchtower', {})

    container_name = watchtower.get('container_name', service['name'])
    host_ip = deployment['target_ip']

    # Read current Update Manager script
    content = run_ssh_command(f'cat {UPDATE_MANAGER_FILE}')

    # Check if container already registered
    if f'"{container_name}"' in content:
        print(f"Container {container_name} already registered with Update Manager")
        return

    # Find CONTAINER_HOSTS dict and add new entry
    # Pattern to match the CONTAINER_HOSTS dict
    pattern = r'(CONTAINER_HOSTS\s*=\s*\{[^}]*)(})'

    # Add new entry before closing brace
    new_entry = f'    "{container_name}": "{host_ip}",\n'

    if re.search(pattern, content, flags=re.DOTALL):
        updated_content = re.sub(
            pattern,
            r'\1' + new_entry + r'\2',
            content,
            flags=re.DOTALL
        )

        # Write updated file using heredoc
        # Escape special characters for shell
        escaped_content = updated_content.replace("'", "'\"'\"'")

        write_cmd = f"cat > {UPDATE_MANAGER_FILE} << 'EOFPYTHON'\n{updated_content}\nEOFPYTHON"
        run_ssh_command(write_cmd)

        print(f"Registered {container_name} ({host_ip}) with Update Manager")

        # Rebuild Update Manager container
        print("Rebuilding Update Manager container...")
        run_ssh_command(
            'cd /opt/update-manager && sudo docker compose build --no-cache && sudo docker compose up -d',
            check=False
        )
        print("Update Manager rebuilt")
    else:
        print("WARNING: Could not find CONTAINER_HOSTS dict in update_manager.py")
        print(f"Please manually add: \"{container_name}\": \"{host_ip}\"")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: register_watchtower.py <service.yml>")
        sys.exit(1)
    register_watchtower(sys.argv[1])
