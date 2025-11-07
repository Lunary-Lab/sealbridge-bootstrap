# src/sealrepos/daemon.py: The main daemon process (sealreposd).
# This module contains the core logic for the background daemon that continuously
# monitors and syncs repositories. It handles polling intervals, jitter to avoid
# thundering herd problems, and cross-process locking to ensure safe operation.

import time
import random
from filelock import FileLock, Timeout

from .config import load_config, Repo
from .repoops import RepoSync
from .util.paths import get_xdg_state_home
from .util.log import get_logger, repo_context

logger = get_logger(__name__)

def run_sync_cycle():
    """
    Runs a single synchronization cycle for all configured repositories.
    """
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return

    for repo in config.repos:
        if repo.mode == "nosync":
            continue

        repo_context.set(repo.name)
        try:
            logger.info(f"Starting sync for repository: {repo.name}")
            sync_instance = RepoSync(repo, config)
            sync_instance.sync()
            logger.info(f"Successfully synced repository: {repo.name}")
        except Exception as e:
            logger.error(f"Failed to sync repository '{repo.name}': {e}", exc_info=True)
        finally:
            repo_context.set(None)

def main():
    """
    Main loop for the daemon.

    It acquires a process lock and then enters an infinite loop to run sync
    cycles periodically, with jitter to distribute the load.
    """
    lock_path = get_xdg_state_home() / "sealreposd.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(lock_path)

    try:
        with lock.acquire(timeout=1):
            logger.info("Daemon started and lock acquired.")
            while True:
                config = load_config() # Reload config each cycle
                run_sync_cycle()
                interval = config.defaults.interval_sec
                jitter = interval * config.defaults.jitter
                sleep_time = interval + random.uniform(-jitter, jitter)
                logger.info(f"Sleeping for {sleep_time:.2f} seconds.")
                time.sleep(sleep_time)
    except Timeout:
        logger.error("Another instance of the daemon is already running. Exiting.")
        exit(1)
    except KeyboardInterrupt:
        logger.info("Daemon shutting down.")
    finally:
        if lock.is_locked:
            lock.release()

if __name__ == "__main__":
    main()
