#!/usr/bin/env python3
"""
Restores Traefik configuration from backup.
Location: /opt/gitlab-runner/scripts/rollback_traefik.py
"""

import sys
import subprocess
import os

TRAEFIK_HOST = "192.168.40.20"
TRAEFIK_USER = "hermes-admin"
TRAEFIK_CONFIG = "/opt/traefik/config/dynamic/services.yml"
SSH_KEY = os.environ.get('SSH_KEY_PATH', '/home/gitlab-runner/.ssh/homelab_ed25519')


def rollback_traefik(backup_file: str):
    """Restore Traefik config from backup file."""
    if not os.path.exists(backup_file):
        print(f"Backup file not found: {backup_file}")
        sys.exit(1)

    # Upload backup to Traefik host
    subprocess.run(
        ['scp', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
         backup_file, f'{TRAEFIK_USER}@{TRAEFIK_HOST}:{TRAEFIK_CONFIG}'],
        check=True
    )

    print("Traefik configuration restored from backup")
    print("Traefik will auto-reload")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: rollback_traefik.py <backup_file>")
        sys.exit(1)
    rollback_traefik(sys.argv[1])
