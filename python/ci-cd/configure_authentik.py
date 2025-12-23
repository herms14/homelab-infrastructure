#!/usr/bin/env python3
"""
Configures Authentik SSO for the service.
Location: /opt/gitlab-runner/scripts/configure_authentik.py
"""

import sys
import yaml
import requests
import os

AUTHENTIK_URL = "http://192.168.40.21:9000"
AUTHENTIK_TOKEN = os.environ.get('AUTHENTIK_TOKEN', '')


def configure_authentik(service_file: str):
    """Configure Authentik application and provider."""
    with open(service_file, 'r') as f:
        config = yaml.safe_load(f)

    authentik = config.get('authentik', {})

    if not authentik.get('enabled', False):
        print("Authentik SSO disabled, skipping...")
        return

    if not AUTHENTIK_TOKEN:
        print("WARNING: AUTHENTIK_TOKEN not set")
        print("Please configure Authentik SSO manually")
        return

    service = config['service']
    traefik = config.get('traefik', {})

    service_name = service['name']
    display_name = service['display_name']
    domain = traefik.get('domain', f"{service_name}.hrmsmrflrii.xyz")
    method = authentik.get('method', 'forward_auth')

    headers = {
        'Authorization': f'Bearer {AUTHENTIK_TOKEN}',
        'Content-Type': 'application/json'
    }

    if method == 'forward_auth':
        # Create proxy provider for forward auth
        provider_data = {
            'name': f'{service_name}-provider',
            'authorization_flow': authentik.get(
                'authorization_flow',
                'default-provider-authorization-implicit-consent'
            ),
            'external_host': f'https://{domain}',
            'mode': 'forward_single'
        }

        response = requests.post(
            f'{AUTHENTIK_URL}/api/v3/providers/proxy/',
            headers=headers,
            json=provider_data
        )

        if response.status_code == 201:
            provider_id = response.json()['pk']
            print(f"Created proxy provider: {provider_id}")
        elif response.status_code == 400:
            # Provider might already exist
            print(f"Provider may already exist: {response.json()}")
            return
        else:
            print(f"Provider creation failed: {response.status_code}")
            print(response.text)
            return

        # Create application
        app_data = {
            'name': display_name,
            'slug': service_name,
            'provider': provider_id,
            'meta_launch_url': f'https://{domain}'
        }

        response = requests.post(
            f'{AUTHENTIK_URL}/api/v3/core/applications/',
            headers=headers,
            json=app_data
        )

        if response.status_code == 201:
            print(f"Created application: {service_name}")
        else:
            print(f"Application creation failed: {response.status_code}")
            print(response.text)
            return

        # Get traefik-outpost
        response = requests.get(
            f'{AUTHENTIK_URL}/api/v3/outposts/instances/',
            headers=headers,
            params={'name__icontains': 'traefik'}
        )

        if response.status_code == 200 and response.json().get('results'):
            outpost = response.json()['results'][0]
            outpost_id = outpost['pk']
            current_providers = [p for p in outpost.get('providers', [])]
            current_providers.append(provider_id)

            # Update outpost with new provider
            response = requests.patch(
                f'{AUTHENTIK_URL}/api/v3/outposts/instances/{outpost_id}/',
                headers=headers,
                json={'providers': current_providers}
            )

            if response.status_code == 200:
                print(f"Added {service_name} to traefik-outpost")
            else:
                print(f"Outpost update failed: {response.status_code}")
        else:
            print("WARNING: traefik-outpost not found")
            print("Please manually add the application to the outpost")

        print(f"Authentik SSO configured for {service_name}")
        print("Note: Traefik router already has 'authentik' middleware applied")

    else:
        print(f"SSO method '{method}' requires manual configuration")
        print("Please configure native OIDC in the application settings")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: configure_authentik.py <service.yml>")
        sys.exit(1)
    configure_authentik(sys.argv[1])
