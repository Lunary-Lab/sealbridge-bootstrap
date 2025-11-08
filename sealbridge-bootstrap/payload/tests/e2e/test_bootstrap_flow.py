# tests/e2e/test_bootstrap_flow.py
import os
import pytest
import docker
from pathlib import Path
import tempfile

# Mark this test as an e2e test
pytestmark = pytest.mark.e2e

@pytest.fixture(scope="module")
def docker_client():
    """Provides a Docker client for the test module."""
    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception as e:
        pytest.skip(f"Docker is not available: {e}")

@pytest.fixture(scope="module")
def bootstrap_image(docker_client):
    """Builds the Docker image for the E2E test."""
    image_tag = "sealbridge-bootstrap-e2e:latest"
    dockerfile_path = str(Path(__file__).parent.parent.parent.absolute())

    try:
        image, logs = docker_client.images.build(
            path=dockerfile_path,
            dockerfile="payload/tests/e2e/Dockerfile.ubuntu",
            tag=image_tag,
            rm=True
        )
        yield image_tag
    finally:
        try:
            docker_client.images.remove(image_tag, force=True)
        except docker.errors.ImageNotFound:
            pass

def test_bootstrap_flow(docker_client, bootstrap_image):
    """
    Runs the full bootstrap process inside a Docker container and verifies the result.
    """
    container = None
    try:
        # Create a temporary file for the bootstrap.yaml config
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("""
version: 1
profile: "work"
otp_gate:
  url: "http://127.0.0.1:8765/v1/verify"
  client_id: "bootstrap"
  client_secret_env: "SB_BOOTSTRAP_CLIENT_SECRET"
age:
  binary:
    version: "v1.2.0"
    checksums_url: "https://github.com/FiloSottile/age/releases/download/v1.2.0/sha256sums.txt"
  encrypted_key_path: "/home/tester/.ssh/id_ed25519"
git:
  dotfiles_repo: "/tmp/dotfiles.git"
  branch: "main"
chezmoi:
  version: "v2.48.1"
  assets:
    linux_amd64:
      url: "https://github.com/twpayne/chezmoi/releases/download/v2.48.1/chezmoi_2.48.1_linux_amd64.tar.gz"
      sha256: "ab61698359b203701cabc08e062efdca595954b7e24c59547c979c377eb5a4da"
            """)
            config_path = f.name

        container = docker_client.containers.run(
            bootstrap_image,
            command=["/bin/bash", "-c", "python3 /app/mock_otp_server.py & . .venv/bin/activate && sbboot run --config /tmp/config.yaml"],
            detach=True,
            ports={'8765/tcp': 8765},
            volumes={config_path: {'bind': '/tmp/config.yaml', 'mode': 'ro'}},
            environment={
                "SB_BOOTSTRAP_CLIENT_SECRET": "test-secret"
            }
        )
        result = container.wait(timeout=300)
        logs = container.logs().decode("utf-8")

        assert "Bootstrap complete!" in logs
        assert "sealbridge-e2e-test" in container.exec_run("cat /home/tester/.test-file").output.decode("utf-8")
        assert result["StatusCode"] == 0

    finally:
        if container:
            container.remove(force=True)
        os.unlink(config_path)
