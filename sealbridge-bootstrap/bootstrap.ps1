#
# SealBridge Bootstrap - PowerShell Entrypoint Stub
#
# iex (irm https://.../bootstrap.ps1)
#

# --- Configuration ---
$APP_VERSION = "0.1.0"
$PAYLOAD_URL = "https://your-dist-server.com/sealbridge/bootstrap/v$APP_VERSION/payload.zip"
$PAYLOAD_SHA256 = "<SHA256_CHECKSUM_EMBEDDED_HERE>"
# ---

function Write-Info {
    param([string]$Message)
    Write-Host "sealbridge-bootstrap: $Message"
}

function Write-Error {
    param([string]$Message)
    Write-Error "ERROR: $Message"
    exit 1
}

function Main {
    $XDG_CACHE_HOME = $env:XDG_CACHE_HOME
    if ([string]::IsNullOrEmpty($XDG_CACHE_HOME)) {
        $XDG_CACHE_HOME = Join-Path $env:USERPROFILE ".cache"
    }
    $APP_CACHE_DIR = Join-Path $XDG_CACHE_HOME "sealbridge/bootstrap/$APP_VERSION"
    if (-not (Test-Path $APP_CACHE_DIR)) {
        New-Item -ItemType Directory -Path $APP_CACHE_DIR | Out-Null
    }

    $TMP_DIR = New-Item -ItemType Directory -Path (Join-Path $env:TEMP ([System.Guid]::NewGuid().ToString()))
    $PAYLOAD_PATH = Join-Path $TMP_DIR "payload.zip"

    Write-Info "Downloading payload from $PAYLOAD_URL..."
    try {
        Invoke-RestMethod -Uri $PAYLOAD_URL -OutFile $PAYLOAD_PATH -UseBasicParsing
    } catch {
        Write-Error "Failed to download payload: $_"
    }

    Write-Info "Verifying payload checksum..."
    $CHECKSUM = (Get-FileHash -Algorithm SHA256 -Path $PAYLOAD_PATH).Hash.ToLower()
    if ($CHECKSUM -ne $PAYLOAD_SHA256.ToLower()) {
        Write-Error "Checksum mismatch! Aborting."
    }

    Write-Info "Extracting payload to $APP_CACHE_DIR..."
    try {
        Expand-Archive -Path $PAYLOAD_PATH -DestinationPath $APP_CACHE_DIR -Force
    } catch {
        Write-Error "Failed to extract payload: $_"
    }

    Push-Location $APP_CACHE_DIR

    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Info "Installing 'uv'..."
        try {
            Invoke-RestMethod -Uri "https://astral.sh/uv/install.ps1" | Invoke-Expression
        } catch {
            Write-Error "Failed to install 'uv': $_"
        }
    }

    Write-Info "Creating Python virtual environment..."
    uv.exe venv

    Write-Info "Installing dependencies..."
    uv.exe pip sync requirements.lock

    Write-Info "Starting SealBridge Bootstrap application..."
    $python_executable = Join-Path $APP_CACHE_DIR ".venv/Scripts/python.exe"
    & $python_executable -m sbboot.cli run $args

    Pop-Location
    Write-Info "Cleaning up..."
    Remove-Item -Recurse -Force $TMP_DIR

    Write-Info "Done."
}

Main $args
