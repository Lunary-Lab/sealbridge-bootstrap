# src/sealrepos/cryptmode/__init__.py: Encryption Strategy registry.
# This file initializes the 'cryptmode' package and serves as a registry for
# different encryption strategies (e.g., git-crypt, sops-age). It allows the
# application to select and use an encryption mode dynamically based on the
# configuration.

from abc import ABC, abstractmethod

class CryptoMode(ABC):
    @abstractmethod
    def unlock(self, repo_path: str):
        """Unlock the repository for the current user."""
        pass

    @abstractmethod
    def is_unlocked(self, repo_path: str) -> bool:
        """Check if the repository is already unlocked."""
        pass
