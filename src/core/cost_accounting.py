"""
Accurate-ish cost from registry rates (V5 M4).
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def rate_per_1k(model: str, registry: Any = None) -> float:
    try:
        if registry is None:
            from .model_registry import ModelRegistry

            registry = ModelRegistry()
        info = registry.get_model(str(model))
        if info and getattr(info, "cost_per_1k_tokens", None) is not None:
            return max(0.0, float(info.cost_per_1k_tokens))
    except Exception:
        pass
    s = str(model or "").lower()
    if s.startswith("cli:") or "ollama" in s or "local" in s or "lmstudio" in s:
        return 0.0
    if any(x in s for x in ("mini", "flash", "nano", "haiku")):
        return 0.0005
    if any(x in s for x in ("deepseek", "qwen", "gemma", "llama")):
        return 0.0008
    return 0.002


def from_usage(
    model: str,
    *,
    total_tokens: int = 0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    registry: Any = None,
) -> Dict[str, Any]:
    tokens = int(total_tokens or 0)
    if tokens <= 0:
        tokens = int(prompt_tokens or 0) + int(completion_tokens or 0)
    rate = rate_per_1k(model, registry=registry)
    usd = round((tokens / 1000.0) * rate, 6)
    return {
        "model": model,
        "tokens": tokens,
        "rate_per_1k": rate,
        "estimated_cost_usd": usd,
    }


def estimate_call(model: str, prompt: str = "", *, registry: Any = None) -> Dict[str, Any]:
    # ~4 chars/token rough
    tokens = max(50, len(prompt or "") // 4 + 80)
    return from_usage(model, total_tokens=tokens, registry=registry)
