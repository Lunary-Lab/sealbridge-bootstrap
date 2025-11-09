#!/bin/sh
#
# SealBridge Bootstrap - POSIX Entrypoint Stub
#
# sh -c "$(curl -fsSL https://.../bootstrap.sh)"
#
set -euf

# --- Configuration ---
APP_VERSION="0.1.0"
PAYLOAD_URL="https://your-dist-server.com/sealbridge/bootstrap/v${APP_VERSION}/payload.tar.zst"
PAYLOAD_SHA256="<SHA256_CHECKSUM_EMBEDDED_HERE>"
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

main() {
    _check_dep "curl"
    _check_dep "tar"
    _check_dep "zstd"

    SHA256_CMD=$(_get_sha256_cmd)

    XDG_CACHE_HOME=${XDG_CACHE_HOME:-"$HOME/.cache"}
    APP_CACHE_DIR="$XDG_CACHE_HOME/sealbridge/bootstrap/$APP_VERSION"
    mkdir -p "$APP_CACHE_DIR"

    TMP_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'sb-bootstrap')
    PAYLOAD_PATH="$TMP_DIR/payload.tar.zst"

    _info "Downloading payload from $PAYLOAD_URL..."
    curl -fsSL --retry 3 -o "$PAYLOAD_PATH" "$PAYLOAD_URL"

    _info "Verifying payload checksum..."
    CHECKSUM=$($SHA256_CMD "$PAYLOAD_PATH" | cut -d' ' -f1)
    if [ "$CHECKSUM" != "$PAYLOAD_SHA256" ]; then
        _err "Checksum mismatch! Aborting."
    fi

    _info "Extracting payload to $APP_CACHE_DIR..."
    tar -I zstd -xf "$PAYLOAD_PATH" -C "$APP_CACHE_DIR"

    cd "$APP_CACHE_DIR"

    if ! command -v "uv" >/dev/null 2>&1; then
        _info "Installing 'uv'..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        . "$HOME/.cargo/env"
    fi

    _info "Creating Python virtual environment..."
    uv venv

    _info "Installing dependencies..."
    uv pip sync requirements.lock

    _info "Starting SealBridge Bootstrap application..."
    .venv/bin/python -m sbboot.cli run "$@"

    _info "Cleaning up..."
    rm -rf "$TMP_DIR"

    _info "Done."
}

main "$@"
