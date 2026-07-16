"""In-CLI what's new (V6 S200)."""

from __future__ import annotations

from typing import Any, Dict, List

ENTRIES: List[Dict[str, str]] = [
    {
        "version": "v6",
        "summary": "World-best CLI backlog phases 1–15 foundations + honest host smoke gate",
    },
    {
        "version": "v5",
        "summary": "Ops maturity: error codes, cancel, golden eval, explain-run",
    },
    {
        "version": "v4",
        "summary": "Trust/cost, streaming, front-door, change-set, local-first",
    },
    {
        "version": "v3",
        "summary": "Tool protocol, failover, tenant, goals safety",
    },
]


def whats_new(limit: int = 5) -> Dict[str, Any]:
    return {
        "ok": True,
        "entries": ENTRIES[:limit],
        "contract": "superai.result.v1",
    }
