# Complete Template Library Guide

This guide will help you create a library of templates for Ubuntu VMs, LXC containers, and Windows VMs.

## Table of Contents
1. [Ubuntu VM Templates](#ubuntu-vm-templates)
2. [LXC Container Templates](#lxc-container-templates)
3. [Windows VM Templates](#windows-vm-templates)

---

## Ubuntu VM Templates

### Ubuntu 22.04 LTS (Already Created)
You already have `ubuntu-cloud-template` (VM ID 9000)

### Ubuntu 24.04 LTS

```bash
# Download Ubuntu 24.04 Noble cloud image
cd /tmp
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img

# Create VM
qm create 9001 --name ubuntu-24-cloud-template --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0

# Import disk
qm importdisk 9001 noble-server-cloudimg-amd64.img local-lvm

# Configure VM
qm set 9001 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9001-disk-0
qm set 9001 --ide2 local-lvm:cloudinit
qm set 9001 --boot c --bootdisk scsi0
qm set 9001 --serial0 socket --vga serial0
qm set 9001 --agent enabled=1

# Convert to template
qm template 9001

# Cleanup
rm noble-server-cloudimg-amd64.img
```

### Ubuntu 20.04 LTS (if needed for older apps)

```bash
# Download Ubuntu 20.04 Focal cloud image
cd /tmp
wget https://cloud-images.ubuntu.com/focal/current/focal-server-cloudimg-amd64.img

# Create VM
qm create 9002 --name ubuntu-20-cloud-template --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0

# Import disk
qm importdisk 9002 focal-server-cloudimg-amd64.img local-lvm

# Configure VM
qm set 9002 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9002-disk-0
qm set 9002 --ide2 local-lvm:cloudinit
qm set 9002 --boot c --bootdisk scsi0
qm set 9002 --serial0 socket --vga serial0
qm set 9002 --agent enabled=1

# Convert to template
qm template 9002

# Cleanup
rm focal-server-cloudimg-amd64.img
```

### Quick Script to Create All Ubuntu Templates

Save this as `create-ubuntu-templates.sh` on your Proxmox server:

```bash
#!/bin/bash

# Ubuntu versions to create
declare -A UBUNTU_VERSIONS=(
    ["22"]="jammy"
    ["24"]="noble"
    ["20"]="focal"
)

VMID=9000
STORAGE="local-lvm"

for version in "${!UBUNTU_VERSIONS[@]}"; do
    CODENAME="${UBUNTU_VERSIONS[$version]}"
    TEMPLATE_NAME="ubuntu-${version}-cloud-template"
    IMAGE_FILE="${CODENAME}-server-cloudimg-amd64.img"

    echo "Creating template: $TEMPLATE_NAME (VM ID: $VMID)"

    # Download image
    wget -q --show-progress "https://cloud-images.ubuntu.com/${CODENAME}/current/${IMAGE_FILE}"

    # Create VM
    qm create $VMID --name $TEMPLATE_NAME --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0

    # Import disk
    qm importdisk $VMID $IMAGE_FILE $STORAGE

    # Configure VM
    qm set $VMID --scsihw virtio-scsi-pci --scsi0 ${STORAGE}:vm-${VMID}-disk-0
    qm set $VMID --ide2 ${STORAGE}:cloudinit
    qm set $VMID --boot c --bootdisk scsi0
    qm set $VMID --serial0 socket --vga serial0
    qm set $VMID --agent enabled=1

    # Convert to template
    qm template $VMID

    # Cleanup
    rm $IMAGE_FILE

    echo "✓ Created $TEMPLATE_NAME"
    ((VMID++))
done

echo "All Ubuntu templates created!"
```

Make it executable and run:
```bash
chmod +x create-ubuntu-templates.sh
./create-ubuntu-templates.sh
```

---

## LXC Container Templates

LXC templates work differently - Proxmox downloads them for you!

### Downloading LXC Templates via Web UI

1. **Navigate to Storage:**
   - Datacenter → node01 → local (or your storage)
   - Click **CT Templates**

2. **Download Templates:**
   - Click **Templates** button
   - Search and download:
     - `ubuntu-22.04-standard` (recommended)
     - `ubuntu-24.04-standard`
     - `ubuntu-20.04-standard`
     - `debian-12-standard`
     - `alpine-3.19-default` (very lightweight)

### Downloading LXC Templates via CLI

```bash
# List available templates
pveam available | grep ubuntu

# Download Ubuntu templates
pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
pveam download local ubuntu-24.04-standard_24.04-1_amd64.tar.zst

# Download Debian
pveam download local debian-12-standard_12.2-1_amd64.tar.zst

# Download Alpine (very lightweight)
pveam download local alpine-3.19-default_20240207_amd64.tar.xz

# List downloaded templates
pveam list local
```

### Creating LXC Container Template (Custom)

If you want a pre-configured LXC template with specific software:

```bash
# Create a container
pct create 9100 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname lxc-template \
  --memory 512 \
  --cores 1 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp

# Start it
pct start 9100

# Enter the container
pct enter 9100

# Inside the container - install common packages
apt update
apt upgrade -y
apt install -y curl wget git vim nano htop

# Exit container
exit

# Stop the container
pct stop 9100

# Convert to template
vzdump 9100 --compress zstd --storage local

# The template will be saved in /var/lib/vz/dump/
# You can then create new containers from this backup
```

**Note:** For Terraform, you typically use the standard LXC templates directly, not custom templates. Terraform will provision the software you need.

---

## Windows VM Templates

Windows requires more manual setup than Linux. Here's the complete process:

### Prerequisites

1. **Download Windows ISO:**
   - Windows Server 2022: [Microsoft Evaluation Center](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-server-2022)
   - Windows 11: Get from Microsoft or MSDN
   - Windows 10: Get from Microsoft

2. **Download VirtIO Drivers:**
   ```bash
   cd /var/lib/vz/template/iso
   wget https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso
   ```

### Windows Server 2022 Template

#### Step 1: Create the VM via CLI

```bash
# Create VM
qm create 9200 \
  --name windows-2022-template \
  --memory 4096 \
  --cores 4 \
  --net0 virtio,bridge=vmbr0 \
  --scsihw virtio-scsi-pci \
  --ostype win11 \
  --cpu host \
  --agent 1

# Add Windows ISO
qm set 9200 --ide2 local:iso/windows-server-2022.iso,media=cdrom

# Add VirtIO drivers ISO
qm set 9200 --ide0 local:iso/virtio-win.iso,media=cdrom

# Add disk (adjust size as needed)
qm set 9200 --scsi0 local-lvm:100

# Set boot order
qm set 9200 --boot order=ide2;scsi0
```

#### Step 2: Install Windows via Proxmox Console

1. **Start the VM:**
   - In Proxmox UI: Select VM 9200 → Start
   - Open Console

2. **Install Windows:**
   - Boot from Windows ISO
   - When asked "Where do you want to install Windows?":
     - Click **Load Driver**
     - Browse to VirtIO ISO → `vioscsi\w11\amd64` (or `2k22\amd64` for Server 2022)
     - Install the driver
     - You should now see the disk
   - Continue with Windows installation

3. **Install VirtIO Drivers:**
   After Windows installs and boots:
   - Open File Explorer → VirtIO CD drive
   - Run `virtio-win-gt-x64.msi`
   - Install all drivers
   - Reboot

4. **Install QEMU Guest Agent:**
   - From VirtIO ISO, run: `guest-agent\qemu-ga-x86_64.msi`
   - Install and start the service

5. **Configure Windows:**
   ```powershell
   # Run in PowerShell as Administrator

   # Set timezone
   Set-TimeZone -Id "Eastern Standard Time"

   # Disable Windows Defender (optional, for template)
   Set-MpPreference -DisableRealtimeMonitoring $true

   # Enable Remote Desktop
   Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -name "fDenyTSConnections" -value 0
   Enable-NetFirewallRule -DisplayGroup "Remote Desktop"

   # Install Windows Updates (recommended)
   Install-Module PSWindowsUpdate -Force
   Get-WindowsUpdate -Install -AcceptAll -AutoReboot
   ```

6. **Sysprep (Generalize the image):**
   ```powershell
   # This removes machine-specific information
   C:\Windows\System32\Sysprep\sysprep.exe /generalize /oobe /shutdown
   ```

   **IMPORTANT:** VM will shutdown after sysprep. Don't start it again!

#### Step 3: Convert to Template

```bash
# Remove the ISOs
qm set 9200 --delete ide0
qm set 9200 --delete ide2

# Convert to template
qm template 9200
```

### Windows 10/11 Template

Same process as Windows Server, but:

```bash
# Create VM for Windows 10/11
qm create 9201 \
  --name windows-11-template \
  --memory 8192 \
  --cores 4 \
  --net0 virtio,bridge=vmbr0 \
  --scsihw virtio-scsi-pci \
  --ostype win11 \
  --cpu host \
  --agent 1 \
  --bios ovmf \
  --efidisk0 local-lvm:1,format=raw,efitype=4m,pre-enrolled-keys=1 \
  --tpmstate0 local-lvm:1,version=v2.0

# Add ISOs
qm set 9201 --ide2 local:iso/windows-11.iso,media=cdrom
qm set 9201 --ide0 local:iso/virtio-win.iso,media=cdrom

# Add disk
qm set 9201 --scsi0 local-lvm:100

# Set boot order
qm set 9201 --boot order=ide2;scsi0
```

Then follow the same installation steps.

### Quick Windows Template Checklist

- [ ] Windows installed
- [ ] VirtIO drivers installed (network, storage, balloon, serial)
- [ ] QEMU Guest Agent installed and running
- [ ] Windows Updates installed
- [ ] Remote Desktop enabled (optional)
- [ ] Timezone set
- [ ] Sysprep completed
- [ ] ISOs removed
- [ ] Converted to template

---

## Template Summary

After completing this guide, you'll have:

### VM Templates
- `ubuntu-cloud-template` (VM 9000) - Ubuntu 22.04
- `ubuntu-24-cloud-template` (VM 9001) - Ubuntu 24.04
- `ubuntu-20-cloud-template` (VM 9002) - Ubuntu 20.04
- `windows-2022-template` (VM 9200) - Windows Server 2022
- `windows-11-template` (VM 9201) - Windows 11

### LXC Templates
- `ubuntu-22.04-standard`
- `ubuntu-24.04-standard`
- `debian-12-standard`
- `alpine-3.19-default`

## Using These Templates in Terraform

### For Ubuntu VMs:
```hcl
template_name = "ubuntu-cloud-template"      # 22.04
# or
template_name = "ubuntu-24-cloud-template"   # 24.04
```

### For Windows VMs:
```hcl
template_name = "windows-2022-template"
# or
template_name = "windows-11-template"
```

### For LXC Containers:
LXC templates are referenced differently (covered in a separate LXC module guide)

---

## Storage Considerations

### Recommended Storage Per Template Type

- **Ubuntu Cloud Images:** ~2-5 GB each
- **LXC Templates:** ~100-300 MB each
- **Windows Templates:** ~30-50 GB each

### Total Storage Needed
- 3 Ubuntu templates: ~15 GB
- 4 LXC templates: ~1 GB
- 2 Windows templates: ~100 GB
- **Total:** ~116 GB

Make sure you have enough space in your storage pool!

---

## Next Steps

1. Create all Ubuntu templates using the script
2. Download LXC templates via web UI or CLI
3. Create Windows templates (takes 1-2 hours each)
4. Update your Terraform configurations to use these templates
5. Test deploying VMs from each template

## Maintenance

**Update templates every 3-6 months:**
- Ubuntu: Download new cloud images
- LXC: Download updated templates from Proxmox
- Windows: Keep one template, update via Windows Update, re-sysprep
