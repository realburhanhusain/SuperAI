"""
Token / chunk streaming helpers for agent-tui (MoSCoW S1).

Provides a generator that yields text chunks and emits progress bus events.
Works with mock mode and full completed responses (word/chunk cascade).
Live provider streaming can plug in later via stream_fn.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Generator, Iterable, List, Optional


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
