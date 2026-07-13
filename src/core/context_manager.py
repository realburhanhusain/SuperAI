"""
Context window manager — summarize long transcripts (S15).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)


def trim_messages(
    messages: List[Dict[str, str]],
    max_tokens: int = 6000,
    keep_system: bool = True,
) -> List[Dict[str, str]]:
    """Keep system + most recent messages under budget."""
    if not messages:
        return []
    system = [m for m in messages if m.get("role") == "system"] if keep_system else []
    rest = [m for m in messages if m.get("role") != "system"]
    kept: List[Dict[str, str]] = []
    budget = max_tokens
    for m in system:
        t = estimate_tokens(m.get("content") or "")
        budget -= t
        kept.append(m)
    # take from end
    selected_rev = []
    for m in reversed(rest):
        t = estimate_tokens(m.get("content") or "")
        if t > budget and selected_rev:
            break
        selected_rev.append(m)
        budget -= t
    kept.extend(reversed(selected_rev))
    return kept


def summarize_text(text: str, max_chars: int = 1500, use_model: bool = False) -> str:
    """Extractive summary; optional model call."""
    text = text or ""
    if len(text) <= max_chars:
        return text
    if use_model:
        try:
            from .model_caller import ModelCaller
            from .model_registry import ModelRegistry

            reg = ModelRegistry()
            names = [n for n in reg.list_all_models() if not str(n).startswith("cli:")]
            model = names[0] if names else "gpt-4o"
            r = ModelCaller(use_mock=True, registry=reg).call(
                model=model,
                prompt=f"Summarize concisely:\n\n{text[:12000]}",
            )
            return str(r.get("response") or text[:max_chars])
        except Exception:
            pass
    # extractive: head + tail
    half = max_chars // 2
    return text[:half] + "\n…[summarized]…\n" + text[-half:]
