# src/sealrepos/config.py: Pydantic models for configuration.
# This module defines the schema for the 'policy.yaml' configuration file using
# Pydantic models. It is responsible for loading, validating, and providing
# access to the configuration, ensuring that it adheres to the expected structure
# and types. It also handles schema versioning.

from __future__ import annotations

import yaml
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError
from typing import Any, List, Literal, Optional

from .util.paths import get_xdg_config_home, expand_path
from .util.errors import ConfigError

# --- Pydantic Models for Configuration Schema ---

class PushPolicy(BaseModel):
    allow_force_with_lease: bool = False

class PRPolicy(BaseModel):
    enable: bool = True
    reviewers: List[str] = Field(default_factory=list)
    labels: List[str] = Field(default_factory=lambda: ["sealbridge"])

class ScanPolicy(BaseModel):
    enable: bool = True
    tool: str = "gitleaks"
    config: Optional[str] = None

class PathPolicy(BaseModel):
    include: List[str] = Field(default_factory=list)
    exclude: List[str] = Field(
        default_factory=lambda: [
            "${HOME}/workspace/**",
            "**/.venv/**",
            "**/node_modules/**",
        ]
    )

class Defaults(BaseModel):
    interval_sec: int = 60
    jitter: float = 0.2
    protected_branches: List[str] = Field(default_factory=lambda: ["main", "master"])
    direction: Literal["bidirectional", "home-to-work", "work-to-home"] = "bidirectional"
    push: PushPolicy = Field(default_factory=PushPolicy)
    pr: PRPolicy = Field(default_factory=PRPolicy)
    scan: ScanPolicy = Field(default_factory=ScanPolicy)
    paths: PathPolicy = Field(default_factory=PathPolicy)

class Crypto(BaseModel):
    mode: Literal["git-crypt", "sops-age"] = "git-crypt"
    gpg_fprs: List[str] = Field(default_factory=list)

class Repo(BaseModel):
    name: str
    path: Path
    personal: str
    relay: Optional[str] = None
    mode: Literal["sealed", "plain", "nosync"]
    direction: Optional[Literal["bidirectional", "home-to-work", "work-to-home"]] = None
    protected_branches: Optional[List[str]] = None
    paths: Optional[PathPolicy] = None

class Config(BaseModel):
    version: int
    profile: Literal["work", "home"]
    defaults: Defaults = Field(default_factory=Defaults)
    crypto: Crypto = Field(default_factory=Crypto)
    repos: List[Repo] = Field(default_factory=list)


# --- Configuration Loading ---

def _expand_vars_in_obj(obj: Any) -> Any:
    """Recursively expand environment variables in a loaded YAML object."""
    if isinstance(obj, dict):
        return {key: _expand_vars_in_obj(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_expand_vars_in_obj(item) for item in obj]
    if isinstance(obj, str):
        # We only expand paths, not every string.
        # A simple heuristic: if it contains typical path chars, expand it.
        if "/" in obj or "\\" in obj or "${" in obj or "~" in obj:
             return str(expand_path(obj))
        return obj
    return obj

def load_config() -> Config:
    """
    Loads, validates, and returns the configuration from the XDG config path.
    """
    config_path = get_xdg_config_home() / "policy.yaml"
    if not config_path.is_file():
        raise ConfigError(
            f"Configuration file not found. Please create it at '{config_path}'."
        )

    try:
        with open(config_path, "r") as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Error parsing YAML configuration: {e}")

    # Recursively expand environment variables like ${HOME} before validation
    expanded_config = _expand_vars_in_obj(raw_config)

    try:
        config = Config.model_validate(expanded_config)
    except ValidationError as e:
        raise ConfigError(f"Configuration validation failed: {e}")

    return config
