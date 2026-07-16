"""
Prompt-injection defenses for tool loops (V6 M015) — foundation → full.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_SUSPICIOUS = [
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions"),
    re.compile(r"(?i)disregard\s+(your|the)\s+(system|developer)\s+prompt"),
    re.compile(r"(?i)you\s+are\s+now\s+(in\s+)?(DAN|developer\s+mode|jailbreak)"),
    re.compile(r"(?i)</?\s*system\s*>"),
    re.compile(r"(?i)exfiltrate\s+(secrets?|keys?|credentials?)"),
    re.compile(r"(?i)do\s+not\s+follow\s+safety"),
    re.compile(r"(?i)override\s+(safety|policy|guardrails?)"),
]


def scan_text(text: str) -> Dict[str, Any]:
    hits: List[str] = []
    s = str(text or "")
    for pat in _SUSPICIOUS:
        m = pat.search(s)
        if m:
            hits.append(m.group(0)[:80])
    return {
        "ok": len(hits) == 0,
        "suspicious": bool(hits),
        "hits": hits[:10],
        "risk": "high" if hits else "low",
    }


def sanitize_tool_result(result: Any, *, max_chars: int = 50_000) -> Dict[str, Any]:
    """
    Wrap tool output: redact secrets, flag injection, truncate.
    """
    from .secrets import redact_text, redact_obj

    if isinstance(result, dict):
        text = str(result.get("content") or result.get("output") or result.get("result") or result)
        clean = redact_obj(result)
    else:
        text = str(result or "")
        clean = redact_text(text)

    scan = scan_text(text)
    out_text = redact_text(text)
    if len(out_text) > max_chars:
        out_text = out_text[:max_chars] + "\n…[truncated]"

    return {
        "ok": True,
        "content": out_text if not isinstance(clean, dict) else clean,
        "injection": scan,
        "sanitized": True,
        "blocked": scan.get("risk") == "high" and len(scan.get("hits") or []) >= 2,
    }


def tool_loop_guard(messages: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Scan recent tool/user messages for injection before next model step."""
    hits: List[Dict[str, Any]] = []
    for m in messages or []:
        role = str(m.get("role") or "")
        content = str(m.get("content") or "")
        if role in {"tool", "user", "system"}:
            sc = scan_text(content)
            if sc.get("suspicious"):
                hits.append({"role": role, **sc})
    return {
        "ok": len(hits) == 0,
        "findings": hits[:20],
        "action": "warn" if hits else "allow",
    }
