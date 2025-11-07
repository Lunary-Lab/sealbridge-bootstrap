# tests/unit/test_config.py: Unit tests for configuration loading and validation.

import pytest
import os
from pathlib import Path
from pydantic import ValidationError

from sealrepos.config import load_config, Config
from sealrepos.util.errors import ConfigError

@pytest.fixture
def mock_config_dir(tmp_path: Path) -> Path:
    """Creates a mock XDG config directory structure and sets the environment variable."""
    # platformdirs will add 'sealbridge' to this path
    os.environ["XDG_CONFIG_HOME"] = str(tmp_path)
    config_dir = tmp_path / "sealbridge"
    config_dir.mkdir()
    return config_dir

def test_load_valid_config(mock_config_dir: Path):
    """Tests that a valid configuration file is loaded and parsed correctly."""
    config_content = """
version: 1
profile: home
repos:
  - name: "test-repo"
    path: "${HOME}/test-repo"
    personal: "git@github.com:user/test-repo.git"
    mode: "sealed"
"""
    (mock_config_dir / "policy.yaml").write_text(config_content)

    config = load_config()

    assert config.version == 1
    assert config.profile == "home"
    assert len(config.repos) == 1
    assert config.repos[0].name == "test-repo"
    assert config.repos[0].path == Path(os.path.expanduser("~/test-repo")).resolve()

def test_load_config_not_found(tmp_path: Path):
    """Tests that a ConfigError is raised if the config file doesn't exist."""
    os.environ["XDG_CONFIG_HOME"] = str(tmp_path)
    with pytest.raises(ConfigError, match="Configuration file not found"):
        load_config()

def test_config_validation_error(mock_config_dir: Path):
    """Tests that a ConfigError is raised on an invalid configuration."""
    # Corrected to use a proper newline
    config_content = "version: 1\nprofile: invalid_profile"
    (mock_config_dir / "policy.yaml").write_text(config_content)

    with pytest.raises(ConfigError, match="Configuration validation failed"):
        load_config()

def test_default_values_are_applied(mock_config_dir: Path):
    """Tests that default values are correctly applied to the config."""
    config_content = """
version: 1
profile: work
repos:
  - name: "test-repo"
    path: "/tmp/repo"
    personal: "git@personal"
    mode: "plain"
"""
    (mock_config_dir / "policy.yaml").write_text(config_content)

    config = load_config()

    assert config.defaults.interval_sec == 60
    assert config.defaults.pr.enable is True
    assert "main" in config.defaults.protected_branches
