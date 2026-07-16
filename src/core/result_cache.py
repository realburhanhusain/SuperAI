"""
Cross-session result cache (V5 S1) — opt-in via SUPERAI_RESULT_CACHE=1.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional


def enabled() -> bool:
    return (os.getenv("SUPERAI_RESULT_CACHE") or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _dir() -> Path:
    d = Path.home() / ".superai" / "cache" / "results"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_key(kind: str, subject: str, **meta: Any) -> str:
    raw = json.dumps({"k": kind, "s": (subject or "")[:2000], **meta}, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def get(kind: str, subject: str, *, ttl_sec: float = 3600, **meta: Any) -> Optional[Dict[str, Any]]:
    if not enabled():
        return None
    path = _dir() / f"{cache_key(kind, subject, **meta)}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - float(data.get("ts") or 0) > ttl_sec:
            path.unlink(missing_ok=True)
            return None
        out = data.get("result")
        if isinstance(out, dict):
            out = dict(out)
            out["result_cache_hit"] = True
            return out
    except Exception:
        return None
    return None


def put(kind: str, subject: str, result: Dict[str, Any], **meta: Any) -> None:
    if not enabled() or not isinstance(result, dict):
        return
    path = _dir() / f"{cache_key(kind, subject, **meta)}.json"
    try:
        slim = {
            k: result.get(k)
            for k in (
                "ok",
                "status",
                "response",
                "message",
                "mock",
                "dry_run",
                "tokens",
                "estimated_cost_usd",
                "contract",
                "model_chain",
                "members",
                "error_code",
            )
            if k in result
        }
        path.write_text(
            json.dumps({"ts": time.time(), "result": slim}, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass
