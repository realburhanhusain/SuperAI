"""Why did CI fail — log triage (V6 N260 / S109)."""

from __future__ import annotations

import re
from typing import Any, Dict, List


def analyze_log(log_text: str) -> Dict[str, Any]:
    text = log_text or ""
    findings: List[Dict[str, str]] = []
    patterns = [
        (r"FAILED\s+([\w./:\\-]+)", "failed_test"),
        (r"ERROR:\s*(.+)", "error"),
        (r"ModuleNotFoundError:\s*(.+)", "missing_module"),
        (r"AssertionError:\s*(.+)", "assertion"),
        (r"npm ERR!\s*(.+)", "npm_error"),
        (r"error TS\d+:\s*(.+)", "typescript"),
        (r"Permission denied", "permission"),
    ]
    for pat, kind in patterns:
        for m in re.finditer(pat, text, flags=re.I):
            findings.append(
                {
                    "kind": kind,
                    "match": (m.group(0) if m.lastindex is None else m.group(0))[:300],
                }
            )
            if len(findings) >= 20:
                break
        if len(findings) >= 20:
            break
    summary = "No clear failure pattern" if not findings else findings[0]["kind"]
    return {
        "ok": True,
        "summary": summary,
        "findings": findings,
        "lines": len(text.splitlines()),
        "hint": "superai do \"fix CI: <paste summary>\"",
        "contract": "superai.result.v1",
    }
