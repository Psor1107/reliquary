"""Storage backend abstraction for Reliquary.

Defines the StorageBackend Protocol used for dependency injection so the
Vault core can remain backend-agnostic (SQLite, remote API, etc.).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class StorageBackend(Protocol):
    def initialize(self) -> None:
        ...

    def vault_exists(self) -> bool:
        ...

    def insert_vault_meta(self, vault_salt: bytes, verifier: bytes) -> None:
        ...

    def get_vault_meta(self) -> tuple[bytes, bytes]:
        ...

    def insert_secret(self, path: str, ciphertext: bytes) -> None:
        ...

    def update_secret(self, path: str, ciphertext: bytes) -> None:
        ...

    def delete_secret(self, path: str) -> None:
        ...

    def get_secret_by_path(self, path: str) -> bytes | None:
        ...

    def get_all_paths(self) -> list[str]:
        ...
