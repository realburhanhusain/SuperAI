"""
Accurate cost from registry rates (V5 M4 / V6 M002).

Rules:
- Prefer real provider ``usage`` tokens when present.
- Price with registry ``cost_per_1k_tokens`` (blended), or optional
  input/output rates when configured on the model entry / extra.
- When usage is missing, fall back to a token estimate and set
  ``cost_source="estimate"`` so automation never confuses estimate with metered usage.
- Local / CLI models are $0.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


def _registry(registry: Any = None) -> Any:
    if registry is not None:
        return registry
    try:
        from .model_registry import ModelRegistry

        return ModelRegistry()
    except Exception:
        return None


def _model_info(model: str, registry: Any = None) -> Any:
    reg = _registry(registry)
    if reg is None:
        return None
    try:
        return reg.get_model(str(model))
    except Exception:
        return None


def is_local_or_cli(model: str) -> bool:
    s = str(model or "").lower()
    return bool(
        s.startswith("cli:")
        or "ollama" in s
        or "lmstudio" in s
        or "vllm-local" in s
        or s.endswith("-local")
        or "/local" in s
    )


def rates_for_model(model: str, registry: Any = None) -> Dict[str, Any]:
    """
    Return pricing metadata for a model.

    Keys: rate_per_1k (blended), input_per_1k, output_per_1k, source, local
    """
    if is_local_or_cli(model):
        return {
            "rate_per_1k": 0.0,
            "input_per_1k": 0.0,
            "output_per_1k": 0.0,
            "source": "zero_local",
            "local": True,
        }

    info = _model_info(model, registry)
    blended: Optional[float] = None
    inp: Optional[float] = None
    out: Optional[float] = None
    src = "heuristic"

    if info is not None:
        try:
            cpk = getattr(info, "cost_per_1k_tokens", None)
            if cpk is not None and float(cpk) > 0:
                blended = float(cpk)
                src = "registry"
        except (TypeError, ValueError):
            pass
        extra = getattr(info, "extra", None) or {}
        if isinstance(extra, dict):
            for key, target in (
                ("input_cost_per_1k", "inp"),
                ("cost_per_1k_input", "inp"),
                ("input_per_1k", "inp"),
                ("output_cost_per_1k", "out"),
                ("cost_per_1k_output", "out"),
                ("output_per_1k", "out"),
            ):
                if extra.get(key) is None:
                    continue
                try:
                    val = float(extra[key])
                except (TypeError, ValueError):
                    continue
                if target == "inp":
                    inp = val
                else:
                    out = val
            if inp is not None or out is not None:
                src = "registry_io"

    if blended is None:
        # Heuristic fallbacks only when registry lacks a positive rate
        s = str(model or "").lower()
        if any(x in s for x in ("mini", "flash", "nano", "haiku")):
            blended = 0.0005
        elif any(x in s for x in ("deepseek", "qwen", "gemma", "llama")):
            blended = 0.0008
        elif any(x in s for x in ("opus", "o1", "o3")):
            blended = 0.015
        else:
            blended = 0.002
        if src != "registry_io":
            src = "heuristic"

    if inp is None:
        inp = blended
    if out is None:
        out = blended
    if blended is None:
        blended = float(inp or out or 0.0)

    return {
        "rate_per_1k": max(0.0, float(blended)),
        "input_per_1k": max(0.0, float(inp or 0.0)),
        "output_per_1k": max(0.0, float(out or 0.0)),
        "source": src,
        "local": False,
    }


def rate_per_1k(model: str, registry: Any = None) -> float:
    return float(rates_for_model(model, registry=registry)["rate_per_1k"])


def normalize_usage(obj: Any) -> Dict[str, int]:
    """Normalize heterogeneous provider usage dicts to prompt/completion/total."""
    if not isinstance(obj, dict):
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    # Nested usage
    usage = obj.get("usage") if isinstance(obj.get("usage"), dict) else obj

    def _i(*keys: str) -> int:
        for k in keys:
            if usage.get(k) is None and obj.get(k) is None:
                continue
            try:
                v = usage.get(k) if usage.get(k) is not None else obj.get(k)
                return max(0, int(v or 0))
            except (TypeError, ValueError):
                continue
        return 0

    prompt = _i(
        "prompt_tokens",
        "input_tokens",
        "prompt_eval_count",
        "inputTokenCount",
        "prompt_token_count",
    )
    completion = _i(
        "completion_tokens",
        "output_tokens",
        "eval_count",
        "outputTokenCount",
        "candidates_token_count",
        "completion_token_count",
    )
    total = _i("total_tokens", "totalTokenCount", "token_count", "tokens")
    if total <= 0:
        total = prompt + completion
    if total > 0 and prompt <= 0 and completion <= 0:
        # only total known — leave split at 0
        pass
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
    }


def from_usage(
    model: str,
    *,
    total_tokens: int = 0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    registry: Any = None,
    cost_source: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Price tokens for ``model`` using registry rates.

    When prompt+completion are both available and IO rates differ, uses split pricing.
    """
    pricing = rates_for_model(model, registry=registry)
    pt = max(0, int(prompt_tokens or 0))
    ct = max(0, int(completion_tokens or 0))
    tokens = int(total_tokens or 0)
    if tokens <= 0:
        tokens = pt + ct

    if pricing["local"]:
        usd = 0.0
        source = "zero_local"
    elif pt > 0 or ct > 0:
        # Prefer split when we have either side (missing side → 0 tokens)
        usd = (pt / 1000.0) * float(pricing["input_per_1k"]) + (
            ct / 1000.0
        ) * float(pricing["output_per_1k"])
        # If only total was intended and split is empty, use blended on total
        if pt == 0 and ct == 0 and tokens > 0:
            usd = (tokens / 1000.0) * float(pricing["rate_per_1k"])
        elif pt + ct > 0 and tokens <= 0:
            tokens = pt + ct
        elif tokens > 0 and pt + ct == 0:
            usd = (tokens / 1000.0) * float(pricing["rate_per_1k"])
        source = cost_source or "usage"
    else:
        usd = (tokens / 1000.0) * float(pricing["rate_per_1k"])
        source = cost_source or ("usage" if tokens > 0 else "estimate")

    return {
        "model": model,
        "tokens": int(tokens),
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "rate_per_1k": float(pricing["rate_per_1k"]),
        "input_per_1k": float(pricing["input_per_1k"]),
        "output_per_1k": float(pricing["output_per_1k"]),
        "estimated_cost_usd": round(float(usd), 6),
        "cost_source": source,
        "pricing_source": pricing["source"],
    }


def from_result(result: Any, model: str = "", *, registry: Any = None) -> Dict[str, Any]:
    """Extract usage from a call result dict and price it."""
    if not isinstance(result, dict):
        return from_usage(model or "unknown", total_tokens=0, registry=registry, cost_source="estimate")
    m = str(model or result.get("model") or "unknown")
    usage = normalize_usage(result)
    if usage["total_tokens"] <= 0 and usage["prompt_tokens"] <= 0:
        # no usage → estimate
        return estimate_call(
            m,
            str(result.get("prompt") or "") + str(result.get("response") or result.get("content") or ""),
            registry=registry,
        )
    return from_usage(
        m,
        total_tokens=usage["total_tokens"],
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        registry=registry,
        cost_source="usage",
    )


def estimate_call(model: str, prompt: str = "", *, registry: Any = None) -> Dict[str, Any]:
    """Rough pre-call / fallback estimate (~4 chars/token + reply headroom)."""
    tokens = max(50, len(prompt or "") // 4 + 80)
    out = from_usage(model, total_tokens=tokens, registry=registry, cost_source="estimate")
    out["cost_source"] = "estimate"
    return out


def aggregate_costs(
    parts: Sequence[Dict[str, Any]],
    *,
    registry: Any = None,
) -> Dict[str, Any]:
    """
    Sum member/step results into board-level totals.

    Uses each part's estimated_cost_usd when present; otherwise prices via from_result.
    """
    total_usd = 0.0
    total_tok = 0
    sources: List[str] = []
    models: List[str] = []
    for p in parts or []:
        if not isinstance(p, dict):
            continue
        model = str(p.get("model") or p.get("member") or "")
        if model:
            models.append(model)
        if p.get("estimated_cost_usd") is not None or p.get("tokens") is not None:
            try:
                total_usd += float(p.get("estimated_cost_usd") or 0)
            except (TypeError, ValueError):
                pass
            try:
                total_tok += int(p.get("tokens") or (p.get("usage") or {}).get("total_tokens") or 0)
            except (TypeError, ValueError):
                pass
            sources.append(str(p.get("cost_source") or "usage"))
            continue
        priced = from_result(p, model=model, registry=registry)
        total_usd += float(priced.get("estimated_cost_usd") or 0)
        total_tok += int(priced.get("tokens") or 0)
        sources.append(str(priced.get("cost_source") or "estimate"))

    # Honest aggregate source
    if not sources:
        agg_source = "estimate"
    elif all(s == "usage" for s in sources):
        agg_source = "usage"
    elif all(s in {"usage", "zero_local"} for s in sources):
        agg_source = "usage"
    elif any(s == "estimate" for s in sources):
        agg_source = "mixed"
    else:
        agg_source = "mixed"

    return {
        "tokens": int(total_tok),
        "estimated_cost_usd": round(total_usd, 6),
        "cost_source": agg_source,
        "parts": len(parts or []),
        "models": models[:20],
    }


def attach_cost_fields(
    result: Dict[str, Any],
    *,
    model: str,
    prompt: str = "",
    registry: Any = None,
) -> Dict[str, Any]:
    """
    Mutate/return result with tokens, estimated_cost_usd, cost_source, rates.

    Prefer real usage; only estimate when usage is absent.
    """
    if not isinstance(result, dict):
        result = {"response": result, "ok": True}

    usage = normalize_usage(result)
    has_usage = usage["total_tokens"] > 0 or usage["prompt_tokens"] > 0 or usage["completion_tokens"] > 0

    if has_usage:
        cost = from_usage(
            model,
            total_tokens=usage["total_tokens"],
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            registry=registry,
            cost_source="usage",
        )
    else:
        # Estimate from prompt + response length
        blob = (prompt or "") + str(result.get("response") or result.get("content") or "")
        cost = estimate_call(model, blob, registry=registry)
        # refine estimate with response size
        tokens = max(int(cost.get("tokens") or 0), len(blob) // 4 + 20)
        cost = from_usage(model, total_tokens=tokens, registry=registry, cost_source="estimate")
        cost["cost_source"] = "estimate"

    result["tokens"] = int(cost.get("tokens") or 0)
    result["prompt_tokens"] = int(cost.get("prompt_tokens") or usage.get("prompt_tokens") or 0)
    result["completion_tokens"] = int(
        cost.get("completion_tokens") or usage.get("completion_tokens") or 0
    )
    result["estimated_cost_usd"] = float(cost.get("estimated_cost_usd") or 0)
    result["rate_per_1k"] = cost.get("rate_per_1k")
    result["cost_source"] = cost.get("cost_source")
    result["pricing_source"] = cost.get("pricing_source")
    result.setdefault("model", model)
    # Keep usage block coherent
    result.setdefault(
        "usage",
        {
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "total_tokens": result["tokens"],
        },
    )
    return result


def audit_m002() -> Dict[str, Any]:
    """Offline proof for M002 — registry rates + usage preference + aggregate."""
    from .spend_guard import ensure_public_result

    issues: List[str] = []
    evidence: Dict[str, Any] = {}

    reg = _registry()
    evidence["registry_source"] = getattr(reg, "source", None) if reg else None
    n_models = len(getattr(reg, "models", {}) or {}) if reg else 0
    evidence["registry_models"] = n_models
    if n_models < 5:
        issues.append("registry_too_small")

    # Known registry rate
    r = rates_for_model("gpt-4o", registry=reg)
    if r["rate_per_1k"] <= 0:
        issues.append("gpt4o_rate_missing")
    evidence["gpt4o_rate"] = r["rate_per_1k"]

    # Usage path
    u = from_usage("gpt-4o", prompt_tokens=500, completion_tokens=500, registry=reg)
    if u.get("cost_source") != "usage":
        issues.append("usage_source_wrong")
    if abs(float(u["estimated_cost_usd"]) - (1000 / 1000.0) * r["rate_per_1k"]) > 1e-9:
        # blended should match when IO rates equal
        if abs(u["input_per_1k"] - u["output_per_1k"]) < 1e-12:
            issues.append("usage_price_mismatch")
    evidence["usage_price"] = u["estimated_cost_usd"]

    # Estimate path
    e = estimate_call("gpt-4o", "hello", registry=reg)
    if e.get("cost_source") != "estimate":
        issues.append("estimate_source_wrong")

    # Local zero
    z = from_usage("cli:claude", total_tokens=9999, registry=reg)
    if float(z["estimated_cost_usd"]) != 0.0 or z.get("cost_source") != "zero_local":
        issues.append("cli_not_zero")

    # Aggregate
    agg = aggregate_costs(
        [
            {"model": "gpt-4o", "tokens": 100, "estimated_cost_usd": 0.001, "cost_source": "usage"},
            {"model": "cli:claude", "tokens": 50, "estimated_cost_usd": 0.0, "cost_source": "zero_local"},
        ]
    )
    if agg["tokens"] != 150:
        issues.append("aggregate_tokens")
    if abs(agg["estimated_cost_usd"] - 0.001) > 1e-9:
        issues.append("aggregate_usd")

    # attach_cost_fields prefers usage
    attached = attach_cost_fields(
        {"ok": True, "response": "x", "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}},
        model="gpt-4o",
        prompt="hi",
        registry=reg,
    )
    if attached.get("cost_source") != "usage" or attached.get("tokens") != 20:
        issues.append("attach_prefers_usage")

    ok = len(issues) == 0
    return ensure_public_result(
        {
            "ok": ok,
            "item": "M002",
            "issues": issues,
            "evidence": evidence,
            "message": "Accurate cost from usage × registry rates" if ok else "M002 gaps",
        },
        ok=ok,
    )
