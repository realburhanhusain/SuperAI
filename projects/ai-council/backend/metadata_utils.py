"""Shared helpers for assistant message metadata."""

from typing import Any, Dict


def metadata_used_search(metadata: Dict[str, Any]) -> bool:
    """True when a run used web search (explicit flag or saved context)."""
    return bool(metadata.get("web_search") or metadata.get("search_context"))
