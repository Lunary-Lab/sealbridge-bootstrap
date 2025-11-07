# tests/unit/test_policy.py: Unit tests for policy evaluation.

import pytest
from sealrepos.policy import is_protected_branch, build_pathspec
from pathlib import Path

def test_is_protected_branch():
    """Tests the protected branch logic."""
    protected = ["main", "develop"]
    assert is_protected_branch("main", protected) is True
    assert is_protected_branch("develop", protected) is True
    assert is_protected_branch("feature/new-stuff", protected) is False

def test_build_pathspec(tmp_path: Path):
    """Tests the pathspec generation and matching."""
    # Create some files
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").touch()
    (tmp_path / "src" / "README.md").touch()
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib").mkdir()

    include = ["**/*.py"]
    exclude = ["**/.venv/**"]

    spec = build_pathspec(include, exclude)
    files = list(spec.match_tree(str(tmp_path)))

    assert "src/main.py" in files
    assert "src/README.md" not in files
    assert all(not f.startswith('.venv') for f in files)
