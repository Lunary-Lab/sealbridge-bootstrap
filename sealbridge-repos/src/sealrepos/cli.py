# src/sealrepos/cli.py: Command-Line Interface (CLI) entry point.
# Implemented using Typer, this module provides the main entry point for user
# interaction via the 'reposctl' command. It defines subcommands for status,
# syncing, and other repository operations.

import typer
import yaml
from rich.console import Console
from rich.table import Table
import json

from .config import load_config, Config
from .repoops import RepoSync
from .util.errors import SealbridgeError
from .cryptmode import gitcrypt
from .pr import create_pull_request
from .util.paths import get_xdg_config_home

app = typer.Typer(
    help="A CLI for managing and syncing repositories with Sealbridge."
)
console = Console()

def get_config() -> Config:
    """Loads the config and handles errors."""
    try:
        return load_config()
    except SealbridgeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)

@app.command()
def status():
    """Show the status of each configured repository."""
    config = get_config()
    console.print(f"Active profile: [bold green]{config.profile}[/bold green]")

    table = Table("Name", "Path", "Mode", "Direction")
    for repo in config.repos:
        table.add_row(
            repo.name,
            str(repo.path),
            repo.mode,
            repo.direction or config.defaults.direction,
        )
    console.print(table)

@app.command()
def sync(
    name: str = typer.Argument(..., help="The name of the repository to sync.")
):
    """Run a single sync cycle for a specific repository."""
    config = get_config()
    repo_to_sync = next((repo for repo in config.repos if repo.name == name), None)

    if not repo_to_sync:
        console.print(f"[bold red]Error:[/bold red] Repository '{name}' not found in configuration.")
        raise typer.Exit(1)

    if repo_to_sync.mode == "nosync":
        console.print(f"Repository '{name}' is marked as 'nosync'. Skipping.")
        return

    try:
        with console.status(f"Syncing [bold cyan]{name}[/bold cyan]...", spinner="dots"):
            sync_instance = RepoSync(repo_to_sync, config)
            sync_instance.sync()
        console.print(f"[bold green]Successfully synced repository: {name}[/bold green]")
    except SealbridgeError as e:
        console.print(f"[bold red]Sync failed for '{name}':[/bold red] {e}")
        raise typer.Exit(1)

@app.command()
def unlock(name: str):
    """Unlock a sealed repository using the configured crypto mode."""
    config = get_config()
    repo_to_unlock = next((repo for repo in config.repos if repo.name == name), None)
    if not repo_to_unlock:
        console.print(f"[bold red]Error:[/bold red] Repository '{name}' not found.")
        raise typer.Exit(1)

    if config.crypto.mode == "git-crypt":
        crypto_strategy = gitcrypt.GitCrypt()
        try:
            crypto_strategy.unlock(repo_to_unlock.path)
            console.print(f"[bold green]Repository '{name}' unlocked successfully.[/bold green]")
        except SealbridgeError as e:
            console.print(f"[bold red]Failed to unlock '{name}':[/bold red] {e}")
            raise typer.Exit(1)

@app.command()
def set_profile(profile: str = typer.Argument(..., help="The profile to set ('home' or 'work').")):
    """Set the active profile (home|work) in the config file."""
    if profile not in ["home", "work"]:
        console.print("[bold red]Error:[/bold red] Profile must be 'home' or 'work'.")
        raise typer.Exit(1)

    config_path = get_xdg_config_home() / "policy.yaml"
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)

    config_data['profile'] = profile

    with open(config_path, 'w') as f:
        yaml.dump(config_data, f)
    console.print(f"Active profile set to: [bold green]{profile}[/bold green]")

@app.command()
def pr(name: str):
    """(Placeholder) Open a Pull Request for a repository with diverged changes."""
    console.print(f"Creating a PR for '{name}'...")
    # This is a simplified example. A real implementation would get details
    # from the git repo.
    create_pull_request(
        repo=name,
        head="feature-branch",
        base="main",
        title="Automated PR from Sealbridge",
        body="This PR was created due to a sync conflict.",
    )
    console.print(f"PR created for '{name}'.")

if __name__ == "__main__":
    app()
