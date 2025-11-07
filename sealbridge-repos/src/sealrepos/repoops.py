# src/sealrepos/repoops.py: Git repository operations engine.
# This module implements the high-level logic for repository synchronization,
# using a Template Method pattern. It defines the decision-making process for
# determining whether to fast-forward, rebase, push, or create a pull request,
# based on the state of the local and remote branches.

from enum import Enum, auto
from pathlib import Path
from .config import Repo, Config
from .gitwrap import (
    git_fetch_all,
    git_current_branch,
    git_get_head_sha,
    git_get_merge_base,
    git_rebase,
    git_push,
    git_is_clean,
)
from .util.errors import PolicyViolationError

class SyncState(Enum):
    """Represents the synchronization state of a branch relative to its upstream."""
    UP_TO_DATE = auto()
    AHEAD = auto()
    BEHIND = auto()
    DIVERGED = auto()

class RepoSync:
    """
    Orchestrates the synchronization of a single repository based on configured policies.
    This class implements the Template Method pattern for the sync process.
    """

    def __init__(self, repo_config: Repo, global_config: Config):
        self.repo = repo_config
        self.config = global_config
        self.path: Path = self.repo.path

    def sync(self) -> None:
        """The main template method for the synchronization process."""
        self._pre_sync_checks()
        self._fetch_remotes()

        branch = git_current_branch(self.path)
        # For now, we assume a simple personal -> relay sync direction
        # A more complex implementation would handle bidirectional sync
        upstream = f"origin/{branch}" # Assuming 'origin' is the personal remote

        state = self._determine_sync_state("HEAD", upstream)

        if state == SyncState.BEHIND:
            self._handle_behind(upstream)
        elif state == SyncState.AHEAD:
            self._handle_ahead("relay", branch) # Assuming 'relay' is the work remote
        elif state == SyncState.DIVERGED:
            self._handle_diverged(upstream, "relay", branch)

    def _pre_sync_checks(self) -> None:
        """Hook for performing checks before starting the sync."""
        if not git_is_clean(self.path):
            raise PolicyViolationError(
                f"Repository '{self.repo.name}' has uncommitted changes. Please commit or stash them."
            )

    def _fetch_remotes(self) -> None:
        """Hook for fetching from all remotes."""
        git_fetch_all(self.path)

    def _determine_sync_state(self, local_ref: str, remote_ref: str) -> SyncState:
        """Determines the sync state between a local and remote reference."""
        local_sha = git_get_head_sha(self.path, local_ref)
        remote_sha = git_get_head_sha(self.path, remote_ref)
        base_sha = git_get_merge_base(self.path, local_sha, remote_sha)

        if local_sha == remote_sha:
            return SyncState.UP_TO_DATE
        elif local_sha == base_sha:
            return SyncState.BEHIND
        elif remote_sha == base_sha:
            return SyncState.AHEAD
        else:
            return SyncState.DIVERGED

    def _handle_behind(self, upstream: str) -> None:
        """Handles the case where the local branch is behind the upstream."""
        # In a simple model, being behind might mean we just need to rebase.
        # This is effectively a fast-forward if there are no local commits.
        git_rebase(self.path, upstream)

    def _handle_ahead(self, remote: str, branch: str) -> None:
        """Handles the case where the local branch is ahead of the upstream."""
        # Before pushing, we would run a secret scan.
        # self._run_secret_scan()
        git_push(self.path, remote, branch)

    def _handle_diverged(self, upstream: str, remote: str, branch: str) -> None:
        """Handles the case where the local and upstream branches have diverged."""
        # Attempt to rebase local changes on top of the upstream.
        git_rebase(self.path, upstream)
        # After a successful rebase, the state becomes 'AHEAD', so we can push.
        git_push(self.path, remote, branch)
        # A real implementation would have more complex logic for PR creation on failure.
