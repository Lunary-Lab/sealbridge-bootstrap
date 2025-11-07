# src/sealrepos/gitwrap.py: Safe subprocess wrappers for Git.
# This module provides functions for interacting with the system's 'git' command
# in a safe and controlled manner. It uses subprocess execution with timeouts,
# environment variable scrubbing, and clear error handling to prevent common
# security and reliability issues.

import os
import subprocess
from pathlib import Path
from typing import List, Optional

from .util.errors import GitError

# --- Core Git Execution ---

def run_git(
    args: List[str],
    cwd: Path,
    timeout: int = 120,
    check: bool = True,
    env: Optional[dict] = None,
) -> subprocess.CompletedProcess:
    """
    Runs a git command in a specified directory with a timeout and error handling.

    Args:
        args: A list of arguments for the git command.
        cwd: The working directory for the command.
        timeout: The command timeout in seconds.
        check: If True, raises GitError on a non-zero exit code.
        env: An optional dictionary of environment variables.

    Returns:
        The CompletedProcess object.

    Raises:
        GitError: If git is not found, the command fails, or it times out.
    """
    if not cwd.is_dir():
        raise GitError(f"Git working directory not found: {cwd}")

    # Secure the environment by default
    base_env = os.environ.copy()
    base_env["GIT_TERMINAL_PROMPT"] = "0"  # Disable interactive prompts
    if env:
        base_env.update(env)

    try:
        process = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check,
            env=base_env,
        )
        return process
    except FileNotFoundError:
        raise GitError("The 'git' command was not found. Is it installed and in your PATH?")
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.strip() or e.stdout.strip()
        raise GitError(f"Git command '{' '.join(args)}' failed: {error_message}")
    except subprocess.TimeoutExpired:
        raise GitError(f"Git command '{' '.join(args)}' timed out after {timeout} seconds.")


# --- High-Level Git Operations ---

def git_fetch_all(cwd: Path) -> None:
    """Fetches all remotes for a repository."""
    run_git(["fetch", "--all", "--prune"], cwd=cwd)

def git_current_branch(cwd: Path) -> str:
    """Gets the current active branch name."""
    result = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    return result.stdout.strip()

def git_get_head_sha(cwd: Path, ref: str = "HEAD") -> str:
    """Gets the SHA of a given reference (defaults to HEAD)."""
    result = run_git(["rev-parse", ref], cwd=cwd)
    return result.stdout.strip()

def git_get_merge_base(cwd: Path, commit1: str, commit2: str) -> str:
    """Finds the common ancestor of two commits."""
    result = run_git(["merge-base", commit1, commit2], cwd=cwd)
    return result.stdout.strip()

def git_rebase(cwd: Path, upstream_ref: str) -> None:
    """Rebases the current branch onto an upstream reference."""
    run_git(["rebase", upstream_ref], cwd=cwd)

def git_push(cwd: Path, remote: str, branch: str, force_with_lease: bool = False) -> None:
    """Pushes a branch to a remote."""
    args = ["push", remote, branch]
    if force_with_lease:
        args.append("--force-with-lease")
    run_git(args, cwd=cwd)

def git_is_clean(cwd: Path) -> bool:
    """Checks if the working directory is clean."""
    result = run_git(["status", "--porcelain"], cwd=cwd)
    return not result.stdout.strip()
