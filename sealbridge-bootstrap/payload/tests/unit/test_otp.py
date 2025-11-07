# tests/unit/test_otp.py
import os
import pytest
import httpx
from pytest_mock import MockerFixture

from sbboot import otp
from sbboot.config import OtpGateConfig
from sbboot.errors import ConfigError, OtpError

@pytest.fixture
def otp_config() -> OtpGateConfig:
    return OtpGateConfig(
        url="http://test-otp-gate/v1/verify",
        client_id="test-client",
        client_secret_env="TEST_SECRET_ENV_VAR"
    )

def test_verify_totp_success(otp_config: OtpGateConfig, mocker: MockerFixture):
    mocker.patch.dict(os.environ, {"TEST_SECRET_ENV_VAR": "supersecret"})

    mock_response = httpx.Response(200, json={"ok": True}, request=mocker.Mock())
    mocker.patch("httpx.Client.post", return_value=mock_response)

    assert otp.verify_totp_code(otp_config, "123456") is True

def test_verify_totp_failure_bad_code(otp_config: OtpGateConfig, mocker: MockerFixture):
    mocker.patch.dict(os.environ, {"TEST_SECRET_ENV_VAR": "supersecret"})

    mock_response = httpx.Response(200, json={"ok": False, "error": "Invalid token"}, request=mocker.Mock())
    mocker.patch("httpx.Client.post", return_value=mock_response)

    with pytest.raises(OtpError, match="Verification failed: Invalid token"):
        otp.verify_totp_code(otp_config, "654321")

def test_verify_totp_http_client_error(otp_config: OtpGateConfig, mocker: MockerFixture):
    mocker.patch.dict(os.environ, {"TEST_SECRET_ENV_VAR": "supersecret"})

    mock_response = httpx.Response(400, json={"error": "Bad request"}, request=mocker.Mock())
    mocker.patch("httpx.Client.post", return_value=mock_response)

    with pytest.raises(OtpError, match="OTP gate returned an error: Bad request"):
        otp.verify_totp_code(otp_config, "123456", max_retries=3)

def test_verify_totp_http_server_error_with_retry(otp_config: OtpGateConfig, mocker: MockerFixture):
    mocker.patch.dict(os.environ, {"TEST_SECRET_ENV_VAR": "supersecret"})

    mock_post = mocker.patch("httpx.Client.post")
    mock_request = mocker.Mock()
    mock_post.side_effect = [
        httpx.Response(500, text="Internal Server Error", request=mock_request),
        httpx.Response(500, text="Internal Server Error", request=mock_request),
        httpx.Response(200, json={"ok": True}, request=mock_request),
    ]

    mocker.patch("time.sleep")

    assert otp.verify_totp_code(otp_config, "123456", max_retries=3) is True
    assert mock_post.call_count == 3

def test_verify_totp_exhausts_retries(otp_config: OtpGateConfig, mocker: MockerFixture):
    mocker.patch.dict(os.environ, {"TEST_SECRET_ENV_VAR": "supersecret"})

    mocker.patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection failed"))
    mocker.patch("time.sleep")

    with pytest.raises(OtpError, match="Failed to verify OTP after 3 attempts"):
        otp.verify_totp_code(otp_config, "123456", max_retries=3)

def test_get_client_secret_missing_env_var(otp_config: OtpGateConfig):
    if "TEST_SECRET_ENV_VAR" in os.environ:
        del os.environ["TEST_SECRET_ENV_VAR"]

    with pytest.raises(ConfigError, match="OTP gate client secret not found"):
        otp._get_client_secret(otp_config)
