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

    if ! command -v "uv" >/dev/null 2>&1; then
        _info "Installing 'uv'..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        # Add cargo bin to PATH if it exists (uv installer places uv in ~/.cargo/bin)
        if [ -d "$HOME/.cargo/bin" ]; then
            export PATH="$HOME/.cargo/bin:$PATH"
        fi
        # Source cargo env if it exists (uv installer may add uv to PATH directly)
        if [ -f "$HOME/.cargo/env" ]; then
            . "$HOME/.cargo/env"
        fi
        # Verify uv is now available
        if ! command -v "uv" >/dev/null 2>&1; then
            _err "uv installation failed. Please install uv manually: https://github.com/astral-sh/uv"
        fi
    fi

    # Ensure we have Python 3.11+ available (uv can install Python if needed)
    _info "Ensuring Python 3.11+ is available..."
    if ! uv python list 3.11 2>/dev/null | grep -q "3.11"; then
        _info "Installing Python 3.11 via uv..."
        uv python install 3.11
    fi

    _info "Creating Python virtual environment with Python 3.11..."
    uv venv --python 3.11

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
