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
    full_atts = []
    for ip in image_paths or []:
        info = describe_image_file(ip)
        full_atts.append(info)
        attachments.append({k: info.get(k) for k in ("ok", "path", "mime", "bytes") if k in info})
        if info.get("ok"):
            parts.append(
                f"\n[Image attachment: {info['path']} mime={info['mime']} "
                f"bytes={info['bytes']}]\n"
                f"(base64 length={len(info.get('base64') or '')}; "
                f"providers with vision can use full payload from attachments)\n"
            )
    return {
        "ok": True,
        "prompt": "\n".join(parts),
        "attachments": full_atts,
        "attachment_meta": attachments,
    }


def vision_messages(
    text: str, attachments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """OpenAI-compatible multimodal message content parts."""
    content: List[Dict[str, Any]] = [{"type": "text", "text": text or ""}]
    for att in attachments or []:
        if not att.get("ok") or not att.get("base64"):
            continue
        mime = att.get("mime") or "image/png"
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime};base64,{att['base64']}",
                },
            }
        )
    return [{"role": "user", "content": content}]
