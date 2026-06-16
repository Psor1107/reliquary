"""Pure cryptographic primitives for Reliquary vault operations."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from base64 import urlsafe_b64encode

from argon2.low_level import Type, hash_secret_raw
from cryptography.fernet import Fernet, InvalidToken

VERIFIER_MESSAGE = b"reliquary-vault-v1"

# Tuned for local desktop use: ~64 MB RAM, ~200-400 ms on typical hardware.
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST_KIB = 65536
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32
SALT_LEN = 16


def generate_salt() -> bytes:
    return secrets.token_bytes(SALT_LEN)


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 32-byte key from the master password and vault salt."""
    return hash_secret_raw(
        secret=password.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST_KIB,
        parallelism=ARGON2_PARALLELISM,
        hash_len=ARGON2_HASH_LEN,
        type=Type.ID,
    )


def _fernet_from_key(raw_key: bytes) -> Fernet:
    fernet_key = urlsafe_b64encode(raw_key)
    return Fernet(fernet_key)


def encrypt(raw_key: bytes, plaintext: str) -> bytes:
    return _fernet_from_key(raw_key).encrypt(plaintext.encode("utf-8"))


def decrypt(raw_key: bytes, ciphertext: bytes) -> str:
    try:
        return _fernet_from_key(raw_key).decrypt(ciphertext).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Decryption failed: invalid key or corrupted data.") from exc


def create_verifier(raw_key: bytes) -> bytes:
    return hmac.new(raw_key, VERIFIER_MESSAGE, hashlib.sha256).digest()


def verify_key(raw_key: bytes, verifier: bytes) -> bool:
    expected = create_verifier(raw_key)
    return hmac.compare_digest(expected, verifier)
