# src/sbboot/config.py
"""Configuration loading and validation using Pydantic."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from . import paths
from .errors import ConfigError


class PolicyConfig(BaseModel):
    """Filesystem access policy."""
    include: List[str] = Field(default_factory=list)
    exclude: List[str] = Field(default_factory=lambda: ["${HOME}/workspace/**"])


class OtpGateConfig(BaseModel):
    """Configuration for the OTP verification gate."""
    url: HttpUrl
    client_id: str
    client_secret_env: str


class AgeBinaryConfig(BaseModel):
    """Configuration for the 'age' binary."""
    version: str
    checksums_url: HttpUrl


class AgeConfig(BaseModel):
    """Configuration for Age encryption."""
    binary: AgeBinaryConfig
    encrypted_key_path: str


class GitRepo(BaseModel):
    """Represents a Git repository to be cloned."""
    name: str
    url: str


class GitConfig(BaseModel):
    """Git-related configuration."""
    dotfiles_repo: str
    extra_repos: List[GitRepo] = Field(default_factory=list)
    branch: str = "main"


class ChezmoiAsset(BaseModel):
    """Represents a downloadable asset for chezmoi."""
    url: HttpUrl
    sha256: str


class ChezmoiConfig(BaseModel):
    """Configuration for the 'chezmoi' dotfiles manager."""
    version: str
    assets: Dict[str, ChezmoiAsset]


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    json_format: bool = Field(True, alias="json")


class BootstrapConfig(BaseModel):
    """Root configuration model."""
    version: int
    profile: str = "work"
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    otp_gate: OtpGateConfig
    age: AgeConfig
    git: GitConfig
    chezmoi: ChezmoiConfig
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    def get_chezmoi_asset_for_system(self, os_arch: str) -> Optional[ChezmoiAsset]:
        """Get the chezmoi asset for the given OS/architecture string (e.g., 'linux_amd64')."""
        return self.chezmoi.assets.get(os_arch)

    def resolve_path(self, path_str: str) -> Path:
        """Resolve a path string, expanding ${HOME} and making it absolute."""
        expanded_path = os.path.expanduser(path_str.replace("${HOME}", str(paths.HOME)))
        return Path(expanded_path).resolve()


@lru_cache(maxsize=1)
def load_config(path: Optional[Path] = None) -> BootstrapConfig:
    """
    Load, parse, and validate the bootstrap configuration file.

    Args:
        path: The path to the configuration file. If None, uses the default path.

    Returns:
        A validated BootstrapConfig instance.

    Raises:
        ConfigError: If the file is not found, cannot be read, or fails validation.
    """
    config_path = path or paths.get_default_config_path()
    if not config_path.is_file():
        raise ConfigError(
            f"Configuration file not found at '{config_path}'. "
            f"Please create it from the example."
        )

    try:
        content = config_path.read_bytes()
        data = yaml.safe_load(content)
        return BootstrapConfig.model_validate(data)
    except (IOError, PermissionError) as e:
        raise ConfigError(f"Failed to read configuration file '{config_path}': {e}") from e
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse configuration file '{config_path}': {e}") from e
    except ValidationError as e:
        raise ConfigError(f"Configuration validation failed:\n{e}") from e


# Global accessor for the loaded config
@lru_cache(maxsize=1)
def get_config() -> BootstrapConfig:
    """Returns the globally loaded application configuration."""
    return load_config()
