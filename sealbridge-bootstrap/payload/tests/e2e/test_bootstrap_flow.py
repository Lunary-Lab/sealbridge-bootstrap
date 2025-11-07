# tests/e2e/test_bootstrap_flow.py
import os
import pytest
import docker
from pathlib import Path

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
    dockerfile_path = Path(__file__).parent

    try:
        image, logs = docker_client.images.build(
            path=str(dockerfile_path),
            dockerfile="Dockerfile.ubuntu",
            tag=image_tag,
            rm=True
        )
        yield image_tag
    finally:
        # Clean up the image
        try:
            docker_client.images.remove(image_tag, force=True)
        except docker.errors.ImageNotFound:
            pass

def test_bootstrap_flow(docker_client, bootstrap_image):
    """
    Runs the bootstrap process inside a Docker container and verifies the result.
    This is a simplified E2E test that checks if the CLI runs without crashing.
    A full E2E test would require a mock OTP server and a git server.
    """
    container = None
    try:
        container = docker_client.containers.run(
            bootstrap_image,
            command=["/usr/bin/python3.11", "-m", "sbboot.cli", "doctor"],
            detach=True,
            environment={
                "SB_BOOTSTRAP_CLIENT_SECRET": "test-secret"
            }
        )
        result = container.wait(timeout=120)
        logs = container.logs().decode("utf-8")

        # Verify that the doctor command ran successfully
        assert "Running SealBridge Doctor" in logs
        assert "XDG Paths are resolved" in logs
        assert "Found 'git' in PATH" in logs
        assert "SSH Agent is running or can be started" in logs

        # A real test would check for a successful bootstrap run,
        # but for now, we'll just check that the doctor command works.
        assert result["StatusCode"] == 0

    finally:
        if container:
            container.remove(force=True)
