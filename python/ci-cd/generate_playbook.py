#!/usr/bin/env python3
"""
Generates Ansible playbook from service definition.
Location: /opt/gitlab-runner/scripts/generate_playbook.py
"""

import sys
import yaml
import json


def generate_compose_content(service_name, deployment, env_vars):
    """Generate docker-compose.yml content as a string."""
    compose = {
        'name': service_name,
        'services': {
            service_name: {
                'image': deployment['image'],
                'container_name': service_name,
                'restart': deployment.get('restart_policy', 'unless-stopped'),
                'ports': [
                    f"{deployment['port']}:{deployment['container_port']}"
                ],
                'environment': env_vars
            }
        }
    }

    # Add volumes if specified
    if deployment.get('volumes'):
        compose['services'][service_name]['volumes'] = deployment['volumes']

    return yaml.dump(compose, default_flow_style=False)


def generate_playbook(service_file: str, output_file: str):
    """Generate deployment playbook from service definition."""
    with open(service_file, 'r') as f:
        config = yaml.safe_load(f)

    service = config['service']
    deployment = config['deployment']

    # Build environment vars
    env_vars = deployment.get('environment', {'TZ': 'America/New_York'})

    # Generate compose content
    compose_content = generate_compose_content(
        service['name'], deployment, env_vars
    )

    # Build the playbook
    playbook = [{
        'name': f"Deploy {service['display_name']}",
        'hosts': deployment['target_host'],
        'become': True,
        'vars': {
            'service_name': service['name'],
            'service_path': deployment.get('install_path', f"/opt/{service['name']}"),
            'service_port': deployment['port'],
            'healthcheck_path': deployment.get('healthcheck_path', '/'),
            'healthcheck_status': deployment.get('healthcheck_status', [200, 301, 302])
        },
        'tasks': [
            {
                'name': 'Create service directories',
                'ansible.builtin.file': {
                    'path': '{{ item }}',
                    'state': 'directory',
                    'mode': '0755'
                },
                'loop': [
                    '{{ service_path }}',
                    '{{ service_path }}/config',
                    '{{ service_path }}/data'
                ]
            },
            {
                'name': 'Create Docker Compose file',
                'ansible.builtin.copy': {
                    'dest': '{{ service_path }}/docker-compose.yml',
                    'content': compose_content,
                    'mode': '0644'
                }
            },
            {
                'name': 'Deploy container',
                'community.docker.docker_compose_v2': {
                    'project_src': '{{ service_path }}',
                    'state': 'present',
                    'pull': 'always'
                }
            },
            {
                'name': 'Wait for service to be ready',
                'ansible.builtin.uri': {
                    'url': f"http://localhost:{{{{ service_port }}}}{{{{ healthcheck_path }}}}",
                    'status_code': '{{ healthcheck_status }}'
                },
                'register': 'service_status',
                'until': 'service_status.status in healthcheck_status',
                'retries': 30,
                'delay': 2,
                'ignore_errors': True
            },
            {
                'name': 'Display deployment info',
                'ansible.builtin.debug': {
                    'msg': [
                        f"{service['display_name']} deployed successfully!",
                        f"Internal: http://{deployment['target_ip']}:{deployment['port']}",
                        f"External: https://{config.get('traefik', {}).get('domain', service['name'] + '.hrmsmrflrii.xyz')}"
                    ]
                }
            }
        ]
    }]

    with open(output_file, 'w') as f:
        yaml.dump(playbook, f, default_flow_style=False, sort_keys=False)

    print(f"Generated playbook: {output_file}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: generate_playbook.py <service.yml> <output.yml>")
        sys.exit(1)
    generate_playbook(sys.argv[1], sys.argv[2])
