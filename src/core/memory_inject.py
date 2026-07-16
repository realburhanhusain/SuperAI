"""
Smarter memory inject with token budget (V5 S4).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def rank_and_pack_memories(
    query: str,
    hits: List[Dict[str, Any]],
    *,
    max_tokens: int = 800,
) -> Dict[str, Any]:
    """
    Rank by importance + recency proxies; pack under token budget.
    """
    scored = []
    q_words = set((query or "").lower().split())
    for h in hits or []:
        if not isinstance(h, dict):
            continue
        text = str(h.get("content") or h.get("text") or h.get("document") or "")
        meta = h.get("metadata") if isinstance(h.get("metadata"), dict) else {}
        imp = float(meta.get("importance") or h.get("importance") or 0.5)
        # simple word overlap
        words = set(text.lower().split())
        overlap = len(q_words & words) / max(1, len(q_words))
        score = imp + 0.5 * overlap
        scored.append((score, text, h))
    scored.sort(key=lambda x: -x[0])

    parts: List[str] = []
    used = 0
    kept = 0
    for score, text, _h in scored:
        t = max(1, len(text) // 4)
        if used + t > max_tokens:
            continue
        parts.append(text[:2000])
        used += t
        kept += 1
        if kept >= 8:
            break
    body = "\n---\n".join(parts)
    return {
        "ok": True,
        "text": body,
        "tokens_est": used,
        "kept": kept,
        "max_tokens": max_tokens,
    }


def inject_for_task(task: str, *, max_tokens: int = 800) -> Dict[str, Any]:
    try:
        from .memory_palace import MemoryPalace

        hits = MemoryPalace().query_semantic(task, top_k=12)
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "text": ""}
    return rank_and_pack_memories(task, hits, max_tokens=max_tokens)
