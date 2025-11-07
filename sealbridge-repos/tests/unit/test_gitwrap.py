# tests/unit/test_gitwrap.py: Unit tests for the Git wrapper.

import pytest
import subprocess
from pathlib import Path

from sealrepos.gitwrap import run_git, git_current_branch
from sealrepos.util.errors import GitError

def test_run_git_success(monkeypatch, tmp_path: Path):
    """Tests that run_git successfully executes a command."""
    def mock_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="main", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    result = run_git(["symbolic-ref", "HEAD"], cwd=tmp_path)
    assert result.stdout == "main"

def test_run_git_failure(monkeypatch, tmp_path: Path):
    """Tests that run_git raises a GitError on a non-zero exit code."""
    def mock_run(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args, stderr="fatal: not a git repository")

    monkeypatch.setattr(subprocess, "run", mock_run)
    with pytest.raises(GitError, match="fatal: not a git repository"):
        run_git(["status"], cwd=tmp_path)

def test_run_git_timeout(monkeypatch, tmp_path: Path):
    """Tests that run_git raises a GitError on a timeout."""
    def mock_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(kwargs.get("args"), kwargs.get("timeout"))

    monkeypatch.setattr(subprocess, "run", mock_run)
    with pytest.raises(GitError, match="timed out"):
        run_git(["fetch"], cwd=tmp_path)

def test_git_current_branch(monkeypatch, tmp_path: Path):
    """Tests the high-level git_current_branch function."""
    def mock_run(*args, **kwargs):
        # Corrected the stdout to have a proper newline
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=" feature/test\n ", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    branch = git_current_branch(tmp_path)
    assert branch == "feature/test"
