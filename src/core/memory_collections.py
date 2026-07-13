"""
Named Memory Palace collections (Phase 3 Track F3.2).

Collections: learnings, skills, tasks, reflections
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .memory_palace import MemoryPalace

COLLECTION_NAMES = ("learnings", "skills", "tasks", "reflections")


class MemoryCollections:
    """Facade over multiple MemoryPalace instances (one Chroma collection each)."""

    def __init__(self, base_dir: Optional[str] = None):
        root = base_dir or os.path.expanduser("~/.superai/memory")
        self.base_dir = root
        self._palaces: Dict[str, MemoryPalace] = {}
        for name in COLLECTION_NAMES:
            # Separate persist dirs keep isolation without requiring multi-collection API
            path = os.path.join(root, name)
            self._palaces[name] = MemoryPalace(persist_directory=path)

    def get(self, name: str) -> MemoryPalace:
        if name not in self._palaces:
            raise KeyError(f"Unknown collection: {name}. Valid: {COLLECTION_NAMES}")
        return self._palaces[name]

    def store(
        self,
        collection: str,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.7,
    ) -> str:
        return self.get(collection).store(
            content=content, tags=tags, metadata=metadata, importance=importance
        )

    def query(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
        tags: Optional[List[str]] = None,
    ) -> List[Dict]:
        return self.get(collection).query_semantic(
            query=query, top_k=top_k, tags=tags
        )

    def stats(self) -> Dict[str, Any]:
        return {
            name: palace.get_memory_stats()
            for name, palace in self._palaces.items()
        }
