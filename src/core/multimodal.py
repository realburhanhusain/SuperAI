"""
Multimodal helpers (Phase 8 N3) — attach local images into text prompts.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional


def describe_image_file(path: str, max_bytes: int = 2_000_000) -> Dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        return {"ok": False, "error": "not_found", "path": path}
    data = p.read_bytes()
    if len(data) > max_bytes:
        return {"ok": False, "error": "too_large", "path": path, "bytes": len(data)}
    mime = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
    b64 = base64.b64encode(data).decode("ascii")
    return {
        "ok": True,
        "path": str(p.resolve()),
        "mime": mime,
        "bytes": len(data),
        "data_url": f"data:{mime};base64,{b64[:80]}…",  # truncated in metadata
        "base64": b64,
    }


def prompt_with_images(text: str, image_paths: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Build a text prompt that includes image metadata + base64 for providers
    that accept data URLs in text (and for logging). Live vision APIs can
    consume base64 from attachments.
    """
    attachments = []
    parts = [text or ""]
    for ip in image_paths or []:
        info = describe_image_file(ip)
        attachments.append({k: info.get(k) for k in ("ok", "path", "mime", "bytes") if k in info})
        if info.get("ok"):
            parts.append(
                f"\n[Image attachment: {info['path']} mime={info['mime']} "
                f"bytes={info['bytes']}]\n"
                f"(base64 length={len(info.get('base64') or '')}; "
                f"providers with vision can use full payload from attachments)\n"
            )
            # Keep full base64 only in structured attachments, not prompt bloat
    return {
        "ok": True,
        "prompt": "\n".join(parts),
        "attachments": [
            describe_image_file(ip) if Path(ip).is_file() else {"ok": False, "path": ip}
            for ip in (image_paths or [])
        ],
        "attachment_meta": attachments,
    }
