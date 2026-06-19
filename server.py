"""FastAPI server for Reliquary remote API mode."""

from __future__ import annotations

import base64
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from reliquary.database import SQLiteStorage
from reliquary.vault import Vault, VaultError

app = FastAPI()
storage = SQLiteStorage()
vault = Vault(storage=storage)


@app.post("/storage/init")
def initialize_storage() -> JSONResponse:
    try:
        storage.initialize()
        return JSONResponse({"status": "ok"})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/storage/exists")
def storage_exists() -> dict[str, bool]:
    return {"exists": storage.vault_exists()}


@app.post("/storage/vault-meta")
def create_vault_meta(payload: dict[str, str]) -> JSONResponse:
    try:
        vault_salt = base64.b64decode(payload["vault_salt"])
        verifier = base64.b64decode(payload["verifier"])
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing field: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        storage.insert_vault_meta(vault_salt, verifier)
        return JSONResponse({"status": "ok"})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/storage/vault-meta")
def get_vault_meta() -> dict[str, str]:
    try:
        vault_salt, verifier = storage.get_vault_meta()
        return {
            "vault_salt": base64.b64encode(vault_salt).decode("ascii"),
            "verifier": base64.b64encode(verifier).decode("ascii"),
        }
    except LookupError:
        raise HTTPException(status_code=404, detail="Vault metadata not found.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/storage/secret")
def insert_secret(payload: dict[str, str]) -> JSONResponse:
    try:
        path = payload["path"]
        ciphertext = base64.b64decode(payload["ciphertext"])
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing field: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        storage.insert_secret(path, ciphertext)
        return JSONResponse({"status": "ok"})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.put("/storage/secret/{path:path}")
def update_secret(path: str, payload: dict[str, str]) -> JSONResponse:
    try:
        ciphertext = base64.b64decode(payload["ciphertext"])
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing field: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        storage.update_secret(path, ciphertext)
        return JSONResponse({"status": "ok"})
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/storage/secret/{path:path}")
def delete_secret(path: str) -> JSONResponse:
    try:
        storage.delete_secret(path)
        return JSONResponse({"status": "ok"})
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/storage/secret/{path:path}")
def get_secret(path: str) -> dict[str, str]:
    try:
        ciphertext = storage.get_secret_by_path(path)
        if ciphertext is None:
            raise LookupError(f"Secret not found: {path}")
        return {"ciphertext": base64.b64encode(ciphertext).decode("ascii")}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/storage/paths")
def get_paths() -> dict[str, list[str]]:
    return {"paths": storage.get_all_paths()}
