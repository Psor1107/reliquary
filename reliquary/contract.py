"""YAML contract parsing and validation for secret injection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_SECRETS_FILENAME = "secrets.yml"


class SecretsContractError(Exception):
    """Raised when the YAML contract is invalid or cannot be located."""


def resolve_secrets_file(explicit_path: Path | None = None) -> Path:
    """Locate secrets.yml in the working directory or in examples/."""
    if explicit_path is not None:
        return explicit_path

    cwd_candidate = Path.cwd() / DEFAULT_SECRETS_FILENAME
    if cwd_candidate.is_file():
        return cwd_candidate

    package_dir = Path(__file__).resolve().parent
    client_candidate = package_dir.parent / "examples" / DEFAULT_SECRETS_FILENAME
    if client_candidate.is_file():
        return client_candidate

    raise SecretsContractError(
        f"Could not find {DEFAULT_SECRETS_FILENAME} in the current directory "
        f"or at {client_candidate}."
    )


def load_secrets_contract(secrets_path: Path) -> dict[str, str]:
    """Parse the YAML contract mapping env var names to vault paths."""
    if not secrets_path.is_file():
        raise SecretsContractError(f"Secrets contract not found: {secrets_path}")

    with secrets_path.open("r", encoding="utf-8") as handle:
        raw: Any = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise SecretsContractError("secrets.yml root must be a mapping.")

    env_section = raw.get("env")
    if not isinstance(env_section, dict) or not env_section:
        raise SecretsContractError("secrets.yml must define a non-empty 'env' mapping.")

    mapping: dict[str, str] = {}
    for env_name, vault_path in env_section.items():
        if not isinstance(env_name, str) or not env_name.strip():
            raise SecretsContractError("Environment variable names must be non-empty strings.")
        if not isinstance(vault_path, str) or not vault_path.strip():
            raise SecretsContractError(
                f"Vault path for '{env_name}' must be a non-empty string."
            )
        mapping[env_name] = vault_path.strip()

    return mapping
