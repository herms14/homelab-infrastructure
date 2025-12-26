#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ansible callback plugin for Discord notifications.
Sends detailed playbook execution summaries to Discord webhook.

To enable:
1. Set DISCORD_WEBHOOK_URL environment variable
2. Add to ansible.cfg: callbacks_enabled = discord_notify

Author: Ansible Automation
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = """
    name: discord_notify
    type: notification
    short_description: Sends playbook results to Discord
    description:
        - This callback sends detailed playbook execution summaries to a Discord webhook
    requirements:
        - DISCORD_WEBHOOK_URL environment variable set
    options:
        webhook_url:
            description: Discord webhook URL
            env:
                - name: DISCORD_WEBHOOK_URL
            ini:
                - section: callback_discord
                  key: webhook_url
"""

import json
import os
import time
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from ansible.plugins.callback import CallbackBase


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "notification"
    CALLBACK_NAME = "discord_notify"
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self):
        super(CallbackModule, self).__init__()
        self.webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
        self.playbook_name = None
        self.playbook_start = None
        self.stats = {
            "ok": 0,
            "changed": 0,
            "failures": 0,
            "skipped": 0,
            "unreachable": 0,
        }
        self.hosts = []
        self.failed_tasks = []

        if not self.webhook_url:
            self._display.warning(
                "Discord webhook URL not set. Set DISCORD_WEBHOOK_URL environment variable."
            )

    def v2_playbook_on_start(self, playbook):
        self.playbook_name = os.path.basename(playbook._file_name)
        self.playbook_start = time.time()

    def v2_playbook_on_play_start(self, play):
        self.hosts = play.get_variable_manager()._inventory.get_hosts(play.hosts)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        if not ignore_errors:
            self.failed_tasks.append({
                "host": result._host.get_name(),
                "task": result._task.get_name(),
                "msg": result._result.get("msg", "Unknown error")[:200]
            })

    def v2_playbook_on_stats(self, stats):
        if not self.webhook_url:
            return

        # Calculate duration
        duration = time.time() - self.playbook_start if self.playbook_start else 0
        duration_str = f"{int(duration // 60)}m {int(duration % 60)}s"

        # Aggregate stats
        hosts = sorted(stats.processed.keys())
        for host in hosts:
            host_stats = stats.summarize(host)
            self.stats["ok"] += host_stats["ok"]
            self.stats["changed"] += host_stats["changed"]
            self.stats["failures"] += host_stats["failures"]
            self.stats["skipped"] += host_stats["skipped"]
            self.stats["unreachable"] += host_stats["unreachable"]

        # Determine status and color
        if self.stats["failures"] > 0 or self.stats["unreachable"] > 0:
            status = "Failed"
            color = 15158332  # Red
            emoji = "❌"
        elif self.stats["changed"] > 0:
            status = "Changed"
            color = 15844367  # Orange
            emoji = "🔄"
        else:
            status = "Success"
            color = 3066993  # Green
            emoji = "✅"

        # Build message
        fields = [
            {"name": "📊 Status", "value": status, "inline": True},
            {"name": "🖥️ Hosts", "value": str(len(hosts)), "inline": True},
            {"name": "⏱️ Duration", "value": duration_str, "inline": True},
            {
                "name": "📈 Task Summary",
                "value": f"```\n✓ OK:      {self.stats['ok']}\n↻ Changed: {self.stats['changed']}\n⊘ Skipped: {self.stats['skipped']}\n✗ Failed:  {self.stats['failures']}\n⚠ Unreach: {self.stats['unreachable']}\n```",
                "inline": False,
            },
            {
                "name": "🎯 Hosts",
                "value": ", ".join(hosts[:10]) + ("..." if len(hosts) > 10 else ""),
                "inline": False,
            },
        ]

        # Add failed tasks if any
        if self.failed_tasks:
            failed_info = "\n".join(
                [f"• {t['host']}: {t['task']}" for t in self.failed_tasks[:5]]
            )
            if len(self.failed_tasks) > 5:
                failed_info += f"\n... and {len(self.failed_tasks) - 5} more"
            fields.append({"name": "❌ Failed Tasks", "value": failed_info, "inline": False})

        payload = {
            "username": "Ansible Bot",
            "avatar_url": "https://raw.githubusercontent.com/ansible/logos/main/vscode-ansible/vscode-ansible.png",
            "embeds": [
                {
                    "title": f"{emoji} Playbook: {self.playbook_name}",
                    "color": color,
                    "fields": fields,
                    "footer": {"text": "Ansible Automation | ansible-controller01"},
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            ],
        }

        # Send to Discord
        try:
            req = Request(
                self.webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            urlopen(req, timeout=10)
            self._display.display("Discord notification sent successfully")
        except (URLError, HTTPError) as e:
            self._display.warning(f"Failed to send Discord notification: {e}")
