# src/sbboot/cli.py
"""Command-line interface for SealBridge Bootstrap."""

import sys
from typing import Optional

import typer
from rich.console import Console

from . import __version__, config, errors, paths
from .errors import ExitCode, SealBridgeError

app = typer.Typer(
    name="sbboot",
    help="SealBridge Bootstrap: A two-gate workstation bootstrap utility.",
    add_completion=False,
)

console = Console(stderr=True)


def version_callback(value: bool):
    """Print the version and exit."""
    if value:
        print(f"sbboot version: {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    config_path: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help=f"Path to the bootstrap.yaml configuration file. [default: {paths.get_default_config_path()}]",
        resolve_path=True,
    ),
    version: Optional[bool] = typer.Option(
        None, "--version", callback=version_callback, is_eager=True
    ),
):
    """
    SealBridge Bootstrap CLI.
    """
    from . import logging
    try:
        cfg = config.load_config(config_path)
        logging.setup_logging(cfg)
        ctx.obj = cfg
    except SealBridgeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=e.exit_code)


@app.command()
def run(
    ctx: typer.Context,
    profile: Optional[str] = typer.Option(
        None, "--profile", help="Dotfiles profile to apply (e.g., 'work' or 'home'). Overrides config."
    ),
):
    """Perform the full bootstrap flow."""
    cfg: config.BootstrapConfig = ctx.obj
    target_profile = profile or cfg.profile
    console.print(f"🚀 [bold]Starting SealBridge Bootstrap[/bold] for profile: [bold cyan]{target_profile}[/bold cyan]")

    try:
        # Gate 1: Verify OTP
        verify_otp(ctx)

        # Gate 2: Add SSH Key
        add_key(ctx)

        # Apply Dotfiles
        apply_dotfiles(ctx, profile=target_profile)

        # Clone extra repos
        from . import gitwrap, policy
        if cfg.git.extra_repos:
            policy_manager = policy.get_policy_manager(cfg)
            console.print("\n[bold]Cloning extra repositories...[/bold]")
            for repo in cfg.git.extra_repos:
                dest_dir = paths.HOME / "workspace" / repo.name
                gitwrap.clone(repo.url, dest_dir, cfg.git.branch, policy_manager)

        console.print("\n🎉 [bold green]Bootstrap complete! Your workstation is ready.[/bold green]")

    except typer.Exit:
        console.print("\n[bold red]Bootstrap process was halted.[/bold red]")
        raise
    except errors.SealBridgeError as e:
        console.print(f"\n[bold red]A critical error occurred during bootstrap:[/bold red]")
        console.print(e)
        raise typer.Exit(code=e.exit_code)


@app.command("verify-otp")
def verify_otp(ctx: typer.Context):
    """Prompt for TOTP and verify with the gate."""
    from . import otp
    cfg: config.BootstrapConfig = ctx.obj
    otp.prompt_and_verify(cfg.otp_gate)


@app.command("add-key")
def add_key(ctx: typer.Context):
    """Decrypt the Age key and add it to the ssh-agent."""
    from . import agewrap, agent
    from rich.prompt import Prompt
    import subprocess

    cfg: config.BootstrapConfig = ctx.obj

    try:
        age_bin = agewrap.get_age_binary(cfg)
        key_path = cfg.resolve_path(cfg.age.encrypted_key_path)

        if not key_path.exists():
            console.print(f"[bold red]Error:[/bold red] Encrypted key file not found at '{key_path}'")
            raise typer.Exit(code=errors.ExitCode.AGE_BINARY_ERROR)

        passphrase = Prompt.ask("Please enter the passphrase for the bootstrap key", password=True)

        with agent.SshAgentManager() as agent_manager:
            console.print("🔐 [bold]Decrypting key into ssh-agent...[/bold]")

            decrypt_proc = subprocess.Popen(
                [str(age_bin), "-d", "-i", "-", str(key_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            decrypted_key, stderr = decrypt_proc.communicate(input=passphrase.encode())

            if decrypt_proc.returncode != 0:
                console.print(f"[bold red]Error decrypting key:[/bold red] {stderr.decode()}")
                raise typer.Exit(code=errors.ExitCode.AGE_BINARY_ERROR)

            agent_manager.add_key(decrypted_key)

            console.print("✅ [bold green]Key added to ssh-agent successfully.[/bold green]")
            console.print("Available keys in agent:")
            console.print(agent_manager.list_keys())

    except errors.SealBridgeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=e.exit_code)


@app.command("apply-dotfiles")
def apply_dotfiles(
    ctx: typer.Context,
    profile: Optional[str] = typer.Option(
        None, "--profile", help="Dotfiles profile to apply (e.g., 'work' or 'home'). Overrides config."
    ),
):
    """Run chezmoi to apply the selected dotfiles profile."""
    from . import chezmoi, agent

    cfg: config.BootstrapConfig = ctx.obj

    try:
        chezmoi_bin = chezmoi.get_chezmoi_binary(cfg)

        with agent.SshAgentManager():
             chezmoi.apply_dotfiles(cfg, chezmoi_bin, profile)

    except errors.SealBridgeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=e.exit_code)


@app.command()
def paths(ctx: typer.Context):
    """Print resolved XDG and application paths as JSON."""
    import orjson

    data = {
        "HOME": str(paths.HOME),
        "XDG_DATA_HOME": str(paths.get_xdg_data_home()),
        "XDG_CONFIG_HOME": str(paths.get_xdg_config_home()),
        "XDG_STATE_HOME": str(paths.get_xdg_state_home()),
        "XDG_CACHE_HOME": str(paths.get_xdg_cache_home()),
        "app_data_dir": str(paths.get_app_data_dir()),
        "app_config_dir": str(paths.get_app_config_dir()),
        "app_state_dir": str(paths.get_app_state_dir()),
        "app_cache_dir": str(paths.get_app_cache_dir()),
        "bin_dir": str(paths.get_bin_dir()),
        "default_config_path": str(paths.get_default_config_path()),
    }
    print(orjson.dumps(data, option=orjson.OPT_INDENT_2).decode())


@app.command()
def doctor(ctx: typer.Context):
    """Validate the environment, configuration, and connectivity."""
    from . import util, agent
    import httpx

    cfg: config.BootstrapConfig = ctx.obj

    console.print("[bold]🩺 Running SealBridge Doctor...[/bold]")

    try:
        paths_json = {
            "HOME": str(paths.HOME),
            "XDG_DATA_HOME": str(paths.get_xdg_data_home()),
            "XDG_CONFIG_HOME": str(paths.get_xdg_config_home()),
            "XDG_STATE_HOME": str(paths.get_xdg_state_home()),
            "XDG_CACHE_HOME": str(paths.get_xdg_cache_home()),
        }
        console.print("✅ [green]XDG Paths are resolved.[/green]")
        console.print(paths_json)
    except errors.SealBridgeError as e:
        console.print(f"❌ [red]XDG Path Check Failed:[/red] {e}")

    console.print("\n[bold]Checking for required binaries...[/bold]")
    for binary in ["git", "ssh-agent", "ssh-add"]:
        if util.find_in_path(binary):
            console.print(f"✅ [green]Found '{binary}' in PATH.[/green]")
        else:
            console.print(f"❌ [red]Could not find '{binary}' in PATH.[/red]")

    console.print("\n[bold]Checking SSH Agent Status...[/bold]")
    try:
        with agent.SshAgentManager():
            console.print("✅ [green]SSH Agent is running or can be started.[/green]")
    except errors.SshAgentError as e:
        console.print(f"❌ [red]SSH Agent Check Failed:[/red] {e}")

    console.print(f"\n[bold]Checking connectivity to OTP Gate at {cfg.otp_gate.url}...[/bold]")
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(cfg.otp_gate.url.copy_with(path="/health"))
            if response.status_code == 200:
                console.print("✅ [green]Successfully connected to the OTP Gate.[/green]")
            else:
                console.print(f"⚠️ [yellow]Connected to OTP Gate, but got status {response.status_code}.[/yellow]")
    except httpx.RequestError as e:
        console.print(f"❌ [red]OTP Gate Connectivity Check Failed:[/red] {e}")


def run_cli():
    """Main entry point for the CLI application."""
    try:
        app()
    except typer.Exit:
        raise
    except SealBridgeError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)
        sys.exit(e.exit_code)
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred:[/bold red] {e}")
        sys.exit(errors.ExitCode.UNKNOWN_ERROR)


if __name__ == "__main__":
    run_cli()
