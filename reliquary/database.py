"""SQLite storage backend implementing the StorageBackend protocol.

This module provides SQLiteStorage, a concrete implementation that can be
injected into Vault via the StorageBackend Protocol defined in
reliquary.storage.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reliquary.storage import StorageBackend


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "registry.db"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteStorage(StorageBackend):
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS vault_meta (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    vault_salt BLOB NOT NULL,
                    verifier BLOB NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS secrets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL UNIQUE,
                    ciphertext BLOB NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def vault_exists(self) -> bool:
        if not self.db_path.exists():
            return False
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM vault_meta WHERE id = 1").fetchone()
        return row is not None

    def get_vault_meta(self) -> tuple[bytes, bytes]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT vault_salt, verifier FROM vault_meta WHERE id = 1"
            ).fetchone()
        if row is None:
            raise LookupError("Vault has not been initialized.")
        return row["vault_salt"], row["verifier"]

    def insert_vault_meta(self, vault_salt: bytes, verifier: bytes) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO vault_meta (id, vault_salt, verifier, created_at)
                VALUES (1, ?, ?, ?)
                """,
                (vault_salt, verifier, _utc_now()),
            )

    def insert_secret(self, path: str, ciphertext: bytes) -> None:
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO secrets (path, ciphertext, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (path, ciphertext, now, now),
            )

    def update_secret(self, path: str, ciphertext: bytes) -> None:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE secrets
                SET ciphertext = ?, updated_at = ?
                WHERE path = ?
                """,
                (ciphertext, _utc_now(), path),
            )
            if cursor.rowcount == 0:
                raise LookupError(f"Secret not found: {path}")

    def delete_secret(self, path: str) -> None:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM secrets WHERE path = ?", (path,))
            if cursor.rowcount == 0:
                raise LookupError(f"Secret not found: {path}")

    def get_secret_by_path(self, path: str) -> bytes | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT ciphertext FROM secrets WHERE path = ?",
                (path,),
            ).fetchone()
        if row is None:
            return None
        return row["ciphertext"]

    def get_all_paths(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT path FROM secrets ORDER BY path ASC").fetchall()
        return [row["path"] for row in rows]
