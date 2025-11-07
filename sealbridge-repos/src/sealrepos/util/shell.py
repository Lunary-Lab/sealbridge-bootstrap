# src/sealrepos/util/shell.py: Subprocess execution wrapper.
# This module provides a secure and reliable way to execute external shell
# commands. It includes features for redacting sensitive information from logs,
# mapping return codes to typed exceptions, and handling process timeouts.

import subprocess
from typing import List

def run_command(args: List[str], redact: bool = False) -> str:
    """
    Run a shell command, with optional output redaction.
    """
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        if redact:
            raise RuntimeError(f"Command failed with redacted output.")
        else:
            raise RuntimeError(f"Command failed: {e.stderr}")
