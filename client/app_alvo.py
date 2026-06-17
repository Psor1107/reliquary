"""Minimal target app to verify environment variable injection."""

from __future__ import annotations

import os


def main() -> None:
    api_key = os.getenv("API_KEY")
    db_password = os.getenv("DB_PASSWORD")

    print(f"API_KEY={api_key!r}")
    print(f"DB_PASSWORD={db_password!r}")


if __name__ == "__main__":
    main()
