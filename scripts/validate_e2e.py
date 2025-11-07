# scripts/validate_e2e.py: Simplified E2E test for sandbox validation.

import os
import subprocess
import shutil
from pathlib import Path

def run_command(args, check=True, cwd=None, env=None):
    """Helper to run a command and capture output."""
    return subprocess.run(args, capture_output=True, text=True, check=check, cwd=cwd, env=env)

def main():
    """Main validation logic."""
    print("--- Starting E2E Validation ---")

    # Create a temporary directory for all test artifacts to manage disk space
    base_dir = Path("/tmp/sealbridge-e2e-validation")
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir()

    # Run from within the sealbridge-repos directory
    os.chdir("sealbridge-repos")

    gpg_home_dir = None
    try:
        # 1. Setup GPG key
        print("Generating GPG key...")
        gpg_output = run_command(["bash", "tests/e2e/fixtures/gpg_test_keygen.sh"])
        lines = gpg_output.stdout.strip().splitlines()
        gpg_home_dir = lines[0]
        gpg_fpr = lines[-1]
        print(f"Generated GPG key in {gpg_home_dir} with fingerprint: {gpg_fpr}")

        # 2. Create bare repos
        print("Creating personal and relay repositories...")
        personal_repo = base_dir / "personal.git"
        relay_repo = base_dir / "relay.git"
        run_command(["bash", "tests/e2e/fixtures/make_personal_repo.sh", str(personal_repo)])

        env = os.environ.copy()
        env["GNUPGHOME"] = gpg_home_dir
        run_command(["bash", "tests/e2e/fixtures/make_relay_repo.sh", str(relay_repo), gpg_fpr], env=env)

        # 3. Add a new file to the personal repo
        print("Adding a new file to the personal repository...")
        personal_clone = base_dir / "personal_clone"
        run_command(["git", "clone", str(personal_repo), str(personal_clone)])
        (personal_clone / "secret.txt").write_text("this is a secret")
        run_command(["git", "add", "."], cwd=str(personal_clone))
        run_command(["git", "commit", "-m", "Add secret file"], cwd=str(personal_clone))
        run_command(["git", "push"], cwd=str(personal_clone))

        # 4. Configure and run the bridge
        print("Simulating bridge: personal -> relay")
        relay_clone_for_bridge = base_dir / "bridge_relay"
        run_command(["git", "clone", str(relay_repo), str(relay_clone_for_bridge)])

        # Correctly pass the env with GNUPGHOME to the unlock command
        run_command(["git-crypt", "unlock"], cwd=str(relay_clone_for_bridge), env=env)

        shutil.copy(personal_clone / "secret.txt", relay_clone_for_bridge / "secret.txt")
        run_command(["git", "add", "."], cwd=str(relay_clone_for_bridge))
        run_command(["git", "commit", "-m", "Sync secret file"], cwd=str(relay_clone_for_bridge))
        run_command(["git", "push"], cwd=str(relay_clone_for_bridge))

        # 5. Verification
        print("Verifying encryption in relay repository...")
        result = run_command(
            ["grep", "-r", "this is a secret", str(relay_repo / "objects")],
            check=False
        )

        if result.returncode == 0:
            print("\n[ERROR] Plaintext secret found in relay objects!")
            exit(1)
        else:
            print("\n[SUCCESS] Secret is not present in plaintext in the relay objects.")

    finally:
        print("--- Cleaning up ---")
        os.chdir("..")
        shutil.rmtree(base_dir)
        if gpg_home_dir and Path(gpg_home_dir).exists():
            shutil.rmtree(gpg_home_dir)


if __name__ == "__main__":
    main()
