# Creating a Cloud-Init Template in Proxmox

## What is Cloud-Init?

Cloud-init is a tool that automatically configures VMs when they first boot. It allows Terraform to:
- Set the VM hostname
- Configure network settings (IP, gateway, DNS)
- Create user accounts with passwords
- Install SSH keys
- Run startup scripts

Without a cloud-init template, you'd have to manually configure each VM after creation.

## Creating an Ubuntu Cloud-Init Template

### Method 1: Using Proxmox Shell (Recommended - Fastest)

1. **SSH into your Proxmox server or use the Shell in the web UI:**
   - In Proxmox web UI: Click your node (e.g., "pve") → Shell

2. **Download Ubuntu Cloud Image:**
   ```bash
   # For Ubuntu 22.04 LTS
   wget https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img

   # OR for Ubuntu 24.04 LTS
   # wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
   ```

3. **Create a VM (ID 9000):**
   ```bash
   qm create 9000 --name ubuntu-cloud-template --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0
   ```

4. **Import the disk:**
   ```bash
   qm importdisk 9000 jammy-server-cloudimg-amd64.img local-lvm
   ```

5. **Configure the VM:**
   ```bash
   # Attach the disk
   qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0

   # Add cloud-init drive
   qm set 9000 --ide2 local-lvm:cloudinit

   # Set boot disk
   qm set 9000 --boot c --bootdisk scsi0

   # Add serial console
   qm set 9000 --serial0 socket --vga serial0

   # Enable QEMU agent
   qm set 9000 --agent enabled=1
   ```

6. **Convert to template:**
   ```bash
   qm template 9000
   ```

7. **Clean up:**
   ```bash
   rm jammy-server-cloudimg-amd64.img
   ```

8. **Done!** Your template is named `ubuntu-cloud-template`

### Method 2: Using Proxmox Web UI

1. **Download the cloud image to your computer:**
   - Go to: https://cloud-images.ubuntu.com/jammy/current/
   - Download: `jammy-server-cloudimg-amd64.img`

2. **Upload to Proxmox:**
   - In Proxmox UI: Select your storage → Upload
   - Upload the `.img` file

3. **Create VM manually:**
   - Click "Create VM"
   - VM ID: 9000
   - Name: ubuntu-cloud-template
   - Do NOT use ISO
   - Skip the OS tab
   - Disk: Delete the default disk
   - CPU: 2 cores
   - Memory: 2048 MB
   - Network: Default (vmbr0)

4. **Attach the cloud image via Shell:**
   ```bash
   qm importdisk 9000 /path/to/jammy-server-cloudimg-amd64.img local-lvm
   qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0
   qm set 9000 --ide2 local-lvm:cloudinit
   qm set 9000 --boot c --bootdisk scsi0
   qm set 9000 --serial0 socket --vga serial0
   qm set 9000 --agent enabled=1
   ```

5. **Convert to template:**
   - Right-click VM 9000 → Convert to template

## Using a Different Storage Pool

If you're not using `local-lvm`, replace it with your storage name:
- `local` - local storage
- `local-lvm` - local LVM storage
- Your custom storage name

Example for "local" storage:
```bash
qm importdisk 9000 jammy-server-cloudimg-amd64.img local
qm set 9000 --scsi0 local:vm-9000-disk-0
qm set 9000 --ide2 local:cloudinit
```

## Verify Your Template

After creating the template:

1. In Proxmox UI, go to your node
2. You should see VM 9000 named "ubuntu-cloud-template" with a template icon
3. Update `main.tf` line 12 to use: `template_name = "ubuntu-cloud-template"`

## Other Linux Distributions

### Debian 12
```bash
wget https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-generic-amd64.qcow2
qm create 9001 --name debian-cloud-template --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0
qm importdisk 9001 debian-12-generic-amd64.qcow2 local-lvm
# ... same steps as Ubuntu
```

### Rocky Linux 9
```bash
wget https://download.rockylinux.org/pub/rocky/9/images/x86_64/Rocky-9-GenericCloud-Base.latest.x86_64.qcow2
qm create 9002 --name rocky-cloud-template --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0
qm importdisk 9002 Rocky-9-GenericCloud-Base.latest.x86_64.qcow2 local-lvm
# ... same steps as Ubuntu
```

## Troubleshooting

**"storage 'local-lvm' does not exist"**
- Check your storage name: Datacenter → Storage
- Use the correct storage name in the commands

**"permission denied"**
- Make sure you're logged in as root on the Proxmox shell
- Or use `sudo` before commands

**Template not showing up**
- Refresh the Proxmox web UI
- Check the node where you created it

## Next Steps

After creating your template:
1. Update `main.tf` with the correct template name
2. Update `main.tf` with the correct storage name
3. Run `terraform apply -auto-approve`
