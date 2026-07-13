"""
Secret redaction and sensitive-pattern scrubbing (M2).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# Common secret-ish patterns
_PATTERNS = [
    (re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|authorization)\s*[=:]\s*['\"]?([^\s'\"]{8,})"), r"\1=***REDACTED***"),
    (re.compile(r"(?i)\b(sk-[A-Za-z0-9_-]{10,})\b"), "***REDACTED_KEY***"),
    (re.compile(r"(?i)\b(Bearer\s+)[A-Za-z0-9._\-]+\b"), r"\1***REDACTED***"),
    (re.compile(r"(?i)\b(xox[baprs]-[A-Za-z0-9-]+)\b"), "***REDACTED_SLACK***"),
    (re.compile(r"(?i)\b(ghp_[A-Za-z0-9]{20,})\b"), "***REDACTED_GH***"),
    (re.compile(r"(?i)\b(AKIA[0-9A-Z]{16})\b"), "***REDACTED_AWS***"),
]


def redact_text(text: Optional[str]) -> str:
    if not text:
        return ""
    out = str(text)
    for pat, repl in _PATTERNS:
        out = pat.sub(repl, out)
    return out


def redact_obj(obj: Any, depth: int = 0) -> Any:
    if depth > 8:
        return obj
    if isinstance(obj, str):
        return redact_text(obj)
    if isinstance(obj, dict):
        return {k: redact_obj(v, depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_obj(x, depth + 1) for x in obj]
    return obj


def looks_like_secret(text: str) -> bool:
    if not text:
        return False
    red = redact_text(text)
    return red != text
