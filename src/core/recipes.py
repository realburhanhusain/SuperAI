"""Recipe gallery (V6 S196 / N300 foundations)."""

from __future__ import annotations

from typing import Any, Dict, List

RECIPES: List[Dict[str, str]] = [
    {
        "id": "fix-bug",
        "title": "Fix a bug",
        "prompt": "Reproduce, locate root cause, write a failing test, fix, re-run tests.",
    },
    {
        "id": "add-api",
        "title": "Add API endpoint",
        "prompt": "Add a REST endpoint with validation, tests, and docs.",
    },
    {
        "id": "refactor-module",
        "title": "Refactor module",
        "prompt": "Refactor for clarity without behavior change; keep tests green.",
    },
    {
        "id": "pr-review",
        "title": "Review PR/diff",
        "prompt": "Review the current git diff for bugs, security, and style.",
    },
    {
        "id": "ci-fail",
        "title": "Fix CI failure",
        "prompt": "From the CI log, identify failure and apply a minimal fix.",
    },
]


def list_recipes() -> Dict[str, Any]:
    return {"ok": True, "recipes": RECIPES, "count": len(RECIPES)}


def get_recipe(rid: str) -> Dict[str, Any]:
    for r in RECIPES:
        if r["id"] == rid:
            return {"ok": True, "recipe": r}
    return {"ok": False, "error": "not_found"}
