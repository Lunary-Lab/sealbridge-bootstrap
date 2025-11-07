# scripts/install.ps1: One-liner installation script for PowerShell (Windows).
# This script provides the same installation semantics as install.sh, but for
# a Windows environment using PowerShell. It sets up XDG directories, installs
# 'uv', creates the virtual environment, and sets up autostart entries.

# --- XDG Setup ---
$Env:XDG_CONFIG_HOME = [System.Environment]::GetEnvironmentVariable('XDG_CONFIG_HOME', 'User')
if ([string]::IsNullOrEmpty($Env:XDG_CONFIG_HOME)) {
    $Env:XDG_CONFIG_HOME = "$HOME\\.config"
}
$Env:XDG_DATA_HOME = [System.Environment]::GetEnvironmentVariable('XDG_DATA_HOME', 'User')
if ([string]::IsNullOrEmpty($Env:XDG_DATA_HOME)) {
    $Env:XDG_DATA_HOME = "$HOME\\.local\\share"
}
New-Item -ItemType Directory -Force -Path $Env:XDG_CONFIG_HOME, $Env:XDG_DATA_HOME

# --- Install uv ---
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv not found, installing..."
    irm https://astral.sh/uv/install.ps1 | iex
}

# --- Project Setup ---
$VenvDir = "$Env:XDG_DATA_HOME\\sealbridge\\.venv"
uv venv $VenvDir -p 3.11
& "$VenvDir\\Scripts\\activate.ps1"

# Install dependencies and the project
uv pip install -e .

# --- Autostart Setup ---
$AutostartDir = "$Env:XDG_CONFIG_HOME\\autostart"
New-Item -ItemType Directory -Force -Path $AutostartDir
Copy-Item "system\\windows\\autostart\\*.cmd" -Destination $AutostartDir

Write-Host "Installation complete."
