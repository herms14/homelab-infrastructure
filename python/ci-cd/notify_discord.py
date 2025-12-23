#!/usr/bin/env python3
"""
Sends Discord notifications for pipeline events.
Location: /opt/gitlab-runner/scripts/notify_discord.py

Also triggers onboarding status check after successful deployments.
"""

import sys
import yaml
import json
import requests
import argparse
import os
from datetime import datetime

# Discord webhook URL from environment
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', '')

# Update Manager endpoint for onboarding checks
UPDATE_MANAGER_URL = os.environ.get('UPDATE_MANAGER_URL', 'http://192.168.40.10:5050')

COLORS = {
    'success': 3066993,   # Green
    'failure': 15158332,  # Red
    'info': 3447003       # Blue
}


def send_notification(args):
    """Send Discord notification."""
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL not set, skipping notification")
        return

    with open(args.service_file, 'r') as f:
        config = yaml.safe_load(f)

    if not config.get('notifications', {}).get('discord', {}).get('enabled', True):
        print("Discord notifications disabled")
        return

    service = config['service']
    traefik = config.get('traefik', {})

    status = args.status
    color = COLORS.get(status, COLORS['info'])

    if status == 'success':
        title = f":white_check_mark: Service Deployed: {service['display_name']}"
        description = f"**{service['name']}** has been successfully deployed!"
        fields = [
            {
                'name': ':globe_with_meridians: Service URL',
                'value': f"https://{traefik.get('domain', service['name'] + '.hrmsmrflrii.xyz')}",
                'inline': True
            },
            {
                'name': ':link: Pipeline',
                'value': f"[View]({args.pipeline_url})",
                'inline': True
            },
            {
                'name': ':hash: Commit',
                'value': args.commit[:8] if args.commit else 'N/A',
                'inline': True
            },
            {
                'name': ':bust_in_silhouette: Author',
                'value': args.author or 'N/A',
                'inline': True
            }
        ]
    else:
        title = f":x: Deployment Failed: {service['display_name']}"
        description = f"Failed to deploy **{service['name']}**"
        fields = [
            {
                'name': ':warning: Failed Job',
                'value': args.failed_job or 'Unknown',
                'inline': True
            },
            {
                'name': ':link: Pipeline',
                'value': f"[View]({args.pipeline_url})",
                'inline': True
            },
            {
                'name': ':hash: Commit',
                'value': args.commit[:8] if args.commit else 'N/A',
                'inline': True
            },
            {
                'name': ':bust_in_silhouette: Author',
                'value': args.author or 'N/A',
                'inline': True
            }
        ]

    payload = {
        'username': 'GitLab CI/CD',
        'avatar_url': 'https://about.gitlab.com/images/press/logo/png/gitlab-icon-rgb.png',
        'embeds': [{
            'title': title,
            'description': description,
            'color': color,
            'fields': fields,
            'footer': {
                'text': 'Homelab Service Onboarding Pipeline'
            },
            'timestamp': datetime.utcnow().isoformat()
        }]
    }

    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)

    if response.status_code in [200, 204]:
        print("Discord notification sent successfully")
    else:
        print(f"Failed to send Discord notification: {response.status_code}")
        print(response.text)

    # Trigger onboarding check for successful deployments
    if status == 'success':
        trigger_onboarding_check(service['name'])


def trigger_onboarding_check(service_name: str):
    """Trigger onboarding status check via Update Manager webhook."""
    try:
        response = requests.post(
            f"{UPDATE_MANAGER_URL}/onboard-check",
            json={'service_name': service_name},
            timeout=30
        )

        if response.status_code == 200:
            print(f"Onboarding check triggered for {service_name}")
        else:
            print(f"Failed to trigger onboarding check: {response.status_code}")
            print(response.text)
    except requests.exceptions.RequestException as e:
        print(f"Error triggering onboarding check: {e}")
        # Don't fail the pipeline if onboarding check fails
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--service-file', required=True)
    parser.add_argument('--status', required=True, choices=['success', 'failure'])
    parser.add_argument('--pipeline-url', default='N/A')
    parser.add_argument('--commit', default='')
    parser.add_argument('--author', default='')
    parser.add_argument('--failed-job', default=None)

    args = parser.parse_args()
    send_notification(args)
