"""
Context packing under a token budget (V4 S7).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


def estimate_tokens(text: str) -> int:
    # rough: ~4 chars/token
    return max(1, len(text or "") // 4)


def pack_context(
    *,
    system: str = "",
    memory: str = "",
    history: str = "",
    tools_hint: str = "",
    user: str = "",
    max_tokens: int = 4000,
) -> Dict[str, Any]:
    """
    Keep user + system first; drop memory/history/tools_hint from the end
    of priority list when over budget.
    Priority keep order: user > system > tools_hint > history > memory
    Drop order: memory → history → tools_hint → truncate history further
    """
    parts = {
        "system": system or "",
        "memory": memory or "",
        "history": history or "",
        "tools_hint": tools_hint or "",
        "user": user or "",
    }
    dropped: List[str] = []

    def total() -> int:
        return sum(estimate_tokens(v) for v in parts.values())

    drop_order = ("memory", "history", "tools_hint")
    for key in drop_order:
        if total() <= max_tokens:
            break
        if parts[key]:
            dropped.append(key)
            parts[key] = ""

    # truncate history if still over
    if total() > max_tokens and parts["history"]:
        budget_left = max_tokens - sum(
            estimate_tokens(parts[k]) for k in parts if k != "history"
        )
        chars = max(200, budget_left * 4)
        parts["history"] = parts["history"][-chars:]
        dropped.append("history_truncated")

    # truncate system last resort (keep head)
    if total() > max_tokens and parts["system"]:
        chars = max(200, (max_tokens // 4) * 4)
        parts["system"] = parts["system"][:chars]
        dropped.append("system_truncated")

    packed = ""
    if parts["system"]:
        packed += parts["system"] + "\n\n"
    if parts["memory"]:
        packed += parts["memory"] + "\n\n"
    if parts["history"]:
        packed += parts["history"] + "\n\n"
    if parts["tools_hint"]:
        packed += parts["tools_hint"] + "\n\n"
    if parts["user"]:
        packed += parts["user"]

    return {
        "ok": True,
        "text": packed.strip(),
        "tokens_est": estimate_tokens(packed),
        "max_tokens": max_tokens,
        "dropped": dropped,
        "parts": {k: bool(v) for k, v in parts.items()},
    }
