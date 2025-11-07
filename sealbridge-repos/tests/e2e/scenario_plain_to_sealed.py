# tests/e2e/scenario_plain_to_sealed.py: E2E test for plain -> sealed sync.

import os
import subprocess
from pathlib import Path

def test_plain_to_sealed_sync(tmp_path: Path):
    """
    Tests the end-to-end scenario of syncing from a plaintext personal repo
    to a sealed (encrypted) relay repo.
    """
    # 1. Setup GPG key
    gpg_output = subprocess.check_output(
        ["bash", "tests/e2e/fixtures/gpg_test_keygen.sh"]
    ).decode().strip()
    lines = gpg_output.strip().splitlines()
    gpg_home_dir = lines[0]
    gpg_fpr = lines[-1]

    # 2. Create bare repos
    personal_repo_path = tmp_path / "personal.git"
    relay_repo_path = tmp_path / "relay.git"

    env = os.environ.copy()
    env["GNUPGHOME"] = gpg_home_dir

    subprocess.run(
        ["bash", "tests/e2e/fixtures/make_personal_repo.sh", str(personal_repo_path)],
        check=True
    )
    subprocess.run(
        ["bash", "tests/e2e/fixtures/make_relay_repo.sh", str(relay_repo_path), gpg_fpr],
        check=True, env=env
    )

    # 3. Add a new file to the personal repo
    personal_clone = tmp_path / "personal_clone"
    subprocess.run(["git", "clone", str(personal_repo_path), str(personal_clone)], check=True)
    (personal_clone / "secret.txt").write_text("this is a secret")
    subprocess.run(["git", "add", "."], cwd=str(personal_clone), check=True)
    subprocess.run(["git", "commit", "-m", "Add secret file"], cwd=str(personal_clone), check=True)
    subprocess.run(["git", "push"], cwd=str(personal_clone), check=True)

    # 4. Run the bridge (simulated)
    relay_clone = tmp_path / "relay_clone"
    subprocess.run(["git", "clone", str(relay_repo_path), str(relay_clone)], check=True)
    subprocess.run(["git-crypt", "unlock"], cwd=str(relay_clone), check=True, env=env)

    shutil.copy(personal_clone / "secret.txt", relay_clone / "secret.txt")
    subprocess.run(["git", "add", "."], cwd=str(relay_clone), check=True)
    subprocess.run(["git", "commit", "-m", "Sync secret file"], cwd=str(relay_clone), check=True)
    subprocess.run(["git", "push"], cwd=str(relay_clone), check=True)

    # 5. Verification
    # Check that the plaintext is not in the relay's git objects
    result = subprocess.run(
        ["grep", "-r", "this is a secret", str(relay_repo_path / "objects")],
        capture_output=True, text=True
    )
    assert result.returncode != 0, "Plaintext secret found in relay git objects!"

    # Check that the unlocked file has the correct content
    final_clone = tmp_path / "final_clone"
    subprocess.run(["git", "clone", str(relay_repo_path), str(final_clone)], check=True)
    subprocess.run(["git-crypt", "unlock"], cwd=str(final_clone), check=True, env=env)
    assert (final_clone / "secret.txt").read_text() == "this is a secret"
