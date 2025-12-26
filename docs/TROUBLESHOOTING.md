# Troubleshooting Guide

> Part of the [Proxmox Infrastructure Documentation](../CLAUDE.md)

This guide documents resolved issues and common problems organized by category for quick reference.

---

## Table of Contents

- [Proxmox Cluster Issues](#proxmox-cluster-issues)
- [Kubernetes Issues](#kubernetes-issues)
- [Authentication Issues](#authentication-issues)
  - [GitLab SSO DNS Resolution Failure](#gitlab-sso-failed-to-open-tcp-connection-dns-resolution)
  - [GitLab SSO Client Secret Mismatch](#gitlab-sso-invalid-client-client-secret-mismatch)
  - [Jellyseerr OIDC Not Working with Latest Image](#jellyseerr-oidc-not-working-with-latest-image)
  - [Jellyseerr SSO Redirect URI Error](#jellyseerr-sso-redirect-uri-error)
  - [Jellyfin SSO Redirect URI Error (ForwardAuth vs SSO-Auth)](#jellyfin-sso-redirect-uri-error-forwardauth-vs-sso-auth)
- [Container & Docker Issues](#container--docker-issues)
  - [Jellyfin Shows Fewer Movies Than Download Monitor](#jellyfin-shows-fewer-movies-than-download-monitor)
  - [Glance Reddit Widget Timeout Error](#glance-reddit-widget-timeout-error)
  - [Glance Template Error - Wrong Number of Args](#glance-template-error---wrong-number-of-args)
- [Service-Specific Issues](#service-specific-issues)
- [Network Issues](#network-issues)
- [Common Issues](#common-issues)
- [Diagnostic Commands](#diagnostic-commands)

---

## Proxmox Cluster Issues

### Corosync SIGSEGV Crash

**Resolved**: December 2025

**Symptoms**:
- `corosync.service` fails to start with `status=11/SEGV`
- Logs stop at: `Initializing transport (Kronosnet)`
- Node cannot join cluster
- Reinstalling corosync alone doesn't fix it

**Root Cause**: Broken or mismatched NSS crypto stack (`libnss3`) caused Corosync to segfault during encrypted cluster transport initialization.

**Why It Happened**:
- Corosync uses kronosnet (knet) for cluster networking
- knet loads a crypto plugin (`crypto_nss`)
- The plugin relies on NSS crypto libraries (`libnss3`)
- Corrupted or mismatched library versions caused the crash

**Diagnosis**:
```bash
# 1. Validate configuration (should pass)
corosync -t

# 2. Install debug tools
apt install systemd-coredump gdb strace

# 3. After crash, analyze core dump
coredumpctl info corosync
```

**Stack trace showed failure in**: `PK11_CipherOp` -> `libnss3.so` -> `crypto_nss.so` -> `libknet.so`

**Resolution**:
```bash
apt install --reinstall -y \
  libnss3 libnss3-tools \
  libknet1t64 libnozzle1t64 \
  corosync libcorosync-common4
```

**Verification**:
```bash
systemctl start corosync
systemctl status corosync
pvecm status
journalctl -u corosync | grep crypto_nss
```

**Prevention**: Keep all nodes package-consistent with `apt update && apt full-upgrade -y`. Avoid partial upgrades.

---

### Node Showing Question Mark / Unhealthy Status

**Resolved**: December 2025

**Symptoms**:
- Question mark icon in Proxmox web UI
- "NR" (Not Ready) status in cluster membership

**Diagnosis**:
```bash
ping 192.168.20.22
ssh root@192.168.20.22 "pvecm status"
ssh root@192.168.20.22 "pvesh get /cluster/resources --type node"
```

**Resolution**:
1. If shutdown in progress: `shutdown -c` (may fail if too late)
2. If shutdown completed: Power on via physical access, IPMI, or WoL
3. If "NR" persists:
   ```bash
   ssh root@192.168.20.22 "systemctl restart pve-cluster && systemctl restart corosync"
   ```

**Verification**:
```bash
ssh root@192.168.20.22 "pvesh get /cluster/resources --type node"
ssh root@192.168.20.22 "pvecm status"
```

---

### Cloud-init VM Boot Failure - UEFI/BIOS Mismatch

**Resolved**: December 2025

**Symptoms**:
- VM creates successfully via Terraform
- Console stops at: `Btrfs loaded, zoned=yes, fsverity=yes`
- Boot hangs before cloud-init
- VM unreachable via SSH/ping

**Root Cause**: UEFI/BIOS boot mode mismatch between template and Terraform config.

**Resolution**: Update `modules/linux-vm/main.tf`:
```hcl
bios    = "ovmf"
machine = "q35"

efidisk {
  storage           = var.storage
  efitype           = "4m"
  pre_enrolled_keys = true
}

scsihw = "virtio-scsi-single"
```

**Lesson**: Always verify template boot mode with `qm config <vmid>` before deploying.

---

## Kubernetes Issues

### kubectl Connection Refused on Secondary Controllers

**Resolved**: December 20, 2025

**Symptoms**: On non-primary Kubernetes controllers (controller02, controller03):
```
E1220 15:24:01.489681    5376 memcache.go:265] couldn't get current server API group list
The connection to the server localhost:8080 was refused - did you specify the right host or port?
```

**Root Cause**: The kubeconfig file (`~/.kube/config`) was not set up on non-primary controller nodes. `kubeadm init` only sets up kubeconfig on the primary controller.

**Fix**:
```bash
# Copy from primary to secondary controllers
ssh hermes-admin@192.168.20.32 "cat ~/.kube/config" | ssh hermes-admin@192.168.20.33 "mkdir -p ~/.kube && cat > ~/.kube/config && chmod 600 ~/.kube/config"
ssh hermes-admin@192.168.20.32 "cat ~/.kube/config" | ssh hermes-admin@192.168.20.34 "mkdir -p ~/.kube && cat > ~/.kube/config && chmod 600 ~/.kube/config"
```

**Verification**:
```bash
for ip in 192.168.20.32 192.168.20.33 192.168.20.34; do
  echo "=== $ip ==="
  ssh hermes-admin@$ip "kubectl get nodes --no-headers | head -3"
done
```

**Prevention**: Add kubeconfig distribution to Kubernetes Ansible playbook post-deployment tasks.

---

### Kubelet Health Endpoint Not Accessible Externally (Glance Monitoring)

**Resolved**: December 22, 2025

**Symptoms**:
- Glance dashboard shows K8s workers as "ERROR" (red)
- K8s controllers show OK (green)
- Workers are actually healthy, just not reachable from Glance monitoring

**Root Cause**: By default, kubelet binds its health endpoint (`/healthz`) to `127.0.0.1:10248`, making it inaccessible from external monitoring tools like Glance running on a different host.

**Diagnosis**:
```bash
# Check kubelet bind address
ssh hermes-admin@192.168.20.40 "cat /var/lib/kubelet/config.yaml | grep healthzBindAddress"
# Output: healthzBindAddress: 127.0.0.1

# Verify kubelet only listens on localhost
ssh hermes-admin@192.168.20.40 "ss -tlnp | grep 10248"
# Output: LISTEN 127.0.0.1:10248 (only localhost)

# Test external access fails
curl -s --connect-timeout 3 http://192.168.20.40:10248/healthz
# Timeout or connection refused
```

**Fix**:
```bash
# Update all worker nodes to bind healthz to 0.0.0.0
for ip in 192.168.20.40 192.168.20.41 192.168.20.42 192.168.20.43 192.168.20.44 192.168.20.45; do
  echo "=== $ip ==="
  ssh hermes-admin@$ip "sudo sed -i 's/healthzBindAddress: 127.0.0.1/healthzBindAddress: 0.0.0.0/' /var/lib/kubelet/config.yaml && sudo systemctl restart kubelet"
done
```

**Verification**:
```bash
# Verify kubelet now listens on all interfaces
ssh hermes-admin@192.168.20.40 "ss -tlnp | grep 10248"
# Output: LISTEN *:10248 (all interfaces)

# Test external access works
for ip in 192.168.20.40 192.168.20.41 192.168.20.42 192.168.20.43 192.168.20.44 192.168.20.45; do
  echo -n "$ip: "
  curl -s --connect-timeout 3 http://$ip:10248/healthz
done
# All should return: ok
```

**Prevention**: Add kubelet healthz bind address configuration to Kubernetes Ansible deployment playbook.

---

## Authentication Issues

### Authentik ForwardAuth "Not Found" Error

**Resolved**: December 21, 2025

**Symptoms**: When accessing services protected by Authentik ForwardAuth (Grafana, Prometheus, Jaeger), users receive a "not found" error instead of being redirected to login.

**Root Cause**: The Authentik **Embedded Outpost had no providers assigned**. Proxy providers and applications were created, but never bound to the outpost that handles ForwardAuth requests from Traefik.

**Diagnosis**:
```bash
ssh hermes-admin@192.168.40.21 "sudo docker exec authentik-server ak shell -c \"
from authentik.outposts.models import Outpost
outpost = Outpost.objects.get(name='authentik Embedded Outpost')
print(f'Providers: {list(outpost.providers.values_list(\"name\", flat=True))}')
\""
# Empty list = problem
```

**Fix**:
```bash
ssh hermes-admin@192.168.40.21 "sudo docker exec authentik-server ak shell -c \"
from authentik.providers.proxy.models import ProxyProvider
from authentik.outposts.models import Outpost

providers = list(ProxyProvider.objects.all())
outpost = Outpost.objects.get(name='authentik Embedded Outpost')
for p in providers:
    outpost.providers.add(p)
outpost.save()
print(f'Added {len(providers)} providers to outpost')
\""
```

**Verification**:
```bash
# Should return 302 (redirect to login)
curl -s -k -o /dev/null -w "%{http_code}" https://grafana.hrmsmrflrii.xyz
```

**Prevention**:
1. Always assign new proxy providers to the Embedded Outpost in Authentik Admin UI
2. Include outpost assignment in blueprints
3. Verify outpost has providers assigned before testing

---

### Authentik "Permission Denied - Internal Users Only"

**Resolved**: December 24, 2025

**Symptoms**: User logs in via Google/GitHub OAuth and sees "Permission denied - Interface can only be accessed by internal users"

**Root Cause**: OAuth sources create users with `type=external` by default. The Authentik Admin Interface (`/if/admin/`) is restricted to internal users by design.

**Understanding User Types**:
| User Type | App Access | Admin UI Access |
|-----------|------------|-----------------|
| `internal` | ✅ Yes | ✅ Yes |
| `external` | ✅ Yes | ❌ No |

**Note**: External users CAN access regular applications (Grafana, Jellyfin, etc.) - this restriction only applies to the Authentik Admin Interface.

**Diagnosis**:
```bash
ssh hermes-admin@192.168.40.21 "sudo docker exec authentik-server ak shell -c \"
from authentik.core.models import User
for u in User.objects.all():
    print(f'{u.username}: type={u.type}')
\""
```

**Fix** (if user needs admin access):
```bash
ssh hermes-admin@192.168.40.21 "sudo docker exec authentik-server ak shell -c \"
from authentik.core.models import User
user = User.objects.get(username='USERNAME_HERE')
user.type = 'internal'
user.save()
print(f'Changed {user.username} to internal')
\""
```

**Verification**: User can now access https://auth.hrmsmrflrii.xyz/if/admin/

**Note**: Only change users to `internal` if they need admin access. Regular app users should remain `external` for security.

---

### GitLab SSO "Failed to open tcp connection" (DNS Resolution)

**Resolved**: December 24, 2025

**Symptoms**: When clicking "Authentik" SSO button on GitLab login page:
```
Could not authenticate you from OpenIDConnect because "Failed to open tcp connection to auth.hrmsmrflrii.xyz:443 (getaddrinfo: name or service not known)".
```

**Root Cause**: GitLab VM had incorrect DNS configuration. The netplan was configured with DNS server `192.168.20.1` instead of `192.168.91.30` (OPNsense). The VM couldn't resolve internal domain names like `auth.hrmsmrflrii.xyz`.

**Diagnosis**:
```bash
# Check DNS resolution from GitLab VM
ssh hermes-admin@192.168.40.23 "nslookup auth.hrmsmrflrii.xyz"
# Returns: NXDOMAIN = DNS misconfigured

# Check current DNS configuration
ssh hermes-admin@192.168.40.23 "resolvectl status | grep 'DNS Server'"
# Shows wrong DNS server
```

**Fix**:
```bash
# Update netplan DNS to correct server
ssh hermes-admin@192.168.40.23 "sudo sed -i 's/192.168.20.1/192.168.91.30/g' /etc/netplan/50-cloud-init.yaml"

# Apply changes
ssh hermes-admin@192.168.40.23 "sudo netplan apply"

# Verify DNS now works
ssh hermes-admin@192.168.40.23 "nslookup auth.hrmsmrflrii.xyz"
# Should return: 192.168.40.20 (Traefik IP)
```

**Verification**:
```bash
# Test from host
ssh hermes-admin@192.168.40.23 "nslookup auth.hrmsmrflrii.xyz && ping -c 2 192.168.40.20"

# Test from Docker container
ssh hermes-admin@192.168.40.23 "docker exec gitlab nslookup auth.hrmsmrflrii.xyz"
```

**Prevention**:
- Ensure all VLAN 40 VMs use DNS `192.168.91.30` (OPNsense)
- Verify DNS resolution works before configuring SSO
- Check Terraform `nameserver` variable in `main.tf` vm_groups

---

### GitLab SSO "Invalid client" (Client Secret Mismatch)

**Resolved**: December 24, 2025

**Symptoms**: After fixing DNS, clicking "Authentik" SSO button shows:
```
Could not authenticate you from OpenIDConnect because "Invalid client :: client authentication failed (e.g., unknown client, no client authentication included, or unsupported authentication method)".
```

**Root Cause**: The client secret in GitLab's docker-compose.yml was truncated/incorrect. The secret had:
- Wrong character: `Jtz41sHn` (digit "1") instead of `Jtz4lsHn` (lowercase "L")
- Truncated: Missing the second half of the secret string

**Diagnosis**:
```bash
# Get correct secret from Authentik database
ssh hermes-admin@192.168.40.21 "docker exec authentik-postgres psql -U authentik -d authentik -c \"
SELECT p.name, o.client_id, o.client_secret
FROM authentik_core_provider p
JOIN authentik_providers_oauth2_oauth2provider o ON p.id = o.provider_ptr_id
WHERE p.name ILIKE '%gitlab%';\""

# Compare with GitLab config
ssh hermes-admin@192.168.40.23 "grep 'secret:' /opt/gitlab/docker-compose.yml"
```

**Fix**:
```bash
# Update GitLab docker-compose.yml with correct secret
ssh hermes-admin@192.168.40.23 "sudo sed -i 's|secret: \"OLD_TRUNCATED_SECRET\"|secret: \"CORRECT_FULL_SECRET\"|' /opt/gitlab/docker-compose.yml"

# Restart GitLab
ssh hermes-admin@192.168.40.23 "cd /opt/gitlab && sudo docker compose down && sudo docker compose up -d"

# Wait for GitLab to initialize (2-3 minutes)
sleep 120 && curl -s -o /dev/null -w "%{http_code}" https://gitlab.hrmsmrflrii.xyz/users/sign_in
```

**Verification**:
1. Navigate to https://gitlab.hrmsmrflrii.xyz
2. Click "Authentik" button
3. Complete Authentik login
4. Should redirect back to GitLab logged in

**Prevention**:
- When copying OAuth secrets, verify full string length matches
- Use copy-paste carefully - "1" (one) vs "l" (lowercase L) are easy to confuse
- Test OIDC immediately after configuration to catch issues early

---

### Jellyfin SSO Button Not Showing on Login Page

**Resolved**: December 24, 2025

**Symptoms**: Jellyfin login page shows only username/password fields, no "Sign in with Authentik" button despite SSO-Auth plugin being installed and configured.

**Root Cause**: The SSO-Auth plugin does not automatically add a login button to the Jellyfin login page. The button must be manually added via Jellyfin's Branding settings.

**Fix**: Add SSO button via Jellyfin Dashboard:

1. Navigate to **Dashboard → General → Branding**
2. In the **"Login disclaimer"** field, add:
```html
<a href="/sso/OID/start/authentik" style="display: block; width: 100%; padding: 12px; margin-top: 10px; background-color: #00a4dc; color: white; text-align: center; text-decoration: none; border-radius: 4px; font-weight: bold;">Sign in with Authentik</a>
```
3. Click **Save**

**Verification**: Refresh Jellyfin login page - "Sign in with Authentik" button should appear below the password field.

**Note**: The button URL `/sso/OID/start/authentik` must match your provider name configured in SSO-Auth plugin settings.

---

### Jellyfin SSO invalid_grant Error

**Resolved**: December 24, 2025

**Symptoms**: After clicking "Sign in with Authentik", user is redirected to Authentik, logs in successfully, but upon redirect back to Jellyfin sees:
```
Error logging in: Error redeeming code: invalid_grant
The provided authorization grant or refresh token is invalid, expired, revoked,
does not match the redirection URI used in the authorization request,
or was issued to another client
```

**Root Cause**: Scheme mismatch during OAuth token exchange. Jellyfin behind Traefik reverse proxy doesn't know it's being accessed via HTTPS, so it generates `http://` redirect URIs during token exchange while the authorization was done with `https://`.

**Diagnosis**:
```bash
# Verify redirect URIs in Authentik match both HTTP and HTTPS
ssh hermes-admin@192.168.40.21 "sudo docker exec authentik-server ak shell -c \"
from authentik.providers.oauth2.models import OAuth2Provider
provider = OAuth2Provider.objects.get(name='jellyfin-provider')
print(provider.redirect_uris)
\""
```

**Fix**: Configure Scheme Override in SSO-Auth plugin:

1. Navigate to **Jellyfin Dashboard → Plugins → SSO-Auth → Settings**
2. In the provider dropdown, select your provider (e.g., "authentik")
3. Click **"Load Provider"**
4. Scroll down to find **"Scheme Override"** field
5. Set to: `https`
6. Click **"Save Provider"**
7. Restart Jellyfin container:
```bash
ssh hermes-admin@192.168.40.11 "docker restart jellyfin"
```

**Verification**:
1. Open Jellyfin login page
2. Click "Sign in with Authentik"
3. Complete Authentik login
4. Should redirect back to Jellyfin and be logged in successfully

**Prevention**: Always configure Scheme Override to `https` for services behind reverse proxies that terminate TLS.

---

### Jellyseerr OIDC Not Working with Latest Image

**Resolved**: December 24, 2025

**Symptoms**:
- OIDC environment variables configured but no SSO button appears
- API shows `openIdProviders: []` (empty array)
- No errors in logs, OIDC just silently not working

**Root Cause**: The `latest` Jellyseerr image does not include native OIDC support. OIDC is only available in the `preview-OIDC` branch image.

**Diagnosis**:
```bash
# Check current image
ssh hermes-admin@192.168.40.11 "docker inspect jellyseerr --format='{{.Config.Image}}'"
# If "fallenbagel/jellyseerr:latest" = OIDC not supported

# Check API for OIDC providers
ssh hermes-admin@192.168.40.11 "curl -s http://localhost:5056/api/v1/settings/public | jq '.openIdProviders'"
# Empty array [] = OIDC not enabled
```

**Fix**:
```bash
# Update docker-compose.yml to use preview-OIDC image
ssh hermes-admin@192.168.40.11 "sudo sed -i 's|fallenbagel/jellyseerr:latest|fallenbagel/jellyseerr:preview-OIDC|' /opt/arr-stack/docker-compose.yml"

# Recreate container
ssh hermes-admin@192.168.40.11 "cd /opt/arr-stack && sudo docker compose up -d --force-recreate jellyseerr"
```

Then configure OIDC via the UI: **Settings → Users → Configure OpenID Connect**

**Key Settings**:
- Discovery URL: `https://auth.hrmsmrflrii.xyz/application/o/jellyseerr/.well-known/openid-configuration`
- Client ID: From Authentik provider
- Client Secret: From Authentik provider
- Button Text: `Sign in with Authentik`

**Verification**:
```bash
# Check API now shows OIDC provider
ssh hermes-admin@192.168.40.11 "curl -s http://localhost:5056/api/v1/settings/public | jq '.openIdProviders'"
# Should show configured provider
```

**Note**: OIDC configuration via environment variables does NOT work. Must use the UI settings.

---

### Jellyseerr SSO Redirect URI Error

**Resolved**: December 24, 2025

**Symptoms**: After clicking SSO button and authenticating with Authentik, user is redirected back with error:
```
Redirect URI Error
The request fails due to a missing, invalid, or mismatching redirection URI
```

**Root Cause**: Two issues:
1. Jellyseerr uses a new callback format: `/login?provider=authentik&callback=true` (not the standard `/outpost.goauthentik.io/callback`)
2. Behind reverse proxy, Jellyseerr generates `http://` URIs instead of `https://`

**Diagnosis**:
```bash
# Check Authentik logs for the actual redirect URI being sent
ssh hermes-admin@192.168.40.21 "sudo docker logs authentik-server --tail 50 2>&1 | grep -i 'redirect'"
# Look for the redirect_uri parameter in the error
```

**Fix**: Add both HTTP and HTTPS redirect URIs with regex matching in Authentik:

```bash
ssh hermes-admin@192.168.40.21 "sudo docker exec authentik-server ak shell -c \"
from authentik.providers.oauth2.models import OAuth2Provider
from authentik.providers.oauth2.constants import RedirectURIMatchingMode
from authentik.providers.oauth2.models import RedirectURI

provider = OAuth2Provider.objects.get(name='jellyseerr-oidc-provider')
new_uris = [
    RedirectURI(matching_mode=RedirectURIMatchingMode.REGEX, url=r'https://jellyseerr\.hrmsmrflrii\.xyz/login\?provider=authentik.*'),
    RedirectURI(matching_mode=RedirectURIMatchingMode.REGEX, url=r'http://jellyseerr\.hrmsmrflrii\.xyz/login\?provider=authentik.*'),
    RedirectURI(matching_mode=RedirectURIMatchingMode.STRICT, url='https://jellyseerr.hrmsmrflrii.xyz/outpost.goauthentik.io/callback'),
]
provider.redirect_uris = new_uris
provider.save()
print('Updated redirect URIs')
\""
```

**Key Points**:
- Use `REGEX` matching mode for the callback URL (contains query parameters)
- Include BOTH `http://` and `https://` versions to handle scheme mismatch
- Escape dots in regex: `\.` not `.`

**Verification**:
1. Navigate to https://jellyseerr.hrmsmrflrii.xyz
2. Click "Sign in with Authentik"
3. Complete Authentik login
4. Should redirect back to Jellyseerr logged in

---

### Jellyfin SSO Redirect URI Error (ForwardAuth vs SSO-Auth)

**Resolved**: December 25, 2025

**Symptoms**:
- Clicking "Sign in with Authentik" on Jellyfin login page
- Authentik shows error: "Redirect URI Error - The request fails due to a missing, invalid, or mismatching redirection URI"
- User never completes login

#### Understanding the Concepts

Before diving into the fix, it's important to understand the key concepts involved:

##### What is a Redirect URI?

A **Redirect URI** (also called Callback URL) is a security mechanism in OAuth2/OIDC authentication. Here's how it works:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        OAuth2 Authentication Flow                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. User clicks "Login with Authentik" on Jellyfin                          │
│     │                                                                        │
│     ▼                                                                        │
│  2. Jellyfin redirects browser to Authentik with:                           │
│     - client_id: "jellyfin-app-id"                                          │
│     - redirect_uri: "https://jellyfin.example.com/sso/OID/redirect/authentik"│
│     - scope: "openid profile email groups"                                  │
│     │                                                                        │
│     ▼                                                                        │
│  3. Authentik VALIDATES the redirect_uri:                                    │
│     "Is https://jellyfin.example.com/sso/OID/redirect/authentik              │
│      in my list of allowed URIs for this client?"                           │
│     │                                                                        │
│     ├── YES → Show login page, continue flow                                │
│     └── NO  → ❌ "Redirect URI Error" (SECURITY BLOCK)                      │
│     │                                                                        │
│     ▼                                                                        │
│  4. User logs in (username/password, Google, etc.)                          │
│     │                                                                        │
│     ▼                                                                        │
│  5. Authentik redirects browser BACK to the redirect_uri with auth code     │
│     │                                                                        │
│     ▼                                                                        │
│  6. Jellyfin exchanges code for tokens, user is logged in                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Why is this validation important?**

Without redirect URI validation, an attacker could:
1. Create a malicious site that looks like Jellyfin
2. Trick users into clicking "Login with Authentik"
3. Change the redirect_uri to point to their malicious site
4. Steal the authentication token when Authentik redirects

The redirect URI whitelist ensures Authentik only sends tokens to legitimate, pre-approved URLs.

##### ForwardAuth vs SSO-Auth Plugin: Two Different Authentication Methods

There are **two completely different ways** to protect Jellyfin with Authentik:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  METHOD 1: ForwardAuth (Proxy-Based)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User → Traefik → [ForwardAuth Check] → Jellyfin                            │
│                         │                                                    │
│                         ▼                                                    │
│                    Authentik Outpost                                         │
│                                                                              │
│  How it works:                                                               │
│  1. User visits jellyfin.example.com                                         │
│  2. Traefik's ForwardAuth middleware asks Authentik: "Is this user logged in?"│
│  3. If NO: Redirect to Authentik login page                                  │
│  4. If YES: Allow request through to Jellyfin                               │
│                                                                              │
│  Redirect URIs used:                                                         │
│  - /outpost.goauthentik.io/callback                                          │
│  - /?X-authentik-auth-callback=true                                          │
│                                                                              │
│  Characteristics:                                                            │
│  - Authentication happens BEFORE reaching Jellyfin                          │
│  - Jellyfin doesn't know about authentication                               │
│  - User appears anonymous inside Jellyfin                                    │
│  - Good for simple "gate" protection                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                  METHOD 2: SSO-Auth Plugin (Native OIDC)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User → Traefik → Jellyfin → [SSO-Auth Plugin] → Authentik                  │
│                                                                              │
│  How it works:                                                               │
│  1. User visits jellyfin.example.com                                         │
│  2. Jellyfin shows login page with "Sign in with Authentik" button          │
│  3. User clicks button, Jellyfin redirects to Authentik                     │
│  4. User logs in at Authentik                                                │
│  5. Authentik redirects back to Jellyfin's SSO callback URL                 │
│  6. Jellyfin SSO-Auth plugin creates/links user account                     │
│                                                                              │
│  Redirect URIs used:                                                         │
│  - /sso/OID/redirect/authentik                                               │
│  - /sso/OID/start/authentik                                                  │
│                                                                              │
│  Characteristics:                                                            │
│  - Authentication happens INSIDE Jellyfin                                   │
│  - Jellyfin knows who the user is                                           │
│  - User gets a real Jellyfin account with proper permissions               │
│  - Supports groups/roles for admin privileges                               │
│  - Better user experience                                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key difference**: The redirect URIs are completely different between these methods!

| Method | Redirect URI Pattern | When to Use |
|--------|---------------------|-------------|
| ForwardAuth | `/outpost.goauthentik.io/callback` | Simple gate protection, no user accounts needed |
| SSO-Auth Plugin | `/sso/OID/redirect/authentik` | Full SSO with user accounts, groups, permissions |

##### The Scheme Mismatch Problem

An additional complication occurs when running behind a reverse proxy like Traefik:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Scheme Mismatch Problem                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  External (What users see):                                                 │
│  https://jellyfin.example.com  ◄── HTTPS (TLS terminated at Traefik)       │
│           │                                                                  │
│           ▼                                                                  │
│  Traefik (Reverse Proxy)                                                    │
│           │                                                                  │
│           ▼                                                                  │
│  Internal (What Jellyfin sees):                                             │
│  http://jellyfin:8096  ◄── HTTP (internal Docker network)                  │
│                                                                              │
│  Problem:                                                                    │
│  - Jellyfin thinks it's running on HTTP                                     │
│  - When generating redirect_uri, it uses: http://jellyfin.example.com/...  │
│  - But Authentik expects: https://jellyfin.example.com/...                  │
│  - MISMATCH! → "Redirect URI Error"                                         │
│                                                                              │
│  Solution:                                                                   │
│  1. Configure BOTH http:// and https:// versions in Authentik               │
│  2. OR set "Scheme Override" to "https" in SSO-Auth plugin settings         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Root Cause of This Issue

The Authentik provider `jellyfin-provider` was configured with **ForwardAuth redirect URIs**:
```
- https://jellyfin.hrmsmrflrii.xyz/outpost.goauthentik.io/callback?X-authentik-auth-callback=true
- https://jellyfin.hrmsmrflrii.xyz?X-authentik-auth-callback=true
```

But Jellyfin's **SSO-Auth plugin** sends a completely different redirect URI:
```
- https://jellyfin.hrmsmrflrii.xyz/sso/OID/redirect/authentik
```

Since `/sso/OID/redirect/authentik` was not in the allowed list, Authentik blocked the request with "Redirect URI Error".

**How this happened**:
- Initially, Jellyfin may have been set up with ForwardAuth (proxy-based auth)
- Later, the SSO-Auth plugin was installed for better integration
- But the Authentik provider's redirect URIs were never updated for the new method

#### Diagnosis

**Step 1**: Check what redirect URIs are currently configured:
```bash
ssh hermes-admin@192.168.40.21 "sudo docker exec authentik-server ak shell -c \"
from authentik.providers.oauth2.models import OAuth2Provider
p = OAuth2Provider.objects.get(name='jellyfin-provider')
print('Current redirect URIs:')
for uri in p.redirect_uris:
    print(f'  - {uri.url} (mode: {uri.matching_mode})')
\""
```

**Step 2**: Compare with what Jellyfin is sending (check Authentik logs):
```bash
ssh hermes-admin@192.168.40.21 "sudo docker logs authentik-server 2>&1 | grep -i 'redirect_uri' | tail -5"
```

**Step 3**: Verify Jellyfin SSO-Auth plugin is installed and configured:
```bash
ssh hermes-admin@192.168.40.11 "sudo docker exec jellyfin ls /config/plugins/ | grep -i sso"
```

#### Fix

Update the Authentik provider with the correct redirect URIs for the SSO-Auth plugin:

```bash
ssh hermes-admin@192.168.40.21 "sudo docker exec authentik-server ak shell -c \"
from authentik.providers.oauth2.models import OAuth2Provider, RedirectURI, RedirectURIMatchingMode

provider = OAuth2Provider.objects.get(name='jellyfin-provider')

# Set up correct redirect URIs for SSO-Auth plugin
new_uris = [
    # HTTPS version for SSO-Auth plugin callback
    RedirectURI(
        matching_mode=RedirectURIMatchingMode.STRICT,
        url='https://jellyfin.hrmsmrflrii.xyz/sso/OID/redirect/authentik'
    ),
    # HTTP version (needed because Jellyfin is behind reverse proxy)
    RedirectURI(
        matching_mode=RedirectURIMatchingMode.STRICT,
        url='http://jellyfin.hrmsmrflrii.xyz/sso/OID/redirect/authentik'
    ),
]
provider.redirect_uris = new_uris
provider.save()

print('Updated redirect URIs:')
for uri in provider.redirect_uris:
    print(f'  - {uri.url}')
\""
```

#### Verification

1. Navigate to https://jellyfin.hrmsmrflrii.xyz
2. Click "Sign in with Authentik" button
3. Log in at Authentik (Google, GitHub, Discord, or password)
4. Should redirect back to Jellyfin and be logged in

#### Summary Table

| Issue | Wrong Config | Correct Config |
|-------|--------------|----------------|
| Auth Method | ForwardAuth redirect URIs | SSO-Auth plugin redirect URIs |
| Redirect URI | `/outpost.goauthentik.io/callback` | `/sso/OID/redirect/authentik` |
| Scheme | HTTPS only | Both HTTP and HTTPS |

#### Prevention

When setting up SSO for an application:

1. **Identify the auth method first**: Is it ForwardAuth (proxy-based) or native OIDC/SSO?
2. **Check the application's documentation** for the exact redirect URI format
3. **Test the redirect URI**: Visit the SSO start URL and check browser's network tab for the actual redirect_uri being sent
4. **Always configure both HTTP and HTTPS** versions when the app is behind a TLS-terminating reverse proxy
5. **Document the configuration** so future troubleshooting is easier

**Prevention**: When configuring OIDC for services behind reverse proxies:
1. Check the actual callback URL format in Authentik logs
2. Add both HTTP and HTTPS versions of redirect URIs
3. Use regex matching for URLs with query parameters

---

## Container & Docker Issues

### Watchtower TLS Handshake Error

**Resolved**: December 2025

**Symptoms**: Watchtower logs show:
```
tls: first record does not look like a TLS handshake
```

**Root Cause**: Using `generic://` instead of `generic+http://` in webhook URL causes HTTPS connection to HTTP endpoint.

**Fix**: Update `WATCHTOWER_NOTIFICATION_URL` in docker-compose.yml:
```yaml
# Wrong
WATCHTOWER_NOTIFICATION_URL: "generic://192.168.40.10:5050/webhook"

# Correct
WATCHTOWER_NOTIFICATION_URL: "generic+http://192.168.40.10:5050/webhook"
```

Then restart: `cd /opt/watchtower && sudo docker compose restart`

---

### Update Manager SSH Key Not Accessible

**Resolved**: December 2025

**Symptoms**: Discord bot returns `❌ Update failed: Could not find compose directory`

**Root Cause**: SSH key not present on utilities host or not mounted in container.

**Fix**:
```bash
# Copy SSH key to host
scp ~/.ssh/homelab_ed25519 hermes-admin@192.168.40.10:/home/hermes-admin/.ssh/
ssh hermes-admin@192.168.40.10 "chmod 600 /home/hermes-admin/.ssh/homelab_ed25519"

# Restart container
ssh hermes-admin@192.168.40.10 "cd /opt/update-manager && sudo docker compose restart"
```

**Verification**:
```bash
ssh hermes-admin@192.168.40.10 "docker exec update-manager ssh -i /root/.ssh/homelab_ed25519 -o StrictHostKeyChecking=no hermes-admin@192.168.40.11 hostname"
```

---

### Docker Build Cache Issues

**Resolved**: December 2025

**Symptoms**: Code changes not reflected after container rebuild.

**Root Cause**: Docker caches build layers.

**Fix**: Force rebuild with no cache:
```bash
sudo docker compose down && sudo docker compose build --no-cache && sudo docker compose up -d
```

---

### Glance Reddit Widget Timeout Error

**Resolved**: December 22, 2025

**Symptoms**:
- Glance Reddit page shows error: `context deadline exceeded (Client.Timeout exceeded while awaiting headers)`
- Reddit Manager API takes too long to respond

**Root Cause**: Sequential fetching of multiple subreddits from Reddit API exceeded Glance's default timeout. Fetching 6 subreddits one-by-one could take 30+ seconds.

**Fix**: Updated Reddit Manager to fetch subreddits in parallel using ThreadPoolExecutor:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=6) as executor:
    future_to_sub = {executor.submit(fetch_subreddit_posts, sub, sort): sub for sub in subreddits}
    for future in as_completed(future_to_sub, timeout=15):
        posts = future.result()
```

**Verification**:
```bash
time curl -s "http://192.168.40.10:5053/api/feed" | head -c 100
# Should complete in ~2 seconds
```

**Prevention**: Parallel fetching is now default behavior.

---

### Glance Template Error - Wrong Number of Args

**Resolved**: December 22, 2025

**Symptoms**: Glance shows error: `template: :2:54: executing "" at <.JSON.String>: wrong number of args for String: want 1 got 2`

**Root Cause**: Attempting to access nested JSON in Glance template with incorrect syntax. Used `.JSON.String "settings" "sort"` but Glance's `.String` method only accepts one argument.

**Fix**: Simplified template to not access nested settings object:
```yaml
# Wrong - multiple arguments
{{ .JSON.String "settings" "sort" }}

# Correct - single key access only
{{ .String "title" }}
```

**Note**: Glance custom-api templates have limited support for nested JSON access. Keep API responses flat where possible.

---

## Service-Specific Issues

### Immich Container Restart Loop - Missing Directory Structure

**Resolved**: December 21, 2025

**Symptoms**:
- Immich container status shows "Restarting"
- Logs show: `Failed to read: "<UPLOAD_LOCATION>/encoded-video/.immich"`
- Container never becomes healthy

**Root Cause**: When pointing Immich to a new empty NFS share, the required directory structure with `.immich` marker files doesn't exist. Immich performs system integrity checks on startup.

**Diagnosis**:
```bash
ssh hermes-admin@192.168.40.22 "sudo docker logs immich-server --tail 30 2>&1 | grep -i error"
```

**Fix**:
```bash
ssh hermes-admin@192.168.40.22 "for dir in thumbs upload backups library profile encoded-video; do \
  sudo mkdir -p /mnt/immich-uploads/\$dir && \
  sudo touch /mnt/immich-uploads/\$dir/.immich; \
done"

ssh hermes-admin@192.168.40.22 "cd /opt/immich && sudo docker compose restart immich-server"
```

**Verification**:
```bash
ssh hermes-admin@192.168.40.22 "sudo docker ps --filter name=immich-server --format '{{.Status}}'"
# Should show "Up X seconds (healthy)" after ~30 seconds
```

**Prevention**: The Ansible playbook now includes tasks to create the directory structure automatically.

---

### Immich External Library Not Visible

**Resolved**: December 21, 2025

**Symptoms**:
- Immich UI shows "Click to upload your first photo"
- NFS mounts working on host but photos not visible in Immich

**Root Cause**: Docker volume mappings missing from docker-compose.yml. The container couldn't see the mounted directories.

**Diagnosis**:
```bash
# Check if container can see external library
ssh hermes-admin@192.168.40.22 "sudo docker exec immich-server ls /usr/src/app/external/ 2>&1"
# Returns "No such file or directory" if mapping missing
```

**Fix**: Update `/opt/immich/docker-compose.yml` volumes section:
```yaml
volumes:
  - /mnt/immich-uploads:/usr/src/app/upload
  - /mnt/synology-photos:/usr/src/app/external/synology:ro
```

Then restart:
```bash
ssh hermes-admin@192.168.40.22 "cd /opt/immich && sudo docker compose down && sudo docker compose up -d"
```

**Verification**:
```bash
ssh hermes-admin@192.168.40.22 "sudo docker exec immich-server ls /usr/src/app/external/synology/ | head -3"
```

---

### Immich Bad Gateway - NFS Mounts Not Mounted After Boot

**Resolved**: December 21, 2025

**Symptoms**:
- Browser shows "Bad Gateway" when accessing https://photos.hrmsmrflrii.xyz
- Immich container in restart loop with status "health: starting"
- Logs show: `Failed to read: "<UPLOAD_LOCATION>/encoded-video/.immich"`
- `microservices worker exited with code 1`

**Root Cause**: After VM reboot, NFS mounts (`/mnt/immich-uploads`, `/mnt/synology-photos`) did not mount automatically despite being in `/etc/fstab`. Immich's storage integrity check fails when the upload directory is empty or inaccessible.

**Diagnosis**:
```bash
# Check if NFS mounts are active
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "mount | grep nfs"
# Empty output = mounts missing

# Check upload directory
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "ls -la /mnt/immich-uploads/"
# If empty or shows local disk, mount is missing

# Check container logs for storage errors
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "docker logs immich-server --tail 30 2>&1 | grep -i 'error\|failed'"
```

**Fix**:
```bash
# Step 1: Mount all NFS shares from fstab
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "sudo mount -a"

# Step 2: Verify mounts are active
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "mount | grep -E 'immich|synology'"

# Step 3: Verify upload directory has content
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "ls -la /mnt/immich-uploads/"

# Step 4: Restart Immich server container
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "cd /opt/immich && docker compose restart immich-server"
```

**Verification**:
```bash
# Wait 30 seconds for health check, then verify
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "docker ps --format 'table {{.Names}}\t{{.Status}}' | grep immich"
# Should show "Up X seconds (healthy)"

# Test API endpoint
ssh -o ProxyJump=root@192.168.20.21 hermes-admin@192.168.40.22 "curl -s -o /dev/null -w '%{http_code}' http://localhost:2283/api/server/ping"
# Should return 200
```

**Prevention** (Implemented on immich-vm01):

Create a systemd service that mounts NFS before Docker starts:

```bash
# Create the service file
cat << 'EOF' | sudo tee /etc/systemd/system/mount-nfs-before-docker.service
[Unit]
Description=Mount NFS shares before Docker
After=network-online.target remote-fs.target
Before=docker.service
Wants=network-online.target
RequiresMountsFor=/mnt

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/bin/sleep 5
ExecStart=/bin/mount -a
ExecStart=/bin/bash -c 'mount | grep -q immich-uploads && echo NFS mounts ready || (echo NFS mount failed && exit 1)'

[Install]
WantedBy=multi-user.target docker.service
EOF

# Enable the service
sudo systemctl daemon-reload
sudo systemctl enable mount-nfs-before-docker.service
```

This ensures NFS mounts are ready before Docker containers start, preventing the "Bad Gateway" issue after reboots or migrations.

**Note**: If SSH to 192.168.40.22 times out from your workstation, use ProxyJump through a Proxmox node:
```bash
ssh -o ProxyJump=root@192.168.20.20 hermes-admin@192.168.40.22 "<command>"
```

---

### GitLab Unsupported Config Value (grafana)

**Resolved**: December 20, 2025

**Symptoms**: GitLab container restart loop with:
```
FATAL: Mixlib::Config::UnknownConfigOptionError: Reading unsupported config value grafana.
```

**Root Cause**: GitLab removed bundled Grafana support. The `grafana['enable'] = false` line is deprecated.

**Fix**: Remove `grafana['enable'] = false` from GITLAB_OMNIBUS_CONFIG in `/opt/gitlab/docker-compose.yml`:
```bash
cd /opt/gitlab && sudo docker compose down && sudo docker compose up -d
```

**Verification**:
```bash
docker ps --filter name=gitlab
docker exec gitlab gitlab-ctl status
```

**Prevention**: Review GitLab release notes for deprecated options before updates.

---

### Glance Dashboard "Migration should take around 5 minutes" Message

**Resolved**: December 22, 2025

**Symptoms**:
- Accessing https://glance.hrmsmrflrii.xyz shows "Migration should take around 5 minutes"
- Dashboard never loads, stuck on migration message
- Container logs show: `!!! WARNING !!! The default location of glance.yml in the Docker image has changed starting from v0.7.0.`

**Root Cause**: Glance v0.7.0 changed the config file location from `/app/glance.yml` (single file mount) to `/app/config/` (directory mount). The old docker-compose.yml was using the deprecated single-file mount format.

**Diagnosis**:
```bash
ssh hermes-admin@192.168.40.10 "docker logs glance 2>&1 | head -10"
# Look for: "The default location of glance.yml in the Docker image has changed"
```

**Fix**:
```bash
# Update docker-compose.yml to use directory mount format
ssh hermes-admin@192.168.40.10 "cat > /opt/glance/docker-compose.yml << 'EOF'
services:
  glance:
    image: glanceapp/glance:latest
    container_name: glance
    restart: unless-stopped
    ports:
      - 8080:8080
    volumes:
      - ./config:/app/config
      - ./assets:/app/assets:ro
      - /etc/timezone:/etc/timezone:ro
      - /etc/localtime:/etc/localtime:ro
    environment:
      - TZ=America/New_York
EOF"

# Restart the container
ssh hermes-admin@192.168.40.10 "cd /opt/glance && sudo docker compose down && sudo docker compose up -d"
```

**Key Changes**:
- Volume mount changed from `./glance.yml:/app/glance.yml` to `./config:/app/config`
- Config file must be at `/opt/glance/config/glance.yml` (not `/opt/glance/glance.yml`)
- Assets directory must also be mounted if `assets-path` is configured

**Verification**:
```bash
# Check logs for successful startup
ssh hermes-admin@192.168.40.10 "docker logs glance 2>&1"
# Should show: "Starting server on :8080"

# Test dashboard access
curl -s -o /dev/null -w "%{http_code}" https://glance.hrmsmrflrii.xyz
# Should return 200
```

**Prevention**:
- Monitor Glance release notes for breaking changes
- Ansible playbook `ansible-playbooks/glance/deploy-glance-dashboard.yml` has been updated to use the v0.7.0+ format
- See: https://github.com/glanceapp/glance/blob/main/docs/v0.7.0-upgrade.md

---

### Glance Service Health Showing ERROR for Traefik

**Resolved**: December 22, 2025

**Symptoms**: Glance dashboard shows Traefik as "ERROR" even though Traefik is running fine.

**Root Cause**: Glance was configured to use `http://192.168.40.20:8080/api/overview` which doesn't exist because Traefik's API is not exposed on port 8080 (insecure mode disabled).

**Fix**:
1. Enable Traefik ping endpoint on a dedicated entrypoint:
```bash
# Update traefik.yml to add ping entrypoint
ssh hermes-admin@192.168.40.20 "sudo cat >> /opt/traefik/config/traefik.yml << 'EOF'
ping:
  entryPoint: traefik
EOF"

# Add traefik entrypoint to entryPoints section:
#   traefik:
#     address: ":8082"

# Update docker-compose.yml to expose port 8082
# ports:
#   - "8082:8082"

# Restart Traefik
ssh hermes-admin@192.168.40.20 "cd /opt/traefik && sudo docker compose restart"
```

2. Update Glance config to use ping endpoint:
```bash
ssh hermes-admin@192.168.40.10 "sudo sed -i 's|url: http://192.168.40.20:8080/api/overview|url: http://192.168.40.20:8082/ping|' /opt/glance/config/glance.yml"
```

**Verification**:
```bash
curl -s http://192.168.40.20:8082/ping
# Should return: OK
```

---

### Glance Service Health Showing ERROR for GitLab

**Resolved**: December 22, 2025

**Symptoms**: Glance dashboard shows GitLab as "ERROR" or "Not Found".

**Root Cause**: Multiple issues:
1. GitLab's health endpoints (`/-/health`, `/-/readiness`) are restricted by `monitoring_whitelist` (default: localhost only)
2. DNS resolution fails on docker-vm-utilities01 for `gitlab.hrmsmrflrii.xyz`

**Fix**:
1. Use direct HTTP URL that returns 200:
```bash
ssh hermes-admin@192.168.40.10 "sudo sed -i 's|url: http://192.168.40.23/-/health|url: http://192.168.40.23/users/sign_in|' /opt/glance/config/glance.yml"
```

Note: Using `/users/sign_in` returns 200 without requiring health endpoint access.

**Alternative (if health endpoint needed)**:
```bash
# Enable monitoring from infrastructure network
ssh hermes-admin@192.168.40.23 "sudo docker exec gitlab sh -c \"echo \\\"gitlab_rails['monitoring_whitelist'] = ['127.0.0.0/8', '::1/128', '192.168.40.0/24', '192.168.20.0/24']\\\" >> /etc/gitlab/gitlab.rb\""
ssh hermes-admin@192.168.40.23 "sudo docker exec gitlab gitlab-ctl reconfigure"
```

**Verification**:
```bash
ssh hermes-admin@192.168.40.10 "curl -s -o /dev/null -w '%{http_code}' http://192.168.40.23/users/sign_in"
# Should return: 200
```

---

### Jellyfin Shows Fewer Movies Than Download Monitor

**Resolved**: December 24, 2025

**Symptoms**:
- Download Monitor (Discord bot) shows several movies downloaded
- Jellyfin only shows 5 movies in library
- Movies visible in `/mnt/media/Completed/` but not in `/mnt/media/Movies/`
- Jellyfin logs show: `Library folder /data/movies is inaccessible or empty, skipping`

**Root Causes (Multiple Issues)**:

1. **Docker Volume Mount Failure**: Jellyfin's `/data/movies` mount wasn't active despite being configured in docker-compose.yml. This was caused by nested bind mounts over NFS not initializing properly.

2. **Dual Root Folders in Radarr**: Two root folders configured (`/data/Movies` and `/movies`) causing inconsistent import paths. Some movies imported to one path, others to another.

3. **Missing SABnzbd Remote Path Mapping**: Only Deluge had remote path mapping configured. SABnzbd downloads weren't being tracked properly for automatic import.

4. **Stuck Radarr Command**: `ProcessMonitoredDownloads` command was stuck in "started" state, blocking other operations including manual imports.

**Diagnosis**:
```bash
# Check Jellyfin container mounts
ssh hermes-admin@192.168.40.11 "docker exec jellyfin ls -la /data/movies"
# Returns: "No such file or directory" = mount not active

# Check Radarr root folders
ssh hermes-admin@192.168.40.11 "curl -s 'http://localhost:7878/api/v3/rootfolder' -H 'X-Api-Key: YOUR_KEY' | jq '.[] | {id, path}'"
# Shows both /data/Movies AND /movies = dual root folder issue

# Check remote path mappings
ssh hermes-admin@192.168.40.11 "curl -s 'http://localhost:7878/api/v3/remotepathmapping' -H 'X-Api-Key: YOUR_KEY' | jq"
# Missing SABnzbd mapping

# Check for stuck commands
ssh hermes-admin@192.168.40.11 "curl -s 'http://localhost:7878/api/v3/command?pageSize=10' -H 'X-Api-Key: YOUR_KEY' | jq '.[] | {name, status}'"
```

**Fix - Step 1: Recreate Jellyfin Container**:
```bash
ssh hermes-admin@192.168.40.11 "cd /opt/arr-stack && sudo docker compose up -d --force-recreate jellyfin"
```

**Fix - Step 2: Add SABnzbd Remote Path Mapping**:
```bash
ssh hermes-admin@192.168.40.11 'curl -s -X POST "http://localhost:7878/api/v3/remotepathmapping" \
  -H "X-Api-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"host\":\"192.168.40.11\",\"remotePath\":\"/data/Completed/\",\"localPath\":\"/data/Completed/\"}"'
```

**Fix - Step 3: Consolidate Root Folders**:
```bash
# Update all movies to use /data/Movies path (Python script)
ssh hermes-admin@192.168.40.11 'cat > /tmp/fix_paths.py << '\''PYEOF'\''
import requests
API_KEY = "YOUR_KEY"
BASE_URL = "http://localhost:7878/api/v3"
HEADERS = {"X-Api-Key": API_KEY, "Content-Type": "application/json"}

movies = requests.get(f"{BASE_URL}/movie", headers=HEADERS).json()
for movie in movies:
    if movie["path"].startswith("/movies/"):
        movie["path"] = movie["path"].replace("/movies/", "/data/Movies/")
        movie["folderName"] = movie["path"]
        movie["rootFolderPath"] = "/data/Movies"
        requests.put(f"{BASE_URL}/movie/{movie[\"id\"]}?moveFiles=false", headers=HEADERS, json=movie)
        print(f"Updated: {movie[\"title\"]}")
PYEOF
python3 /tmp/fix_paths.py'

# Delete legacy root folder
ssh hermes-admin@192.168.40.11 'curl -s -X DELETE "http://localhost:7878/api/v3/rootfolder/3" -H "X-Api-Key: YOUR_KEY"'
```

**Fix - Step 4: Restart Radarr to Clear Stuck Commands**:
```bash
ssh hermes-admin@192.168.40.11 "docker restart radarr"
```

**Fix - Step 5: Trigger Manual Import for Orphaned Downloads**:
```bash
ssh hermes-admin@192.168.40.11 'curl -s -X POST "http://localhost:7878/api/v3/command" \
  -H "X-Api-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"DownloadedMoviesScan\"}"'
```

**Verification**:
```bash
# Verify Jellyfin sees movies
ssh hermes-admin@192.168.40.11 "docker exec jellyfin ls /data/movies/"

# Verify single root folder
ssh hermes-admin@192.168.40.11 "curl -s 'http://localhost:7878/api/v3/rootfolder' -H 'X-Api-Key: YOUR_KEY' | jq '.[] | .path'"
# Should only show: /data/Movies

# Verify movies have files
ssh hermes-admin@192.168.40.11 "curl -s 'http://localhost:7878/api/v3/movie' -H 'X-Api-Key: YOUR_KEY' | jq '[.[] | select(.hasFile == true)] | length'"
```

**Prevention**:
1. Use unified `/data` mount for all arr-stack services (documented in SERVICES.md)
2. Configure remote path mappings for ALL download clients
3. Use only ONE root folder per media type
4. Avoid nested Docker bind mounts over NFS - use single parent mount
5. Monitor Radarr commands for stuck operations

**Configuration Best Practices (docker-compose.yml)**:
```yaml
# All arr-stack services should use the same unified mount
volumes:
  - /mnt/media:/data  # Single parent mount

# NOT this (causes mount issues):
volumes:
  - /mnt/media:/data
  - /mnt/media/Movies:/data/movies  # Nested mount - problematic!
```

---

### Glance Bookmark Icons Not Displaying (Arr Stack)

**Resolved**: December 23, 2025

**Symptoms**: Several icons in the Media Apps bookmarks show as placeholder squares or missing:
- Lidarr, Prowlarr, Bazarr, Jellyseerr, Tdarr icons not loading

**Root Cause**: Simple Icons (`si:`) prefix works for some icons but not all. Some icons may not exist in Simple Icons or have different slug names.

**Fix**: Replace `si:` icons with Dashboard Icons URLs (more reliable):
```bash
# Fix Lidarr icon
ssh hermes-admin@192.168.40.10 'sudo sed -i "s|icon: si:lidarr|icon: https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/lidarr.png|g" /opt/glance/config/glance.yml'

# Fix Prowlarr icon
ssh hermes-admin@192.168.40.10 'sudo sed -i "s|icon: si:prowlarr|icon: https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/prowlarr.png|g" /opt/glance/config/glance.yml'

# Fix Bazarr icon
ssh hermes-admin@192.168.40.10 'sudo sed -i "s|icon: si:bazarr|icon: https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/bazarr.png|g" /opt/glance/config/glance.yml'

# Fix Jellyseerr icon
ssh hermes-admin@192.168.40.10 'sudo sed -i "s|icon: si:jellyseerr|icon: https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/jellyseerr.png|g" /opt/glance/config/glance.yml'

# Fix Tdarr icon
ssh hermes-admin@192.168.40.10 'sudo sed -i "s|icon: si:tdarr|icon: https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/tdarr.png|g" /opt/glance/config/glance.yml'

# Restart Glance
ssh hermes-admin@192.168.40.10 'cd /opt/glance && sudo docker compose restart'
```

**Icon Sources for Glance**:
| Source | Format | Example |
|--------|--------|---------|
| Simple Icons | `si:iconname` | `si:radarr` |
| Material Design | `mdi:iconname` | `mdi:home` |
| Dashboard Icons | Full URL | `https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/radarr.png` |

**Dashboard Icons Repository**: https://github.com/walkxcode/dashboard-icons

**Prevention**: For arr stack apps, prefer Dashboard Icons URLs as they are consistently maintained and display correctly.

---

## Network Issues

### VLAN-Aware Bridge Missing

**Symptoms**: `QEMU exited with code 1` on VM deployment

**Root Cause**: Node missing VLAN-aware bridge configuration.

**Fix**: Configure `/etc/network/interfaces`:
```bash
auto vmbr0
iface vmbr0 inet static
    address 192.168.20.XX/24
    gateway 192.168.20.1
    bridge-ports nic0
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 2-4094
```

Then: `ifreload -a` or reboot.

**Verify**:
```bash
ip -d link show vmbr0 | grep vlan_filtering
# Should show "vlan_filtering 1"
```

---

### NFS Mount Failures

**Diagnosis**:
```bash
showmount -e 192.168.20.31
df -h | grep nfs
mount -t nfs 192.168.20.31:/volume2/ProxmoxCluster-VMDisks /mnt/test
```

**Common Fixes**:
- Ensure NFS service running on NAS
- Check firewall rules (NFS ports 111, 2049)
- Verify export permissions include Proxmox node IPs
- For stale mounts: `umount -l /mnt/stale && mount -a`

---

## Common Issues

### Connection Refused Errors

**Symptom**: `dial tcp 192.168.20.21:8006: connectex: No connection could be made`

**Cause**: Proxmox API temporarily unavailable

**Solution**: Wait and retry, or check node status:
```bash
ssh root@192.168.20.21 "systemctl status pveproxy"
```

---

### Template Not Found (LXC)

**Symptom**: `template 'local:vztmpl/...' does not exist`

**Solution**:
```bash
ssh root@<node> "pveam update && pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
```

---

### Tainted Terraform Resources

**Symptom**: Resources marked as tainted

**Solution**: Run `terraform apply` to recreate properly

---

### Terraform State Lock

**Symptom**: Terraform state is locked

**Solution**:
1. Ensure no other terraform operations running
2. Force unlock if needed (caution): `terraform force-unlock <lock-id>`

---

## Diagnostic Commands

### Terraform
```bash
terraform state list
terraform state show <resource>
terraform refresh
terraform validate
terraform fmt
```

### Proxmox
```bash
pvecm status
pvesh get /cluster/resources --type node
qm config <vmid>
pct config <ctid>
systemctl status pve-cluster corosync pveproxy
journalctl -xeu corosync
coredumpctl info corosync
```

### Kubernetes
```bash
kubectl get nodes
kubectl get pods -A
kubectl describe node <node>
kubectl logs -n <namespace> <pod>
```

### Ansible
```bash
ansible all -m ping
ansible <host> -m setup
```

### Network
```bash
ip -d link show vmbr0 | grep vlan_filtering
bridge link show
ip route show
```

### Docker/Watchtower
```bash
docker logs <container> --tail 50
docker exec <container> <command>
ssh hermes-admin@192.168.40.10 "docker logs update-manager --tail 50"
ssh hermes-admin@192.168.40.11 "docker logs watchtower --tail 50"
```

### Authentik
```bash
# List providers
ssh hermes-admin@192.168.40.21 "sudo docker exec authentik-server ak shell -c \"
from authentik.providers.proxy.models import ProxyProvider
for p in ProxyProvider.objects.all():
    print(p.name)
\""

# Check outpost providers
ssh hermes-admin@192.168.40.21 "sudo docker exec authentik-server ak shell -c \"
from authentik.outposts.models import Outpost
outpost = Outpost.objects.get(name='authentik Embedded Outpost')
print(f'Providers: {outpost.providers.count()}')
\""
```

---

### Immich

```bash
# Check container health
ssh hermes-admin@192.168.40.22 "sudo docker ps --filter name=immich --format 'table {{.Names}}\t{{.Status}}'"

# View Immich logs
ssh hermes-admin@192.168.40.22 "sudo docker logs immich-server --tail 50"

# Verify NFS mounts
ssh hermes-admin@192.168.40.22 "mount | grep -E 'synology|immich'"

# Check container volume access
ssh hermes-admin@192.168.40.22 "sudo docker exec immich-server ls /usr/src/app/external/synology/ | head -5"
ssh hermes-admin@192.168.40.22 "sudo docker exec immich-server ls /usr/src/app/upload/"

# Test API health
ssh hermes-admin@192.168.40.22 "curl -s http://localhost:2283/api/server/ping"
```

---

## Related Documentation

- [Proxmox](./PROXMOX.md) - Cluster configuration
- [Networking](./NETWORKING.md) - Network configuration
- [Terraform](./TERRAFORM.md) - Deployment configuration
- [Services](./SERVICES.md) - Docker services
- [Application Configurations](./APPLICATION_CONFIGURATIONS.md) - Detailed app setup guides
- [Ansible](./ANSIBLE.md) - Automation playbooks
