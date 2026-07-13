"""
Memory Palace for SuperAI — Persistent semantic memory (ChromaDB + in-memory fallback).
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import chromadb

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from .embeddings import create_embedding_function, describe_embedding


def _safe_metadata(metadata: Dict[str, Any], tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """Chroma only accepts str/int/float/bool primitives."""
    safe: Dict[str, Any] = {}
    if tags is not None:
        safe["tags"] = ",".join(tags)
    for k, v in metadata.items():
        if v is None:
            continue
        if isinstance(v, bool):
            # Store as int for broader Chroma compatibility, keep bool if accepted
            safe[k] = v
        elif isinstance(v, (str, int, float)):
            safe[k] = v
        else:
            safe[k] = str(v)
    return safe


def _parse_tags(meta: Dict[str, Any], mem: Optional[Dict] = None) -> set[str]:
    raw = (meta or {}).get("tags", "")
    tags: set[str] = set()
    if isinstance(raw, str):
        tags = {t.strip().lower() for t in raw.split(",") if t.strip()}
    elif isinstance(raw, list):
        tags = {str(t).lower() for t in raw}
    if mem:
        for t in mem.get("tags") or []:
            tags.add(str(t).lower())
    return tags


class MemoryPalace:
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        embedding_model: Optional[str] = None,
        embedding_function: Any = None,
    ):
        if persist_directory:
            self.persist_directory = persist_directory
        else:
            self.persist_directory = os.path.expanduser("~/.superai/memory")

        os.makedirs(self.persist_directory, exist_ok=True)
        self.memories: List[Dict[str, Any]] = []

        # F3.1: local EmbeddingGemma / ST / hash embeddings
        prefer_hash = os.getenv("SUPERAI_EMBEDDING_HASH", "").lower() in {
            "1",
            "true",
            "yes",
        }
        self.embedding_function = embedding_function or create_embedding_function(
            embedding_model, prefer_hash=prefer_hash
        )
        self.embedding_id = describe_embedding(self.embedding_function)

        if CHROMADB_AVAILABLE:
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            safe = re.sub(r"[^a-zA-Z0-9_]+", "_", self.embedding_id)[:48] or "default"
            coll_name = f"superai_memories_{safe}"
            try:
                self.collection = self.client.get_or_create_collection(
                    name=coll_name,
                    metadata={
                        "hnsw:space": "cosine",
                        "embedding": self.embedding_id[:200],
                    },
                    embedding_function=self.embedding_function,
                )
            except Exception:
                # Older chroma / incompatible EF — fall back to default EF collection
                self.collection = self.client.get_or_create_collection(
                    name="superai_memories",
                    metadata={"hnsw:space": "cosine"},
                )
            self.use_chromadb = True
        else:
            self.use_chromadb = False

    def store(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.7,
    ) -> str:
        if tags is None:
            tags = []
        if metadata is None:
            metadata = {}

        metadata = dict(metadata)
        metadata["importance"] = float(importance)
        metadata["created_at"] = datetime.now().isoformat()
        metadata.setdefault("last_accessed", metadata["created_at"])
        metadata.setdefault("deprecated", False)

        memory_id = f"{datetime.now().timestamp():.6f}-{uuid.uuid4().hex[:8]}"

        if self.use_chromadb:
            safe_meta = _safe_metadata(metadata, tags=tags)
            self.collection.add(
                documents=[content],
                metadatas=[safe_meta],
                ids=[memory_id],
            )
        else:
            self.memories.append(
                {
                    "id": memory_id,
                    "content": content,
                    "tags": list(tags),
                    "metadata": metadata,
                    "importance": importance,
                    "created_at": metadata["created_at"],
                }
            )
        return memory_id

    def update_metadata(self, memory_id: str, metadata_updates: Dict[str, Any]) -> bool:
        """Persist metadata updates (importance, deprecated flags, etc.)."""
        if self.use_chromadb:
            try:
                existing = self.collection.get(ids=[memory_id])
                if not existing["ids"]:
                    return False
                meta = dict(existing["metadatas"][0] or {})
                meta.update(metadata_updates)
                # Re-sanitize
                tags_str = meta.get("tags", "")
                tags = [t for t in str(tags_str).split(",") if t] if tags_str else None
                safe = _safe_metadata(
                    {k: v for k, v in meta.items() if k != "tags"},
                    tags=tags,
                )
                if tags_str and "tags" not in safe:
                    safe["tags"] = tags_str
                self.collection.update(ids=[memory_id], metadatas=[safe])
                return True
            except Exception:
                return False

        for mem in self.memories:
            if mem.get("id") == memory_id:
                meta = mem.setdefault("metadata", {})
                meta.update(metadata_updates)
                if "importance" in metadata_updates:
                    mem["importance"] = metadata_updates["importance"]
                return True
        return False

    def query_semantic(
        self,
        query: str,
        top_k: int = 5,
        n_results: Optional[int] = None,
        tags: Optional[List[str]] = None,
        include_deprecated: bool = False,
        **kwargs: Any,
    ) -> List[Dict]:
        if n_results is not None:
            top_k = n_results
        _ = kwargs

        if self.use_chromadb:
            # Fetch extra then filter if tags requested
            fetch_n = max(top_k * 3, top_k) if tags else top_k
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=max(fetch_n, 1),
                )
            except Exception:
                return []

            memories: List[Dict] = []
            ids = (results.get("ids") or [[]])[0]
            docs = (results.get("documents") or [[]])[0]
            metas = (results.get("metadatas") or [[]])[0]
            dists = (results.get("distances") or [[None] * len(ids)])[0]

            wanted = {t.lower() for t in tags} if tags else None

            for i, memory_id in enumerate(ids):
                metadata = dict(metas[i] or {})
                if not include_deprecated and metadata.get("deprecated") in (True, "True", "true", 1):
                    continue
                if wanted:
                    mem_tags = _parse_tags(metadata)
                    if not wanted.intersection(mem_tags):
                        continue
                try:
                    metadata["last_accessed"] = datetime.now().isoformat()
                    self.collection.update(ids=[memory_id], metadatas=[_safe_metadata(metadata)])
                except Exception:
                    pass
                memories.append(
                    {
                        "id": memory_id,
                        "content": docs[i],
                        "metadata": metadata,
                        "importance": float(metadata.get("importance", 0.5)),
                        "distance": dists[i] if i < len(dists) else None,
                    }
                )
                if len(memories) >= top_k:
                    break
            return memories

        # In-memory keyword fallback
        results = []
        query_lower = query.lower()
        wanted = {t.lower() for t in tags} if tags else None
        for mem in self.memories:
            meta = mem.get("metadata") or {}
            if not include_deprecated and meta.get("deprecated"):
                continue
            if query_lower not in (mem.get("content") or "").lower():
                continue
            if wanted and not wanted.intersection(_parse_tags(meta, mem)):
                continue
            results.append(
                {
                    "id": mem["id"],
                    "content": mem["content"],
                    "metadata": meta,
                    "importance": mem.get("importance", meta.get("importance", 0.5)),
                    "tags": mem.get("tags", []),
                }
            )
        return results[:top_k]

    def retrieve_by_tags(
        self,
        tags: List[str],
        limit: int = 50,
        match_all: bool = False,
        include_deprecated: bool = False,
    ) -> List[Dict]:
        if not tags:
            return []

        wanted = {t.lower() for t in tags}
        memories = self.get_all_memories()
        matched: List[Dict] = []

        for mem in memories:
            meta = mem.get("metadata") or {}
            if not include_deprecated and meta.get("deprecated") in (True, "True", "true", 1):
                continue
            mem_tags = _parse_tags(meta, mem)
            if match_all:
                ok = wanted.issubset(mem_tags)
            else:
                ok = bool(wanted.intersection(mem_tags))
            if not ok:
                continue
            out = {
                **mem,
                "importance": float(
                    mem.get("importance", meta.get("importance", 0.5))
                ),
            }
            matched.append(out)
            if len(matched) >= limit:
                break
        return matched

    def get_all_memories(self) -> List[Dict]:
        if self.use_chromadb:
            results = self.collection.get()
            memories = []
            for i in range(len(results["ids"])):
                meta = results["metadatas"][i] or {}
                memories.append(
                    {
                        "id": results["ids"][i],
                        "content": results["documents"][i],
                        "metadata": meta,
                        "importance": float(meta.get("importance", 0.5)),
                    }
                )
            return memories
        return list(self.memories)

    def delete(self, memory_id: str) -> None:
        if self.use_chromadb:
            self.collection.delete(ids=[memory_id])
        else:
            self.memories = [m for m in self.memories if m.get("id") != memory_id]

    def get_memory_stats(self) -> Dict[str, Any]:
        if self.use_chromadb:
            count = self.collection.count()
        else:
            count = len(self.memories)
        return {
            "total_memories": count,
            "using_chromadb": self.use_chromadb,
            "embedding": getattr(self, "embedding_id", "unknown"),
        }

    def apply_memory_decay(
        self, decay_factor: float = 0.97, min_importance: float = 0.05
    ) -> int:
        """Reduce importance of stale memories. Works for Chroma and in-memory."""
        updated_count = 0
        memories = self.get_all_memories()

        for mem in memories:
            meta = dict(mem.get("metadata") or {})
            if meta.get("deprecated"):
                continue
            importance = float(meta.get("importance", mem.get("importance", 0.7)))
            created_at_str = meta.get("created_at")
            last_accessed_str = meta.get("last_accessed", created_at_str)
            if not last_accessed_str:
                continue
            try:
                last_accessed = datetime.fromisoformat(str(last_accessed_str))
            except Exception:
                continue

            days_since_access = (datetime.now() - last_accessed).days
            effective_decay = 0.995 if importance > 0.85 else decay_factor

            if days_since_access > 7:
                new_importance = max(min_importance, importance * effective_decay)
                if new_importance < importance:
                    if self.update_metadata(
                        mem["id"],
                        {"importance": round(new_importance, 4)},
                    ):
                        updated_count += 1
        return updated_count
