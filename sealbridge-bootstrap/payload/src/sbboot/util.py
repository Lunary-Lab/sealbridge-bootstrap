# src/sbboot/util.py
"""Utility functions for checksumming, downloading, and file operations."""

import hashlib
import shutil
import tempfile
from pathlib import Path

import httpx
from rich.progress import Progress

from .errors import ChecksumMismatchError, SealBridgeError


def verify_sha256(file_path: Path, expected_checksum: str) -> None:
    """
    Verifies the SHA256 checksum of a file.

    Args:
        file_path: The path to the file to verify.
        expected_checksum: The expected SHA256 checksum in hex format.

    Raises:
        ChecksumMismatchError: If the checksums do not match.
        IOError: If the file cannot be read.
    """
    hasher = hashlib.sha256()
    try:
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
    except IOError as e:
        raise SealBridgeError(f"Failed to read file for checksum verification: {file_path}") from e

    actual_checksum = hasher.hexdigest()
    if not actual_checksum.lower() == expected_checksum.lower():
        raise ChecksumMismatchError(
            f"Checksum mismatch for {file_path.name}.\n"
            f"  Expected: {expected_checksum}\n"
            f"  Actual:   {actual_checksum}"
        )


def download_file(url: str, dest_path: Path) -> None:
    """
    Downloads a file from a URL to a destination path with a progress bar.

    Args:
        url: The URL to download from.
        dest_path: The path to save the downloaded file to.

    Raises:
        SealBridgeError: If the download fails.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, dir=dest_path.parent) as tmp_file:
            tmp_path = Path(tmp_file.name)
            with httpx.stream("GET", url, follow_redirects=True, timeout=30.0) as response:
                response.raise_for_status()
                total = int(response.headers.get("Content-Length", 0))

                with Progress(transient=True) as progress:
                    task = progress.add_task(f"Downloading {dest_path.name}...", total=total)
                    for chunk in response.iter_bytes():
                        tmp_file.write(chunk)
                        progress.update(task, advance=len(chunk))

            shutil.move(tmp_path, dest_path)
    except httpx.HTTPError as e:
        raise SealBridgeError(f"Failed to download file from {url}: {e}")
    except (IOError, OSError) as e:
        if 'tmp_path' in locals() and tmp_path.exists():
            tmp_path.unlink()
        raise SealBridgeError(f"Failed to write downloaded file to {dest_path}: {e}")


def find_in_path(name: str) -> Path | None:
    """
    Finds an executable in the system's PATH.

    Returns:
        The full path to the executable, or None if not found.
    """
    return shutil.which(name)


def parse_checksum_file(content: str) -> dict[str, str]:
    """
    Parses a checksum file (like sha256sums.txt) into a dictionary.

    Args:
        content: The text content of the checksum file.

    Returns:
        A dictionary mapping filenames to their SHA256 checksums.
    """
    checksums = {}
    for line in content.splitlines():
        parts = line.strip().split()
        if len(parts) == 2:
            checksum, filename = parts
            checksums[filename.lstrip('*')] = checksum
    return checksums
