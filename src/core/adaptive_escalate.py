"""Adaptive escalate on quality failure (V5 S2 / V6 S130)."""

from __future__ import annotations

from typing import Any, Dict, Optional


def quality_failed(result: Dict[str, Any]) -> bool:
    if not isinstance(result, dict):
        return True
    if result.get("blocked") or result.get("ok") is False:
        return True
    status = str(result.get("status") or "").lower()
    if status in {"error", "failed", "cancelled"}:
        return True
    text = str(result.get("response") or result.get("text") or "").strip()
    if not text:
        return True
    if len(text) < 8 and status != "success":
        return True
    low = text.lower()
    if any(x in low for x in ("i cannot", "as an ai", "error:", "traceback")):
        return True
    return False


def pick_premium(model: str, registry: Any = None) -> str:
    """Pick a stronger model for one retry."""
    s = str(model or "")
    # explicit map
    for cheap, prem in (
        ("mini", "gpt-4o"),
        ("flash", "gpt-4o"),
        ("haiku", "claude-sonnet-4"),
        ("local", "gpt-4o"),
        ("ollama", "gpt-4o"),
    ):
        if cheap in s.lower():
            return prem
    try:
        if registry:
            for name in registry.list_all_models():
                n = str(name).lower()
                if any(x in n for x in ("gpt-4o", "sonnet", "opus", "claude-3")):
                    if str(name) != s:
                        return str(name)
    except Exception:
        pass
    return "gpt-4o"


def call_with_escalate(
    caller: Any,
    model: str,
    prompt: str,
    *,
    system_prompt: Optional[str] = None,
    once: bool = True,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Call model; on quality fail, escalate once to premium."""
    first = caller.call(
        model=model, prompt=prompt, system_prompt=system_prompt, **kwargs
    )
    if not quality_failed(first) or not once:
        first["escalated"] = False
        return first
    premium = pick_premium(model, registry=getattr(caller, "registry", None))
    if premium == model:
        first["escalated"] = False
        return first
    second = caller.call(
        model=premium,
        prompt=prompt,
        system_prompt=system_prompt,
        **kwargs,
    )
    second["escalated"] = True
    second["escalated_from"] = model
    second["first_attempt"] = {
        "model": model,
        "status": first.get("status"),
        "ok": first.get("ok"),
    }
    return second
