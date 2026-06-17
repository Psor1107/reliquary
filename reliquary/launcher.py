"""Process environment assembly and subprocess execution."""

from __future__ import annotations

import os
import subprocess


class LauncherError(Exception):
    """Raised when the target command cannot be executed."""


def build_merged_environ(injected: dict[str, str]) -> dict[str, str]:
    """Merge injected secrets on top of the current process environment."""
    merged = os.environ.copy()
    merged.update(injected)
    return merged


def run_target_command(command: list[str], env: dict[str, str]) -> int:
    """Execute the target process with the provided environment."""
    if not command:
        raise LauncherError("No target command was provided after '--'.")

    completed = subprocess.run(command, env=env, check=False)
    return completed.returncode
