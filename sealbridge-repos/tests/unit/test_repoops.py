# tests/unit/test_repoops.py: Unit tests for the repository operations engine.

import pytest
from unittest.mock import MagicMock, patch

from sealrepos.repoops import RepoSync, SyncState
from sealrepos.config import Repo, Config

@pytest.fixture
def mock_repo_sync():
    """Fixture to create a RepoSync instance with mocked git functions."""
    repo_config = Repo(
        name="test-repo",
        path="/tmp/test-repo",
        personal="...",
        mode="sealed",
    )
    global_config = Config(version=1, profile="home", repos=[repo_config])

    with patch('sealrepos.repoops.git_is_clean', return_value=True), \
         patch('sealrepos.repoops.git_fetch_all'), \
         patch('sealrepos.repoops.git_current_branch', return_value='main'), \
         patch('sealrepos.repoops.git_rebase') as mock_rebase, \
         patch('sealrepos.repoops.git_push') as mock_push:

        sync_instance = RepoSync(repo_config, global_config)
        yield sync_instance, mock_rebase, mock_push

def test_sync_state_behind(mock_repo_sync):
    """Tests that a rebase is triggered when the repo is behind."""
    sync, mock_rebase, mock_push = mock_repo_sync
    with patch.object(sync, '_determine_sync_state', return_value=SyncState.BEHIND):
        sync.sync()
        mock_rebase.assert_called_once()
        mock_push.assert_not_called()

def test_sync_state_ahead(mock_repo_sync):
    """Tests that a push is triggered when the repo is ahead."""
    sync, mock_rebase, mock_push = mock_repo_sync
    with patch.object(sync, '_determine_sync_state', return_value=SyncState.AHEAD):
        sync.sync()
        mock_rebase.assert_not_called()
        mock_push.assert_called_once()

def test_sync_state_diverged(mock_repo_sync):
    """Tests that a rebase and then a push are triggered when diverged."""
    sync, mock_rebase, mock_push = mock_repo_sync
    with patch.object(sync, '_determine_sync_state', return_value=SyncState.DIVERGED):
        sync.sync()
        mock_rebase.assert_called_once()
        mock_push.assert_called_once()

def test_sync_state_up_to_date(mock_repo_sync):
    """Tests that no action is taken when the repo is up-to-date."""
    sync, mock_rebase, mock_push = mock_repo_sync
    with patch.object(sync, '_determine_sync_state', return_value=SyncState.UP_TO_DATE):
        sync.sync()
        mock_rebase.assert_not_called()
        mock_push.assert_not_called()
