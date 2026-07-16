"""
Task complexity classifier (V4 S1 / M6) — drives member count and cheap-first.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


def classify_task(text: str) -> Dict[str, Any]:
    """
    Return complexity tier and routing hints.
    tiers: trivial | simple | moderate | complex
    step_kind: plan | summarize | review | code | general
    """
    t = (text or "").strip()
    low = t.lower()
    words = len(t.split())

    code_kw = (
        "implement",
        "refactor",
        "fix",
        "bug",
        "write code",
        "add feature",
        "diff",
        "test",
        "pr ",
        "pull request",
    )
    plan_kw = ("plan", "architect", "design", "break down", "roadmap")
    review_kw = ("review", "critique", "look over", "audit")
    sum_kw = ("summarize", "summary", "tl;dr", "explain briefly", "what is")

    step_kind = "general"
    if any(k in low for k in code_kw):
        step_kind = "code"
    elif any(k in low for k in plan_kw):
        step_kind = "plan"
    elif any(k in low for k in review_kw):
        step_kind = "review"
    elif any(k in low for k in sum_kw) or words < 12:
        step_kind = "summarize"

    if words < 8 and step_kind in {"summarize", "general"}:
        tier = "trivial"
        max_members = 1
        prefer_cheap = True
    elif words < 40 and step_kind != "code":
        tier = "simple"
        max_members = 2
        prefer_cheap = step_kind in {"summarize", "plan"}
    elif step_kind == "code" or words > 80 or "multi" in low:
        tier = "complex"
        max_members = 4
        prefer_cheap = False
    else:
        tier = "moderate"
        max_members = 3
        prefer_cheap = step_kind in {"summarize", "plan", "review"}

    return {
        "tier": tier,
        "step_kind": step_kind,
        "max_members": max_members,
        "prefer_cheap": prefer_cheap,
        "words": words,
    }


def cheap_first_models(
    candidates: List[str],
    *,
    prefer_cheap: bool,
    max_n: int = 3,
) -> List[str]:
    """Order candidates: local/cli/cheap first when prefer_cheap."""
    if not candidates:
        return []
    if not prefer_cheap:
        return list(candidates)[:max_n]

    def score(m: str) -> tuple:
        s = str(m).lower()
        if s.startswith("cli:") or "ollama" in s or "local" in s or "lmstudio" in s:
            return (0, s)
        if any(x in s for x in ("flash", "mini", "nano", "haiku", "deepseek", "qwen", "gemma")):
            return (1, s)
        return (2, s)

    return sorted(candidates, key=score)[:max_n]
