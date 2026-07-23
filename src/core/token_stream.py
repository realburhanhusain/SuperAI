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
    return {
        "ok": True,
        "product": "stream_capabilities",
        "modes": {
            "sse_openai_compatible": openai_compat,
            "sse_anthropic_messages": True,  # path implemented; needs live key
            "mock_chunked": True,
            "chunked_fallback": True,
        },
        "model": model,
        "provider": provider,
        "cancel_between_chunks": True,
        "last": get_stream_meta(),
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
