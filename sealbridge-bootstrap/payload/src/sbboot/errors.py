# src/sbboot/errors.py
"""Typed exceptions and exit codes for the application."""

from enum import IntEnum


class ExitCode(IntEnum):
    """Enumeration for application exit codes."""
    OK = 0
    UNKNOWN_ERROR = 1
    CONFIG_ERROR = 10
    OTP_VERIFY_FAILED = 11
    AGE_BINARY_ERROR = 12
    SSH_AGENT_ERROR = 13
    GIT_ERROR = 14
    CHEZMOI_ERROR = 15
    POLICY_VIOLATION = 16
    CHECKSUM_MISMATCH = 17
    ENVIRONMENT_ERROR = 18


class SealBridgeError(Exception):
    """Base exception for all SealBridge Bootstrap errors."""
    def __init__(self, message: str, exit_code: ExitCode = ExitCode.UNKNOWN_ERROR):
        super().__init__(message)
        self.exit_code = exit_code

    def __str__(self) -> str:
        return f"[{self.exit_code.name}] {super().__str__()}"


class ConfigError(SealBridgeError):
    """Exception for configuration loading or validation errors."""
    def __init__(self, message: str):
        super().__init__(message, ExitCode.CONFIG_ERROR)


class OtpError(SealBridgeError):
    """Exception for OTP verification failures."""
    def __init__(self, message: str):
        super().__init__(message, ExitCode.OTP_VERIFY_FAILED)


class AgeBinaryError(SealBridgeError):
    """Exception related to acquiring or verifying the 'age' binary."""
    def __init__(self, message: str):
        super().__init__(message, ExitCode.AGE_BINARY_ERROR)


class SshAgentError(SealBridgeError):
    """Exception for SSH agent-related failures."""
    def __init__(self, message: str):
        super().__init__(message, ExitCode.SSH_AGENT_ERROR)


class GitError(SealBridgeError):
    """Exception for Git-related failures."""
    def __init__(self, message: str):
        super().__init__(message, ExitCode.GIT_ERROR)


class ChezmoiError(SealBridgeError):
    """Exception for chezmoi-related failures."""
    def __init__(self, message: str):
        super().__init__(message, ExitCode.CHEZMOI_ERROR)


class PolicyViolationError(SealBridgeError):
    """Exception for filesystem policy violations."""
    def __init__(self, message: str):
        super().__init__(message, ExitCode.POLICY_VIOLATION)


class ChecksumMismatchError(SealBridgeError):
    """Exception for checksum verification failures."""
    def __init__(self, message: str):
        super().__init__(message, ExitCode.CHECKSUM_MISMATCH)


class EnvironmentError(SealBridgeError):
    """Exception for invalid environment (e.g., bad HOME path)."""
    def __init__(self, message: str):
        super().__init__(message, ExitCode.ENVIRONMENT_ERROR)


class SealreposError(SealBridgeError):
    """Exception for sealbridge-repos installation/configuration errors."""
    def __init__(self, message: str):
        super().__init__(message, ExitCode.UNKNOWN_ERROR)
