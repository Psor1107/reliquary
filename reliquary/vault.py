"""High-level vault operations and in-memory session management."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from reliquary import crypto, database


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
    db_path: Path = field(default_factory=lambda: database.DEFAULT_DB_PATH)
    _key: bytes | None = field(default=None, repr=False)

    def initialize(self) -> None:
        database.init_db(self.db_path)

    def is_initialized(self) -> bool:
        self.initialize()
        return database.vault_exists(self.db_path)

    def is_unlocked(self) -> bool:
        return self._key is not None

    def create_vault(self, master_password: str) -> None:
        if not master_password:
            raise VaultError("Master password cannot be empty.")

        self.initialize()
        if database.vault_exists(self.db_path):
            raise VaultError("Vault already exists.")

        salt = crypto.generate_salt()
        key = crypto.derive_key(master_password, salt)
        verifier = crypto.create_verifier(key)

        database.insert_vault_meta(salt, verifier, self.db_path)
        self._key = key

    def unlock(self, master_password: str) -> None:
        if not master_password:
            raise VaultError("Master password cannot be empty.")

        self.initialize()
        if not database.vault_exists(self.db_path):
            raise VaultNotInitializedError("Vault has not been created yet.")

        salt, verifier = database.get_vault_meta(self.db_path)
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
        return database.get_all_paths(self.db_path)

    def add_secret(self, path: str, plaintext: str) -> None:
        path = path.strip()
        if not path:
            raise VaultError("Secret path cannot be empty.")

        key = self._require_key()
        if database.get_secret_by_path(path, self.db_path) is not None:
            raise SecretAlreadyExistsError(f"Secret already exists: {path}")

        ciphertext = crypto.encrypt(key, plaintext)
        database.insert_secret(path, ciphertext, self.db_path)

    def get_secret(self, path: str) -> str:
        key = self._require_key()
        ciphertext = database.get_secret_by_path(path, self.db_path)
        if ciphertext is None:
            raise SecretNotFoundError(f"Secret not found: {path}")
        return crypto.decrypt(key, ciphertext)

    def update_secret(self, path: str, plaintext: str) -> None:
        key = self._require_key()
        if database.get_secret_by_path(path, self.db_path) is None:
            raise SecretNotFoundError(f"Secret not found: {path}")

        ciphertext = crypto.encrypt(key, plaintext)
        database.update_secret(path, ciphertext, self.db_path)

    def delete_secret(self, path: str) -> None:
        self._require_key()
        try:
            database.delete_secret(path, self.db_path)
        except LookupError as exc:
            raise SecretNotFoundError(str(exc)) from exc
