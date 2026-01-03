# =============================================================================
# Enable PowerShell Remoting and Additional Configuration
# =============================================================================
# This script enables PowerShell remoting and performs additional
# configuration needed for Ansible management.
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Enabling PowerShell Remoting..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Enable PowerShell Remoting
Write-Host "Running Enable-PSRemoting..." -ForegroundColor Yellow
Enable-PSRemoting -Force -SkipNetworkProfileCheck

# Configure TrustedHosts (allow all for Packer/Ansible)
Write-Host "Configuring TrustedHosts..." -ForegroundColor Yellow
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force

# Set execution policy
Write-Host "Setting execution policy..." -ForegroundColor Yellow
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Force -Scope LocalMachine

# Increase MaxMemoryPerShellMB for large Ansible playbooks
Write-Host "Configuring WinRM memory limits..." -ForegroundColor Yellow
Set-Item WSMan:\localhost\Shell\MaxMemoryPerShellMB -Value 2048
Set-Item WSMan:\localhost\Plugin\Microsoft.PowerShell\Quotas\MaxMemoryPerShellMB -Value 2048

# Disable UAC remote restrictions
Write-Host "Disabling UAC remote restrictions..." -ForegroundColor Yellow
$regPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
Set-ItemProperty -Path $regPath -Name "EnableLUA" -Value 0

# Configure CredSSP (optional, for Ansible double-hop scenarios)
Write-Host "Enabling CredSSP..." -ForegroundColor Yellow
Enable-WSManCredSSP -Role Server -Force

# Disable Windows Defender real-time protection temporarily (speeds up provisioning)
Write-Host "Disabling Windows Defender real-time protection..." -ForegroundColor Yellow
try {
    Set-MpPreference -DisableRealtimeMonitoring $true -ErrorAction SilentlyContinue
} catch {
    Write-Host "Warning: Could not disable Defender. Continuing..." -ForegroundColor Yellow
}

# Disable Windows Update during setup (prevents reboots)
Write-Host "Pausing Windows Update..." -ForegroundColor Yellow
try {
    $AutoUpdate = (New-Object -ComObject Microsoft.Update.AutoUpdate)
    $AutoUpdate.Pause()
} catch {
    Write-Host "Warning: Could not pause Windows Update. Continuing..." -ForegroundColor Yellow
}

# Disable IE Enhanced Security Configuration
Write-Host "Disabling IE ESC..." -ForegroundColor Yellow
$AdminKey = "HKLM:\SOFTWARE\Microsoft\Active Setup\Installed Components\{A509B1A7-37EF-4b3f-8CFC-4F3A74704073}"
$UserKey = "HKLM:\SOFTWARE\Microsoft\Active Setup\Installed Components\{A509B1A8-37EF-4b3f-8CFC-4F3A74704073}"
Set-ItemProperty -Path $AdminKey -Name "IsInstalled" -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path $UserKey -Name "IsInstalled" -Value 0 -ErrorAction SilentlyContinue

# Enable Remote Registry (for some Ansible modules)
Write-Host "Enabling Remote Registry..." -ForegroundColor Yellow
Set-Service -Name RemoteRegistry -StartupType Automatic
Start-Service -Name RemoteRegistry

# Enable Windows Remote Management
Write-Host "Ensuring WinRM is running..." -ForegroundColor Yellow
Set-Service -Name WinRM -StartupType Automatic
Start-Service -Name WinRM

# Verify configuration
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Configuration Summary:" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "PowerShell Remoting: Enabled" -ForegroundColor White
Write-Host "WinRM Service: $(Get-Service WinRM | Select-Object -ExpandProperty Status)" -ForegroundColor White
Write-Host "Execution Policy: $(Get-ExecutionPolicy)" -ForegroundColor White
Write-Host "TrustedHosts: $(Get-Item WSMan:\localhost\Client\TrustedHosts | Select-Object -ExpandProperty Value)" -ForegroundColor White
Write-Host ""
Write-Host "Setup completed successfully!" -ForegroundColor Green
