"""
Token / chunk streaming helpers for agent-tui (MoSCoW S1 / V6 M027).

Provides a generator that yields text chunks and emits progress bus events.
Works with mock mode and full completed responses (word/chunk cascade).
Live provider streaming plugs in via ModelCaller.call_stream / stream_fn.

Stream modes (honest labels):
- ``sse`` — true provider token/event stream
- ``mock_chunked`` — mock response split into chunks
- ``chunked_fallback`` — full non-stream call re-chunked for UX
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Generator, Iterable, List, Optional

# Last stream mode observed (process-local; for tests / TUI status)
_LAST_STREAM_META: Dict[str, Any] = {
    "mode": None,
    "provider": None,
    "model": None,
    "chunks": 0,
    "chars": 0,
}


def set_stream_meta(**kwargs: Any) -> Dict[str, Any]:
    _LAST_STREAM_META.update(kwargs)
    return dict(_LAST_STREAM_META)


def get_stream_meta() -> Dict[str, Any]:
    return dict(_LAST_STREAM_META)


def finalize_stream_result(
    text: str,
    *,
    model: str,
    provider: Optional[str] = None,
    mode: Optional[str] = None,
    cancelled: bool = False,
    fallback_reason: Optional[str] = None,
    mock: bool = False,
    chunks: int = 0,
    prompt: str = "",
) -> Dict[str, Any]:
    """
    Build a contracted superai.result.v1 envelope after stream completion (M027).

    Aggregates full text, stream meta (mode/provider/model), and cost fields.
    """
    body = text or ""
    meta = {
        "mode": mode or get_stream_meta().get("mode"),
        "provider": provider or get_stream_meta().get("provider"),
        "model": model,
        "chunks": chunks or get_stream_meta().get("chunks") or 0,
        "chars": len(body),
        "cancelled": cancelled,
        "fallback_reason": fallback_reason,
    }
    result: Dict[str, Any] = {
        "ok": not cancelled and bool(body or mode == "budget_blocked"),
        "status": (
            "cancelled"
            if cancelled
            else "error"
            if mode == "budget_blocked"
            else "success"
            if body
            else "empty"
        ),
        "response": body,
        "model": model,
        "provider": meta["provider"],
        "mock": bool(mock),
        "stream": True,
        "stream_meta": meta,
        "tokens": max(1, len(body) // 4) if body else 0,
        "product": "model_caller.call_stream",
    }
    if mode == "budget_blocked":
        result["ok"] = False
        result["blocked"] = True
        result["error"] = fallback_reason or "budget_exceeded"
        result["error_code"] = "budget"
    if cancelled:
        result["ok"] = False
        result["error_code"] = "cancelled"
    try:
        from .cost_accounting import attach_cost_fields

        result = attach_cost_fields(result, model=model, prompt=prompt or body[:500])
    except Exception:
        result.setdefault("estimated_cost_usd", 0.0)
        result.setdefault("cost_source", "estimate")
    try:
        from .spend_guard import ensure_public_result

        result = ensure_public_result(
            result, mock=mock, ok=result.get("ok"), dry_run=False
        )
    except Exception:
        result.setdefault("contract", "superai.result.v1")
    set_stream_meta(aggregated=result, **meta)
    return result


def supports_stream(
    model: Optional[str] = None, provider: Optional[str] = None
) -> Dict[str, Any]:
    """
    Per-model/provider stream capability flag (V4-M4 registry-style).

    Offline-honest: reports implemented *paths*, not live proof.
    """
    prov = str(provider or "").lower()
    mod = str(model or "").lower()
    if not prov and model:
        try:
            from .model_registry import ModelRegistry

            info = ModelRegistry().get_model(str(model))
            if info is not None:
                prov = str(getattr(info, "provider", "") or "").lower()
        except Exception:
            pass

    is_anthropic = (
        "anthropic" in prov
        or "claude" in prov
        or "claude" in mod
        or "anthropic" in mod
    )
    is_ollama = "ollama" in prov or "ollama" in mod or mod.startswith("local")
    is_openai_compat = (not is_anthropic) or "openai" in prov or "azure" in prov

    # Implemented code paths
    if is_anthropic:
        mode = "sse_anthropic_messages"
        supports = True
        note = "Anthropic Messages SSE path; requires ANTHROPIC_API_KEY for live"
    elif is_ollama:
        mode = "sse_openai_compatible"
        supports = True
        note = "Ollama OpenAI-compatible stream=True; falls back to chunked if empty"
    else:
        mode = "sse_openai_compatible"
        supports = True
        note = "OpenAI-compatible chat.completions stream=True; chunked_fallback on failure"

    return {
        "supports_stream": supports,
        "preferred_mode": mode,
        "fallback_mode": "chunked_fallback",
        "mock_mode": "mock_chunked",
        "provider": provider or prov or None,
        "model": model,
        "note": note,
    }


def stream_capabilities(model: Optional[str] = None, provider: Optional[str] = None) -> Dict[str, Any]:
    """
    Report which streaming backends SuperAI can use offline/online.

    Does not claim live SSE success without a live call — only capability paths.
    """
    openai_compat = True
    anthropic = False
    try:
        from .provider_catalog import get_openai_compat_config, resolve_compat_provider

        if provider:
            anthropic = "anthropic" in str(provider).lower() or "claude" in str(provider).lower()
            openai_compat = bool(get_openai_compat_config(resolve_compat_provider(provider))) or not anthropic
        if model and ("claude" in str(model).lower() or "anthropic" in str(model).lower()):
            anthropic = True
    except Exception:
        pass

    matrix = [
        {
            "provider_kind": "anthropic",
            "path": "ModelCaller._stream_anthropic",
            "mode": "sse",
            "live_required": ["ANTHROPIC_API_KEY"],
            "offline": "chunked_fallback or mock_chunked",
        },
        {
            "provider_kind": "openai_compatible",
            "path": "openai.OpenAI chat.completions stream=True",
            "mode": "sse",
            "live_required": ["OPENAI_API_KEY or provider key"],
            "offline": "chunked_fallback or mock_chunked",
        },
        {
            "provider_kind": "ollama_local",
            "path": "OpenAI-compatible base_url → Ollama",
            "mode": "sse",
            "live_required": ["local Ollama running"],
            "offline": "chunked_fallback or mock_chunked",
        },
        {
            "provider_kind": "mock",
            "path": "ModelCaller.call + chunk_text",
            "mode": "mock_chunked",
            "live_required": [],
            "offline": "always available when use_mock",
        },
        {
            "provider_kind": "any_fallback",
            "path": "ModelCaller.call + chunk_text",
            "mode": "chunked_fallback",
            "live_required": [],
            "offline": "always after stream failure/empty",
        },
    ]
    per = supports_stream(model=model, provider=provider)
    return {
        "ok": True,
        "product": "stream_capabilities",
        "modes": {
            "sse_openai_compatible": openai_compat,
            "sse_anthropic_messages": True,  # path implemented; needs live key
            "mock_chunked": True,
            "chunked_fallback": True,
        },
        "provider_matrix": matrix,
        "supports_stream": per,
        "model": model,
        "provider": provider,
        "cancel_between_chunks": True,
        "last": get_stream_meta(),
        "honesty": (
            "Live SSE success is host-gated by API keys / local runtime. "
            "Offline complete = mock_chunked + chunked_fallback + meta labels proven."
        ),
        "message": "Streaming capability matrix (live SSE still host-gated by API keys).",
    }


def chunk_text(text: str, size: int = 12) -> List[str]:
    t = text or ""
    if not t:
        return []
    return [t[i : i + size] for i in range(0, len(t), max(1, size))]


def stream_tokens(
    text: str,
    *,
    chunk_size: int = 16,
    delay_sec: float = 0.0,
    on_token: Optional[Callable[[str], None]] = None,
    emit_progress: bool = True,
) -> Generator[str, None, str]:
    """
    Yield token-ish chunks of text; return full text when done.
    """
    bus = None
    if emit_progress:
        try:
            from .progress_events import get_progress_bus

            bus = get_progress_bus()
            bus.emit("stream_start", chars=len(text or ""))
        except Exception:
            bus = None
    parts: List[str] = []
    for ch in chunk_text(text, chunk_size):
        parts.append(ch)
        if on_token:
            try:
                on_token(ch)
            except Exception:
                pass
        if bus:
            try:
                bus.emit("token", text=ch[:80], n=len(ch))
            except Exception:
                pass
        if delay_sec > 0:
            time.sleep(delay_sec)
        yield ch
    full = "".join(parts)
    if bus:
        try:
            bus.emit("stream_end", chars=len(full))
        except Exception:
            pass
    return full


def stream_response_dict(
    result: Dict[str, Any],
    *,
    on_token: Optional[Callable[[str], None]] = None,
) -> str:
    """Extract assistant text from ask/result dict and stream it."""
    body = ""
    if isinstance(result, dict):
        res = result.get("result")
        if isinstance(res, dict):
            body = str(
                res.get("message")
                or res.get("result")
                or (res.get("board") or {}).get("summary")
                or res.get("response")
                or ""
            )
        if not body:
            body = str(
                result.get("message")
                or result.get("response")
                or result.get("error")
                or ""
            )
    else:
        body = str(result)
    body = body[:4000]
    for _ in stream_tokens(body, on_token=on_token):
        pass
    return body
