"""
Encrypted team memory sync package (N19) — export/import encrypted bundle.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from .memory_palace import MemoryPalace


def _derive(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=120_000)
    return kdf.derive(password.encode("utf-8"))


def export_encrypted_memory(password: str, dest: Path) -> Path:
    mp = MemoryPalace()
    docs = mp.get_all_memories()
    payload = json.dumps({"memories": docs}, default=str).encode("utf-8")
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive(password, salt)
    ct = AESGCM(key).encrypt(nonce, payload, None)
    dest = Path(dest)
    dest.write_bytes(salt + nonce + ct)
    return dest


def import_encrypted_memory(password: str, src: Path) -> Dict[str, Any]:
    raw = Path(src).read_bytes()
    salt, nonce, ct = raw[:16], raw[16:28], raw[28:]
    key = _derive(password, salt)
    pt = AESGCM(key).decrypt(nonce, ct, None)
    data = json.loads(pt.decode("utf-8"))
    mp = MemoryPalace()
    n = 0
    for m in data.get("memories") or []:
        content = m.get("content") or ""
        if not content:
            continue
        tags = m.get("tags") or []
        if isinstance(tags, str):
            tags = [t for t in tags.split(",") if t]
        mp.store(content, tags=tags, metadata=m.get("metadata") or {})
        n += 1
    return {"ok": True, "imported": n}
