# API Token Permissions Setup

## Error Received
```
user terraform-deployment-user@pve has valid credentials but cannot retrieve user list,
check privilege separation of api token
```

## Solution: Disable Privilege Separation

### Steps to Fix:

1. **Log into Proxmox Web UI** (https://192.168.20.21:8006)

2. **Navigate to API Token Settings:**
   - Click **Datacenter** (left sidebar)
   - Expand **Permissions**
   - Click **API Tokens**

3. **Find Your Token:**
   - Look for: `terraform-deployment-user@pve!tf`

4. **Check Privilege Separation:**
   - Look at the **Privsep** column
   - If it shows **Yes** or is checked, that's the problem

5. **Fix Option A - Edit Token (if possible):**
   - Select the token
   - Click **Edit**
   - **Uncheck** "Privilege Separation"
   - Click **OK**

6. **Fix Option B - Recreate Token (if editing not available):**
   - Select the token and click **Remove**
   - Click **Add** to create new token
   - Set:
     - **User:** `terraform-deployment-user@pve`
     - **Token ID:** `tf`
     - **Privilege Separation:** **UNCHECKED** ← Important!
   - Click **Add**
   - Copy the new secret and update `terraform.tfvars`

## Why This Happens

When **Privilege Separation** is enabled, the API token has its own separate permission set
from the user. When disabled, the token inherits all permissions from the user account.

## Verify User Has Permissions

While you're in Proxmox, verify the user has proper permissions:

1. Go to **Datacenter → Permissions**
2. Check if `terraform-deployment-user@pve` appears with appropriate permissions
3. If not, click **Add → User Permission**:
   - **Path:** `/`
   - **User:** `terraform-deployment-user@pve`
   - **Role:** `Administrator` or `PVEAdmin`
   - Click **Add**

## After Making Changes

Return to the terminal and run:
```bash
terraform apply
```

The deployment should proceed successfully.
