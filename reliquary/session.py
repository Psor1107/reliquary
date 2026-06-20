"""
Mecanismo de Cache em Disco com TTL Passivo e Hardware-Bound Encryption.
Os dados da sessão são criptografados com uma chave AES derivada 
da assinatura única do hardware e do usuário do SO.
"""

from __future__ import annotations

import json
import os
import time
import base64
import getpass
import hashlib
import uuid
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

CACHE_DIR = Path.home() / ".reliquary"
CACHE_FILE = CACHE_DIR / ".session"
TTL_SECONDS = 900  # 15 minutos


def _get_hardware_key() -> bytes:
    """
    Gera uma chave AES (Fernet)  determinística amarrada à máquina.
    Usa o endereço MAC da placa-mãe + o nome do usuário do SO.
    Se o arquivo for roubado para outro PC, a chave gerada lá será diferente e a leitura falha.
    """
    # Ex: User + 00:1A:2B:3C:4D:5E
    hw_signature = f"{getpass.getuser()}_{uuid.getnode()}".encode('utf-8')
    
    # Faz um hash SHA-256 da assinatura para garantir 32 bytes (tamanho exigido pelo Fernet/AES)
    key_hash = hashlib.sha256(hw_signature).digest()
    
    # Retorna o hash no formato base64 compatível com Fernet
    return base64.urlsafe_b64encode(key_hash)


def save_session(password: str, ttl: int = TTL_SECONDS) -> None:
    """Criptografa e salva a sessão atrelada ao hardware."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        os.chmod(CACHE_DIR, 0o700)
    except OSError:
        pass

    expires_at = time.time() + float(ttl)
    data = {"password": password, "expires_at": expires_at}
    
    # Transforma o JSON em bytes
    payload = json.dumps(data).encode('utf-8')
    
    # Criptografa o payload com a chave da máquina
    fernet = Fernet(_get_hardware_key())
    encrypted_payload = fernet.encrypt(payload)
    
    tmp = CACHE_DIR / (CACHE_FILE.name + ".tmp")
    try:
        with open(tmp, "wb") as f:
            f.write(encrypted_payload)
            f.flush()
            os.fsync(f.fileno())
            
        os.replace(tmp, CACHE_FILE)
        
        try:
            os.chmod(CACHE_FILE, 0o600)
        except OSError:
            pass
            
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def load_session() -> Optional[str]:
    """Lê o arquivo, descriptografa com a chave de hardware e valida o TTL."""
    if not CACHE_FILE.is_file():
        return None
        
    try:
        # Lê os bytes criptografados
        with open(CACHE_FILE, "rb") as f:
            encrypted_payload = f.read()
            
        # Descriptografa gerando a mesma chave atrelada ao PC
        fernet = Fernet(_get_hardware_key())
        decrypted_payload = fernet.decrypt(encrypted_payload)
        
        data = json.loads(decrypted_payload.decode('utf-8'))
        
        # TTL Passivo: Verifica se a validade passou
        if float(data.get("expires_at", 0)) > time.time():
            pw = data.get("password")
            if isinstance(pw, str) and pw:
                return pw
                
        # Expirou, apaga o arquivo
        clear_session()
        return None
        
    except (InvalidToken, json.JSONDecodeError, OSError):
        clear_session()
        return None


def clear_session() -> None:
    """Tranca o cofre destruindo o cache instantaneamente."""
    try:
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
    except OSError:
        pass