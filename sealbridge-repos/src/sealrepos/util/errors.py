# src/sealrepos/util/errors.py: Typed exceptions and exit codes.
# This module defines a hierarchy of custom exception types for the application.
# Associating specific exceptions with different error conditions allows for
# more granular error handling and mapping exceptions to process exit codes.

class SealbridgeError(Exception):
    """Base exception for the application."""
    exit_code = 1

class ConfigError(SealbridgeError):
    """Configuration-related errors."""
    exit_code = 2

class GitError(SealbridgeError):
    """Git command errors."""
    exit_code = 3

class PolicyViolationError(SealbridgeError):
    """Policy violation errors."""
    exit_code = 4

class SecretFoundError(PolicyViolationError):
    """Secret found during scan."""
    exit_code = 5
