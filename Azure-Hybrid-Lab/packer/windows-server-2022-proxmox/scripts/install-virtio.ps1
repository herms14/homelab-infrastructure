# =============================================================================
# Install VirtIO Drivers and QEMU Guest Agent
# =============================================================================
# This script installs VirtIO drivers from the mounted ISO and the QEMU
# Guest Agent for better Proxmox integration.
# =============================================================================

$ErrorActionPreference = "SilentlyContinue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installing VirtIO Drivers..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Find the VirtIO ISO drive letter (usually E:)
$virtIODrive = $null
Get-Volume | ForEach-Object {
    $driveLetter = $_.DriveLetter
    if ($driveLetter) {
        $testPath = "${driveLetter}:\guest-agent"
        if (Test-Path $testPath) {
            $virtIODrive = "${driveLetter}:"
            Write-Host "Found VirtIO ISO at $virtIODrive" -ForegroundColor Green
        }
    }
}

if (-not $virtIODrive) {
    Write-Host "VirtIO ISO not found, checking default locations..." -ForegroundColor Yellow
    $defaultDrives = @("E:", "D:", "F:")
    foreach ($drive in $defaultDrives) {
        if (Test-Path "${drive}\vioscsi") {
            $virtIODrive = $drive
            Write-Host "Found VirtIO ISO at $virtIODrive" -ForegroundColor Green
            break
        }
    }
}

if (-not $virtIODrive) {
    Write-Host "VirtIO ISO not found! Skipping driver installation." -ForegroundColor Red
    exit 0
}

# Install QEMU Guest Agent
Write-Host "Installing QEMU Guest Agent..." -ForegroundColor Yellow
$guestAgentMsi = Get-ChildItem -Path "${virtIODrive}\guest-agent\" -Filter "qemu-ga-x86_64.msi" -ErrorAction SilentlyContinue

if ($guestAgentMsi) {
    Write-Host "Installing $($guestAgentMsi.Name)..." -ForegroundColor Yellow
    Start-Process msiexec.exe -ArgumentList "/i", $guestAgentMsi.FullName, "/quiet", "/norestart" -Wait -NoNewWindow
    Write-Host "QEMU Guest Agent installed" -ForegroundColor Green
} else {
    Write-Host "QEMU Guest Agent MSI not found, skipping..." -ForegroundColor Yellow
}

# Install VirtIO drivers using pnputil
Write-Host "Installing VirtIO drivers via pnputil..." -ForegroundColor Yellow

$driverPaths = @(
    "${virtIODrive}\vioscsi\2k22\amd64",
    "${virtIODrive}\NetKVM\2k22\amd64",
    "${virtIODrive}\Balloon\2k22\amd64",
    "${virtIODrive}\qxldod\2k22\amd64",
    "${virtIODrive}\viorng\2k22\amd64",
    "${virtIODrive}\vioserial\2k22\amd64",
    "${virtIODrive}\pvpanic\2k22\amd64",
    "${virtIODrive}\qemupciserial\2k22\amd64"
)

foreach ($driverPath in $driverPaths) {
    if (Test-Path $driverPath) {
        $infFiles = Get-ChildItem -Path $driverPath -Filter "*.inf"
        foreach ($inf in $infFiles) {
            Write-Host "Installing driver: $($inf.Name)" -ForegroundColor Yellow
            pnputil.exe /add-driver $inf.FullName /install 2>&1 | Out-Null
        }
    }
}

# Set QEMU Guest Agent service to auto-start
Write-Host "Configuring QEMU Guest Agent service..." -ForegroundColor Yellow
$qemuService = Get-Service -Name "QEMU-GA" -ErrorAction SilentlyContinue
if ($qemuService) {
    Set-Service -Name "QEMU-GA" -StartupType Automatic
    Start-Service -Name "QEMU-GA" -ErrorAction SilentlyContinue
    Write-Host "QEMU Guest Agent service configured" -ForegroundColor Green
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "VirtIO driver installation completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
