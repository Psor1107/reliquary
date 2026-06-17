"""High-level vault operations and in-memory session management."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from reliquary import crypto
from reliquary.storage import StorageBackend


class VaultError(Exception):
    """Base error for vault operations."""


class VaultLockedError(VaultError):
    """Raised when an operation requires an unlocked vault."""


class VaultNotInitializedError(VaultError):
    """Raised when the vault has not been created yet."""


class InvalidMasterPasswordError(VaultError):
    """Raised when the master password cannot unlock the vault."""


class SecretAlreadyExistsError(VaultError):
    """Raised when inserting a duplicate secret path."""


class SecretNotFoundError(VaultError):
    """Raised when a secret path does not exist."""


@dataclass
class Vault:
    storage: StorageBackend
    _key: bytes | None = field(default=None, repr=False)

    def initialize(self) -> None:
        self.storage.initialize()

    def is_initialized(self) -> bool:
        self.initialize()
        return self.storage.vault_exists()

    def is_unlocked(self) -> bool:
        return self._key is not None

    def create_vault(self, master_password: str) -> None:
        if not master_password:
            raise VaultError("Master password cannot be empty.")

        self.initialize()
        if self.storage.vault_exists():
            raise VaultError("Vault already exists.")

        salt = crypto.generate_salt()
        key = crypto.derive_key(master_password, salt)
        verifier = crypto.create_verifier(key)

        self.storage.insert_vault_meta(salt, verifier)
        self._key = key

    def unlock(self, master_password: str) -> None:
        if not master_password:
            raise VaultError("Master password cannot be empty.")

        self.initialize()
        if not self.storage.vault_exists():
            raise VaultNotInitializedError("Vault has not been created yet.")

        salt, verifier = self.storage.get_vault_meta()
        key = crypto.derive_key(master_password, salt)

        if not crypto.verify_key(key, verifier):
            self._key = None
            raise InvalidMasterPasswordError("Invalid master password.")

        self._key = key

    def lock(self) -> None:
        self._key = None

    def _require_key(self) -> bytes:
        if self._key is None:
            raise VaultLockedError("Vault is locked. Unlock with the master password.")
        return self._key

    def list_paths(self) -> list[str]:
        self._require_key()
        return self.storage.get_all_paths()

    def add_secret(self, path: str, plaintext: str) -> None:
        path = path.strip()
        if not path:
            raise VaultError("Secret path cannot be empty.")

        key = self._require_key()
        if self.storage.get_secret_by_path(path) is not None:
            raise SecretAlreadyExistsError(f"Secret already exists: {path}")

        ciphertext = crypto.encrypt(key, plaintext)
        self.storage.insert_secret(path, ciphertext)

    def get_secret(self, path: str) -> str:
        key = self._require_key()
        ciphertext = self.storage.get_secret_by_path(path)
        if ciphertext is None:
            raise SecretNotFoundError(f"Secret not found: {path}")
        return crypto.decrypt(key, ciphertext)

    def update_secret(self, path: str, plaintext: str) -> None:
        key = self._require_key()
        if self.storage.get_secret_by_path(path) is None:
            raise SecretNotFoundError(f"Secret not found: {path}")

        ciphertext = crypto.encrypt(key, plaintext)
        self.storage.update_secret(path, ciphertext)

    def delete_secret(self, path: str) -> None:
        self._require_key()
        try:
            self.storage.delete_secret(path)
        except LookupError as exc:
            raise SecretNotFoundError(str(exc)) from exc
