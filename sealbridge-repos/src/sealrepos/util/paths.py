# src/sealrepos/util/paths.py: XDG-compliant path resolution.
# This module provides functions for resolving XDG base directories (config,
# data, state, cache) on both Linux and Windows. It ensures that the application
# respects the user's environment variables and never writes outside of the
# user's HOME directory.

import os
from pathlib import Path
import platformdirs
from .errors import SealbridgeError

def get_xdg_config_home() -> Path:
    """Get the XDG_CONFIG_HOME path for the application."""
    return Path(platformdirs.user_config_dir("sealbridge"))

def get_xdg_data_home() -> Path:
    """Get the XDG_DATA_HOME path for the application."""
    return Path(platformdirs.user_data_dir("sealbridge"))

def get_xdg_state_home() -> Path:
    """Get the XDG_STATE_HOME path for the application."""
    return Path(platformdirs.user_state_dir("sealbridge"))

def get_xdg_cache_home() -> Path:
    """Get the XDG_CACHE_HOME path for the application."""
    return Path(platformdirs.user_cache_dir("sealbridge"))

def expand_path(path: str | Path) -> Path:
    """Expand environment variables and user home directory in a path."""
    return Path(os.path.expandvars(os.path.expanduser(str(path)))).resolve()

def ensure_home_guard(path: str | Path) -> None:
    """Raise an error if the path is outside the user's home directory."""
    home_dir = expand_path("~")
    resolved_path = expand_path(path)

    if not resolved_path.is_relative_to(home_dir):
        raise SealbridgeError(
            f"Path '{resolved_path}' is outside the user's HOME directory '{home_dir}'. "
            "Sealbridge is not allowed to operate outside of HOME."
        )
