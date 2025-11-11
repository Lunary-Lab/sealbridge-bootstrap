# SealBridge Bootstrap - PowerShell Entrypoint
#
# $script = [System.Text.Encoding]::UTF8.GetString((Invoke-WebRequest -Uri "https://github.com/Lunary-Lab/sealbridge-bootstrap/releases/download/v0.1.0/bootstrap.ps1" -UseBasicParsing).Content); Invoke-Expression $script
#

$ErrorActionPreference = "Stop"

# --- Configuration ---
$APP_VERSION = "0.1.0"
$PAYLOAD_URL = "https://github.com/Lunary-Lab/sealbridge-bootstrap/releases/download/v0.1.0/payload.tar.gz"
$PAYLOAD_SHA256 = "7986abd5c47865559070c0b74663f1faa6db137cf5db035cc36cee8f4db387bb"
# ---

function Write-Info {
    param([string]$Message)
    Write-Host "sealbridge-bootstrap: $Message" -ForegroundColor Cyan
}

function Write-Error {
    param([string]$Message)
    Write-Host "sealbridge-bootstrap: ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Test-Command {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    if (-not $?) {
        Write-Error "'$Command' is required but not found in PATH."
    }
}

function Get-Sha256Hash {
    param([string]$FilePath)
    $hash = Get-FileHash -Path $FilePath -Algorithm SHA256
    return $hash.Hash.ToLower()
}

function Main {
    # Check dependencies
    Test-Command "curl"
    
    # Determine cache directory
    $XDG_CACHE_HOME = if ($env:XDG_CACHE_HOME) { $env:XDG_CACHE_HOME } else { "$env:USERPROFILE\.cache" }
    $APP_CACHE_DIR = "$XDG_CACHE_HOME\sealbridge\bootstrap\$APP_VERSION"
    New-Item -ItemType Directory -Force -Path $APP_CACHE_DIR | Out-Null
    
    # Create temp directory
    $TMP_DIR = New-TemporaryFile | ForEach-Object { Remove-Item $_; New-Item -ItemType Directory -Path $_ }
    $PAYLOAD_PATH = "$TMP_DIR\payload.tar.gz"
    
    Write-Info "Downloading payload from $PAYLOAD_URL..."
    try {
        Invoke-WebRequest -Uri $PAYLOAD_URL -OutFile $PAYLOAD_PATH -UseBasicParsing
    } catch {
        Write-Error "Failed to download payload: $_"
    }
    
    Write-Info "Verifying payload checksum..."
    $CHECKSUM = Get-Sha256Hash -FilePath $PAYLOAD_PATH
    if ($CHECKSUM -ne $PAYLOAD_SHA256) {
        Write-Error "Checksum mismatch! Expected: $PAYLOAD_SHA256, Got: $CHECKSUM"
    }
    
    Write-Info "Extracting payload to $APP_CACHE_DIR..."
    # Use tar if available (Windows 10 1903+), otherwise use 7zip or other tools
    if (Get-Command tar -ErrorAction SilentlyContinue) {
        # Use Windows tar (not WSL tar) - ensure we're using the Windows version
        $tarPath = (Get-Command tar -ErrorAction SilentlyContinue).Source
        if ($tarPath -like "*\Windows\*" -or $tarPath -like "*\Program Files\*") {
            & tar -xzf $PAYLOAD_PATH -C $APP_CACHE_DIR
        } else {
            # If it's WSL tar, try to find Windows tar or use alternative
            $windowsTar = "$env:SystemRoot\System32\tar.exe"
            if (Test-Path $windowsTar) {
                & $windowsTar -xzf $PAYLOAD_PATH -C $APP_CACHE_DIR
            } else {
                Write-Error "tar is required but not found. Please install tar (available on Windows 10 1903+ or via Git for Windows)."
            }
        }
    } else {
        Write-Error "tar is required but not found. Please install tar (available on Windows 10 1903+ or via Git for Windows)."
    }
    
    Set-Location $APP_CACHE_DIR
    
    # Check for uv
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Info "Installing 'uv'..."
        $uvInstallScript = "$TMP_DIR\install-uv.ps1"
        Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -OutFile $uvInstallScript -UseBasicParsing
        & $uvInstallScript
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    }
    
    Write-Info "Creating Python virtual environment..."
    & uv venv
    
    Write-Info "Installing dependencies..."
    & uv pip sync requirements.lock
    
    Write-Info "Starting SealBridge Bootstrap application..."
    & .venv\Scripts\python.exe -m sbboot.cli run @args
    
    Write-Info "Cleaning up..."
    Remove-Item -Recurse -Force $TMP_DIR
    
    Write-Info "Done."
}

Main @args
