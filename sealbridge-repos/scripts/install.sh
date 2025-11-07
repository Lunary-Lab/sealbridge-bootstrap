#!/bin/bash
# scripts/install.sh: One-liner installation script for Linux.
# This script automates the setup process by ensuring that XDG environment
# variables are set, installing 'uv', creating a virtual environment, and
# installing the project with its dependencies. It finishes by enabling the
# systemd user services for the daemon and/or bridge.

set -e

# --- XDG Setup ---
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME"

# --- Install uv ---
if ! command -v uv &> /dev/null; then
    echo "uv not found, installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.cargo/env"
fi

# --- Project Setup ---
VENV_DIR="$XDG_DATA_HOME/sealbridge/.venv"
uv venv "$VENV_DIR" -p 3.11
source "$VENV_DIR/bin/activate"

# Install dependencies and the project itself
uv pip install -e .

# --- Systemd Service ---
SYSTEMD_USER_DIR="$XDG_CONFIG_HOME/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"
cp system/linux/*.service "$SYSTEMD_USER_DIR/"
cp system/linux/*.timer "$SYSTEMD_USER_DIR/"
systemctl --user daemon-reload
systemctl --user enable --now sealreposd.timer
systemctl --user enable --now sealbridge-bridge.timer

echo "Installation complete."
