"""
Encrypted team memory sync package (N19) — export/import encrypted bundle.

Phase 3: concurrent-safe import/export under store locks; merge by memory id
(skip duplicates, optional overwrite).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from .memory_palace import MemoryPalace, get_shared_palace
from .store_lock import store_lock


def _derive(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=120_000)
    return kdf.derive(password.encode("utf-8"))


def export_encrypted_memory(password: str, dest: Path) -> Path:
    mp = get_shared_palace()
    root = Path(mp.persist_directory)
    with store_lock(root, name="palace.lock", timeout=60.0):
        docs = mp.get_all_memories()
        payload = json.dumps({"memories": docs, "format": "superai.memory_sync.v1"}, default=str).encode(
            "utf-8"
        )
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive(password, salt)
    ct = AESGCM(key).encrypt(nonce, payload, None)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(salt + nonce + ct)
    return dest


def import_encrypted_memory(
    password: str,
    src: Path,
    *,
    merge: str = "skip",
    use_queue: bool = False,
) -> Dict[str, Any]:
    """
    Import encrypted memories.

    merge:
      - skip: do not overwrite existing id (default)
      - overwrite: re-store content with same logical content (new ids if needed)
      - always: always store as new entries
    use_queue: route stores through memory write queue (parallel multi-CLI safe)
    """
    raw = Path(src).read_bytes()
    salt, nonce, ct = raw[:16], raw[16:28], raw[28:]
    key = _derive(password, salt)
    pt = AESGCM(key).decrypt(nonce, ct, None)
    data = json.loads(pt.decode("utf-8"))
    mp = get_shared_palace()
    existing_ids = set()
    existing_content = set()
    try:
        for m in mp.get_all_memories() or []:
            if m.get("id"):
                existing_ids.add(str(m["id"]))
            c = (m.get("content") or "").strip()
            if c:
                existing_content.add(c[:500])
    except Exception:
        pass

    imported = 0
    skipped = 0
    errors = 0
    for m in data.get("memories") or []:
        content = m.get("content") or ""
        if not content:
            continue
        mid = str(m.get("id") or "")
        if merge == "skip":
            if mid and mid in existing_ids:
                skipped += 1
                continue
            if content.strip()[:500] in existing_content:
                skipped += 1
                continue
        tags = m.get("tags") or []
        if isinstance(tags, str):
            tags = [t for t in tags.split(",") if t]
        meta = dict(m.get("metadata") or {})
        meta.setdefault("imported_from_sync", True)
        try:
            if use_queue:
                new_id = mp.store_queued(
                    content,
                    tags=tags,
                    metadata=meta,
                    importance=float(m.get("importance") or meta.get("importance") or 0.7),
                )
            else:
                new_id = mp.store(
                    content,
                    tags=tags,
                    metadata=meta,
                    importance=float(m.get("importance") or meta.get("importance") or 0.7),
                )
            imported += 1
            existing_ids.add(str(new_id))
            existing_content.add(content.strip()[:500])
        except Exception:
            errors += 1
    return {
        "ok": errors == 0,
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "merge": merge,
        "use_queue": use_queue,
    }
