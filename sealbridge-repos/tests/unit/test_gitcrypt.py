# tests/unit/test_gitcrypt.py: Unit tests for the git-crypt strategy.

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from sealrepos.cryptmode.gitcrypt import GitCrypt
from sealrepos.util.errors import GitError

@patch('sealrepos.cryptmode.gitcrypt.run_git')
def test_gitcrypt_unlock_success(mock_run_git, tmp_path: Path):
    """Tests that the unlock command is called correctly."""
    crypto = GitCrypt()
    crypto.unlock(tmp_path)
    mock_run_git.assert_called_once_with(["crypt", "unlock"], cwd=tmp_path)

@patch('sealrepos.cryptmode.gitcrypt.run_git', side_effect=GitError("Unlock failed"))
def test_gitcrypt_unlock_failure(mock_run_git, tmp_path: Path):
    """Tests that a GitError is propagated on unlock failure."""
    crypto = GitCrypt()
    with pytest.raises(GitError, match="Failed to unlock"):
        crypto.unlock(tmp_path)

@patch('sealrepos.cryptmode.gitcrypt.run_git')
def test_gitcrypt_is_unlocked_true(mock_run_git, tmp_path: Path):
    """Tests that is_unlocked returns True when the repo is unlocked."""
    mock_run_git.return_value = MagicMock(returncode=0)
    crypto = GitCrypt()
    assert crypto.is_unlocked(tmp_path) is True
    mock_run_git.assert_called_once_with(["crypt", "status", "-e"], cwd=tmp_path, check=False)

@patch('sealrepos.cryptmode.gitcrypt.run_git')
def test_gitcrypt_is_unlocked_false(mock_run_git, tmp_path: Path):
    """Tests that is_unlocked returns False when the repo is locked."""
    mock_run_git.return_value = MagicMock(returncode=1)
    crypto = GitCrypt()
    assert crypto.is_unlocked(tmp_path) is False
