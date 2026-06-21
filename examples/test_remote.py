"""End-to-end robust test for Reliquary remote API mode.

This script exercises the full CRUD lifecycle against a running Reliquary FastAPI
server. It prompts interactively for the master password using `getpass` and
prints a concise report for each step. It always attempts cleanup
in a finally block.

Usage: run the FastAPI server (see README) and then:

    python examples/test_remote.py

"""

from __future__ import annotations

import sys
import time
import traceback
from getpass import getpass
from typing import Optional

from reliquary.remote import RemoteAPIStorage
from reliquary.vault import (
    InvalidMasterPasswordError,
    SecretAlreadyExistsError,
    SecretNotFoundError,
    Vault,
    VaultError,
)


TEST_PATH = "examples/test_key"


def log_ok(msg: str) -> None:
    print(f"[ OK ] {msg}")


def log_fail(msg: str) -> None:
    print(f"[ FAIL ] {msg}")


def log_running(msg: str) -> None:
    print(f"[ RUNNING ] {msg}")


def main() -> int:
    remote_url = input("Remote server URL [http://localhost:8000]: ") or "http://localhost:8000"
    password = getpass("Master Password: ")

    storage = RemoteAPIStorage(base_url=remote_url)
    vault = Vault(storage=storage)

    created_vault = False
    created_secret = False

    # Give nice header
    print("\nReliquary Remote E2E — Robust Test")
    print(f"Target: {remote_url}")

    try:
        log_running("Initializing remote storage schema (idempotent)")
        try:
            storage.initialize()
            log_ok("Remote storage initialized (or already present)")
        except Exception as exc:
            log_fail(f"Failed to initialize remote storage: {exc}")
            raise

        # Create or unlock vault
        log_running("Checking vault existence")
        try:
            if not vault.is_initialized():
                log_running("Vault not initialized remotely — creating vault")
                vault.create_vault(password)
                created_vault = True
                log_ok("Vault created and unlocked")
            else:
                log_running("Vault exists; attempting to unlock with provided password")
                vault.unlock(password)
                log_ok("Vault unlocked")
        except InvalidMasterPasswordError:
            log_fail("Invalid master password provided — cannot unlock remote vault")
            return 2
        except Exception as exc:
            log_fail(f"Error while creating/unlocking vault: {exc}")
            raise

        # Keep using the unlocked vault for CRUD
        # 1) Add secret
        value_a = f"value-A-{int(time.time())}"
        log_running(f"Adding secret at path '{TEST_PATH}'")
        try:
            vault.add_secret(TEST_PATH, value_a)
            created_secret = True
            log_ok("Secret added")
        except SecretAlreadyExistsError:
            log_fail("Secret already exists when trying to add (expected for duplicate test)")
            # For our success-path we want a fresh secret, so treat as failure
            raise

        # 2) Read secret
        log_running("Reading back secret and validating value")
        try:
            got = vault.get_secret(TEST_PATH)
            if got == value_a:
                log_ok("Read secret matches written value")
            else:
                log_fail("Read secret does NOT match written value")
                raise AssertionError("Secret mismatch")
        except Exception as exc:
            log_fail(f"Failed reading/validating secret: {exc}")
            raise

        # 3) Update secret
        value_b = f"value-B-{int(time.time())}"
        log_running("Updating secret value")
        try:
            vault.update_secret(TEST_PATH, value_b)
            got2 = vault.get_secret(TEST_PATH)
            if got2 == value_b:
                log_ok("Update persisted correctly")
            else:
                log_fail("Updated value not observed")
                raise AssertionError("Update mismatch")
        except Exception as exc:
            log_fail(f"Failed updating secret: {exc}")
            raise

        # 4) List paths -> expect our test path
        log_running("Listing all paths and checking presence of test path")
        try:
            paths = vault.list_paths()
            if TEST_PATH in paths:
                log_ok("Test path present in remote paths list")
            else:
                log_fail("Test path not found in remote paths list")
                raise AssertionError("Path missing from list")
        except Exception as exc:
            log_fail(f"Failed listing paths: {exc}")
            raise

        # Edge cases
        # - Get non-existent secret
        log_running("Attempting to fetch a non-existent secret (should fail 404)")
        try:
            try:
                vault.get_secret("does/not/exist")
                log_fail("Unexpectedly found non-existent secret")
                raise AssertionError("Non-existent secret unexpectedly returned")
            except SecretNotFoundError:
                log_ok("Non-existent secret raised SecretNotFoundError as expected")
            except LookupError:
                # Remote client may surface LookupError
                log_ok("Non-existent secret resulted in LookupError (mapped to 404) as expected")
        except Exception as exc:
            log_fail(f"Error while testing non-existent secret case: {exc}")
            raise

        # - Add duplicate secret
        log_running("Attempting to add duplicate secret (should raise)")
        try:
            try:
                vault.add_secret(TEST_PATH, "duplicate")
                log_fail("Duplicate insertion did not raise")
                raise AssertionError("Duplicate insertion did not fail")
            except SecretAlreadyExistsError:
                log_ok("Duplicate insertion raised SecretAlreadyExistsError as expected")
        except Exception as exc:
            log_fail(f"Error while testing duplicate insertion: {exc}")
            raise

        # All good
        print("\nAll remote E2E checks passed.")
        return 0

    except Exception:
        print("\nOne or more checks failed; see trace below:")
        traceback.print_exc()
        return 1

    finally:
        # Teardown: attempt to delete created secret
        try:
            if vault and created_secret:
                log_running(f"Cleaning up: deleting test secret '{TEST_PATH}'")
                try:
                    vault.delete_secret(TEST_PATH)
                    log_ok("Test secret deleted")
                except Exception as exc:
                    log_fail(f"Failed to delete test secret: {exc}")
        except Exception:
            # best-effort cleanup must not mask original error
            pass


if __name__ == "__main__":
    sys.exit(main())
