# Quick Start

> **TL;DR**: Clone the repo, configure credentials, run `terraform apply` to create VMs, then `ansible-playbook` to deploy services.

## Goal

In this guide, you'll:
1. Clone the repository
2. Configure your credentials
3. Deploy a virtual machine with Terraform
4. Configure it with Ansible

**Time required**: ~15 minutes

---

## Prerequisites

Before starting, ensure you have:
- [ ] Proxmox VE installed and accessible
- [ ] Proxmox API token created (see [Prerequisites](Prerequisites))
- [ ] Terraform installed on your workstation
- [ ] Ansible installed on your workstation
- [ ] SSH key generated

---

## Step 1: Clone the Repository

**What we're doing**: Download all the infrastructure code to your computer.

```bash
git clone https://github.com/herms14/Proxmox-TerraformDeployments.git
cd Proxmox-TerraformDeployments
```

**What each part means**:
- `git clone`: Downloads a copy of the repository
- `cd`: Changes into the downloaded directory

**Expected result**: You now have all the Terraform and Ansible files locally.

[Screenshot: Terminal showing successful git clone]

---

## Step 2: Configure Terraform Variables

**What we're doing**: Tell Terraform how to connect to your Proxmox server.

### 2.1 Create the variables file

```bash
cp terraform.tfvars.example terraform.tfvars
```

**Why**: The example file shows what's needed; we copy it to create our actual config.

### 2.2 Edit the variables

```bash
nano terraform.tfvars
```

**Fill in your values**:

```hcl
# Proxmox Connection
proxmox_api_url   = "https://YOUR-PROXMOX-IP:8006/api2/json"
proxmox_api_token = "root@pam!terraform=YOUR-TOKEN-SECRET"

# SSH Key (your public key)
ssh_public_key = "ssh-ed25519 AAAA... your-email@example.com"

# Network Settings (adjust to your network)
gateway    = "192.168.20.1"
nameserver = "192.168.20.1"
```

**What each setting means**:
- `proxmox_api_url`: Where Terraform connects to Proxmox
- `proxmox_api_token`: Authentication (format: `user@realm!tokenid=secret`)
- `ssh_public_key`: The key that will be added to VMs for SSH access
- `gateway`: Your network's default gateway (usually your router)
- `nameserver`: DNS server to use

**Save and exit**: Press `Ctrl+X`, then `Y`, then `Enter`

[Screenshot: terraform.tfvars file with example values]

---

## Step 3: Initialize Terraform

**What we're doing**: Download the Proxmox provider plugin that Terraform needs.

```bash
terraform init
```

**What happens**:
1. Terraform reads the configuration files
2. Downloads the `telmate/proxmox` provider
3. Creates a `.terraform` directory with plugins

**Expected output**:
```
Initializing the backend...
Initializing provider plugins...
- Finding telmate/proxmox versions...
- Installing telmate/proxmox v3.0.1-rc1...

Terraform has been successfully initialized!
```

[Screenshot: Successful terraform init output]

---

## Step 4: Preview the Deployment

**What we're doing**: See what Terraform will create WITHOUT actually creating it.

```bash
terraform plan
```

**What happens**:
1. Terraform connects to Proxmox
2. Compares desired state (your config) with actual state
3. Shows what changes it would make

**Expected output** (abbreviated):
```
Terraform will perform the following actions:

  # module.vms["ansible-controller"].proxmox_vm_qemu.linux_vm will be created
  + resource "proxmox_vm_qemu" "linux_vm" {
      + name     = "ansible-controller01"
      + cores    = 2
      + memory   = 4096
      ...
    }

Plan: 17 to add, 0 to change, 0 to destroy.
```

**Read this carefully!** Make sure:
- The number of VMs looks correct
- IP addresses are in your expected range
- Resources (cores, memory) are appropriate

[Screenshot: terraform plan output showing VMs to create]

---

## Step 5: Deploy the Infrastructure

**What we're doing**: Actually create the VMs in Proxmox.

```bash
terraform apply
```

**What happens**:
1. Terraform shows the plan again
2. Asks for confirmation
3. Creates all the VMs in parallel

**When prompted**:
```
Do you want to perform these actions?
  Terraform will perform the actions described above.
  Only 'yes' will be accepted to approve.

  Enter a value: yes
```

Type `yes` and press Enter.

**This takes 5-10 minutes** depending on your hardware.

**Expected output**:
```
module.vms["ansible-controller"].proxmox_vm_qemu.linux_vm: Creating...
module.vms["ansible-controller"].proxmox_vm_qemu.linux_vm: Still creating... [10s elapsed]
module.vms["ansible-controller"].proxmox_vm_qemu.linux_vm: Creation complete after 45s

Apply complete! Resources: 17 added, 0 changed, 0 destroyed.

Outputs:

vm_ips = {
  "ansible-controller01" = "192.168.20.30"
  ...
}
```

[Screenshot: Proxmox web UI showing newly created VMs]

---

## Step 6: Verify SSH Access

**What we're doing**: Confirm you can connect to the new VMs.

```bash
ssh hermes-admin@192.168.20.30
```

**What each part means**:
- `hermes-admin`: The username created by cloud-init
- `192.168.20.30`: The IP address of the Ansible controller

**Expected result**: You should be logged into the VM.

```
Welcome to Ubuntu 24.04 LTS (GNU/Linux 6.8.0-xx-generic x86_64)

hermes-admin@ansible-controller01:~$
```

**If this fails**, see [Troubleshooting: VM Issues](VM-Issues).

[Screenshot: Successful SSH connection]

---

## Step 7: Run Ansible (Optional)

**What we're doing**: Configure the VMs automatically with Ansible.

### From the Ansible Controller

First, SSH to the controller:
```bash
ssh hermes-admin@192.168.20.30
```

Then run a playbook:
```bash
cd ~/ansible
ansible-playbook docker/install-docker.yml -l docker_hosts
```

**What each part means**:
- `cd ~/ansible`: Navigate to the Ansible directory
- `ansible-playbook`: Run an Ansible playbook
- `docker/install-docker.yml`: The playbook to run
- `-l docker_hosts`: Limit to only Docker host VMs

**Expected output**:
```
PLAY [Install Docker on target hosts] ****************************************

TASK [Install prerequisites] *************************************************
ok: [docker-vm-utilities01]
ok: [docker-vm-media01]

...

PLAY RECAP *******************************************************************
docker-vm-utilities01      : ok=8    changed=5    unreachable=0    failed=0
docker-vm-media01          : ok=8    changed=5    unreachable=0    failed=0
```

[Screenshot: Successful Ansible playbook run]

---

## What You've Accomplished

You now have:
- ✅ 17 virtual machines running on Proxmox
- ✅ All VMs accessible via SSH
- ✅ Infrastructure defined as code (reproducible!)
- ✅ (Optional) Docker installed on service VMs

---

## Common Issues

### "Permission denied" when SSHing

**Cause**: SSH key not added correctly

**Fix**: Check your public key in `terraform.tfvars`:
```bash
cat ~/.ssh/id_ed25519.pub
# This should match what's in terraform.tfvars
```

### "Could not connect to Proxmox API"

**Cause**: Wrong URL or credentials

**Fix**:
1. Verify you can access `https://your-proxmox:8006` in a browser
2. Check your API token format: `user@realm!tokenid=secret`

### VMs created but can't get IP

**Cause**: Cloud-init not configured or network issues

**Fix**:
1. Check VM console in Proxmox for boot errors
2. Verify DHCP is working on your network
3. See [VM Issues](VM-Issues) for detailed troubleshooting

---

## Next Steps

Now that your infrastructure is running:

1. **[Deploy Services](Services-Overview)** - Add Traefik, Jellyfin, etc.
2. **[Configure SSL](SSL-Certificates)** - Set up HTTPS for all services
3. **[Set up DNS](DNS-Configuration)** - Nice domain names for services

---

## Clean Up (If Testing)

To destroy everything and start fresh:

```bash
terraform destroy
```

**Warning**: This deletes all VMs! Only do this if you're testing.

---

*Congratulations! You've deployed your first homelab infrastructure with Infrastructure as Code.*
