# tests/e2e/scenario_path_policy.py: E2E test for path policies.

import os
import subprocess
from pathlib import Path
import shutil
from sealrepos.util.fs import safe_copy_tree

def test_path_policy_exclusion(tmp_path: Path):
    """
    Tests that the include/exclude path policies are correctly enforced
    during the bridging process.
    """
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()

    (src / "allowed.py").write_text("allowed")
    (src / "another_allowed.py").write_text("allowed")
    (src / "disallowed.txt").write_text("disallowed")
    (src / ".venv").mkdir()
    (src / ".venv" / "lib").mkdir()
    (src / ".venv" / "lib" / "python3.11").mkdir()

    include = ["*.py"]
    exclude = ["**/.venv/**"]

    safe_copy_tree(str(src), str(dst), include, exclude)

    assert (dst / "allowed.py").exists()
    assert (dst / "another_allowed.py").exists()
    assert not (dst / "disallowed.txt").exists()
    assert not (dst / ".venv").exists()
