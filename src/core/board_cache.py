"""
Short-TTL cache for multi-member review/advise boards (Improvement Phase 4).

S3: optional semantic key — normalize subject + coarse embedding-hash so
near-duplicate prompts share a board entry when SUPERAI_BOARD_SEMANTIC=1.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional


def _cache_dir() -> Path:
    d = Path.home() / ".superai" / "cache" / "boards"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _normalize_subject(subject: str) -> str:
    s = (subject or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s:#./@-]", "", s)
    return s[:2000]


def semantic_subject_key(subject: str) -> str:
    """
    Coarse semantic fingerprint (S3).
    Prefer embedding hash when available; else normalized token bag hash.
    """
    norm = _normalize_subject(subject)
    if not norm:
        return "empty"
    # Optional real embedding path (offline-safe hash of vector)
    try:
        if os.getenv("SUPERAI_BOARD_SEMANTIC", "1").strip() not in {
            "0",
            "false",
            "no",
        }:
            from .embeddings import embed_text

            vec = embed_text(norm)
            if vec is not None:
                # quantize to reduce float noise
                if hasattr(vec, "tolist"):
                    vals = vec.tolist()
                else:
                    vals = list(vec)
                q = ",".join(f"{float(x):.3f}" for x in vals[:64])
                return hashlib.sha256(q.encode("utf-8")).hexdigest()[:24]
    except Exception:
        pass
    # Token bag: sorted unique words length>=3
    toks = sorted({t for t in re.findall(r"[a-z0-9_]{3,}", norm)})
    bag = " ".join(toks[:80]) or norm
    return hashlib.sha256(bag.encode("utf-8")).hexdigest()[:24]


def _key(subject: str, mode: str, members: list, prefer: str, dry_run: bool) -> str:
    use_sem = os.getenv("SUPERAI_BOARD_SEMANTIC", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }
    subj = semantic_subject_key(subject) if use_sem else (subject or "")[:2000]
    raw = json.dumps(
        {
            "s": subj,
            "sem": use_sem,
            "m": mode,
            "mem": list(members or []),
            "p": prefer,
            "d": bool(dry_run),
        },
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def get_board(
    subject: str,
    *,
    mode: str,
    members: list,
    prefer: str,
    dry_run: bool,
    ttl_sec: float = 300.0,
) -> Optional[Dict[str, Any]]:
    path = _cache_dir() / f"{_key(subject, mode, members, prefer, dry_run)}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - float(data.get("ts") or 0) > ttl_sec:
            path.unlink(missing_ok=True)
            return None
        result = data.get("result")
        if isinstance(result, dict):
            result = dict(result)
            result["cache_hit"] = True
            return result
    except Exception:
        return None
    return None


def put_board(
    subject: str,
    result: Dict[str, Any],
    *,
    mode: str,
    members: list,
    prefer: str,
    dry_run: bool,
) -> None:
    path = _cache_dir() / f"{_key(subject, mode, members, prefer, dry_run)}.json"
    try:
        # Don't store huge raw opinion blobs forever — keep summary fields
        slim = {
            k: result.get(k)
            for k in (
                "ok",
                "status",
                "mode",
                "role",
                "members",
                "board",
                "mock",
                "dry_run",
                "model_chain",
                "tokens",
                "estimated_cost_usd",
                "protocol",
                "prefer",
                "contract",
                "memory_ids",
            )
            if k in result
        }
        # Keep short opinion summaries only
        ops = []
        for o in (result.get("opinions") or [])[:8]:
            if isinstance(o, dict):
                ops.append(
                    {
                        "member_id": o.get("member_id") or o.get("cli"),
                        "verdict": o.get("verdict"),
                        "summary": str(o.get("summary") or "")[:400],
                        "ok": o.get("ok"),
                    }
                )
        slim["opinions"] = ops
        path.write_text(
            json.dumps({"ts": time.time(), "result": slim}, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def smart_max_members(subject: str, default: int = 3, hard_cap: int = 5) -> int:
    """Fewer members for short/simple subjects (cost control). V4 S1: complexity."""
    try:
        from .task_complexity import classify_task

        cx = classify_task(subject)
        return max(1, min(int(cx.get("max_members") or default), hard_cap))
    except Exception:
        pass
    s = (subject or "").strip()
    n = len(s)
    if n < 80:
        return max(1, min(2, hard_cap))
    if n < 400:
        return max(1, min(default, hard_cap))
    return max(1, min(hard_cap, default + 1))
