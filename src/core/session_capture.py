"""
Agent turn-capture hooks (Memory Roadmap P8 / Cognee gap 8).

Captures into **session memory** (P3), not always permanent palace/graph:

| Hook              | Kind stored   | Notes                                      |
|-------------------|---------------|--------------------------------------------|
| user_prompt       | user          | secrets redacted                           |
| tool_result       | tool          | tool name + summary/paths; secrets redacted|
| assistant_final   | assistant     | answer summary (truncated)                  |
| precompact        | snapshot      | force session snapshot note                |
| session_end       | (end)         | promote per level; optional cognify        |

Capture levels (SUPERAI_CAPTURE_LEVEL or explicit):
  off              — no-op
  session          — buffer only (default)
  session+promote  — buffer; promote on session_end
  full-cognify     — buffer; promote + cognify on session_end

Integration:
  - SessionCapture API (agents / tests)
  - process_turn_stream for offline fake turns
  - optional hooks.register_post for tool results
  - CLI ``superai capture`` and MCP ``superai_capture``
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

CAPTURE_LEVELS = frozenset(
    {"off", "session", "session+promote", "full-cognify"}
)

_HOOK_KINDS = {
    "user_prompt": "user",
    "user": "user",
    "tool_result": "tool",
    "tool": "tool",
    "assistant_final": "assistant",
    "assistant": "assistant",
    "precompact": "snapshot",
    "snapshot": "snapshot",
    "session_end": "session_end",
    "end": "session_end",
}

_DEFAULT_SUMMARY_CHARS = 2000
_DEFAULT_TOOL_CHARS = 1200


def resolve_capture_level(explicit: Optional[str] = None) -> str:
    raw = (explicit or os.getenv("SUPERAI_CAPTURE_LEVEL") or "session").strip().lower()
    # aliases
    aliases = {
        "on": "session",
        "true": "session",
        "1": "session",
        "false": "off",
        "0": "off",
        "none": "off",
        "promote": "session+promote",
        "session_promote": "session+promote",
        "cognify": "full-cognify",
        "full": "full-cognify",
    }
    raw = aliases.get(raw, raw)
    if raw not in CAPTURE_LEVELS:
        return "session"
    return raw


def _redact(text: str) -> str:
    try:
        from .secrets import redact_text

        return redact_text(text or "")
    except Exception:
        # minimal fallback
        out = text or ""
        out = re.sub(
            r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+",
            r"\1=[REDACTED]",
            out,
        )
        out = re.sub(r"sk-[a-zA-Z0-9]{20,}", "sk-[REDACTED]", out)
        return out


def _truncate(text: str, max_chars: int) -> str:
    t = text or ""
    if len(t) <= max_chars:
        return t
    return t[: max(0, max_chars - 20)] + "\n…[truncated]"


def _summarize_tool_result(
    tool_name: str,
    result: Any,
    *,
    max_chars: int = _DEFAULT_TOOL_CHARS,
) -> str:
    name = (tool_name or "tool").strip() or "tool"
    paths: List[str] = []
    summary = ""
    if isinstance(result, dict):
        for key in ("path", "paths", "file", "files", "cwd"):
            val = result.get(key)
            if isinstance(val, str) and val:
                paths.append(val)
            elif isinstance(val, list):
                paths.extend(str(x) for x in val[:10] if x)
        for key in ("summary", "message", "output", "content", "text", "error"):
            if result.get(key):
                summary = str(result.get(key))
                break
        if not summary:
            try:
                summary = json.dumps(
                    {k: result[k] for k in list(result)[:12]},
                    default=str,
                )[:max_chars]
            except Exception:
                summary = str(result)[:max_chars]
        ok = result.get("ok")
        head = f"tool={name} ok={ok}" if ok is not None else f"tool={name}"
    else:
        summary = str(result or "")
        head = f"tool={name}"
    if paths:
        head += " paths=" + ",".join(paths[:8])
    body = _truncate(_redact(summary), max_chars)
    return _redact(f"{head}\n{body}".strip())


@dataclass
class SessionCapture:
    """
    Bound capture context for one agent/CLI session.

    Example:
        cap = SessionCapture.start(title="demo", level="session")
        cap.user_prompt("How does Cloud SQL work?")
        cap.tool_result("search", {"ok": True, "summary": "..."})
        cap.assistant_final("Cloud SQL is ...")
        cap.session_end()
    """

    session_id: str
    level: str = "session"
    dataset_id: str = "default"
    source: str = "capture"
    sm: Any = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    _ended: bool = False

    # ------------------------------------------------------------------ factory
    @classmethod
    def start(
        cls,
        *,
        session_id: Optional[str] = None,
        title: Optional[str] = None,
        dataset_id: Optional[str] = None,
        source: str = "capture",
        level: Optional[str] = None,
        sm: Any = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> "SessionCapture":
        from .memory_dataset import resolve_dataset_id
        from .session_memory import SessionMemory, get_default_session_memory

        level_r = resolve_capture_level(level)
        did = resolve_dataset_id(dataset_id) or "default"
        memory = sm or get_default_session_memory()
        if level_r == "off":
            # still allocate an id for API stability but do not write
            sid = session_id or f"off_{os.getpid()}"
            return cls(
                session_id=sid,
                level="off",
                dataset_id=did,
                source=source,
                sm=memory,
            )
        out = memory.start(
            session_id=session_id,
            title=title or "agent capture",
            dataset_id=did,
            source=source,
            meta={
                **(meta or {}),
                "capture_level": level_r,
                "product": "session_capture",
            },
        )
        sid = (out.get("session") or {}).get("id") or session_id
        return cls(
            session_id=str(sid),
            level=level_r,
            dataset_id=did,
            source=source,
            sm=memory,
        )

    # ------------------------------------------------------------------ config
    def set_level(self, level: str) -> str:
        self.level = resolve_capture_level(level)
        return self.level

    @property
    def enabled(self) -> bool:
        return self.level != "off"

    # ------------------------------------------------------------------ hooks
    def capture(
        self,
        hook: str,
        content: Any = None,
        *,
        tool_name: Optional[str] = None,
        importance: Optional[float] = None,
        pinned: bool = False,
        meta: Optional[Dict[str, Any]] = None,
        max_chars: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generic hook dispatcher."""
        hook_l = (hook or "").strip().lower()
        kind = _HOOK_KINDS.get(hook_l, hook_l or "note")

        if kind == "session_end":
            return self.session_end(
                cognify_mode=str((meta or {}).get("cognify_mode") or "mock")
            )

        if not self.enabled:
            ev = {
                "ok": True,
                "skipped": True,
                "reason": "capture_level=off",
                "hook": hook_l,
                "session_id": self.session_id,
            }
            self.events.append(ev)
            return ev

        if kind == "user":
            return self.user_prompt(
                str(content or ""),
                importance=importance,
                pinned=pinned,
                meta=meta,
                max_chars=max_chars,
            )
        if kind == "tool":
            return self.tool_result(
                tool_name or (meta or {}).get("tool") or "tool",
                content if content is not None else meta or {},
                importance=importance,
                meta=meta,
                max_chars=max_chars,
            )
        if kind == "assistant":
            return self.assistant_final(
                str(content or ""),
                importance=importance,
                pinned=pinned,
                meta=meta,
                max_chars=max_chars,
            )
        if kind == "snapshot":
            return self.precompact(
                note=str(content or "") or None,
                meta=meta,
            )
        # free-form note
        return self._remember(
            str(content or ""),
            kind=kind or "note",
            importance=importance if importance is not None else 0.5,
            pinned=pinned,
            meta={**(meta or {}), "hook": hook_l},
            max_chars=max_chars or _DEFAULT_SUMMARY_CHARS,
        )

    def user_prompt(
        self,
        text: str,
        *,
        importance: Optional[float] = None,
        pinned: bool = False,
        meta: Optional[Dict[str, Any]] = None,
        max_chars: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._remember(
            text,
            kind="user",
            importance=importance if importance is not None else 0.55,
            pinned=pinned,
            meta={**(meta or {}), "hook": "user_prompt"},
            max_chars=max_chars or _DEFAULT_SUMMARY_CHARS,
        )

    def tool_result(
        self,
        tool_name: str,
        result: Any,
        *,
        importance: Optional[float] = None,
        meta: Optional[Dict[str, Any]] = None,
        max_chars: Optional[int] = None,
    ) -> Dict[str, Any]:
        body = _summarize_tool_result(
            tool_name, result, max_chars=max_chars or _DEFAULT_TOOL_CHARS
        )
        return self._remember(
            body,
            kind="tool",
            importance=importance if importance is not None else 0.45,
            pinned=False,
            meta={
                **(meta or {}),
                "hook": "tool_result",
                "tool": tool_name,
            },
            max_chars=None,  # already truncated
        )

    def assistant_final(
        self,
        text: str,
        *,
        importance: Optional[float] = None,
        pinned: bool = False,
        meta: Optional[Dict[str, Any]] = None,
        max_chars: Optional[int] = None,
    ) -> Dict[str, Any]:
        return self._remember(
            text,
            kind="assistant",
            importance=importance if importance is not None else 0.6,
            pinned=pinned,
            meta={**(meta or {}), "hook": "assistant_final"},
            max_chars=max_chars or _DEFAULT_SUMMARY_CHARS,
        )

    def precompact(
        self,
        *,
        note: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Force a session snapshot before context compaction."""
        if not self.enabled:
            ev = {
                "ok": True,
                "skipped": True,
                "reason": "capture_level=off",
                "hook": "precompact",
            }
            self.events.append(ev)
            return ev
        # list current items as a compact snapshot summary
        items_out = self.sm.list_items(self.session_id, limit=50) if self.sm else {}
        n = int(items_out.get("count") or 0)
        lines = [
            f"[precompact snapshot] session={self.session_id} items={n}",
        ]
        if note:
            lines.append(_redact(note)[:500])
        for it in (items_out.get("items") or [])[:15]:
            lines.append(
                f"- {it.get('kind')}: {str(it.get('content') or '')[:120]}"
            )
        body = "\n".join(lines)
        return self._remember(
            body,
            kind="snapshot",
            importance=0.7,
            pinned=True,
            meta={**(meta or {}), "hook": "precompact", "item_count": n},
            max_chars=4000,
        )

    def session_end(
        self,
        *,
        cognify_mode: str = "mock",
        min_importance: float = 0.6,
    ) -> Dict[str, Any]:
        """End session; promote/cognify depending on capture level."""
        if self._ended:
            return {
                "ok": True,
                "session_id": self.session_id,
                "already_ended": True,
                "message": "Session already ended",
            }
        self._ended = True

        if not self.enabled:
            return {
                "ok": True,
                "skipped": True,
                "reason": "capture_level=off",
                "session_id": self.session_id,
                "level": self.level,
                "message": "Capture off — no end side effects",
            }

        auto_promote = self.level in {"session+promote", "full-cognify"}
        cognify = self.level == "full-cognify"
        # Always call end so status becomes ended; promote only when level asks
        out = self.sm.end(
            self.session_id,
            auto_promote=auto_promote,
            min_importance=min_importance,
            cognify_graph=cognify,
            cognify_mode=cognify_mode,
        )
        out["level"] = self.level
        out["capture_promoted"] = auto_promote
        out["capture_cognify"] = cognify
        out.setdefault(
            "message",
            f"Session end level={self.level} promote={auto_promote} cognify={cognify}",
        )
        self.events.append({"hook": "session_end", **{k: out.get(k) for k in ("ok", "promoted", "level")}})
        return out

    # ------------------------------------------------------------------ internal
    def _remember(
        self,
        content: str,
        *,
        kind: str,
        importance: float,
        pinned: bool,
        meta: Optional[Dict[str, Any]],
        max_chars: Optional[int],
    ) -> Dict[str, Any]:
        if not self.enabled:
            ev = {
                "ok": True,
                "skipped": True,
                "reason": "capture_level=off",
                "kind": kind,
            }
            self.events.append(ev)
            return ev
        text = _redact(str(content or ""))
        if max_chars is not None:
            text = _truncate(text, max_chars)
        if not text.strip():
            return {
                "ok": False,
                "error": "empty content after redact",
                "error_code": "validation",
                "kind": kind,
            }
        out = self.sm.remember(
            self.session_id,
            text,
            kind=kind,
            importance=importance,
            pinned=pinned,
            tags=["capture", f"kind:{kind}", f"dataset:{self.dataset_id}"],
            meta={
                **(meta or {}),
                "capture_level": self.level,
                "redacted": True,
            },
            dataset_id=self.dataset_id,
            source=self.source,
        )
        self.events.append(
            {
                "hook": (meta or {}).get("hook") or kind,
                "ok": out.get("ok"),
                "kind": kind,
                "item_id": (out.get("item") or {}).get("id"),
            }
        )
        return out

    def status(self) -> Dict[str, Any]:
        st = self.sm.get(self.session_id) if self.sm else {}
        return {
            "ok": True,
            "product": "session_capture",
            "session_id": self.session_id,
            "level": self.level,
            "dataset_id": self.dataset_id,
            "enabled": self.enabled,
            "ended": self._ended,
            "events_recorded": len(self.events),
            "session": st.get("session"),
            "message": (
                f"Capture session={self.session_id} level={self.level} "
                f"events={len(self.events)}"
            ),
        }


def process_turn_stream(
    turns: Sequence[Dict[str, Any]],
    *,
    session_id: Optional[str] = None,
    level: Optional[str] = None,
    dataset_id: Optional[str] = None,
    source: str = "turn_stream",
    sm: Any = None,
    title: str = "turn stream",
    auto_end: bool = True,
) -> Dict[str, Any]:
    """
    Offline/E2E helper: process a list of turn dicts.

    Each turn:
      {"hook": "user_prompt"|"tool_result"|"assistant_final"|"precompact"|"session_end",
       "content": "...", "tool": "...", "result": {...}, ...}
    """
    cap = SessionCapture.start(
        session_id=session_id,
        title=title,
        dataset_id=dataset_id,
        source=source,
        level=level,
        sm=sm,
    )
    results: List[Dict[str, Any]] = []
    for i, turn in enumerate(turns or []):
        if not isinstance(turn, dict):
            results.append({"ok": False, "error": "turn must be dict", "index": i})
            continue
        hook = str(turn.get("hook") or turn.get("type") or turn.get("kind") or "note")
        content = turn.get("content", turn.get("text", turn.get("message")))
        if hook.lower() in {"tool_result", "tool"}:
            r = cap.tool_result(
                str(turn.get("tool") or turn.get("tool_name") or "tool"),
                turn.get("result", content),
                importance=turn.get("importance"),
                meta=turn.get("meta"),
            )
        else:
            r = cap.capture(
                hook,
                content,
                tool_name=turn.get("tool"),
                importance=turn.get("importance"),
                pinned=bool(turn.get("pinned")),
                meta=turn.get("meta"),
            )
        results.append(r)

    end_out = None
    if auto_end and not cap._ended:
        # only auto-end if stream didn't include session_end
        if not any(
            str(t.get("hook") or "").lower() in {"session_end", "end"}
            for t in (turns or [])
            if isinstance(t, dict)
        ):
            end_out = cap.session_end(
                cognify_mode=str(
                    os.getenv("SUPERAI_COGNIFY_MODE") or "mock"
                )
            )

    items = cap.sm.list_items(cap.session_id, limit=100) if cap.sm and cap.enabled else {
        "count": 0,
        "items": [],
    }
    report = {
        "ok": all(r.get("ok") is not False for r in results) or cap.level == "off",
        "product": "session_capture_stream",
        "session_id": cap.session_id,
        "level": cap.level,
        "dataset_id": cap.dataset_id,
        "turns_processed": len(results),
        "items_count": items.get("count"),
        "items": items.get("items"),
        "turn_results": results,
        "session_end": end_out,
        "events": cap.events,
        "message": (
            f"Processed {len(results)} turn(s) → session {cap.session_id} "
            f"level={cap.level} items={items.get('count')}"
        ),
    }
    try:
        from .memory_otel import instrument_report

        report = instrument_report("capture_stream", report)
    except Exception:
        pass
    return report


def maybe_start_agent_auto_capture(
    *,
    session_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
    title: str = "agent tui",
    source: str = "agent_tui",
) -> Optional[SessionCapture]:
    """
    MR-6: opt-in auto-capture for main agent / agent-tui paths.

    Enabled when SUPERAI_CAPTURE_LEVEL is not off (default session).
    Set SUPERAI_AGENT_AUTO_CAPTURE=0 to disable without changing level.
    """
    if (os.getenv("SUPERAI_AGENT_AUTO_CAPTURE") or "1").strip().lower() in {
        "0",
        "false",
        "off",
        "no",
    }:
        return None
    level = resolve_capture_level()
    if level == "off":
        return None
    try:
        cap = SessionCapture.start(
            session_id=session_id,
            title=title,
            dataset_id=dataset_id,
            source=source,
            level=level,
        )
        set_active_capture(cap)
        return cap
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Global optional tool-hook wiring
# ---------------------------------------------------------------------------

_ACTIVE: Optional[SessionCapture] = None
_POST_REGISTERED = False


def get_active_capture() -> Optional[SessionCapture]:
    return _ACTIVE


def set_active_capture(cap: Optional[SessionCapture]) -> None:
    global _ACTIVE
    _ACTIVE = cap


def install_tool_capture_hooks(cap: Optional[SessionCapture] = None) -> Dict[str, Any]:
    """Register post-tool hook that captures tool results into active session."""
    global _POST_REGISTERED, _ACTIVE
    if cap is not None:
        _ACTIVE = cap
    if _POST_REGISTERED:
        return {"ok": True, "already": True, "session_id": getattr(_ACTIVE, "session_id", None)}

    from . import hooks as hook_mod

    def _post(name: str, args: Dict[str, Any], result: Dict[str, Any]) -> None:
        active = _ACTIVE
        if active is None or not active.enabled:
            return
        try:
            active.tool_result(name, result if isinstance(result, dict) else {"output": result})
        except Exception:
            return

    hook_mod.register_post(_post)
    _POST_REGISTERED = True
    return {
        "ok": True,
        "installed": True,
        "session_id": getattr(_ACTIVE, "session_id", None),
        "message": "Tool post-hook capture installed",
    }


def capture_config() -> Dict[str, Any]:
    """Current env/default capture configuration (for docs/CLI)."""
    level = resolve_capture_level(None)
    return {
        "ok": True,
        "product": "session_capture_config",
        "level": level,
        "levels": sorted(CAPTURE_LEVELS),
        "env": {
            "SUPERAI_CAPTURE_LEVEL": os.getenv("SUPERAI_CAPTURE_LEVEL"),
            "SUPERAI_DATASET_ID": os.getenv("SUPERAI_DATASET_ID"),
        },
        "storage": {
            "sessions_db": str(
                Path(os.path.expanduser("~/.superai/memory/sessions.sqlite"))
            ),
            "note": "Session buffer only until promote; never stores raw API keys (redacted)",
        },
        "hooks": [
            "user_prompt",
            "tool_result",
            "assistant_final",
            "precompact",
            "session_end",
        ],
        "message": f"Capture level={level}",
    }
