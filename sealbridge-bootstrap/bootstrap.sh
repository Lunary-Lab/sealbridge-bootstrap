#!/bin/sh
#
# SealBridge Bootstrap - POSIX Entrypoint Stub
#
# sh -c "$(curl -fsSL https://.../bootstrap.sh)"
#
set -euf

# --- Configuration ---
APP_VERSION="0.1.26"
PAYLOAD_URL="https://github.com/Lunary-Lab/sealbridge-bootstrap/releases/download/v0.1.26/payload.tar.gz"
PAYLOAD_SHA256="7c8aaf68707d86f41d55968416af9810867df9bbb62e9910863b3e60360637a1"
# ---

_info() {
    printf "sealbridge-bootstrap: %s\\n" "$@" >&2
}

_warn() {
    printf "sealbridge-bootstrap: WARNING: %s\\n" "$@" >&2
}

_err() {
    printf "sealbridge-bootstrap: ERROR: %s\\n" "$@" >&2
    exit 1
}

_check_dep() {
    command -v "$1" >/dev/null 2>&1 || _err "'$1' is required but not found in PATH."
}

_get_sha256_cmd() {
    if command -v "sha256sum" >/dev/null 2>&1; then
        echo "sha256sum"
    elif command -v "shasum" >/dev/null 2>&1; then
        echo "shasum -a 256"
    else
        _err "Could not find 'sha256sum' or 'shasum' for checksum verification."
    fi
}

_add_bin_to_path() {
    # Only add to PATH if dotfiles are not configured (dotfiles will handle PATH)
    XDG_CONFIG_HOME=${XDG_CONFIG_HOME:-"$HOME/.config"}
    CONFIG_FILE="$XDG_CONFIG_HOME/sealbridge/bootstrap.yaml"
    
    # Check if dotfiles_repo is configured (not null or empty)
    if [ -f "$CONFIG_FILE" ]; then
        # Check if dotfiles_repo exists and has a non-null, non-empty value
        # YAML format: dotfiles_repo: "value" or dotfiles_repo: value (not null or empty string)
        if grep -q "^[[:space:]]*dotfiles_repo:" "$CONFIG_FILE" 2>/dev/null; then
            # Extract the value after the colon
            DOTFILES_REPO=$(grep "^[[:space:]]*dotfiles_repo:" "$CONFIG_FILE" | sed 's/.*dotfiles_repo:[[:space:]]*//' | sed 's/^"//' | sed 's/"$//' | sed "s/^'//" | sed "s/'$//")
            
            # Validate extracted value (prevent command injection)
            # Check for dangerous characters that could be used in command injection
            if echo "$DOTFILES_REPO" | grep -qE '[;&|`$(){}]'; then
                _err "Invalid characters in dotfiles_repo value. Potential security risk."
            fi
            
            # Check if it's not null, not empty, and not just whitespace
            if [ -n "$DOTFILES_REPO" ] && [ "$DOTFILES_REPO" != "null" ] && [ "$DOTFILES_REPO" != "~" ]; then
                _info "Dotfiles repository configured - skipping PATH modification (dotfiles will handle it)"
                return 0
            fi
        fi
    fi
    
    # Determine bin directory
    XDG_DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
    BIN_DIR="$XDG_DATA_HOME/sealbridge/bin"
    
    # Validate bin directory path to prevent path traversal
    EXPECTED_BIN_DIR="$XDG_DATA_HOME/sealbridge/bin"
    BIN_DIR_RESOLVED=$(cd "$BIN_DIR" 2>/dev/null && pwd) || BIN_DIR_RESOLVED=""
    EXPECTED_RESOLVED=$(cd "$EXPECTED_BIN_DIR" 2>/dev/null && pwd) || EXPECTED_RESOLVED=""
    
    if [ -n "$BIN_DIR_RESOLVED" ] && [ -n "$EXPECTED_RESOLVED" ] && [ "$BIN_DIR_RESOLVED" != "$EXPECTED_RESOLVED" ]; then
        _err "Invalid bin directory path: $BIN_DIR (resolved to $BIN_DIR_RESOLVED, expected $EXPECTED_RESOLVED)"
    fi
    
    mkdir -p "$BIN_DIR"
    
    # Detect shell and add to appropriate profile
    SHELL_NAME=$(basename "$SHELL" 2>/dev/null || echo "bash")
    PROFILE_FILE=""
    
    case "$SHELL_NAME" in
        bash)
            if [ -f "$HOME/.bashrc" ]; then
                PROFILE_FILE="$HOME/.bashrc"
            elif [ -f "$HOME/.bash_profile" ]; then
                PROFILE_FILE="$HOME/.bash_profile"
            fi
            ;;
        zsh)
            if [ -f "$HOME/.zshrc" ]; then
                PROFILE_FILE="$HOME/.zshrc"
            else
                # Create .zshrc if it doesn't exist on macOS (zsh is default shell)
                if [ "$(uname)" = "Darwin" ]; then
                    touch "$HOME/.zshrc"
                    PROFILE_FILE="$HOME/.zshrc"
                fi
            fi
            ;;
        fish)
            if [ -d "$HOME/.config/fish" ]; then
                PROFILE_FILE="$HOME/.config/fish/config.fish"
            fi
            ;;
    esac
    
    if [ -z "$PROFILE_FILE" ]; then
        # Fallback to .profile
        PROFILE_FILE="$HOME/.profile"
    fi
    
    # Check if already in PATH
    if grep -q "$BIN_DIR" "$PROFILE_FILE" 2>/dev/null; then
        _info "SealBridge bin directory already in PATH"
        return 0
    fi
    
    # Validate BIN_DIR one more time before writing
    if [ ! -d "$BIN_DIR" ]; then
        _err "Bin directory does not exist: $BIN_DIR"
    fi
    
    # Ensure BIN_DIR is within expected XDG directory (prevent path traversal)
    if ! echo "$BIN_DIR" | grep -q "^$XDG_DATA_HOME/sealbridge/bin"; then
        _err "Bin directory path validation failed: $BIN_DIR (must be within $XDG_DATA_HOME/sealbridge/bin)"
    fi
    
    # Add to PATH
    _info "Adding SealBridge bin directory to PATH in $PROFILE_FILE..."
    {
        echo ""
        echo "# SealBridge bin directory (added by bootstrap.sh)"
        # Escape the path properly to prevent injection
        ESCAPED_BIN_DIR=$(printf '%s\n' "$BIN_DIR" | sed 's/[[\.*^$()+?{|]/\\&/g')
        echo "export PATH=\"\$PATH:$ESCAPED_BIN_DIR\""
    } >> "$PROFILE_FILE"
    
    _info "✅ Added $BIN_DIR to PATH in $PROFILE_FILE"
    _info "Note: You may need to restart your shell or run: source $PROFILE_FILE"
}

main() {
    _check_dep "curl"
    _check_dep "tar"

    SHA256_CMD=$(_get_sha256_cmd)

    XDG_CACHE_HOME=${XDG_CACHE_HOME:-"$HOME/.cache"}
    APP_CACHE_DIR="$XDG_CACHE_HOME/sealbridge/bootstrap/$APP_VERSION"
    mkdir -p "$APP_CACHE_DIR"

    TMP_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'sb-bootstrap')
    PAYLOAD_PATH="$TMP_DIR/payload.tar.gz"

    _info "Downloading payload from $PAYLOAD_URL..."
    curl -fsSL --retry 3 -o "$PAYLOAD_PATH" "$PAYLOAD_URL"

    _info "Verifying payload checksum..."
    CHECKSUM=$($SHA256_CMD "$PAYLOAD_PATH" | cut -d' ' -f1)
    if [ "$CHECKSUM" != "$PAYLOAD_SHA256" ]; then
        _err "Checksum mismatch! Aborting."
    fi

    _info "Extracting payload to $APP_CACHE_DIR..."
    tar -xzf "$PAYLOAD_PATH" -C "$APP_CACHE_DIR"

    cd "$APP_CACHE_DIR"

    # Check for existing uv installation (common locations)
    UV_CMD=""
    for uv_path in \
        "$HOME/.local/bin/uv" \
        "$HOME/.cargo/bin/uv" \
        "/usr/local/bin/uv" \
        "/opt/homebrew/bin/uv"; do
        if [ -x "$uv_path" ]; then
            UV_CMD="$uv_path"
            _info "Found existing uv at $uv_path"
            export PATH="$(dirname "$uv_path"):$PATH"
            break
        fi
    done
    
    # If not found, check PATH
    if [ -z "$UV_CMD" ] && command -v "uv" >/dev/null 2>&1; then
        UV_CMD="uv"
        _info "Found uv in PATH"
    fi
    
    # Install uv if not found
    if [ -z "$UV_CMD" ]; then
        _info "Installing 'uv'..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Add cargo bin to PATH if it exists (uv installer places uv in ~/.cargo/bin)
        if [ -d "$HOME/.cargo/bin" ]; then
            export PATH="$HOME/.cargo/bin:$PATH"
        fi
        # Also check ~/.local/bin (newer uv installers)
        if [ -d "$HOME/.local/bin" ]; then
            export PATH="$HOME/.local/bin:$PATH"
        fi
        # Source cargo env if it exists (uv installer may add uv to PATH directly)
        if [ -f "$HOME/.cargo/env" ]; then
            . "$HOME/.cargo/env"
        fi
        # Verify uv is now available
        if ! command -v "uv" >/dev/null 2>&1; then
            _err "uv installation failed. Please install uv manually: https://github.com/astral-sh/uv"
        fi
        UV_CMD="uv"
    fi

    # Install Python 3.11 via uv (required - cannot use system Python)
    _info "Installing Python 3.11 via uv..."
    
    # Check if Python 3.11 is already installed via uv
    PYTHON_SPEC=""
    if "$UV_CMD" python list 3.11 2>/dev/null | grep -q "3.11"; then
        _info "Python 3.11 already installed via uv"
        # Try to get the actual path to the installed Python
        PYTHON_PATH="$("$UV_CMD" python list 3.11 2>/dev/null | grep "3.11" | head -1 | awk '{print $NF}' || echo "")"
        if [ -n "$PYTHON_PATH" ] && [ -x "$PYTHON_PATH" ]; then
            PYTHON_SPEC="$PYTHON_PATH"
            _info "Using Python at: $PYTHON_PATH"
        else
            # Fall back to version specifier
            PYTHON_SPEC="3.11"
        fi
    else
        # Try to install Python 3.11 via uv
        # On macOS with corporate proxies, uv may fail due to SSL certificate issues
        # uv uses rustls which may not use the macOS system certificate store
        _info "Downloading Python 3.11 (this may take a moment)..."
        
        # On macOS, try to export certificates from keychain for rustls
        if [ "$(uname)" = "Darwin" ]; then
            # Create a temporary certificate bundle from macOS keychain
            # This helps rustls (used by uv) access system certificates
            CERT_BUNDLE=""
            if command -v security >/dev/null 2>&1; then
                CERT_BUNDLE="$(mktemp)"
                # Export system root certificates to a PEM file
                security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain > "$CERT_BUNDLE" 2>/dev/null || true
                # Also try to get user certificates if available
                security find-certificate -a -p /Library/Keychains/System.keychain >> "$CERT_BUNDLE" 2>/dev/null || true
                
                if [ -s "$CERT_BUNDLE" ]; then
                    export SSL_CERT_FILE="$CERT_BUNDLE"
                    export REQUESTS_CA_BUNDLE="$CERT_BUNDLE"
                    export CURL_CA_BUNDLE="$CERT_BUNDLE"
                    _info "Using system certificates from macOS keychain"
                else
                    rm -f "$CERT_BUNDLE"
                    CERT_BUNDLE=""
                fi
            fi
        fi
        
        # Try to install Python via uv
        UV_OUTPUT="$("$UV_CMD" python install 3.11 2>&1)"
        UV_EXIT=$?
        
        # Clean up temporary certificate bundle
        if [ -n "$CERT_BUNDLE" ] && [ -f "$CERT_BUNDLE" ]; then
            rm -f "$CERT_BUNDLE"
        fi
        
        if [ $UV_EXIT -eq 0 ]; then
            PYTHON_SPEC="3.11"
            _info "Python 3.11 installed successfully"
        else
            # Check if it's an SSL certificate error
            if echo "$UV_OUTPUT" | grep -qi "certificate\|SSL\|TLS\|peer certificate"; then
                _warn "uv failed due to SSL certificate issues (likely corporate proxy/firewall)"
                _warn "Attempting workaround: downloading Python manually with curl..."
                
                # Workaround: Use curl (which uses system certificates) to download Python
                # Then tell uv to use it
                PYTHON_VERSION="3.11.14"
                ARCH="$(uname -m)"
                if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
                    ARCH_SUFFIX="aarch64-apple-darwin"
                else
                    ARCH_SUFFIX="x86_64-apple-darwin"
                fi
                
                # Get the latest Python 3.11 version from uv's known versions
                # Try common recent versions
                for PYTHON_VERSION in "3.11.14" "3.11.13" "3.11.12" "3.11.11" "3.11.10"; do
                    ARCH="$(uname -m)"
                    if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
                        ARCH_SUFFIX="aarch64-apple-darwin"
                    else
                        ARCH_SUFFIX="x86_64-apple-darwin"
                    fi
                    
                    # Try different release dates (uv uses specific build dates)
                    for BUILD_DATE in "20251205" "20251124" "20251110"; do
                        PYTHON_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${BUILD_DATE}/cpython-${PYTHON_VERSION}+${BUILD_DATE}-${ARCH_SUFFIX}-install_only_stripped.tar.gz"
                        PYTHON_TAR="$(mktemp)"
                        
                        _info "Trying to download Python ${PYTHON_VERSION} (build ${BUILD_DATE}) via curl..."
                        if curl -fsSL "$PYTHON_URL" -o "$PYTHON_TAR" && [ -s "$PYTHON_TAR" ]; then
                            _info "Downloaded Python via curl, extracting..."
                            # Extract to uv's Python directory structure
                            # uv stores Python as: ~/.local/share/uv/python/cpython-{version}+{date}-{arch}/
                            UV_PYTHON_BASE="$HOME/.local/share/uv/python"
                            PYTHON_DIR_NAME="cpython-${PYTHON_VERSION}+${BUILD_DATE}-${ARCH_SUFFIX}"
                            mkdir -p "$UV_PYTHON_BASE/$PYTHON_DIR_NAME"
                            
                            # Extract the tarball
                            if tar -xzf "$PYTHON_TAR" -C "$UV_PYTHON_BASE/$PYTHON_DIR_NAME" 2>/dev/null; then
                                rm -f "$PYTHON_TAR"
                                
                                # Verify uv can see it
                                if "$UV_CMD" python list 3.11 2>/dev/null | grep -q "3.11"; then
                                    PYTHON_SPEC="3.11"
                                    _info "Python 3.11 installed successfully via workaround"
                                    break 2
                                else
                                    _warn "Python extracted but uv cannot detect it, trying next version..."
                                    rm -rf "$UV_PYTHON_BASE/$PYTHON_DIR_NAME"
                                fi
                            else
                                rm -f "$PYTHON_TAR"
                                _warn "Failed to extract Python tarball, trying next version..."
                            fi
                        else
                            rm -f "$PYTHON_TAR"
                        fi
                    done
                done
                
                if [ -z "$PYTHON_SPEC" ]; then
                    _err "Failed to install Python 3.11 via workaround. SSL certificate issues detected. Please install Python 3.11 manually or configure your system certificates."
                fi
            else
                _err "Failed to install Python 3.11 via uv: $UV_OUTPUT"
            fi
        fi
    fi
    
    _info "Creating Python virtual environment with Python $PYTHON_SPEC..."
    
    # Try to create venv - if it fails with SSL error, use workaround
    VENV_OUTPUT="$("$UV_CMD" venv --python "$PYTHON_SPEC" 2>&1)"
    VENV_EXIT=$?
    
    if [ $VENV_EXIT -ne 0 ]; then
        # Check if it's an SSL certificate error
        if echo "$VENV_OUTPUT" | grep -qi "certificate\|SSL\|TLS\|peer certificate"; then
            _warn "uv venv failed due to SSL certificate issues"
            _warn "Python 3.11 is installed but uv cannot verify it. Trying workaround..."
            
            # If we have a Python path, try using it directly
            if [ -n "$PYTHON_PATH" ] && [ -x "$PYTHON_PATH" ]; then
                _info "Using Python directly: $PYTHON_PATH"
                "$UV_CMD" venv --python "$PYTHON_PATH" || {
                    _warn "Direct Python path failed, trying without --python flag..."
                    # Last resort: let uv use whatever Python it finds
                    "$UV_CMD" venv || _err "Failed to create virtual environment"
                }
            else
                # Try without specifying Python version - let uv use what it finds
                _warn "Trying to create venv without specifying Python version..."
                "$UV_CMD" venv || _err "Failed to create virtual environment. SSL certificate issues detected."
            fi
        else
            _err "Failed to create virtual environment: $VENV_OUTPUT"
        fi
    fi

    _info "Installing dependencies..."
    uv pip sync requirements.lock

    _info "Installing sbboot package..."
    uv pip install -e .

    # Ensure XDG directories exist
    XDG_DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
    XDG_CONFIG_HOME=${XDG_CONFIG_HOME:-"$HOME/.config"}
    XDG_CACHE_HOME=${XDG_CACHE_HOME:-"$HOME/.cache"}
    XDG_STATE_HOME=${XDG_STATE_HOME:-"$HOME/.local/state"}
    mkdir -p "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$XDG_STATE_HOME"

    # Add bin directory to PATH if dotfiles are not configured
    _add_bin_to_path

    _info "Starting SealBridge Bootstrap application..."
    # Environment variables are automatically inherited by Python subprocess
    .venv/bin/python -m sbboot.cli run "$@"

    _info "Cleaning up..."
    rm -rf "$TMP_DIR"

    _info "Done."
}

main "$@"
