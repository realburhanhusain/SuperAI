"""
Session compact (Sprint B M6 / V6 M029 / V2-B3) — preserve decisions + todos.

Edge cases closed (2026-07-23):
- role/content message shapes (not only user/assistant keys)
- nested ``message`` / ``parts`` text
- completed markdown checkboxes and done/cancelled todo statuses excluded
- richer decision / next-action phrase detection
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

_DECISION_RE = re.compile(
    r"(?i)\b("
    r"decided|decision\s*:|we\s+will|we\s+agreed|agreed\s+to|chose\s+to|"
    r"going\s+with|final\s+decision|we'll\s+use|we\s+will\s+use|"
    r"settled\s+on|the\s+plan\s+is"
    r")\b"
)
_TODO_LINE_RE = re.compile(
    r"(?i)(?:^|\n)\s*(?:"
    r"todo\s*:|"
    r"-\s*\[\s*\]|"
    r"next\s*:|"
    r"action\s*:|"
    r"next\s+steps?\s*:|"
    r"follow[- ]?up\s*:"
    r")\s*(.+)"
)
_DONE_CHECKBOX_RE = re.compile(r"(?i)^\s*-\s*\[[xX✓✔]\]\s*")
_OPEN_CHECKBOX_RE = re.compile(r"(?i)^\s*-\s*\[\s*\]\s*(.+)$")
_DONE_STATUSES = frozenset(
    {
        "done",
        "completed",
        "complete",
        "closed",
        "cancelled",
        "canceled",
        "resolved",
        "wontfix",
        "won't fix",
        "skipped",
    }
)
_OPEN_STATUSES = frozenset(
    {
        "",
        "open",
        "pending",
        "in_progress",
        "in-progress",
        "todo",
        "active",
        "blocked",
        "started",
    }
)


def _uniq(xs: Sequence[str], *, limit: int = 20) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for x in xs:
        s = (x or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= limit:
            break
    return out


def _text_from_parts(parts: Any) -> str:
    if not isinstance(parts, list):
        return ""
    chunks: List[str] = []
    for p in parts:
        if isinstance(p, str):
            chunks.append(p)
        elif isinstance(p, dict):
            if p.get("type") in (None, "text") and p.get("text"):
                chunks.append(str(p.get("text") or ""))
            elif p.get("content"):
                chunks.append(str(p.get("content") or ""))
    return "\n".join(chunks)


def turn_text(turn: Any) -> str:
    """Normalize a turn dict (or string) into plain text for extraction."""
    if turn is None:
        return ""
    if isinstance(turn, str):
        return turn
    if not isinstance(turn, dict):
        return str(turn)

    chunks: List[str] = []
    for key in ("user", "assistant", "content", "text", "input", "output", "prompt", "response"):
        val = turn.get(key)
        if isinstance(val, str) and val.strip():
            chunks.append(val)
        elif isinstance(val, list):
            t = _text_from_parts(val)
            if t:
                chunks.append(t)

    # Chat-style role/content
    role = turn.get("role")
    content = turn.get("content")
    if role is not None and content is not None:
        if isinstance(content, str) and content.strip():
            chunks.append(content)
        elif isinstance(content, list):
            t = _text_from_parts(content)
            if t:
                chunks.append(t)

    nested = turn.get("message")
    if isinstance(nested, dict):
        chunks.append(turn_text(nested))
    elif isinstance(nested, str) and nested.strip():
        chunks.append(nested)

    return "\n".join(chunks)


def _is_open_todo_status(status: Any) -> bool:
    s = str(status or "").strip().lower()
    if s in _DONE_STATUSES:
        return False
    if s in _OPEN_STATUSES:
        return True
    # Unknown statuses: treat as open so we do not silently drop work
    return True


def _todo_item_text(td: Any) -> Optional[str]:
    if td is None:
        return None
    if isinstance(td, str):
        s = td.strip()
        if not s or _DONE_CHECKBOX_RE.match(s):
            return None
        m = _OPEN_CHECKBOX_RE.match(s)
        return (m.group(1).strip() if m else s)[:240] or None
    if not isinstance(td, dict):
        return str(td)[:240]

    if not _is_open_todo_status(td.get("status") or td.get("state")):
        return None
    # explicit done flag
    if td.get("done") is True or td.get("completed") is True:
        return None

    raw = td.get("content") or td.get("text") or td.get("title") or td.get("name") or ""
    s = str(raw).strip()
    if not s or _DONE_CHECKBOX_RE.match(s):
        return None
    m = _OPEN_CHECKBOX_RE.match(s)
    return (m.group(1).strip() if m else s)[:240] or None


def _scan_text_for_todos(text: str) -> List[str]:
    found: List[str] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if _DONE_CHECKBOX_RE.match(line):
            continue
        m = _OPEN_CHECKBOX_RE.match(line)
        if m:
            found.append(m.group(1).strip()[:240])
            continue
        m2 = _TODO_LINE_RE.search(line)
        if m2:
            body = m2.group(1).strip()
            # Skip "Todo: done" style closures
            if body.lower() in _DONE_STATUSES:
                continue
            found.append(body[:240])
    return found


def _scan_text_for_decisions(text: str) -> List[str]:
    found: List[str] = []
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if _DECISION_RE.search(s):
            found.append(s[:240])
    # whole-turn fallback if multi-sentence without newlines
    if not found and _DECISION_RE.search(text or ""):
        found.append((text or "").strip()[:240])
    return found


def extract_decisions_and_todos(
    turns: List[Dict[str, Any]],
    todos: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Structured extract of decisions and open todos for compaction."""
    decisions: List[str] = []
    open_todos: List[str] = []

    for t in turns or []:
        text = turn_text(t)
        if not text:
            continue
        decisions.extend(_scan_text_for_decisions(text))
        open_todos.extend(_scan_text_for_todos(text))

    for td in todos or []:
        item = _todo_item_text(td)
        if item:
            open_todos.append(item)

    return {
        "decisions": _uniq(decisions),
        "todos": _uniq(open_todos),
    }


def smart_compact(
    turns: List[Dict[str, Any]],
    max_chars: int = 1500,
    *,
    todos: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Prefer structured bullet extract preserving decisions/todos; fall back to trim."""
    if not turns and not todos:
        return ""
    preserved = extract_decisions_and_todos(turns, todos=todos)
    bullets: List[str] = []
    if preserved["decisions"]:
        bullets.append("[Decisions]")
        for d in preserved["decisions"][:12]:
            bullets.append(f"- {d}")
    if preserved["todos"]:
        bullets.append("[Open todos]")
        for t in preserved["todos"][:12]:
            bullets.append(f"- [ ] {t}")
    bullets.append("[Recent turns]")
    for t in (turns or [])[-12:]:
        if isinstance(t, dict):
            u = str(t.get("user") or "").strip().replace("\n", " ")
            a = str(t.get("assistant") or "").strip().replace("\n", " ")
            if not u and not a:
                # role/content shape
                role = str(t.get("role") or "").lower()
                body = turn_text(t).strip().replace("\n", " ")
                if role == "user" and body:
                    u = body
                elif role == "assistant" and body:
                    a = body
                elif body:
                    bullets.append(f"- Turn: {body[:180]}")
                    continue
            if u:
                bullets.append(f"- User asked: {u[:180]}")
            if a:
                bullets.append(f"  Outcome: {a[:180]}")
        else:
            body = turn_text(t).strip().replace("\n", " ")
            if body:
                bullets.append(f"- Turn: {body[:180]}")

    text = "[Smart compact]\n" + "\n".join(bullets)
    if len(text) <= max_chars:
        return text
    # Keep decisions/todos first when truncating
    head: List[str] = []
    if preserved["decisions"] or preserved["todos"]:
        head.append("[Decisions]")
        head.extend(f"- {d}" for d in preserved["decisions"][:8])
        head.append("[Open todos]")
        head.extend(f"- [ ] {t}" for t in preserved["todos"][:8])
    head_text = "\n".join(head)
    room = max(200, max_chars - len(head_text) - 20)
    tail = text[len(head_text) : len(head_text) + room] if head_text else text[:max_chars]
    return (head_text + "\n" + tail)[:max_chars] if head_text else text[:max_chars]


def compact_turns_simple(turns: List[Dict[str, Any]], max_chars: int = 1200) -> str:
    from .agent_tui import compact_turns

    return compact_turns(turns, max_chars=max_chars)
