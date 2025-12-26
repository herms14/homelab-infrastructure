# Ansible Basics

> **TL;DR**: Ansible automates configuration management via SSH. Write playbooks describing desired state, run `ansible-playbook`, and Ansible configures all target hosts.

## What is Ansible?

Ansible is an agentless automation tool that manages remote systems over SSH. Key characteristics:

- **Agentless**: No software installed on managed nodes
- **Idempotent**: Running the same playbook multiple times produces the same result
- **Declarative**: Describe desired state, not steps
- **YAML-based**: Human-readable configuration

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Ansible Architecture                                 │
│                                                                              │
│   ansible-controller01                                                       │
│   (192.168.20.30)                                                           │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                                                                      │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│   │  │ Playbooks   │  │  Inventory  │  │   Roles     │                 │   │
│   │  │ (tasks)     │  │  (hosts)    │  │ (reusable)  │                 │   │
│   │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│   │                         │                                            │   │
│   │                         ▼                                            │   │
│   │                  SSH Connections                                     │   │
│   │                         │                                            │   │
│   └─────────────────────────┼────────────────────────────────────────────┘   │
│                             │                                                │
│         ┌───────────────────┼───────────────────┐                           │
│         │                   │                   │                           │
│         ▼                   ▼                   ▼                           │
│   ┌───────────┐       ┌───────────┐       ┌───────────┐                    │
│   │ Target 1  │       │ Target 2  │       │ Target N  │                    │
│   │ k8s-      │       │ docker-   │       │  ...      │                    │
│   │ worker01  │       │ vm-media  │       │           │                    │
│   └───────────┘       └───────────┘       └───────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
ansible/
├── ansible.cfg              # Ansible configuration
├── inventory.ini            # Host inventory
├── group_vars/              # Variables per group
│   ├── all.yml
│   ├── k8s_controllers.yml
│   └── docker_hosts.yml
├── host_vars/               # Variables per host
│   └── docker-vm-media01.yml
├── docker/                  # Docker-related playbooks
│   ├── install-docker.yml
│   └── deploy-arr-stack.yml
├── k8s/                     # Kubernetes playbooks
│   ├── k8s-deploy-all.yml
│   └── k8s-prerequisites.yml
├── traefik/
│   └── deploy-traefik.yml
├── authentik/
│   └── deploy-authentik.yml
├── immich/
│   └── deploy-immich.yml
├── n8n/
│   └── deploy-n8n.yml
└── opnsense/
    ├── add-dns-record.yml
    └── add-all-services-dns.yml
```

---

## Core Concepts

### Inventory

Defines managed hosts and groups:

**inventory.ini**:
```ini
[k8s_controllers]
k8s-controller01 ansible_host=192.168.20.32
k8s-controller02 ansible_host=192.168.20.33
k8s-controller03 ansible_host=192.168.20.34

[k8s_workers]
k8s-worker01 ansible_host=192.168.20.40
k8s-worker02 ansible_host=192.168.20.41
k8s-worker03 ansible_host=192.168.20.42
k8s-worker04 ansible_host=192.168.20.43
k8s-worker05 ansible_host=192.168.20.44
k8s-worker06 ansible_host=192.168.20.45

[k8s:children]
k8s_controllers
k8s_workers

[docker_hosts]
docker-vm-utilities01 ansible_host=192.168.40.10
docker-vm-media01 ansible_host=192.168.40.11

[services]
traefik-vm01 ansible_host=192.168.40.20
authentik-vm01 ansible_host=192.168.40.21
immich-vm01 ansible_host=192.168.40.22
gitlab-vm01 ansible_host=192.168.40.23

[all:vars]
ansible_user=hermes-admin
ansible_ssh_private_key_file=~/.ssh/id_ed25519
ansible_python_interpreter=/usr/bin/python3
```

### Playbooks

YAML files defining tasks to execute:

**install-docker.yml**:
```yaml
---
- name: Install Docker on target hosts
  hosts: docker_hosts
  become: yes

  tasks:
    - name: Install prerequisites
      apt:
        name:
          - ca-certificates
          - curl
          - gnupg
        state: present
        update_cache: yes

    - name: Add Docker GPG key
      apt_key:
        url: https://download.docker.com/linux/ubuntu/gpg
        state: present

    - name: Add Docker repository
      apt_repository:
        repo: "deb https://download.docker.com/linux/ubuntu {{ ansible_distribution_release }} stable"
        state: present

    - name: Install Docker
      apt:
        name:
          - docker-ce
          - docker-ce-cli
          - containerd.io
          - docker-compose-plugin
        state: present
        update_cache: yes

    - name: Start Docker service
      systemd:
        name: docker
        state: started
        enabled: yes

    - name: Add user to docker group
      user:
        name: "{{ ansible_user }}"
        groups: docker
        append: yes
```

### Tasks

Individual operations within playbooks:

```yaml
- name: Task description
  module_name:
    parameter1: value1
    parameter2: value2
  register: result_variable
  when: condition
  notify: handler_name
```

### Handlers

Tasks triggered by notifications:

```yaml
handlers:
  - name: Restart nginx
    systemd:
      name: nginx
      state: restarted

tasks:
  - name: Update nginx config
    template:
      src: nginx.conf.j2
      dest: /etc/nginx/nginx.conf
    notify: Restart nginx  # Only runs if task changes something
```

### Variables

```yaml
# Inline variable
- name: Create directory
  file:
    path: "{{ app_dir }}"
    state: directory

# Playbook-level vars
vars:
  app_dir: /opt/myapp
  app_port: 8080

# Vars from file
vars_files:
  - vars/main.yml
```

### Conditionals

```yaml
- name: Install on Debian
  apt:
    name: nginx
  when: ansible_os_family == "Debian"

- name: Install on RedHat
  yum:
    name: nginx
  when: ansible_os_family == "RedHat"
```

### Loops

```yaml
- name: Create multiple directories
  file:
    path: "{{ item }}"
    state: directory
  loop:
    - /opt/app/config
    - /opt/app/data
    - /opt/app/logs

- name: Create users
  user:
    name: "{{ item.name }}"
    groups: "{{ item.groups }}"
  loop:
    - { name: 'alice', groups: 'admin' }
    - { name: 'bob', groups: 'users' }
```

---

## Essential Commands

### Run Playbook

```bash
ansible-playbook playbook.yml
```

**Common options**:

| Option | Purpose |
|--------|---------|
| `-i inventory.ini` | Specify inventory file |
| `-l hosts` | Limit to specific hosts |
| `-e "var=value"` | Pass extra variables |
| `-v / -vv / -vvv` | Increase verbosity |
| `--check` | Dry run (show changes) |
| `--diff` | Show file changes |
| `-b` | Become root (sudo) |

### Examples

```bash
# Run on all hosts
ansible-playbook install-docker.yml

# Limit to specific group
ansible-playbook install-docker.yml -l docker_hosts

# Limit to specific host
ansible-playbook install-docker.yml -l docker-vm-media01

# Dry run
ansible-playbook install-docker.yml --check

# Pass variable
ansible-playbook deploy-app.yml -e "app_version=1.2.3"

# Verbose output
ansible-playbook install-docker.yml -vvv
```

### Ad-Hoc Commands

Run single commands without playbooks:

```bash
# Ping all hosts
ansible all -m ping

# Check uptime
ansible all -a "uptime"

# Install package
ansible docker_hosts -m apt -a "name=htop state=present" -b

# Copy file
ansible all -m copy -a "src=./file.txt dest=/tmp/file.txt"

# Restart service
ansible docker_hosts -m systemd -a "name=docker state=restarted" -b
```

### Inventory Commands

```bash
# List all hosts
ansible-inventory --list

# List hosts in group
ansible docker_hosts --list-hosts

# Graph inventory structure
ansible-inventory --graph
```

---

## Common Modules

### Package Management

```yaml
# apt (Debian/Ubuntu)
- name: Install packages
  apt:
    name:
      - nginx
      - htop
    state: present
    update_cache: yes

# yum (RHEL/CentOS)
- name: Install packages
  yum:
    name: nginx
    state: present
```

### File Operations

```yaml
# Create directory
- name: Create app directory
  file:
    path: /opt/app
    state: directory
    mode: '0755'
    owner: root
    group: root

# Copy file
- name: Copy config
  copy:
    src: files/app.conf
    dest: /etc/app/app.conf
    mode: '0644'

# Template
- name: Deploy config from template
  template:
    src: templates/app.conf.j2
    dest: /etc/app/app.conf

# Line in file
- name: Add line to config
  lineinfile:
    path: /etc/hosts
    line: "192.168.20.30 ansible-controller"

# Create symlink
- name: Create symlink
  file:
    src: /opt/app/current
    dest: /var/www/app
    state: link
```

### Service Management

```yaml
# systemd
- name: Start and enable service
  systemd:
    name: nginx
    state: started
    enabled: yes
    daemon_reload: yes

# service (generic)
- name: Restart service
  service:
    name: nginx
    state: restarted
```

### User Management

```yaml
- name: Create user
  user:
    name: appuser
    groups: docker
    shell: /bin/bash
    create_home: yes

- name: Add SSH key
  authorized_key:
    user: appuser
    key: "{{ lookup('file', '~/.ssh/id_ed25519.pub') }}"
```

### Docker

```yaml
# Docker container
- name: Run container
  docker_container:
    name: nginx
    image: nginx:latest
    state: started
    ports:
      - "80:80"
    volumes:
      - /opt/nginx/html:/usr/share/nginx/html

# Docker compose
- name: Deploy with compose
  docker_compose:
    project_src: /opt/myapp
    state: present
    pull: yes
```

### URI/API Calls

```yaml
- name: Make API request
  uri:
    url: "https://api.example.com/endpoint"
    method: POST
    headers:
      Authorization: "Bearer {{ api_token }}"
    body_format: json
    body:
      key: value
    status_code: [200, 201]
  register: api_response
```

---

## Variable Precedence

From lowest to highest priority:

1. Role defaults (`roles/*/defaults/main.yml`)
2. Inventory file variables
3. Inventory `group_vars/`
4. Inventory `host_vars/`
5. Playbook `vars:`
6. Playbook `vars_files:`
7. Role vars (`roles/*/vars/main.yml`)
8. Block vars
9. Task vars
10. Extra vars (`-e`)

---

## Error Handling

### Ignore Errors

```yaml
- name: Check if service exists
  command: systemctl status nonexistent
  register: result
  ignore_errors: yes

- name: Act on result
  debug:
    msg: "Service not found"
  when: result.rc != 0
```

### Block/Rescue/Always

```yaml
- block:
    - name: Attempt risky operation
      command: /opt/risky-script.sh
  rescue:
    - name: Handle failure
      debug:
        msg: "Script failed, running cleanup"
  always:
    - name: Always run this
      debug:
        msg: "This always runs"
```

### Failed When

```yaml
- name: Check process
  command: pgrep nginx
  register: result
  failed_when: result.rc not in [0, 1]
```

---

## Best Practices

### Playbook Organization

- One playbook per application/role
- Use roles for reusable components
- Keep playbooks focused and modular

### Idempotency

- Ensure playbooks can run multiple times safely
- Use `state: present` instead of install commands
- Use templates instead of shell echo/sed

### Security

- Use `ansible-vault` for secrets
- Don't commit credentials to git
- Use `no_log: true` for sensitive tasks

### Performance

- Use `serial` for rolling updates
- Limit fact gathering when not needed
- Use `async` for long-running tasks

---

## Debugging

### Verbose Output

```bash
ansible-playbook playbook.yml -vvv
```

### Debug Module

```yaml
- name: Print variable
  debug:
    var: my_variable

- name: Print message
  debug:
    msg: "Value is {{ my_variable }}"
```

### Register and Assert

```yaml
- name: Run command
  command: whoami
  register: result

- name: Assert result
  assert:
    that:
      - result.stdout == "root"
    fail_msg: "Not running as root"
```

---

## What's Next?

- **[Controller Setup](Controller-Setup)** - Configure ansible-controller01
- **[Inventory Management](Inventory-Management)** - Advanced inventory
- **[Playbook Guide](Playbook-Guide)** - Production playbooks

---

*Ansible: infrastructure as code without the complexity.*
