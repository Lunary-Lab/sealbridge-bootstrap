# src/sealrepos/cryptmode/gitcrypt.py: git-crypt encryption strategy.
# This module implements the 'CryptoMode' interface for 'git-crypt'. It is
# responsible for detecting a git-crypt-enabled repository, verifying the
# '.gitattributes' configuration, and handling the 'unlock' command to decrypt
# the repository using the user's GPG key.

from pathlib import Path

from . import CryptoMode
from ..gitwrap import run_git
from ..util.errors import GitError

class GitCrypt(CryptoMode):
    """
    Implements the CryptoMode strategy for git-crypt.
    """
    def unlock(self, repo_path: Path) -> None:
        """
        Unlocks the repository using 'git-crypt unlock'.
        """
        try:
            run_git(["crypt", "unlock"], cwd=repo_path)
        except GitError as e:
            # Prepend a more user-friendly message to the underlying git error
            raise GitError(f"Failed to unlock git-crypt repository at '{repo_path}'. "
                         f"Ensure you have a configured GPG key. Original error: {e}")

    def is_unlocked(self, repo_path: Path) -> bool:
        """
        Checks if the repository is unlocked by running 'git-crypt status'.
        """
        try:
            # The status command exits with 0 if unlocked, and non-zero otherwise
            result = run_git(["crypt", "status", "-e"], cwd=repo_path, check=False)
            return result.returncode == 0
        except GitError:
            # If the command fails for other reasons (e.g., not a git-crypt repo),
            # we can assume it's not unlocked.
            return False

    def add_gpg_user(self, repo_path: Path, gpg_fingerprint: str) -> None:
        """
        Adds a new GPG user to the repository.
        """
        run_git(["crypt", "add-gpg-user", gpg_fingerprint], cwd=repo_path)
