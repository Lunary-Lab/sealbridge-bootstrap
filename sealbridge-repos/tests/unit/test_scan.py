# tests/unit/test_scan.py: Unit tests for the secret scanning adapter.

import pytest
from unittest.mock import patch

from sealrepos.scan import GitleaksScanner, NoOpScanner
from sealrepos.util.errors import SecretFoundError, SealbridgeError

@patch('sealrepos.scan.run_command')
def test_gitleaks_scanner_no_findings(mock_run_command, tmp_path):
    """Tests that the gitleaks scanner passes when no secrets are found."""
    mock_run_command.return_value = "[]" # Empty JSON array
    scanner = GitleaksScanner()
    # Should not raise an exception
    scanner.scan(tmp_path)
    mock_run_command.assert_called_once()

@patch('sealrepos.scan.run_command')
def test_gitleaks_scanner_with_findings(mock_run_command, tmp_path):
    """Tests that a SecretFoundError is raised when gitleaks finds secrets."""
    gitleaks_output = """
    [
        {
            "Description": "Generic API Key",
            "File": "config.yaml",
            "StartLine": 10
        }
    ]
    """
    mock_run_command.return_value = gitleaks_output
    scanner = GitleaksScanner()

    with pytest.raises(SecretFoundError) as excinfo:
        scanner.scan(tmp_path)

    assert "found 1 secrets" in str(excinfo.value)
    assert len(excinfo.value.args[1]) == 1 # Check that the findings list is passed
    assert excinfo.value.args[1][0].file == "config.yaml"

def test_noop_scanner(tmp_path):
    """Tests that the NoOpScanner does nothing."""
    scanner = NoOpScanner()
    # Should not raise any exception
    scanner.scan(tmp_path)
