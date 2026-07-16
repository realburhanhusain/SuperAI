"""
Minimal in-process tools (Improvement Phase 5) — workspace-jailed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def _root() -> Path:
    try:
        from .workspace import workspace_root

        return Path(workspace_root())
    except Exception:
        return Path(os.getenv("SUPERAI_WORKSPACE") or Path.cwd()).resolve()


def _safe(path: str) -> Path:
    root = _root().resolve()
    p = (root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if not str(p).startswith(str(root)):
        raise PermissionError(f"Path escapes workspace: {path}")
    return p


def tool_read(path: str, max_chars: int = 20000) -> Dict[str, Any]:
    p = _safe(path)
    if not p.is_file():
        return {"ok": False, "error": "not_found", "path": str(p)}
    text = p.read_text(encoding="utf-8", errors="replace")[:max_chars]
    return {"ok": True, "path": str(p), "content": text, "chars": len(text)}


def tool_write(path: str, content: str, *, dry_run: bool = False) -> Dict[str, Any]:
    p = _safe(path)
    if dry_run:
        return {"ok": True, "dry_run": True, "path": str(p), "bytes": len(content.encode())}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(p), "bytes": len(content.encode())}


def tool_glob(pattern: str, limit: int = 50) -> Dict[str, Any]:
    root = _root()
    hits = [str(x.relative_to(root)) for x in root.glob(pattern)][:limit]
    return {"ok": True, "pattern": pattern, "hits": hits, "count": len(hits)}


def list_tools() -> List[str]:
    return ["read", "write", "glob"]
