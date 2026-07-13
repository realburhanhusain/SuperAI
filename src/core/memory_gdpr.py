"""
Memory TTL + forget / GDPR-style wipe (N27).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .memory_palace import MemoryPalace


def forget_query(query: str, *, dry_run: bool = False) -> Dict[str, Any]:
    """Delete memories matching semantic query or tag substring."""
    mp = MemoryPalace()
    hits = mp.query_semantic(query, top_k=50)
    # also tag match via all memories
    q = query.lower()
    all_m = mp.get_all_memories()
    ids = {h.get("id") for h in hits if h.get("id")}
    for m in all_m:
        blob = f"{m.get('content')} {m.get('metadata')} {m.get('tags')}".lower()
        if q in blob and m.get("id"):
            ids.add(m["id"])
    deleted = []
    if not dry_run:
        for mid in ids:
            try:
                mp.delete(str(mid))
                deleted.append(mid)
            except Exception:
                pass
    else:
        deleted = list(ids)
    return {"ok": True, "matched": len(ids), "deleted": deleted, "dry_run": dry_run}


def apply_ttl(max_age_days: float = 90.0, *, dry_run: bool = False) -> Dict[str, Any]:
    """Deprecate or delete memories older than max_age_days with low importance."""
    mp = MemoryPalace()
    now = datetime.now(timezone.utc)
    removed = []
    for m in mp.get_all_memories():
        meta = m.get("metadata") or {}
        created = meta.get("created_at") or m.get("created_at")
        if not created:
            continue
        try:
            dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
        except ValueError:
            continue
        age = (now - dt).total_seconds() / 86400.0
        imp = float(meta.get("importance") or m.get("importance") or 0.5)
        if age > max_age_days and imp < 0.85:
            mid = m.get("id")
            if mid and not dry_run:
                try:
                    mp.delete(str(mid))
                    removed.append(mid)
                except Exception:
                    pass
            elif mid:
                removed.append(mid)
    return {"ok": True, "removed": len(removed), "ids": removed[:50], "dry_run": dry_run}
