# src/sbboot/sealrepos.py
"""Installation and configuration of sealbridge-repos."""

import os
import subprocess
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, Prompt

from . import paths
from .config import BootstrapConfig
from .errors import SealreposError
from .gitwrap import clone

console = Console(stderr=True)


def install_sealrepos(config: BootstrapConfig, policy_manager) -> None:
    """Install sealbridge-repos by cloning the repository and running its install script.

    Args:
        config: The bootstrap configuration.
        policy_manager: The policy manager to check filesystem access.

    """
    console.print("\n[bold]Installing SealBridge Repos...[/bold]")

    # Check if already installed
    sealreposctl_path = paths.get_bin_dir() / (
        "sealreposctl.exe" if paths.is_windows() else "sealreposctl"
    )
    if sealreposctl_path.exists():
        console.print(
            "✅ [green]SealBridge Repos appears to already be installed.[/green]"
        )
        return

    # Determine where to clone
    install_dir = paths.HOME / ".local" / "share" / "sealbridge" / "sealbridge-repos"
    repo_dir = install_dir / "sealbridge-repos"

    # Check if repo already exists
    if repo_dir.exists() and (repo_dir / ".git").exists():
        console.print(f"Repository already exists at {repo_dir}, skipping clone.")
    else:
        # Clone the repository
        console.print(f"Cloning sealbridge-repos to {repo_dir}...")
        policy_manager.check_write(repo_dir)
        repo_dir.parent.mkdir(parents=True, exist_ok=True)

        # Obtain repo URL from configuration or environment to avoid hardcoding secrets
        repo_url = None
        if hasattr(config, "sealrepos") and isinstance(
            getattr(config, "sealrepos", None), dict
        ):
            repo_url = config.sealrepos.get("repo_url") or None
        if not repo_url:
            repo_url = os.environ.get("SEALBRIDGE_REPOS_URL")
        if not repo_url:
            raise SealreposError(
                "SealBridge Repos URL not provided. Set SEALBRIDGE_REPOS_URL or configure in bootstrap config."
            )
        clone(repo_url, repo_dir, policy_manager, "main")

    # Run the install script
    console.print("Running sealbridge-repos installation script...")

    if paths.is_windows():
        install_script = repo_dir / "scripts" / "install.ps1"
        if not install_script.exists():
            raise SealreposError(f"Install script not found at {install_script}")

        # Run PowerShell script
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(install_script)],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise SealreposError(f"Installation failed: {result.stderr}")
    else:
        install_script = repo_dir / "scripts" / "install.sh"
        if not install_script.exists():
            raise SealreposError(f"Install script not found at {install_script}")

        # Make executable and run
        os.chmod(install_script, 0o755)
        result = subprocess.run(
            ["bash", str(install_script)],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )
        if result.returncode != 0:
            raise SealreposError(f"Installation failed: {result.stderr}")

    console.print(
        "✅ [bold green]SealBridge Repos installed successfully.[/bold green]"
    )


def configure_sealrepos(config: BootstrapConfig, policy_manager) -> None:
    """Configure sealbridge-repos by creating or updating the repos.yaml config file.
    Prompts for critical configuration if not present in config.

    Args:
        config: The bootstrap configuration.
        policy_manager: The policy manager to check filesystem access.

    """
    console.print("\n[bold]Configuring SealBridge Repos...[/bold]")

    config_dir = paths.get_xdg_config_home() / "sealrepos"
    config_file = config_dir / "repos.yaml"

    # Check if config already exists
    if config_file.exists():
        console.print(f"Configuration file already exists at {config_file}")
        if not Confirm.ask("Do you want to overwrite it?", default=False):
            console.print("Skipping configuration.")
            return

    # Get configuration from bootstrap config or prompt
    # Check if config has a sealrepos attribute (would be added to BootstrapConfig if needed)
    repos_config = None
    if hasattr(config, "sealrepos") and config.sealrepos:
        repos_config = config.sealrepos

    if repos_config:
        # Use configuration from bootstrap.yaml
        create_config_from_bootstrap(config_file, repos_config, policy_manager)
    else:
        # Prompt for critical configuration
        create_config_interactive(config_file, config, policy_manager)

    console.print(f"✅ [bold green]Configuration saved to {config_file}[/bold green]")


def create_config_from_bootstrap(
    config_file: Path, repos_config: dict, policy_manager
) -> None:
    """Create repos.yaml from bootstrap configuration."""
    import yaml

    policy_manager.check_write(config_file)
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # Write the configuration
    with config_file.open("w") as f:
        yaml.dump(repos_config, f, default_flow_style=False, sort_keys=False)


def create_config_interactive(
    config_file: Path, bootstrap_config: BootstrapConfig, policy_manager
) -> None:
    """Create repos.yaml by prompting for critical configuration."""
    import yaml

    policy_manager.check_write(config_file)
    config_file.parent.mkdir(parents=True, exist_ok=True)

    console.print("Please provide configuration for SealBridge Repos:")

    # Get profile
    profile = Prompt.ask("Profile", default=bootstrap_config.profile)

    # Basic configuration structure
    repos_config = {
        "version": 1,
        "profile": profile,
        "policy": {
            "paths": {
                "include": ["${HOME}/workspace/**", "${HOME}/src/**"],
                "exclude": ["**/.venv/**", "**/node_modules/**"],
            }
        },
        "logging": {"level": "INFO", "json": True},
        "gpg": {
            "recipients_file": "${XDG_CONFIG_HOME}/age/recipients.txt",
            "gpg_fprs_file": "${XDG_CONFIG_HOME}/sealbridge/gpg_fprs.txt",
        },
        "sync": {
            "interval_sec": 90,
            "jitter": 0.25,
            "max_parallel": 3,
            "integration": "rebase",
            "push_protected_branches": False,
        },
        "repos": [],
        "network": {
            "reachability": {"work_hosts": [], "home_hosts": ["github.com"]},
            "vpn_required": [],
        },
    }

    # Prompt for work hosts
    work_hosts_input = Prompt.ask(
        "Work Git hosts (comma-separated, e.g., ghe.example.com,gitlab.corp.local)",
        default="",
    )
    if work_hosts_input:
        repos_config["network"]["reachability"]["work_hosts"] = [
            h.strip() for h in work_hosts_input.split(",")
        ]
        repos_config["network"]["vpn_required"] = repos_config["network"][
            "reachability"
        ]["work_hosts"]

    # Ask if user wants to add repositories now
    if Confirm.ask("Do you want to configure repositories now?", default=False):
        repos = []
        while True:
            repo_name = Prompt.ask("Repository name (or press Enter to finish)")
            if not repo_name:
                break

            local_path = Prompt.ask(
                "Local path", default=f"${{HOME}}/workspace/code/{repo_name}"
            )

            direction = Prompt.ask(
                "Sync direction",
                choices=["both", "home_to_work", "work_to_home"],
                default="both",
            )

            home_url = Prompt.ask(
                "Home remote URL (e.g., git@github.com:user/repo.git)"
            )

            work_url = Prompt.ask(
                "Work remote URL (e.g., ssh://git@ghe.example.com/org/repo.git)",
                default="",
            )

            repo_config = {
                "name": repo_name,
                "local_path": local_path,
                "direction": direction,
                "branches": ["main"],
                "path_filters": {
                    "include": ["**/*"],
                    "exclude": ["**/.cache/**", "**/.DS_Store"],
                },
                "signing": True,
                "remotes": {"home": {"type": "plain", "url": home_url}},
            }

            if work_url:
                repo_config["remotes"]["work"] = {
                    "type": "gcrypt",
                    "url": work_url,
                    "recipients": [],
                }
                # Prompt for GPG recipients
                recipients_input = Prompt.ask(
                    "GPG fingerprints for work remote (comma-separated)", default=""
                )
                if recipients_input:
                    repo_config["remotes"]["work"]["recipients"] = [
                        r.strip() for r in recipients_input.split(",")
                    ]

            repos.append(repo_config)

        repos_config["repos"] = repos

    # Write the configuration
    with config_file.open("w") as f:
        yaml.dump(repos_config, f, default_flow_style=False, sort_keys=False)
