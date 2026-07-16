"""Model capability tags (V6 S152)."""

from __future__ import annotations

from typing import Any, Dict, List, Set


def tags_for_model(name: str) -> List[str]:
    s = (name or "").lower()
    tags: Set[str] = set()
    if any(x in s for x in ("gpt-4o", "claude-4", "gemini-2", "vision", "4o")):
        tags.add("vision")
    if any(x in s for x in ("o3", "o4", "r1", "reason")):
        tags.add("reasoning")
    if any(x in s for x in ("coder", "code", "deepseek-coder", "qwen2.5-coder")):
        tags.add("coding")
    if any(x in s for x in ("flash", "mini", "nano", "haiku")):
        tags.add("fast")
        tags.add("cheap")
    if any(
        x in s
        for x in (
            "ollama",
            "local",
            "lmstudio",
            "vllm",
            "cli:",
            "llama",
            "gemma",
            "mistral",
        )
    ):
        tags.add("local")
    if "cli:" in s:
        tags.add("external_cli")
    if not tags:
        tags.add("general")
    tags.add("tools")  # SuperAI can wrap tools for most
    return sorted(tags)


def catalog_with_tags(models: List[str]) -> List[Dict[str, Any]]:
    return [{"model": m, "capabilities": tags_for_model(m)} for m in models]


def filter_by_capability(models: List[str], need: str) -> List[str]:
    n = (need or "").lower().strip()
    return [m for m in models if n in tags_for_model(m)]
