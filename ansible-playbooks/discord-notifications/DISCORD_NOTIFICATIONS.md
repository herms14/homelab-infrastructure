# Discord Notifications for Ansible

This guide explains how to set up Discord notifications for Ansible playbook runs.

## Overview

Two methods are available:
1. **Callback Plugin** (Recommended) - Automatic notifications at the end of every playbook
2. **Role-based** - Manual notifications that can be customized per playbook

## Quick Start

### 1. Create Discord Webhook

1. Open Discord and go to your server
2. Right-click on the channel where you want notifications
3. Select **Edit Channel** → **Integrations** → **Webhooks**
4. Click **New Webhook**
5. Name it "Ansible Bot" and copy the Webhook URL

### 2. Set Environment Variable

```bash
# Add to ~/.bashrc or run before playbooks
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN"
```

### 3. Run Any Playbook

```bash
cd ~/ansible
ansible-playbook docker/deploy-arr-stack.yml -l docker_media
```

The callback plugin will automatically send a notification to Discord when the playbook completes!

## Notification Examples

### Success Notification
```
✅ Playbook: deploy-arr-stack.yml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Status: Success
🖥️ Hosts: 1
⏱️ Duration: 2m 15s

📈 Task Summary
┌─────────────────┐
│ ✓ OK:      45   │
│ ↻ Changed: 3    │
│ ⊘ Skipped: 2    │
│ ✗ Failed:  0    │
└─────────────────┘

🎯 Hosts: docker-vm-media01
```

### Failed Notification
```
❌ Playbook: deploy-service.yml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Status: Failed
🖥️ Hosts: 3
⏱️ Duration: 1m 45s

❌ Failed Tasks:
• server01: Install package
• server02: Start service
```

## Configuration Options

### Environment Variables

| Variable | Description |
|----------|-------------|
| `DISCORD_WEBHOOK_URL` | Discord webhook URL (required) |

### ansible.cfg Settings

```ini
[callback_discord]
webhook_url = https://discord.com/api/webhooks/...
```

### Disable for Specific Runs

```bash
# Temporarily disable notifications
ANSIBLE_CALLBACKS_ENABLED="timer,profile_tasks" ansible-playbook playbook.yml
```

## Using the Role (Optional)

For custom notifications or mid-playbook alerts:

```yaml
- name: My Playbook
  hosts: all
  tasks:
    - name: Do work
      # ... your tasks ...

    # Send custom notification
    - name: Notify Discord
      ansible.builtin.include_role:
        name: discord-notify
      vars:
        discord_webhook_url: "{{ lookup('env', 'DISCORD_WEBHOOK_URL') }}"
```

## File Locations

```
~/ansible/
├── ansible.cfg                      # Updated with callback settings
├── callback_plugins/
│   └── discord_notify.py           # Automatic notification callback
├── roles/
│   └── discord-notify/             # Role for manual notifications
│       ├── defaults/main.yml
│       └── tasks/main.yml
├── example-discord-notify.yml      # Example playbook
└── DISCORD_NOTIFICATIONS.md        # This file
```

## Deployment

Copy files to ansible-controller01:
```bash
# Copy callback plugin
scp callback_plugins/discord_notify.py hermes-admin@192.168.20.30:~/ansible/callback_plugins/

# Copy role
scp -r roles/discord-notify hermes-admin@192.168.20.30:~/ansible/roles/

# Copy updated ansible.cfg
scp ansible.cfg hermes-admin@192.168.20.30:~/ansible/
```

## Troubleshooting

### Notifications not sending

1. Check webhook URL is set:
   ```bash
   echo $DISCORD_WEBHOOK_URL
   ```

2. Test webhook directly:
   ```bash
   curl -X POST "$DISCORD_WEBHOOK_URL" \
     -H "Content-Type: application/json" \
     -d '{"content": "Test message from Ansible"}'
   ```

3. Check Ansible callback is enabled:
   ```bash
   grep callbacks_enabled ~/ansible/ansible.cfg
   ```

### Webhook rate limited

Discord has rate limits. If running many playbooks, notifications may be delayed or dropped.

---

*Created: December 19, 2025*
*For: ansible-controller01 (192.168.20.30)*
