# Playbook Guide

> **TL;DR**: Production playbooks for Docker, Kubernetes, and service deployments. Each playbook is idempotent and can be re-run safely.

## Playbook Structure

### Standard Template

```yaml
---
# playbook-name.yml
# Description of what this playbook does

- name: Descriptive play name
  hosts: target_group
  become: yes
  gather_facts: yes

  vars:
    var_name: value

  vars_files:
    - vars/main.yml

  pre_tasks:
    - name: Pre-flight checks
      # ...

  tasks:
    - name: Main tasks
      # ...

  handlers:
    - name: Handler name
      # ...

  post_tasks:
    - name: Verification
      # ...
```

---

## Docker Playbooks

### install-docker.yml

**Path**: `ansible/docker/install-docker.yml`

```yaml
---
- name: Install Docker CE on target hosts
  hosts: docker_required
  become: yes
  gather_facts: yes

  vars:
    docker_users:
      - "{{ ansible_user }}"

  tasks:
    - name: Remove old Docker packages
      apt:
        name:
          - docker
          - docker-engine
          - docker.io
          - containerd
          - runc
        state: absent

    - name: Install prerequisites
      apt:
        name:
          - ca-certificates
          - curl
          - gnupg
          - lsb-release
        state: present
        update_cache: yes

    - name: Create Docker keyring directory
      file:
        path: /etc/apt/keyrings
        state: directory
        mode: '0755'

    - name: Add Docker GPG key
      get_url:
        url: https://download.docker.com/linux/ubuntu/gpg
        dest: /etc/apt/keyrings/docker.asc
        mode: '0644'

    - name: Add Docker repository
      apt_repository:
        repo: >-
          deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc]
          https://download.docker.com/linux/ubuntu
          {{ ansible_distribution_release }} stable
        state: present
        filename: docker

    - name: Install Docker packages
      apt:
        name:
          - docker-ce
          - docker-ce-cli
          - containerd.io
          - docker-buildx-plugin
          - docker-compose-plugin
        state: present
        update_cache: yes

    - name: Ensure Docker service is running
      systemd:
        name: docker
        state: started
        enabled: yes

    - name: Add users to docker group
      user:
        name: "{{ item }}"
        groups: docker
        append: yes
      loop: "{{ docker_users }}"

    - name: Create Docker network for Traefik
      docker_network:
        name: traefik
        state: present
```

**Usage**:
```bash
ansible-playbook docker/install-docker.yml
ansible-playbook docker/install-docker.yml -l docker-vm-media01
```

---

### deploy-arr-stack.yml

**Path**: `ansible/docker/deploy-arr-stack.yml`

```yaml
---
- name: Deploy Arr Media Stack
  hosts: docker-vm-media01
  become: yes
  gather_facts: yes

  vars:
    arr_stack_dir: /opt/arr-stack
    media_mount: /mnt/media
    puid: "1000"
    pgid: "1000"
    timezone: "America/New_York"

  tasks:
    - name: Ensure NFS client is installed
      apt:
        name: nfs-common
        state: present

    - name: Create media mount point
      file:
        path: "{{ media_mount }}"
        state: directory
        mode: '0755'

    - name: Mount NFS media share
      mount:
        path: "{{ media_mount }}"
        src: "192.168.20.31:/volume2/Proxmox-Media"
        fstype: nfs
        opts: defaults,_netdev
        state: mounted

    - name: Create stack directory
      file:
        path: "{{ arr_stack_dir }}"
        state: directory
        mode: '0755'

    - name: Create service directories
      file:
        path: "{{ arr_stack_dir }}/{{ item }}"
        state: directory
        mode: '0755'
        owner: "{{ puid }}"
        group: "{{ pgid }}"
      loop:
        - jellyfin
        - radarr
        - sonarr
        - lidarr
        - prowlarr
        - bazarr
        - overseerr
        - jellyseerr
        - tdarr
        - tdarr/server
        - tdarr/configs
        - tdarr/logs
        - autobrr

    - name: Deploy docker-compose.yml
      template:
        src: templates/arr-stack-compose.yml.j2
        dest: "{{ arr_stack_dir }}/docker-compose.yml"
        mode: '0644'

    - name: Start Arr stack
      docker_compose:
        project_src: "{{ arr_stack_dir }}"
        state: present
        pull: yes
      register: compose_result

    - name: Display running containers
      debug:
        msg: "{{ compose_result.services | default('Stack deployed') }}"
```

**Template**: `templates/arr-stack-compose.yml.j2`

```yaml
version: "3.8"

services:
  jellyfin:
    image: jellyfin/jellyfin:latest
    container_name: jellyfin
    environment:
      - PUID={{ puid }}
      - PGID={{ pgid }}
      - TZ={{ timezone }}
    volumes:
      - {{ arr_stack_dir }}/jellyfin:/config
      - {{ media_mount }}/Movies:/movies:ro
      - {{ media_mount }}/Series:/series:ro
      - {{ media_mount }}/Music:/music:ro
    ports:
      - "8096:8096"
    restart: unless-stopped

  radarr:
    image: lscr.io/linuxserver/radarr:latest
    container_name: radarr
    environment:
      - PUID={{ puid }}
      - PGID={{ pgid }}
      - TZ={{ timezone }}
    volumes:
      - {{ arr_stack_dir }}/radarr:/config
      - {{ media_mount }}/Movies:/movies
      - {{ media_mount }}/Downloads:/downloads
    ports:
      - "7878:7878"
    restart: unless-stopped

  # Additional services...
```

---

## Kubernetes Playbooks

### k8s-prerequisites.yml

**Path**: `ansible/k8s/k8s-prerequisites.yml`

```yaml
---
- name: Configure Kubernetes prerequisites
  hosts: k8s
  become: yes
  gather_facts: yes

  tasks:
    - name: Disable swap
      command: swapoff -a
      changed_when: false

    - name: Remove swap from fstab
      lineinfile:
        path: /etc/fstab
        regexp: '\sswap\s'
        state: absent

    - name: Load required kernel modules
      modprobe:
        name: "{{ item }}"
        state: present
      loop:
        - overlay
        - br_netfilter

    - name: Persist kernel modules
      copy:
        content: |
          overlay
          br_netfilter
        dest: /etc/modules-load.d/k8s.conf
        mode: '0644'

    - name: Set sysctl parameters
      sysctl:
        name: "{{ item.key }}"
        value: "{{ item.value }}"
        sysctl_file: /etc/sysctl.d/k8s.conf
        reload: yes
      loop:
        - { key: 'net.bridge.bridge-nf-call-iptables', value: '1' }
        - { key: 'net.bridge.bridge-nf-call-ip6tables', value: '1' }
        - { key: 'net.ipv4.ip_forward', value: '1' }

    - name: Install containerd
      apt:
        name: containerd
        state: present
        update_cache: yes

    - name: Configure containerd
      shell: |
        mkdir -p /etc/containerd
        containerd config default > /etc/containerd/config.toml
      args:
        creates: /etc/containerd/config.toml

    - name: Enable SystemdCgroup in containerd
      lineinfile:
        path: /etc/containerd/config.toml
        regexp: 'SystemdCgroup = false'
        line: '            SystemdCgroup = true'
      notify: Restart containerd

    - name: Start containerd
      systemd:
        name: containerd
        state: started
        enabled: yes

    - name: Add Kubernetes apt key
      get_url:
        url: https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key
        dest: /etc/apt/keyrings/kubernetes-apt-keyring.asc
        mode: '0644'

    - name: Add Kubernetes repository
      apt_repository:
        repo: >-
          deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.asc]
          https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /
        state: present
        filename: kubernetes

    - name: Install Kubernetes packages
      apt:
        name:
          - kubelet
          - kubeadm
          - kubectl
        state: present
        update_cache: yes

    - name: Hold Kubernetes packages
      dpkg_selections:
        name: "{{ item }}"
        selection: hold
      loop:
        - kubelet
        - kubeadm
        - kubectl

  handlers:
    - name: Restart containerd
      systemd:
        name: containerd
        state: restarted
```

---

### k8s-init-cluster.yml

**Path**: `ansible/k8s/k8s-init-cluster.yml`

```yaml
---
- name: Initialize Kubernetes control plane
  hosts: k8s-controller01
  become: yes
  gather_facts: yes

  vars:
    pod_network_cidr: "10.244.0.0/16"
    control_plane_endpoint: "192.168.20.32:6443"

  tasks:
    - name: Check if cluster is initialized
      stat:
        path: /etc/kubernetes/admin.conf
      register: kubeadm_init

    - name: Initialize cluster
      command: >-
        kubeadm init
        --control-plane-endpoint={{ control_plane_endpoint }}
        --pod-network-cidr={{ pod_network_cidr }}
        --upload-certs
      when: not kubeadm_init.stat.exists
      register: init_output

    - name: Save join command
      copy:
        content: "{{ init_output.stdout }}"
        dest: /root/kubeadm-init-output.txt
        mode: '0600'
      when: init_output.changed

    - name: Create .kube directory
      file:
        path: "/home/{{ ansible_user }}/.kube"
        state: directory
        owner: "{{ ansible_user }}"
        group: "{{ ansible_user }}"
        mode: '0755'

    - name: Copy admin.conf
      copy:
        src: /etc/kubernetes/admin.conf
        dest: "/home/{{ ansible_user }}/.kube/config"
        remote_src: yes
        owner: "{{ ansible_user }}"
        group: "{{ ansible_user }}"
        mode: '0600'

    - name: Install Calico CNI
      become_user: "{{ ansible_user }}"
      command: kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/calico.yaml
      when: init_output.changed

    - name: Get join command for controllers
      command: kubeadm token create --print-join-command --certificate-key $(kubeadm init phase upload-certs --upload-certs 2>/dev/null | tail -1)
      register: controller_join_command
      changed_when: false

    - name: Get join command for workers
      command: kubeadm token create --print-join-command
      register: worker_join_command
      changed_when: false

    - name: Save controller join command
      copy:
        content: "{{ controller_join_command.stdout }}"
        dest: /root/controller-join-command.txt
        mode: '0600'

    - name: Save worker join command
      copy:
        content: "{{ worker_join_command.stdout }}"
        dest: /root/worker-join-command.txt
        mode: '0600'
```

---

## Service Playbooks

### deploy-authentik.yml

**Path**: `ansible/authentik/deploy-authentik.yml`

```yaml
---
- name: Deploy Authentik SSO
  hosts: authentik-vm01
  become: yes
  gather_facts: yes

  vars:
    authentik_dir: /opt/authentik
    authentik_secret_key: "{{ lookup('password', '/dev/null length=50 chars=ascii_letters,digits') }}"
    postgres_password: "{{ lookup('password', '/dev/null length=32 chars=ascii_letters,digits') }}"

  tasks:
    - name: Create Authentik directory
      file:
        path: "{{ authentik_dir }}"
        state: directory
        mode: '0755'

    - name: Deploy docker-compose.yml
      template:
        src: templates/authentik-compose.yml.j2
        dest: "{{ authentik_dir }}/docker-compose.yml"
        mode: '0644'

    - name: Deploy .env file
      template:
        src: templates/authentik-env.j2
        dest: "{{ authentik_dir }}/.env"
        mode: '0600'

    - name: Create Docker network
      docker_network:
        name: authentik
        state: present

    - name: Start Authentik
      docker_compose:
        project_src: "{{ authentik_dir }}"
        state: present
        pull: yes

    - name: Wait for Authentik to be ready
      uri:
        url: "http://localhost:9000/-/health/ready/"
        status_code: 200
      register: result
      until: result.status == 200
      retries: 30
      delay: 10

    - name: Display access information
      debug:
        msg:
          - "Authentik is ready!"
          - "Access: http://{{ ansible_host }}:9000"
          - "Initial setup: http://{{ ansible_host }}:9000/if/flow/initial-setup/"
```

---

## OPNsense Playbooks

### add-dns-record.yml

**Path**: `ansible/opnsense/add-dns-record.yml`

```yaml
---
- name: Add DNS record to OPNsense Unbound
  hosts: localhost
  gather_facts: no

  vars:
    opnsense_url: "https://192.168.91.30"
    opnsense_api_key: "{{ lookup('env', 'OPNSENSE_API_KEY') }}"
    opnsense_api_secret: "{{ lookup('env', 'OPNSENSE_API_SECRET') }}"
    dns_domain: "hrmsmrflrii.xyz"
    dns_ip: "192.168.40.20"
    # Required: dns_hostname (pass via -e)

  tasks:
    - name: Validate required variables
      assert:
        that:
          - dns_hostname is defined
          - dns_hostname | length > 0
        fail_msg: "dns_hostname must be provided via -e dns_hostname=value"

    - name: Add host override
      uri:
        url: "{{ opnsense_url }}/api/unbound/settings/addHostOverride"
        method: POST
        user: "{{ opnsense_api_key }}"
        password: "{{ opnsense_api_secret }}"
        force_basic_auth: yes
        validate_certs: no
        body_format: json
        body:
          host:
            enabled: "1"
            hostname: "{{ dns_hostname }}"
            domain: "{{ dns_domain }}"
            rr: "A"
            server: "{{ dns_ip }}"
            description: "Added via Ansible - {{ ansible_date_time.iso8601 | default('') }}"
        status_code: [200]
      register: add_result

    - name: Apply Unbound configuration
      uri:
        url: "{{ opnsense_url }}/api/unbound/service/reconfigure"
        method: POST
        user: "{{ opnsense_api_key }}"
        password: "{{ opnsense_api_secret }}"
        force_basic_auth: yes
        validate_certs: no
        status_code: [200]

    - name: Verify DNS resolution
      command: "nslookup {{ dns_hostname }}.{{ dns_domain }} 192.168.91.30"
      register: nslookup_result
      changed_when: false
      delegate_to: localhost

    - name: Display result
      debug:
        msg:
          - "DNS record added: {{ dns_hostname }}.{{ dns_domain }} → {{ dns_ip }}"
          - "Verification: {{ nslookup_result.stdout_lines[-1] | default('Check manually') }}"
```

**Usage**:
```bash
export OPNSENSE_API_KEY="your-key"
export OPNSENSE_API_SECRET="your-secret"

ansible-playbook opnsense/add-dns-record.yml -e "dns_hostname=newservice"
ansible-playbook opnsense/add-dns-record.yml -e "dns_hostname=myapp dns_ip=192.168.40.50"
```

---

## Utility Playbooks

### update-all-systems.yml

```yaml
---
- name: Update all managed systems
  hosts: all
  become: yes
  serial: 5  # Update 5 hosts at a time

  tasks:
    - name: Update apt cache
      apt:
        update_cache: yes
        cache_valid_time: 3600

    - name: Upgrade all packages
      apt:
        upgrade: dist
      register: upgrade_result

    - name: Check if reboot required
      stat:
        path: /var/run/reboot-required
      register: reboot_required

    - name: Display upgrade summary
      debug:
        msg: "{{ inventory_hostname }}: {{ upgrade_result.changed | ternary('Updated', 'No updates') }}, Reboot: {{ reboot_required.stat.exists | ternary('Required', 'Not needed') }}"
```

### gather-facts.yml

```yaml
---
- name: Gather and display system facts
  hosts: all
  gather_facts: yes

  tasks:
    - name: Display system information
      debug:
        msg:
          - "Hostname: {{ ansible_hostname }}"
          - "IP: {{ ansible_default_ipv4.address }}"
          - "OS: {{ ansible_distribution }} {{ ansible_distribution_version }}"
          - "Kernel: {{ ansible_kernel }}"
          - "CPU: {{ ansible_processor_vcpus }} vCPUs"
          - "Memory: {{ (ansible_memtotal_mb / 1024) | round(1) }} GB"
          - "Disk: {{ (ansible_mounts | selectattr('mount', 'eq', '/') | first).size_total | human_readable }}"
```

---

## Running Playbooks

### Common Commands

```bash
# Change to ansible directory
cd ~/ansible

# Run playbook
ansible-playbook docker/install-docker.yml

# Limit to specific hosts
ansible-playbook docker/install-docker.yml -l docker-vm-media01

# Dry run
ansible-playbook docker/install-docker.yml --check

# Show diff
ansible-playbook docker/install-docker.yml --check --diff

# Verbose
ansible-playbook docker/install-docker.yml -v
ansible-playbook docker/install-docker.yml -vvv

# Pass variables
ansible-playbook deploy.yml -e "version=1.2.3"
ansible-playbook deploy.yml -e "@vars.yml"

# Step through tasks
ansible-playbook playbook.yml --step

# Start at specific task
ansible-playbook playbook.yml --start-at-task="Install packages"
```

---

## What's Next?

- **[Services Overview](Services-Overview)** - All deployed services
- **[Traefik](Traefik)** - Reverse proxy setup
- **[Arr-Stack](Arr-Stack)** - Media automation

---

*Playbooks are recipes for infrastructure. Write once, run anywhere.*
