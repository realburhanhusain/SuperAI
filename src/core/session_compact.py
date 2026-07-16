"""
Session compact (Sprint B M6) — structured extract + optional model summarize.
"""

from __future__ import annotations

from typing import Any, Dict, List


def smart_compact(turns: List[Dict[str, Any]], max_chars: int = 1500) -> str:
    """Prefer structured bullet extract; fall back to char trim."""
    if not turns:
        return ""
    bullets = []
    for t in turns[-12:]:
        u = str(t.get("user") or "").strip().replace("\n", " ")
        a = str(t.get("assistant") or "").strip().replace("\n", " ")
        if u:
            bullets.append(f"- User asked: {u[:180]}")
        if a:
            bullets.append(f"  Outcome: {a[:180]}")
    text = "[Smart compact]\n" + "\n".join(bullets)
    if len(text) <= max_chars:
        return text
    # model optional (mock-friendly)
    try:
        from .config import Config
        from .model_caller import ModelCaller
        from .model_registry import ModelRegistry

        if not Config().use_mock:
            # keep extract-only offline-friendly by default for cost
            pass
        caller = ModelCaller(use_mock=True, registry=ModelRegistry())
        out = caller.call(
            model="gpt-4o",
            prompt=(
                "Summarize this agent dialog into <=12 bullet facts for future context:\n"
                + text[:6000]
            ),
        )
        summary = str(out.get("response") or "")[:max_chars]
        if summary:
            return "[Smart compact model]\n" + summary
    except Exception:
        pass
    return text[:max_chars]


def compact_turns_simple(turns: List[Dict[str, Any]], max_chars: int = 1200) -> str:
    from .agent_tui import compact_turns

    return compact_turns(turns, max_chars=max_chars)
