# tests/unit/test_agewrap.py
from pathlib import Path
import pytest
from pytest_mock import MockerFixture

from sbboot import agewrap
from sbboot.config import AgeConfig, AgeBinaryConfig, BootstrapConfig
from sbboot.errors import AgeBinaryError

@pytest.fixture
def mock_bootstrap_config(mocker: MockerFixture) -> "BootstrapConfig":
    mock_config = mocker.MagicMock(spec=BootstrapConfig)
    mock_config.age = mocker.MagicMock()
    mock_config.age.binary = mocker.MagicMock()
    mock_config.age.binary.version = "v1.2.0"
    mock_config.age.binary.checksums_url = "https://example.com/age/v1.2.0/sha256sums.txt"
    mock_config.policy = mocker.MagicMock()
    return mock_config

def test_get_age_binary_found(mocker: MockerFixture, mock_bootstrap_config: "BootstrapConfig"):
    mocker.patch("sbboot.paths.get_bin_dir", return_value=Path("/fake/bin"))
    mocker.patch("sbboot.paths.is_windows", return_value=False)
    mocker.patch.object(Path, "exists", return_value=True)

    assert agewrap.get_age_binary(mock_bootstrap_config) == Path("/fake/bin/age")

def test_get_age_binary_download_and_verify(mocker: MockerFixture, mock_bootstrap_config: "BootstrapConfig", tmp_path: Path):
    mocker.patch("sbboot.paths.get_bin_dir", return_value=tmp_path)
    mocker.patch("sbboot.paths.is_windows", return_value=False)
    mocker.patch("sbboot.agewrap._get_system_arch", return_value="linux-amd64")

    mocker.patch("sbboot.util.download_file")

    checksums_content = "aabbcc  age-v1.2.0-linux-amd64.tar.gz"
    mock_httpx_get = mocker.patch("httpx.get")
    mock_httpx_get.return_value.text = checksums_content

    mocker.patch("sbboot.util.verify_sha256")
    mocker.patch("sbboot.agewrap._extract_binary")
    mocker.patch.object(Path, "unlink")

    binary_path = agewrap.get_age_binary(mock_bootstrap_config)

    assert binary_path == tmp_path / "age"

def test_get_age_binary_checksum_mismatch(mocker: MockerFixture, mock_bootstrap_config: "BootstrapConfig", tmp_path: Path):
    mocker.patch("sbboot.paths.get_bin_dir", return_value=tmp_path)
    mocker.patch("sbboot.agewrap._get_system_arch", return_value="linux-amd64")
    mocker.patch("sbboot.util.download_file")

    checksums_content = "ddccbb  age-v1.2.0-linux-amd64.tar.gz"
    mocker.patch("httpx.get").return_value.text = checksums_content

    mocker.patch("sbboot.util.verify_sha256", side_effect=AgeBinaryError("mismatch"))

    with pytest.raises(AgeBinaryError):
        agewrap.get_age_binary(mock_bootstrap_config)
