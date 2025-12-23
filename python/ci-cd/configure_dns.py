#!/usr/bin/env python3
"""
Configures DNS record in OPNsense.
Location: /opt/gitlab-runner/scripts/configure_dns.py
"""

import sys
import yaml
import os
import requests
import urllib3

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

OPNSENSE_URL = "https://192.168.91.30"
OPNSENSE_API_KEY = os.environ.get('OPNSENSE_API_KEY', '')
OPNSENSE_API_SECRET = os.environ.get('OPNSENSE_API_SECRET', '')
DOMAIN = "hrmsmrflrii.xyz"


def configure_dns(service_file: str):
    """Add DNS record to OPNsense Unbound."""
    with open(service_file, 'r') as f:
        config = yaml.safe_load(f)

    if not config.get('dns', {}).get('enabled', True):
        print("DNS configuration disabled, skipping...")
        return

    dns = config.get('dns', {})
    service_name = config['service']['name']

    hostname = dns.get('hostname', service_name)
    ip = dns.get('ip', '192.168.40.20')  # Default to Traefik

    if not OPNSENSE_API_KEY or not OPNSENSE_API_SECRET:
        print("WARNING: OPNsense API credentials not set")
        print(f"Please manually add DNS record:")
        print(f"  Hostname: {hostname}")
        print(f"  Domain: {DOMAIN}")
        print(f"  IP: {ip}")
        return

    auth = (OPNSENSE_API_KEY, OPNSENSE_API_SECRET)

    # Check if record already exists
    response = requests.get(
        f"{OPNSENSE_URL}/api/unbound/settings/searchHostOverride",
        auth=auth,
        verify=False
    )

    if response.status_code == 200:
        for row in response.json().get('rows', []):
            if row.get('hostname') == hostname and row.get('domain') == DOMAIN:
                print(f"DNS record for {hostname}.{DOMAIN} already exists")
                return

    # Add new record
    record_data = {
        'host': {
            'enabled': '1',
            'hostname': hostname,
            'domain': DOMAIN,
            'server': ip,
            'description': f'Auto-created for {service_name}'
        }
    }

    response = requests.post(
        f"{OPNSENSE_URL}/api/unbound/settings/addHostOverride",
        auth=auth,
        json=record_data,
        verify=False
    )

    if response.status_code == 200:
        result = response.json()
        if result.get('result') == 'saved':
            print(f"DNS record created: {hostname}.{DOMAIN} -> {ip}")

            # Apply changes
            requests.post(
                f"{OPNSENSE_URL}/api/unbound/service/reconfigure",
                auth=auth,
                verify=False
            )
            print("DNS changes applied")
        else:
            print(f"Failed to create DNS record: {result}")
            sys.exit(1)
    else:
        print(f"DNS API error: {response.status_code}")
        print(response.text)
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: configure_dns.py <service.yml>")
        sys.exit(1)
    configure_dns(sys.argv[1])
