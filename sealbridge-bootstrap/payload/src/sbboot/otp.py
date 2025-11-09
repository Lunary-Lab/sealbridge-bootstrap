# src/sbboot/otp.py
"""Client for the SealBridge OTP verification gate."""

import os
import time
from typing import Dict

import httpx
from rich.console import Console
from rich.prompt import Prompt

from .config import OtpGateConfig
from .errors import ConfigError, OtpError

console = Console(stderr=True)


def _get_client_secret(config: OtpGateConfig) -> str:
    """
    Retrieve the client secret from the environment variable specified in the config.

    Raises:
        ConfigError: If the environment variable is not set.
    """
    secret = os.environ.get(config.client_secret_env)
    if not secret:
        raise ConfigError(
            f"OTP gate client secret not found. "
            f"Please set the '{config.client_secret_env}' environment variable."
        )
    return secret


def _redact(data: Dict) -> Dict:
    """Create a copy of a dictionary with sensitive values redacted."""
    redacted = data.copy()
    if "client_secret" in redacted:
        redacted["client_secret"] = "[REDACTED]"
    if "token" in redacted:
        redacted["token"] = f"{redacted['token'][:1]}...{redacted['token'][-1:]}"
    return redacted


def verify_totp_code(
    config: OtpGateConfig,
    totp_code: str,
    max_retries: int = 3,
    backoff_factor: float = 0.5,
) -> bool:
    """
    Verifies a TOTP code with the sealbridge-otp-gate.

    Args:
        config: The OTP gate configuration.
        totp_code: The 6-digit TOTP code from the user.
        max_retries: The maximum number of times to retry on transient errors.
        backoff_factor: The factor for exponential backoff between retries.

    Returns:
        True if the verification was successful, False otherwise.

    Raises:
        OtpError: If a non-transient error occurs or retries are exhausted.
        ConfigError: If the client secret is not found in the environment.
    """
    client_secret = _get_client_secret(config)
    payload = {
        "client_id": config.client_id,
        "client_secret": client_secret,
        "token": totp_code,
    }

    last_exception: Exception | None = None

    with httpx.Client(timeout=10.0) as client:
        for attempt in range(max_retries):
            try:
                console.log(f"Attempting OTP verification (attempt {attempt + 1}/{max_retries})...")
                response = client.post(str(config.url), json=payload)
                response.raise_for_status()

                data = response.json()
                if data.get("ok") is True:
                    console.log("OTP verification successful.")
                    return True
                else:
                    error_message = data.get("error", "Unknown error from OTP gate")
                    raise OtpError(f"Verification failed: {error_message}")

            except httpx.HTTPStatusError as e:
                if 400 <= e.response.status_code < 500:
                    try:
                        error_detail = e.response.json().get("error", e.response.text)
                    except Exception:
                        error_detail = e.response.text
                    raise OtpError(f"OTP gate returned an error: {error_detail}") from e
                last_exception = e
                console.log(f"Server error during OTP verification: {e}. Retrying...")

            except httpx.RequestError as e:
                last_exception = e
                console.log(f"Network error during OTP verification: {e}. Retrying...")

            time.sleep(backoff_factor * (2**attempt))

    raise OtpError(
        f"Failed to verify OTP after {max_retries} attempts. "
        f"Last error: {last_exception}"
    )


def prompt_and_verify(config: OtpGateConfig) -> None:
    """
    Prompts the user for a TOTP code and verifies it.

    Raises:
        OtpError: If verification fails.
    """
    console.print("🔐 [bold]OTP Verification Required[/bold]")
    try:
        totp_code = Prompt.ask("Please enter your 6-digit verification code")
        if not (totp_code.isdigit() and len(totp_code) == 6):
            raise OtpError("Invalid format. Please provide exactly 6 digits.")

        with console.status("[bold yellow]Verifying code with OTP gate...[/bold yellow]", spinner="dots"):
            if not verify_totp_code(config, totp_code):
                raise OtpError("Verification failed for an unknown reason.")

        console.print("✅ [bold green]OTP verification successful.[/bold green]")

    except (KeyboardInterrupt, EOFError):
        console.print("\n[bold red]Operation cancelled by user.[/bold red]")
        import typer
        raise typer.Exit(code=1)
