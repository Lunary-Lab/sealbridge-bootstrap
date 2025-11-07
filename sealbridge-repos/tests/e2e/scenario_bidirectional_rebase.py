# tests/e2e/scenario_bidirectional_rebase.py: E2E test for bidirectional sync.

import os
import subprocess
from pathlib import Path
import shutil

def test_bidirectional_rebase(tmp_path: Path):
    """
    Tests the scenario where commits are made on both the personal and relay
    sides, forcing a rebase during the sync process.
    """
    # 1. Setup
    gpg_output = subprocess.check_output(
        ["bash", "tests/e2e/fixtures/gpg_test_keygen.sh"]
    ).decode().strip()
    lines = gpg_output.strip().splitlines()
    gpg_home_dir = lines[0]
    gpg_fpr = lines[-1]

    env = os.environ.copy()
    env["GNUPGHOME"] = gpg_home_dir

    personal_repo = tmp_path / "personal.git"
    relay_repo = tmp_path / "relay.git"
    subprocess.run(["bash", "tests/e2e/fixtures/make_personal_repo.sh", str(personal_repo)], check=True)
    subprocess.run(["bash", "tests/e2e/fixtures/make_relay_repo.sh", str(relay_repo), gpg_fpr], check=True, env=env)

    # 2. Initial sync
    personal_clone = tmp_path / "personal_clone"
    relay_clone = tmp_path / "relay_clone"
    subprocess.run(["git", "clone", str(personal_repo), str(personal_clone)], check=True)
    subprocess.run(["git", "clone", str(relay_repo), str(relay_clone)], check=True)
    subprocess.run(["git-crypt", "unlock"], cwd=str(relay_clone), check=True, env=env)

    shutil.copy(personal_clone / "README.md", relay_clone / "README.md")
    subprocess.run(["git", "commit", "-am", "Initial sync"], cwd=str(relay_clone), check=True)
    subprocess.run(["git", "push"], cwd=str(relay_clone), check=True)

    # 3. Diverge
    (personal_clone / "personal_file.txt").write_text("from personal")
    subprocess.run(["git", "add", "."], cwd=str(personal_clone), check=True)
    subprocess.run(["git", "commit", "-m", "Commit from personal"], cwd=str(personal_clone), check=True)
    subprocess.run(["git", "push"], cwd=str(personal_clone), check=True)

    (relay_clone / "relay_file.txt").write_text("from relay")
    subprocess.run(["git", "add", "."], cwd=str(relay_clone), check=True)
    subprocess.run(["git", "commit", "-m", "Commit from relay"], cwd=str(relay_clone), check=True)
    subprocess.run(["git", "push"], cwd=str(relay_clone), check=True)

    # 4. Simulate bridge sync (relay -> personal)
    subprocess.run(["git", "fetch"], cwd=str(personal_clone), check=True)
    subprocess.run(["git", "rebase", "origin/main"], cwd=str(personal_clone), check=True)

    # 5. Verification
    assert (personal_clone / "personal_file.txt").exists()
    assert (personal_clone / "relay_file.txt").exists()
