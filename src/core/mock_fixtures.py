"""Deterministic mock fixtures for CI (V6 M092)."""

from __future__ import annotations

from typing import Any, Dict, List


FIXTURES: Dict[str, Dict[str, Any]] = {
    "hello": {
        "ok": True,
        "status": "success",
        "mock": True,
        "response": "Hello from SuperAI mock fixture.",
        "tokens": 12,
        "estimated_cost_usd": 0.0,
        "model": "mock-fixture",
    },
    "json_tool": {
        "ok": True,
        "status": "success",
        "mock": True,
        "response": '{"tool":"read","path":"README.md"}',
        "tokens": 20,
        "estimated_cost_usd": 0.0,
    },
    "error_budget": {
        "ok": False,
        "status": "error",
        "mock": True,
        "error_code": "budget",
        "error": "budget_exceeded",
        "blocked": True,
    },
    "board_opinions": {
        "ok": True,
        "mock": True,
        "opinions": [
            {"cli": "mock-a", "verdict": "approve", "confidence": 0.9, "summary": "ok"},
            {"cli": "mock-b", "verdict": "approve", "confidence": 0.8, "summary": "ok"},
        ],
    },
}


def get_fixture(name: str) -> Dict[str, Any]:
    data = FIXTURES.get(str(name))
    if not data:
        return {
            "ok": False,
            "error": f"unknown_fixture:{name}",
            "available": list_fixtures(),
        }
    return dict(data)


def list_fixtures() -> List[str]:
    return sorted(FIXTURES.keys())
