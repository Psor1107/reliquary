"""Remote API storage backend for Reliquary.

This module provides RemoteAPIStorage, a StorageBackend implementation that
consumes a Reliquary HTTP server via REST endpoints.
"""

from __future__ import annotations

import base64
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

from reliquary.storage import StorageBackend


class RemoteAPIStorage(StorageBackend):
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def _request(
        self,
        path: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        allow_not_found: bool = False,
    ) -> Any:
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        body = None

        if data is not None:
            body = json.dumps(data).encode("utf-8")

        request = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(request) as response:
                raw = response.read()
                if not raw:
                    return None
                return json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404 and allow_not_found:
                return None
            if exc.code == 404:
                raise LookupError("Remote resource not found.") from exc
            if exc.code == 400:
                raise LookupError("Remote request failed.") from exc
            raise
        except URLError as exc:
            raise ConnectionError(f"Failed to connect to remote server: {exc}") from exc

    def initialize(self) -> None:
        self._request("/storage/init", method="POST")

    def vault_exists(self) -> bool:
        result = self._request("/storage/exists", method="GET")
        return bool(result.get("exists", False))

    def insert_vault_meta(self, vault_salt: bytes, verifier: bytes) -> None:
        self._request(
            "/storage/vault-meta",
            method="POST",
            data={
                "vault_salt": base64.b64encode(vault_salt).decode("ascii"),
                "verifier": base64.b64encode(verifier).decode("ascii"),
            },
        )

    def get_vault_meta(self) -> tuple[bytes, bytes]:
        result = self._request("/storage/vault-meta", method="GET")
        try:
            vault_salt = base64.b64decode(result["vault_salt"])
            verifier = base64.b64decode(result["verifier"])
            return vault_salt, verifier
        except KeyError as exc:
            raise LookupError("Invalid remote vault metadata response.") from exc

    def insert_secret(self, path: str, ciphertext: bytes) -> None:
        self._request(
            "/storage/secret",
            method="POST",
            data={
                "path": path,
                "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
            },
        )

    def update_secret(self, path: str, ciphertext: bytes) -> None:
        self._request(
            f"/storage/secret/{quote(path, safe='')}",
            method="PUT",
            data={"ciphertext": base64.b64encode(ciphertext).decode("ascii")},
        )

    def delete_secret(self, path: str) -> None:
        self._request(f"/storage/secret/{quote(path, safe='')}", method="DELETE")

    def get_secret_by_path(self, path: str) -> bytes | None:
        result = self._request(
            f"/storage/secret/{quote(path, safe='')}",
            method="GET",
            allow_not_found=True,
        )
        if result is None:
            return None
        ciphertext = result.get("ciphertext")
        if ciphertext is None:
            return None
        return base64.b64decode(ciphertext)

    def get_all_paths(self) -> list[str]:
        result = self._request("/storage/paths", method="GET")
        return list(result.get("paths", []))
