# src/sbboot/agewrap.py
"""Wrapper for acquiring and using the 'age' binary for decryption."""

import platform
import stat
import tarfile
import zipfile
from pathlib import Path

import httpx
from rich.console import Console

from . import paths, util, policy
from .config import AgeConfig
from .errors import AgeBinaryError

console = Console(stderr=True)


def _get_system_arch() -> str:
    """Determine the system architecture in a format compatible with release assets."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":
        if machine in ["x86_64", "amd64"]:
            return "linux-amd64"
        if machine == "aarch64":
            return "linux-arm64"
    elif system == "windows":
        if machine in ["x86_64", "amd64"]:
            return "windows-amd64"
    elif system == "darwin":
        if machine in ["x86_64", "amd64"]:
            return "darwin-amd64"
        if machine == "arm64":
            return "darwin-arm64"

    raise AgeBinaryError(f"Unsupported operating system or architecture: {system}/{machine}")


def _get_asset_name_and_binary_path(version: str, arch: str) -> tuple[str, str]:
    """Get the expected asset filename and the path to the binary inside the archive."""
    if arch.startswith("windows"):
        asset_name = f"age-{version}-{arch}.zip"
        binary_path = "age/age.exe"
    else:
        asset_name = f"age-{version}-{arch}.tar.gz"
        binary_path = "age/age"
    return asset_name, binary_path


def _extract_binary(archive_path: Path, binary_path_in_archive: str, dest_path: Path):
    """Extract the 'age' binary from its archive."""
    console.log(f"Extracting '{archive_path.name}'...")
    if archive_path.name.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zipf:
            with zipf.open(binary_path_in_archive) as source, open(dest_path, "wb") as target:
                target.write(source.read())
    elif archive_path.name.endswith(".tar.gz"):
        with tarfile.open(archive_path, "r:gz") as tarf:
            member = tarf.extractfile(binary_path_in_archive)
            if not member:
                raise AgeBinaryError(f"Binary not found in archive: {binary_path_in_archive}")
            with open(dest_path, "wb") as target:
                target.write(member.read())
    else:
        raise AgeBinaryError(f"Unsupported archive format: {archive_path.name}")

    dest_path.chmod(dest_path.stat().st_mode | stat.S_IEXEC)
    console.log(f"Binary extracted to '{dest_path}'")


def get_age_binary(config: "BootstrapConfig") -> Path:
    """
    Ensures the 'age' binary is available, downloading and verifying it if necessary.

    Returns:
        The path to the executable 'age' binary.

    Raises:
        AgeBinaryError: If the binary cannot be found, downloaded, or verified.
    """
    bin_dir = paths.get_bin_dir()
    expected_binary_path = bin_dir / ("age.exe" if paths.is_windows() else "age")

    if expected_binary_path.exists():
        console.log(f"Found existing 'age' binary at '{expected_binary_path}'")
        return expected_binary_path

    console.print(f"Age binary not found. Downloading version [bold cyan]{config.age.binary.version}[/bold cyan]...")
    arch = _get_system_arch()
    version = config.age.binary.version
    asset_name, binary_in_archive_path = _get_asset_name_and_binary_path(version, arch)

    try:
        console.log(f"Fetching checksums from {config.age.binary.checksums_url}")
        checksum_content = httpx.get(str(config.age.binary.checksums_url)).text
        checksums = util.parse_checksum_file(checksum_content)
        expected_checksum = checksums.get(asset_name)
        if not expected_checksum:
            raise AgeBinaryError(f"Could not find checksum for asset '{asset_name}'")

        policy_manager = policy.get_policy_manager(config)
        download_url = str(config.age.binary.checksums_url).replace("sha256sums.txt", asset_name)
        download_path = bin_dir / asset_name
        util.download_file(download_url, download_path, policy_manager)

        console.log(f"Verifying checksum for '{asset_name}'...")
        util.verify_sha256(download_path, expected_checksum)
        console.log("Checksum verified.")

        _extract_binary(download_path, binary_in_archive_path, expected_binary_path)
        download_path.unlink()

        console.print("✅ [bold green]'age' binary is ready.[/bold green]")
        return expected_binary_path

    except (httpx.HTTPError, AgeBinaryError) as e:
        raise AgeBinaryError(f"Failed to acquire 'age' binary: {e}") from e
    except Exception as e:
        raise AgeBinaryError(f"An unexpected error occurred while acquiring 'age': {e}") from e
