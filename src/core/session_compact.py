"""
Session compact (Sprint B M6 / V6 M029) — preserve decisions + todos.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def extract_decisions_and_todos(
    turns: List[Dict[str, Any]],
    todos: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Structured extract of decisions and open todos for compaction."""
    decisions: List[str] = []
    open_todos: List[str] = []
    for t in turns or []:
        for key in ("user", "assistant", "content", "text"):
            s = str(t.get(key) or "")
            low = s.lower()
            if any(x in low for x in ("decided", "decision:", "we will", "agreed")):
                decisions.append(s.strip()[:240])
            if any(x in low for x in ("todo:", "- [ ]", "next:", "action:")):
                open_todos.append(s.strip()[:240])
    for td in todos or []:
        if isinstance(td, dict):
            status = str(td.get("status") or "open").lower()
            if status in {"open", "pending", "in_progress", ""}:
                open_todos.append(str(td.get("content") or td.get("text") or td)[:240])
        else:
            open_todos.append(str(td)[:240])
    # de-dupe preserve order
    def _uniq(xs: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in xs:
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        return out[:20]

    return {"decisions": _uniq(decisions), "todos": _uniq(open_todos)}


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
    bullets = []
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
        u = str(t.get("user") or "").strip().replace("\n", " ")
        a = str(t.get("assistant") or "").strip().replace("\n", " ")
        if u:
            bullets.append(f"- User asked: {u[:180]}")
        if a:
            bullets.append(f"  Outcome: {a[:180]}")
    text = "[Smart compact]\n" + "\n".join(bullets)
    if len(text) <= max_chars:
        return text
    # Keep decisions/todos first when truncating
    head = []
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
