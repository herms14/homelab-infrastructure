#!/usr/bin/env python3
"""
Service Onboarding Checker Module
Checks if services have all required configurations in place.
Location: /opt/gitlab-runner/scripts/onboarding_checker.py (also used by Update Manager)
"""

import os
import re
import yaml
import subprocess
import requests
import urllib3
from typing import Dict, List, Optional

# Disable SSL warnings for self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class OnboardingChecker:
    """Checks service onboarding status across infrastructure components."""

    def __init__(self, ssh_key_path: str = '/root/.ssh/homelab_ed25519'):
        self.ssh_key_path = ssh_key_path
        self.domain = 'hrmsmrflrii.xyz'

        # API endpoints
        self.opnsense_url = 'https://192.168.91.30'
        self.authentik_url = 'http://192.168.40.21:9000'

        # Host IPs
        self.traefik_host = '192.168.40.20'
        self.ansible_host = '192.168.20.30'
        self.gitlab_runner_host = '192.168.40.24'

        # API credentials from environment
        self.opnsense_api_key = os.environ.get('OPNSENSE_API_KEY', '')
        self.opnsense_api_secret = os.environ.get('OPNSENSE_API_SECRET', '')
        self.authentik_token = os.environ.get('AUTHENTIK_TOKEN', '')

        # Cache for traefik config
        self._traefik_config_cache = None

    def _ssh_command(self, host: str, command: str, timeout: int = 30) -> Optional[str]:
        """Execute SSH command and return output."""
        try:
            cmd = (
                f"ssh -i {self.ssh_key_path} -o StrictHostKeyChecking=no "
                f"-o ConnectTimeout=10 hermes-admin@{host} \"{command}\""
            )
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def get_traefik_config(self) -> Optional[dict]:
        """Fetch and parse Traefik services.yml."""
        if self._traefik_config_cache:
            return self._traefik_config_cache

        output = self._ssh_command(
            self.traefik_host,
            "cat /opt/traefik/config/dynamic/services.yml"
        )
        if output:
            try:
                self._traefik_config_cache = yaml.safe_load(output)
                return self._traefik_config_cache
            except yaml.YAMLError:
                return None
        return None

    def get_all_services(self) -> List[str]:
        """Get all service names from Traefik config."""
        config = self.get_traefik_config()
        if not config:
            return []

        services = set()
        routers = config.get('http', {}).get('routers', {})

        # Skip internal/infrastructure services
        skip_patterns = [
            'api@internal', 'authentik-outpost', 'proxmox-node',
            'traefik-dashboard', 'proxmox'
        ]

        for router_name, router_config in routers.items():
            # Skip internal routers
            if any(skip in router_name for skip in skip_patterns):
                continue

            # Extract service name from rule
            rule = router_config.get('rule', '')
            match = re.search(r"Host\(`([^.]+)\.", rule)
            if match:
                service_name = match.group(1)
                # Skip auth subdomain
                if service_name not in ['auth', 'node01', 'node02', 'node03']:
                    services.add(service_name)

        return sorted(list(services))

    def check_terraform(self, service_name: str) -> bool:
        """Check if service has Terraform VM configuration."""
        # Read main.tf from gitlab runner (where repo is cloned)
        output = self._ssh_command(
            self.gitlab_runner_host,
            f"grep -l '{service_name}' /opt/gitlab-runner/repos/*/main.tf 2>/dev/null || "
            f"grep -q '{service_name}' /home/hermes-admin/tf-proxmox/main.tf 2>/dev/null && echo 'found'"
        )
        if output:
            return True

        # Also check locally via ansible controller
        output = self._ssh_command(
            self.ansible_host,
            f"grep -q '{service_name}' ~/tf-proxmox/main.tf 2>/dev/null && echo 'found'"
        )
        return output is not None and 'found' in output

    def check_ansible(self, service_name: str) -> bool:
        """Check if service has Ansible playbook."""
        # Check ansible-playbooks directory
        output = self._ssh_command(
            self.ansible_host,
            f"ls -d ~/ansible-playbooks/{service_name}/ 2>/dev/null || "
            f"ls ~/ansible-playbooks/*/{service_name}*.yml 2>/dev/null || "
            f"ls ~/ansible-playbooks/{service_name}*.yml 2>/dev/null"
        )
        if output:
            return True

        # Also check for service in deployed compose files
        output = self._ssh_command(
            self.gitlab_runner_host,
            f"ls -d /opt/gitlab-runner/repos/*{service_name}*/ 2>/dev/null"
        )
        return output is not None

    def check_dns(self, service_name: str) -> bool:
        """Check if service has DNS record in OPNsense."""
        if not self.opnsense_api_key or not self.opnsense_api_secret:
            # Fallback to DNS lookup
            try:
                import socket
                socket.gethostbyname(f"{service_name}.{self.domain}")
                return True
            except socket.gaierror:
                return False

        try:
            response = requests.get(
                f"{self.opnsense_url}/api/unbound/settings/searchHostOverride",
                auth=(self.opnsense_api_key, self.opnsense_api_secret),
                verify=False,
                timeout=10
            )
            if response.status_code == 200:
                for row in response.json().get('rows', []):
                    if row.get('hostname') == service_name and row.get('domain') == self.domain:
                        return True
        except Exception:
            pass
        return False

    def check_traefik(self, service_name: str) -> bool:
        """Check if service has Traefik router configuration."""
        config = self.get_traefik_config()
        if not config:
            return False

        routers = config.get('http', {}).get('routers', {})

        # Check for router matching service name
        for router_name, router_config in routers.items():
            if service_name.lower() in router_name.lower():
                return True

            # Also check rule for hostname
            rule = router_config.get('rule', '')
            if f"`{service_name}." in rule:
                return True

        return False

    def check_ssl(self, service_name: str) -> bool:
        """Check if service has SSL/TLS configured."""
        config = self.get_traefik_config()
        if not config:
            return False

        routers = config.get('http', {}).get('routers', {})

        for router_name, router_config in routers.items():
            if service_name.lower() in router_name.lower():
                tls = router_config.get('tls', {})
                if tls and tls.get('certResolver'):
                    return True

            # Also check by hostname in rule
            rule = router_config.get('rule', '')
            if f"`{service_name}." in rule:
                tls = router_config.get('tls', {})
                if tls and tls.get('certResolver'):
                    return True

        return False

    def check_authentik(self, service_name: str) -> bool:
        """Check if service has Authentik SSO application."""
        if not self.authentik_token:
            return False

        try:
            headers = {
                'Authorization': f'Bearer {self.authentik_token}',
                'Content-Type': 'application/json'
            }
            response = requests.get(
                f"{self.authentik_url}/api/v3/core/applications/",
                headers=headers,
                params={'slug': service_name},
                timeout=10
            )
            if response.status_code == 200:
                results = response.json().get('results', [])
                return len(results) > 0
        except Exception:
            pass
        return False

    def check_documentation(self, service_name: str) -> bool:
        """Check if service is documented in docs/SERVICES.md."""
        output = self._ssh_command(
            self.ansible_host,
            f"grep -qi '{service_name}' ~/tf-proxmox/docs/SERVICES.md 2>/dev/null && echo 'found'"
        )
        if output and 'found' in output:
            return True

        # Also check gitlab runner location
        output = self._ssh_command(
            self.gitlab_runner_host,
            f"grep -qi '{service_name}' /opt/gitlab-runner/repos/*/docs/SERVICES.md 2>/dev/null && echo 'found'"
        )
        return output is not None and 'found' in output

    def check_service(self, service_name: str) -> Dict[str, bool]:
        """Run all checks for a single service."""
        return {
            'terraform': self.check_terraform(service_name),
            'ansible': self.check_ansible(service_name),
            'dns': self.check_dns(service_name),
            'traefik': self.check_traefik(service_name),
            'ssl': self.check_ssl(service_name),
            'authentik': self.check_authentik(service_name),
            'documentation': self.check_documentation(service_name),
        }

    def generate_report(self, services: Optional[List[str]] = None) -> str:
        """Generate a formatted report table for services."""
        if services is None:
            services = self.get_all_services()

        if not services:
            return "No services found in Traefik configuration."

        # Header
        header = (
            "```\n"
            f"{'Service':<15} | {'TF':<3} | {'Ans':<3} | {'DNS':<3} | "
            f"{'Traf':<4} | {'SSL':<3} | {'Auth':<4} | {'Docs':<4}\n"
            f"{'-'*15}-+-{'-'*3}-+-{'-'*3}-+-{'-'*3}-+-"
            f"{'-'*4}-+-{'-'*3}-+-{'-'*4}-+-{'-'*4}\n"
        )

        rows = []
        summary = {'complete': 0, 'incomplete': 0}

        for service in services:
            checks = self.check_service(service)

            # Count complete vs incomplete
            required_checks = ['dns', 'traefik', 'ssl']  # Core requirements
            core_complete = all(checks[c] for c in required_checks)

            if core_complete:
                summary['complete'] += 1
            else:
                summary['incomplete'] += 1

            row = (
                f"{service[:15]:<15} | "
                f"{'Y' if checks['terraform'] else 'N':^3} | "
                f"{'Y' if checks['ansible'] else 'N':^3} | "
                f"{'Y' if checks['dns'] else 'N':^3} | "
                f"{'Y' if checks['traefik'] else 'N':^4} | "
                f"{'Y' if checks['ssl'] else 'N':^3} | "
                f"{'Y' if checks['authentik'] else '-':^4} | "
                f"{'Y' if checks['documentation'] else 'N':^4}"
            )
            rows.append(row)

        table = header + "\n".join(rows) + "\n```"

        # Summary
        summary_text = (
            f"\n**Summary:** {summary['complete']} fully onboarded, "
            f"{summary['incomplete']} need attention\n"
            f"*Legend: TF=Terraform, Ans=Ansible, Traf=Traefik, Auth=Authentik, Docs=Documentation*"
        )

        return table + summary_text

    def generate_single_report(self, service_name: str) -> str:
        """Generate detailed report for a single service."""
        checks = self.check_service(service_name)

        report = f"**Onboarding Status: {service_name}**\n\n"

        icons = {True: ':white_check_mark:', False: ':x:'}

        report += f"{icons[checks['terraform']]} **Terraform Config**\n"
        report += f"{icons[checks['ansible']]} **Ansible Playbook**\n"
        report += f"{icons[checks['dns']]} **DNS Record** ({service_name}.{self.domain})\n"
        report += f"{icons[checks['traefik']]} **Traefik Router**\n"
        report += f"{icons[checks['ssl']]} **SSL/TLS Certificate**\n"
        report += f"{icons[checks['authentik']]} **Authentik SSO** (optional)\n"
        report += f"{icons[checks['documentation']]} **Documentation**\n"

        # Overall status
        required = ['dns', 'traefik', 'ssl']
        if all(checks[c] for c in required):
            report += "\n:tada: **Core onboarding complete!**"
        else:
            missing = [c for c in required if not checks[c]]
            report += f"\n:warning: **Missing core requirements:** {', '.join(missing)}"

        return report


# Standalone testing
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Check service onboarding status')
    parser.add_argument('--service', '-s', help='Specific service to check')
    parser.add_argument('--all', '-a', action='store_true', help='Check all services')
    parser.add_argument('--list', '-l', action='store_true', help='List all services')

    args = parser.parse_args()

    checker = OnboardingChecker()

    if args.list:
        services = checker.get_all_services()
        print("Services in Traefik config:")
        for s in services:
            print(f"  - {s}")
    elif args.service:
        print(checker.generate_single_report(args.service))
    elif args.all:
        print(checker.generate_report())
    else:
        parser.print_help()
