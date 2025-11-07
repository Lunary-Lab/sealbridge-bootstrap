# src/sealrepos/scan.py: Secret scanning adapter.
# This module implements a Strategy pattern for secret scanning. It provides a
# configurable adapter that can invoke different scanning tools like 'gitleaks'
# or a no-op scanner if scanning is disabled. It is responsible for parsing the
# scanner's output and gating commits based on the findings.

from __future__ import annotations
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from .util.shell import run_command
from .util.errors import SecretFoundError, SealbridgeError

class Finding:
    """Represents a single secret found by a scanner."""
    def __init__(self, description: str, file: str, line: int):
        self.description = description
        self.file = file
        self.line = line

    def __str__(self):
        return f"[{self.description}] in {self.file}:{self.line}"

class Scanner(ABC):
    """Abstract base class for a secret scanner."""
    @abstractmethod
    def scan(self, repo_path: Path) -> None:
        """
        Scan for secrets. If any are found, raise a SecretFoundError.
        """
        pass

class GitleaksScanner(Scanner):
    """
    A scanner implementation that uses the 'gitleaks' tool.
    """
    def scan(self, repo_path: Path) -> None:
        """
        Runs 'gitleaks detect' and parses the JSON report.
        """
        try:
            # We use --report-format json and --exit-code 0 to always get a report
            # and handle the logic ourselves.
            report = run_command(
                [
                    "gitleaks", "detect",
                    "--source", str(repo_path),
                    "--report-format", "json",
                    "--exit-code", "0"
                ]
            )
            findings = self._parse_report(report)
            if findings:
                raise SecretFoundError(
                    f"gitleaks found {len(findings)} secrets.", findings
                )
        except FileNotFoundError:
            raise SealbridgeError(
                "The 'gitleaks' command was not found. Please install it."
            )
        except json.JSONDecodeError:
            raise SealbridgeError("Failed to parse gitleaks JSON report.")

    def _parse_report(self, report_json: str) -> List[Finding]:
        """Parses a gitleaks JSON report into a list of Finding objects."""
        findings_data = json.loads(report_json)
        return [
            Finding(
                description=f["Description"],
                file=f["File"],
                line=f["StartLine"],
            )
            for f in findings_data
        ]

class NoOpScanner(Scanner):
    """
    A scanner that does nothing, for when secret scanning is disabled.
    """
    def scan(self, repo_path: Path) -> None:
        """This scanner performs no action."""
        pass
