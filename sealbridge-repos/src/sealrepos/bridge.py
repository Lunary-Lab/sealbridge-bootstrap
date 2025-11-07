# src/sealrepos/bridge.py: Home-only translator process.
# This module implements the core logic for the 'sealbridge-bridge', which is
# responsible for mirroring repositories between a personal (plaintext) remote
# and a work (encrypted) remote. It orchestrates the two-clone model to ensure
# separation and security.

import time
import random
import shutil
from pathlib import Path
from filelock import FileLock, Timeout

from .config import load_config, Repo
from .gitwrap import git_fetch_all, git_push, git_is_clean, run_git
from .util.paths import get_xdg_state_home, get_xdg_data_home
from .util.log import get_logger, repo_context
from .util.fs import safe_copy_tree

logger = get_logger(__name__)

class RepoBridge:
    """
    Manages the two-clone mirroring for a single repository.
    """

    def __init__(self, repo_config: Repo):
        self.repo = repo_config
        self.base_path = get_xdg_data_home() / "bridge_clones"
        self.personal_clone_path = self.base_path / f"{self.repo.name}-personal"
        self.relay_clone_path = self.base_path / f"{self.repo.name}-relay"

    def sync_bridge(self):
        """
        Orchestrates the bi-directional sync between the personal and relay clones.
        """
        self._ensure_clones_exist()
        self._mirror_personal_to_relay()
        self._mirror_relay_to_personal()

    def _ensure_clones_exist(self):
        """Ensures that the two working clones exist."""
        if not self.personal_clone_path.exists():
            run_git(["clone", self.repo.personal, str(self.personal_clone_path)], cwd=self.base_path)
        if not self.relay_clone_path.exists():
            run_git(["clone", self.repo.relay, str(self.relay_clone_path)], cwd=self.base_path)
        logger.info(f"Ensured clones exist for {self.repo.name}")

    def _mirror_personal_to_relay(self):
        """Mirrors changes from the personal clone to the relay clone."""
        logger.info("Mirroring from personal to relay...")
        git_fetch_all(self.personal_clone_path)

        # This is a simplified check for changes. A real implementation would be more robust.
        if "ahead" in run_git(["status", "-sb"], cwd=self.personal_clone_path).stdout:
            safe_copy_tree(str(self.personal_clone_path), str(self.relay_clone_path), [], [])

            if not git_is_clean(self.relay_clone_path):
                run_git(["add", "."], cwd=self.relay_clone_path)
                run_git(["commit", "-m", "Automated sync from personal"], cwd=self.relay_clone_path)
                git_push(self.relay_clone_path, "origin", "main")
                logger.info("Pushed changes to relay.")

    def _mirror_relay_to_personal(self):
        """Mirrors changes from the relay clone to the personal clone."""
        logger.info("Mirroring from relay to personal...")
        git_fetch_all(self.relay_clone_path)

        if "ahead" in run_git(["status", "-sb"], cwd=self.relay_clone_path).stdout:
            # Assumes git-crypt is unlocked
            safe_copy_tree(str(self.relay_clone_path), str(self.personal_clone_path), [], [])

            if not git_is_clean(self.personal_clone_path):
                run_git(["add", "."], cwd=self.personal_clone_path)
                run_git(["commit", "-m", "Automated sync from relay"], cwd=self.personal_clone_path)
                git_push(self.personal_clone_path, "origin", "main")
                logger.info("Pushed changes to personal.")

def main():
    """
    Main loop for the bridge.
    """
    lock_path = get_xdg_state_home() / "sealbridge-bridge.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(lock_path)

    try:
        with lock.acquire(timeout=1):
            logger.info("Bridge started and lock acquired.")
            while True:
                config = load_config()
                if config.profile != "home":
                    logger.warning("Bridge is designed to run only with the 'home' profile. Sleeping.")
                    time.sleep(300)
                    continue

                for repo in config.repos:
                    if repo.mode != "sealed":
                        continue

                    repo_context.set(repo.name)
                    try:
                        bridge = RepoBridge(repo)
                        bridge.sync_bridge()
                    except Exception as e:
                        logger.error(f"Failed to bridge repo '{repo.name}': {e}", exc_info=True)
                    finally:
                        repo_context.set(None)

                interval = config.defaults.interval_sec
                jitter = interval * config.defaults.jitter
                sleep_time = interval + random.uniform(-jitter, jitter)
                logger.info(f"Bridge sleeping for {sleep_time:.2f} seconds.")
                time.sleep(sleep_time)
    except Timeout:
        logger.error("Another instance of the bridge is already running. Exiting.")
        exit(1)
    except KeyboardInterrupt:
        logger.info("Bridge shutting down.")
    finally:
        if lock.is_locked:
            lock.release()

if __name__ == "__main__":
    main()
