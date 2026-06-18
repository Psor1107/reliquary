"""CLI entry point for injecting vault secrets into subprocess environments."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from reliquary.contract import (
    DEFAULT_SECRETS_FILENAME,
    SecretsContractError,
    load_secrets_contract,
    resolve_secrets_file,
)
from reliquary.launcher import LauncherError, build_merged_environ, run_target_command
from reliquary.remote import RemoteAPIStorage
from reliquary.vault import (
    InvalidMasterPasswordError,
    SecretNotFoundError,
    Vault,
    VaultError,
    VaultNotInitializedError,
)
from reliquary.database import SQLiteStorage


# Session cache configuration
SESSION_DIR: Path = Path.home() / ".reliquary"
SESSION_FILE: Path = SESSION_DIR / ".session"
SESSION_TTL: int = 900  # 15 minutes


def _ensure_session_dir() -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(SESSION_DIR, 0o700)
    except Exception:
        # Best-effort: chmod may not be supported on some platforms
        pass


def _read_session() -> str | None:
    try:
        if not SESSION_FILE.is_file():
            return None
        with SESSION_FILE.open("r", encoding="utf-8") as fh:
            data: Any = json.load(fh)
        expires_at = float(data.get("expires_at", 0))
        if expires_at > time.time():
            pw = data.get("password")
            if isinstance(pw, str) and pw:
                return pw
        # expired or invalid
        try:
            SESSION_FILE.unlink()
        except Exception:
            pass
    except Exception:
        # On any error, return no session
        return None
    return None


def _write_session(password: str, ttl: int = SESSION_TTL) -> None:
    _ensure_session_dir()
    data = {"password": password, "expires_at": time.time() + float(ttl)}
    tmp = SESSION_DIR / (SESSION_FILE.name + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, SESSION_FILE)
        try:
            os.chmod(SESSION_FILE, 0o600)
        except Exception:
            pass
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


def unlock_vault(master_password: str, db_path: Path | None = None, remote_url: str | None = None) -> Vault:
    """Unlock the vault without mutating stored secrets.

    This constructs either a remote or local storage backend and injects it into Vault.
    """
    if remote_url:
        storage = RemoteAPIStorage(base_url=remote_url)
    else:
        storage = SQLiteStorage(db_path=db_path) if db_path else SQLiteStorage()

    vault = Vault(storage=storage)

    if not vault.is_initialized():
        raise VaultNotInitializedError("Vault has not been created yet.")

    vault.unlock(master_password)
    return vault


def resolve_env_from_vault(vault: Vault, mapping: dict[str, str]) -> dict[str, str]:
    """Fetch every secret referenced by the contract before subprocess execution."""
    resolved: dict[str, str] = {}
    missing: list[str] = []

    for env_name, vault_path in mapping.items():
        try:
            resolved[env_name] = vault.get_secret(vault_path)
        except SecretNotFoundError:
            missing.append(f"{env_name} -> {vault_path}")

    if missing:
        details = "\n".join(f"  - {item}" for item in missing)
        raise SecretsContractError(
            "One or more secrets referenced in secrets.yml were not found in the vault:\n"
            f"{details}"
        )

    return resolved


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a command with secrets from Reliquary injected as environment variables.",
    )
    parser.add_argument(
        "--password",
        required=False,
        help="Master password used to unlock the local vault (optional; will prompt if omitted).",
    )
    parser.add_argument(
        "--secrets-file",
        type=Path,
        default=None,
        help=(
            f"Path to the YAML contract (default: {DEFAULT_SECRETS_FILENAME} "
            "in cwd or client/)."
        ),
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Optional path to registry.db (defaults to the project registry.db).",
    )
    parser.add_argument(
        "--remote-url",
        type=str,
        default=None,
        help="Optional remote Reliquary server URL, e.g. http://localhost:8000.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Target command after '--', e.g. -- python client/app_alvo.py",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.command[:1] == ["--"]:
        command = args.command[1:]
    else:
        command = args.command

    try:
        secrets_path = resolve_secrets_file(args.secrets_file)
        mapping = load_secrets_contract(secrets_path)

        # Determine master password: CLI arg -> session cache -> interactive prompt
        password: str | None = None
        if getattr(args, "password", None):
            password = args.password
        else:
            password = _read_session()

        if not password:
            try:
                password = getpass.getpass("Master Password: ")
            except Exception:
                print("Error: failed reading master password.", file=sys.stderr)
                return 1

        vault = unlock_vault(password, args.db_path, args.remote_url)

        # On successful unlock, cache the password for a short TTL for DX
        try:
            _write_session(password, ttl=SESSION_TTL)
        except Exception:
            # Best-effort: do not block execution if session caching fails
            pass

        injected = resolve_env_from_vault(vault, mapping)
        env = build_merged_environ(injected)
        vault.lock()
        return run_target_command(command, env)
    except InvalidMasterPasswordError:
        print("Error: invalid master password.", file=sys.stderr)
        return 1
    except VaultNotInitializedError:
        print("Error: vault has not been created yet. Run the GUI first.", file=sys.stderr)
        return 1
    except SecretsContractError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except LauncherError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except VaultError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
