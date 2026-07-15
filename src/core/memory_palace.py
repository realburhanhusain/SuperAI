"""
Memory Palace for SuperAI — Persistent semantic memory (ChromaDB + in-memory fallback).

Phase 3 concurrent safety:
  - process file lock + per-process thread RLock on store/update
  - shared singleton per persist_directory
  - optional write queue for multi-CLI fan-out
"""

from __future__ import annotations

import os
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import chromadb

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from .embeddings import create_embedding_function, describe_embedding
from .faiss_store import FaissMemoryStore, use_faiss_backend
from .store_lock import memory_write_queue, store_lock, thread_lock_for


_PALACE_SINGLETONS: Dict[str, "MemoryPalace"] = {}
_PALACE_SINGLETONS_GUARD = threading.Lock()


def get_shared_palace(
    persist_directory: Optional[str] = None,
    **kwargs: Any,
) -> "MemoryPalace":
    """
    Process-wide shared MemoryPalace for a given store path.
    Prefer this over constructing many MemoryPalace() instances under concurrency.
    """
    if persist_directory:
        key = str(Path(persist_directory).expanduser().resolve())
    else:
        key = str(Path(os.path.expanduser("~/.superai/memory")).resolve())
    with _PALACE_SINGLETONS_GUARD:
        if key not in _PALACE_SINGLETONS:
            _PALACE_SINGLETONS[key] = MemoryPalace(
                persist_directory=persist_directory or key, **kwargs
            )
        return _PALACE_SINGLETONS[key]


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
        self._root = Path(self.persist_directory)
        self._thread_lock = thread_lock_for(self._root)

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

        # N5: optional FAISS / brute-force vector backend
        self.use_faiss = use_faiss_backend()
        self.faiss_store: Optional[FaissMemoryStore] = None
        if self.use_faiss:
            self.faiss_store = FaissMemoryStore(
                root=Path(self.persist_directory) / "faiss"
            )
            self.use_chromadb = False
            return

        if CHROMADB_AVAILABLE:
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            safe = re.sub(r"[^a-zA-Z0-9_]+", "_", self.embedding_id)[:48] or "default"
            coll_name = f"superai_memories_{safe}"
            # HNSW knobs via env (Future Plan advanced embedding)
            hnsw_meta = {
                "hnsw:space": os.getenv("SUPERAI_HNSW_SPACE", "cosine"),
                "embedding": self.embedding_id[:200],
            }
            # Chroma accepts construction-time M / ef via metadata on some versions
            for env_k, meta_k in (
                ("SUPERAI_HNSW_M", "hnsw:M"),
                ("SUPERAI_HNSW_EF_CONSTRUCTION", "hnsw:construction_ef"),
                ("SUPERAI_HNSW_EF_SEARCH", "hnsw:search_ef"),
            ):
                raw = os.getenv(env_k)
                if raw and raw.isdigit():
                    hnsw_meta[meta_k] = int(raw)
            try:
                self.collection = self.client.get_or_create_collection(
                    name=coll_name,
                    metadata=hnsw_meta,
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

    def _locked_write(self, fn):
        """Serialize writers (thread + cross-process lock)."""
        with store_lock(self._root, name="palace.lock", timeout=45.0):
            return fn()

    def store_queued(self, *args: Any, **kwargs: Any) -> str:
        """Enqueue a store through the process write queue (parallel multi-CLI safe)."""
        return memory_write_queue().submit(lambda: self.store(*args, **kwargs))

    def store(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.7,
        *,
        wing: Optional[str] = None,
        room: Optional[str] = None,
        auto_wings: bool = True,
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
        # Mempalace-inspired provenance
        metadata.setdefault("version", int(metadata.get("version") or 1))
        if metadata.get("parent_id"):
            metadata["parent_id"] = str(metadata["parent_id"])
        metadata.setdefault("source", metadata.get("source") or "superai")

        # Wings & Rooms — first-class metadata (core to palace, not only sidecar)
        if auto_wings or wing or room:
            try:
                from .wings import WingsManager

                wm = WingsManager()
                if wing and room:
                    loc = {"wing": wing, "room": room}
                else:
                    loc = wm.classify_from_metadata(metadata, content=content)
                    if wing:
                        loc["wing"] = wing
                    if room:
                        loc["room"] = room
                metadata["wing"] = str(loc["wing"])
                metadata["room"] = str(loc["room"])
                # mirror tags for easy filter/browse
                for extra in (f"wing:{loc['wing']}", f"room:{loc['room']}"):
                    if extra not in tags:
                        tags = list(tags) + [extra]
            except Exception:
                metadata.setdefault("wing", wing or "learning")
                metadata.setdefault("room", room or "general")

        memory_id = f"{datetime.now().timestamp():.6f}-{uuid.uuid4().hex[:8]}"
        tags_final = list(tags)
        meta_final = metadata
        imp = importance

        # Compute embeddings outside the palace lock (may be CPU/network heavy)
        faiss_emb = None
        if self.use_faiss and self.faiss_store is not None:
            faiss_emb = self.embedding_function([content])[0]

        def _do_store() -> str:
            if self.use_faiss and self.faiss_store is not None:
                self.faiss_store.add(
                    content=content,
                    embedding=faiss_emb,
                    metadata=meta_final,
                    tags=tags_final,
                    memory_id=memory_id,
                )
            elif self.use_chromadb:
                safe_meta = _safe_metadata(meta_final, tags=tags_final)
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
                        "tags": tags_final,
                        "metadata": meta_final,
                        "importance": imp,
                        "created_at": meta_final["created_at"],
                    }
                )

            # Sidecar assignment index (best-effort, never blocks store)
            if meta_final.get("wing") and meta_final.get("room"):
                try:
                    from .wings import WingsManager

                    WingsManager().assign(
                        memory_id,
                        str(meta_final["wing"]),
                        str(meta_final["room"]),
                        note="memory_palace.store",
                    )
                except Exception:
                    pass
            return memory_id

        return self._locked_write(_do_store)

    def store_version(
        self,
        parent_id: str,
        content: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.7,
    ) -> str:
        """Store a new memory version linked to parent (provenance)."""
        meta = dict(metadata or {})
        parent_ver = 1
        # Try to read parent version from store
        for mem in self.get_all_memories():
            if mem.get("id") == parent_id:
                parent_ver = int((mem.get("metadata") or {}).get("version") or 1)
                break
        meta["parent_id"] = parent_id
        meta["version"] = parent_ver + 1
        meta["provenance"] = f"child_of:{parent_id}"
        return self.store(content=content, tags=tags, metadata=meta, importance=importance)

    def update_metadata(self, memory_id: str, metadata_updates: Dict[str, Any]) -> bool:
        """Persist metadata updates (importance, deprecated flags, etc.)."""

        def _do() -> bool:
            if self.use_faiss and self.faiss_store is not None:
                doc = self.faiss_store.docs.get(memory_id)
                if not doc:
                    return False
                meta = dict(doc.get("metadata") or {})
                meta.update(metadata_updates)
                doc["metadata"] = meta
                if "importance" in metadata_updates:
                    doc["importance"] = metadata_updates["importance"]
                self.faiss_store.docs[memory_id] = doc
                self.faiss_store.save()
                return True
            if self.use_chromadb:
                try:
                    existing = self.collection.get(ids=[memory_id])
                    if not existing["ids"]:
                        return False
                    meta = dict(existing["metadatas"][0] or {})
                    meta.update(metadata_updates)
                    tags_str = meta.get("tags", "")
                    tags = (
                        [t for t in str(tags_str).split(",") if t] if tags_str else None
                    )
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

        return bool(self._locked_write(_do))

    def query_semantic(
        self,
        query: str,
        top_k: int = 5,
        n_results: Optional[int] = None,
        tags: Optional[List[str]] = None,
        include_deprecated: bool = False,
        wing: Optional[str] = None,
        room: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict]:
        if n_results is not None:
            top_k = n_results
        _ = kwargs
        # Fetch extra when filtering by tags/wing/room
        need_filter = bool(tags or wing or room)
        fetch_k = top_k * 4 if need_filter else top_k

        def _loc_ok(meta: Dict[str, Any], mem: Optional[Dict] = None) -> bool:
            if wing and str(meta.get("wing") or "").lower() != str(wing).lower():
                # also accept wing: tag
                mem_tags = _parse_tags(meta, mem)
                if f"wing:{wing}".lower() not in mem_tags:
                    return False
            if room and str(meta.get("room") or "").lower() != str(room).lower():
                mem_tags = _parse_tags(meta, mem)
                if f"room:{room}".lower() not in mem_tags:
                    return False
            return True

        if self.use_faiss and self.faiss_store is not None:
            emb = self.embedding_function([query])[0]
            hits = self.faiss_store.search(
                emb, top_k=fetch_k if need_filter else top_k
            )
            out = []
            wanted = {t.lower() for t in tags} if tags else None
            for h in hits:
                meta = h.get("metadata") or {}
                if not include_deprecated and meta.get("deprecated") in (
                    True,
                    "True",
                    "true",
                    1,
                ):
                    continue
                if not _loc_ok(meta, h):
                    continue
                if wanted:
                    mem_tags = {str(t).lower() for t in (h.get("tags") or [])}
                    tag_str = str(meta.get("tags") or "")
                    mem_tags |= {
                        t.strip().lower() for t in tag_str.split(",") if t.strip()
                    }
                    if not wanted.intersection(mem_tags):
                        continue
                out.append(h)
                if len(out) >= top_k:
                    break
            return out

        if self.use_chromadb:
            fetch_n = max(fetch_k, top_k)
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=max(fetch_n, 1),
                )
            except Exception:
                results = {}

            memories: List[Dict] = []
            ids = (results.get("ids") or [[]])[0] if results else []
            docs = (results.get("documents") or [[]])[0] if results else []
            metas = (results.get("metadatas") or [[]])[0] if results else []
            dists = (
                (results.get("distances") or [[None] * len(ids)])[0]
                if results
                else []
            )

            wanted = {t.lower() for t in tags} if tags else None

            for i, memory_id in enumerate(ids):
                metadata = dict(metas[i] or {})
                if not include_deprecated and metadata.get("deprecated") in (
                    True,
                    "True",
                    "true",
                    1,
                ):
                    continue
                if not _loc_ok(metadata):
                    continue
                if wanted:
                    mem_tags = _parse_tags(metadata)
                    if not wanted.intersection(mem_tags):
                        continue
                # Do not mutate collection on read path (races with concurrent stores)
                metadata["last_accessed"] = datetime.now().isoformat()
                memories.append(
                    {
                        "id": memory_id,
                        "content": docs[i],
                        "metadata": metadata,
                        "importance": float(metadata.get("importance", 0.5)),
                        "distance": dists[i] if i < len(dists) else None,
                        "wing": metadata.get("wing"),
                        "room": metadata.get("room"),
                    }
                )
                if len(memories) >= top_k:
                    break
            if memories:
                return memories
            # Fall through to keyword scan when vector query returns empty

        # Keyword fallback (in-memory list + full store scan)
        return self._keyword_search(
            query,
            top_k=top_k,
            tags=tags,
            include_deprecated=include_deprecated,
            wing=wing,
            room=room,
        )

    def _keyword_search(
        self,
        query: str,
        top_k: int = 5,
        tags: Optional[List[str]] = None,
        include_deprecated: bool = False,
        wing: Optional[str] = None,
        room: Optional[str] = None,
    ) -> List[Dict]:
        """Token/substring search over get_all_memories + in-RAM list."""
        results: List[Dict] = []
        query_lower = (query or "").lower().strip()
        tokens = [t for t in re.split(r"\W+", query_lower) if len(t) > 2]
        wanted = {t.lower() for t in tags} if tags else None

        pool: List[Dict[str, Any]] = list(self.memories or [])
        try:
            for m in self.get_all_memories() or []:
                pool.append(m)
        except Exception:
            pass

        seen: set[str] = set()
        for mem in pool:
            mid = str(mem.get("id") or "")
            if mid and mid in seen:
                continue
            if mid:
                seen.add(mid)
            meta = mem.get("metadata") or {}
            if not include_deprecated and meta.get("deprecated") in (
                True,
                "True",
                "true",
                1,
            ):
                continue
            if wing and str(meta.get("wing") or "").lower() != str(wing).lower():
                continue
            if room and str(meta.get("room") or "").lower() != str(room).lower():
                continue
            content = mem.get("content") or ""
            content_l = content.lower()
            if query_lower and query_lower not in content_l:
                if tokens and not any(t in content_l for t in tokens):
                    continue
            if wanted and not wanted.intersection(_parse_tags(meta, mem)):
                continue
            results.append(
                {
                    "id": mem.get("id"),
                    "content": content,
                    "metadata": meta,
                    "importance": mem.get(
                        "importance", meta.get("importance", 0.5)
                    ),
                    "tags": mem.get("tags", []),
                    "wing": meta.get("wing"),
                    "room": meta.get("room"),
                }
            )
            if len(results) >= top_k:
                break
        return results

    def query_by_location(
        self,
        wing: Optional[str] = None,
        room: Optional[str] = None,
        limit: int = 50,
        include_deprecated: bool = False,
    ) -> List[Dict[str, Any]]:
        """Browse palace by wing/room (no semantic query required)."""
        out: List[Dict[str, Any]] = []
        for mem in self.get_all_memories():
            meta = mem.get("metadata") or {}
            if not include_deprecated and meta.get("deprecated") in (
                True,
                "True",
                "true",
                1,
            ):
                continue
            if wing and str(meta.get("wing") or "").lower() != str(wing).lower():
                continue
            if room and str(meta.get("room") or "").lower() != str(room).lower():
                continue
            out.append(
                {
                    **mem,
                    "wing": meta.get("wing"),
                    "room": meta.get("room"),
                    "importance": float(
                        mem.get("importance") or meta.get("importance") or 0.5
                    ),
                }
            )
            if len(out) >= limit:
                break
        return out

    def palace_layout(self) -> Dict[str, Any]:
        """Counts of memories by wing → room (from metadata)."""
        by_wing: Dict[str, Dict[str, int]] = {}
        total = 0
        unassigned = 0
        for mem in self.get_all_memories():
            meta = mem.get("metadata") or {}
            w = str(meta.get("wing") or "")
            r = str(meta.get("room") or "")
            if not w:
                unassigned += 1
                continue
            total += 1
            by_wing.setdefault(w, {})
            by_wing[w][r or "general"] = by_wing[w].get(r or "general", 0) + 1
        try:
            from .wings import WingsManager

            catalog = WingsManager().list_wings()
        except Exception:
            catalog = {}
        return {
            "total_located": total,
            "unassigned": unassigned,
            "by_wing": by_wing,
            "catalog": catalog,
        }

    def cluster_memories(
        self,
        limit: int = 200,
        max_clusters: int = 8,
        *,
        method: str = "auto",
    ) -> List[Dict[str, Any]]:
        """
        Cluster memories.

        method:
          - auto: embedding k-means if possible, else hierarchical tags, else flat tags
          - embedding: numpy k-means on embeddings
          - wing: group by wing/room
          - tag: group by task_type/tag (legacy)
        """
        mems = self.get_all_memories()[:limit]
        if not mems:
            return []

        method = (method or "auto").lower()
        if method == "auto":
            emb = self._cluster_by_embedding(mems, max_clusters=max_clusters)
            if emb:
                return emb
            wing_c = self._cluster_by_wing_room(mems, max_clusters=max_clusters)
            if wing_c:
                return wing_c
            return self._cluster_by_tag(mems, max_clusters=max_clusters)
        if method == "embedding":
            return self._cluster_by_embedding(mems, max_clusters=max_clusters) or self._cluster_by_tag(
                mems, max_clusters=max_clusters
            )
        if method in {"wing", "wings", "room"}:
            return self._cluster_by_wing_room(mems, max_clusters=max_clusters)
        return self._cluster_by_tag(mems, max_clusters=max_clusters)

    def _cluster_by_tag(
        self, mems: List[Dict[str, Any]], max_clusters: int = 8
    ) -> List[Dict[str, Any]]:
        buckets: Dict[str, List[Dict[str, Any]]] = {}
        for m in mems:
            meta = m.get("metadata") or {}
            key = (
                str(meta.get("task_type") or "")
                or (str(meta.get("tags") or "").split(",")[0].strip())
                or "general"
            )
            if not key:
                key = "general"
            buckets.setdefault(key, []).append(m)
        return self._format_clusters(buckets, max_clusters, method="tag")

    def _cluster_by_wing_room(
        self, mems: List[Dict[str, Any]], max_clusters: int = 8
    ) -> List[Dict[str, Any]]:
        buckets: Dict[str, List[Dict[str, Any]]] = {}
        for m in mems:
            meta = m.get("metadata") or {}
            w = str(meta.get("wing") or "unassigned")
            r = str(meta.get("room") or "general")
            key = f"{w}/{r}"
            buckets.setdefault(key, []).append(m)
        return self._format_clusters(buckets, max_clusters, method="wing")

    def _cluster_by_embedding(
        self, mems: List[Dict[str, Any]], max_clusters: int = 8
    ) -> List[Dict[str, Any]]:
        """Simple k-means over embeddings (numpy only; no sklearn required)."""
        if len(mems) < 3:
            return []
        try:
            import numpy as np
        except ImportError:
            return []

        texts = [str(m.get("content") or "")[:2000] for m in mems]
        try:
            vectors = self.embedding_function(texts)
        except Exception:
            return []
        if not vectors or len(vectors) != len(mems):
            return []

        X = np.asarray(vectors, dtype=float)
        if X.ndim != 2 or X.shape[0] < 3:
            return []
        # Normalize
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        X = X / norms

        k = max(2, min(max_clusters, X.shape[0] // 2, max_clusters))
        # Init centers: spread indices
        idx = np.linspace(0, X.shape[0] - 1, k, dtype=int)
        centers = X[idx].copy()
        labels = np.zeros(X.shape[0], dtype=int)
        for _ in range(15):
            # Assign
            # cosine distance via dot (vectors normalized)
            sims = X @ centers.T
            labels = np.argmax(sims, axis=1)
            new_centers = centers.copy()
            for j in range(k):
                members = X[labels == j]
                if len(members) == 0:
                    continue
                c = members.mean(axis=0)
                n = np.linalg.norm(c)
                new_centers[j] = c / n if n else c
            if np.allclose(new_centers, centers, atol=1e-4):
                centers = new_centers
                break
            centers = new_centers

        buckets: Dict[str, List[Dict[str, Any]]] = {}
        for i, m in enumerate(mems):
            key = f"emb-{int(labels[i])}"
            buckets.setdefault(key, []).append(m)

        clusters = self._format_clusters(buckets, max_clusters, method="embedding")
        # Label clusters with dominant wing/room or task_type
        for c in clusters:
            items = [m for m in mems if m.get("id") in set(c.get("ids") or [])]
            wings = [
                str((m.get("metadata") or {}).get("wing") or "")
                for m in items
                if (m.get("metadata") or {}).get("wing")
            ]
            rooms = [
                str((m.get("metadata") or {}).get("room") or "")
                for m in items
                if (m.get("metadata") or {}).get("room")
            ]
            if wings:
                # most common
                from collections import Counter

                w = Counter(wings).most_common(1)[0][0]
                r = Counter(rooms).most_common(1)[0][0] if rooms else "general"
                c["label"] = f"{w}/{r}"
                c["cluster"] = f"emb:{w}/{r}"
            else:
                c["label"] = c.get("cluster")
        return clusters

    def _format_clusters(
        self,
        buckets: Dict[str, List[Dict[str, Any]]],
        max_clusters: int,
        method: str,
    ) -> List[Dict[str, Any]]:
        clusters = []
        for key, items in sorted(buckets.items(), key=lambda kv: -len(kv[1]))[
            :max_clusters
        ]:
            sample = (items[0].get("content") or "")[:160]
            meta0 = items[0].get("metadata") or {}
            clusters.append(
                {
                    "cluster": key,
                    "method": method,
                    "size": len(items),
                    "sample": sample,
                    "ids": [i.get("id") for i in items[:10]],
                    "wing": meta0.get("wing"),
                    "room": meta0.get("room"),
                    "avg_importance": round(
                        sum(float(i.get("importance") or 0.5) for i in items)
                        / max(1, len(items)),
                        3,
                    ),
                }
            )
        return clusters

    def suggest_rooms_from_clusters(
        self,
        *,
        limit: int = 200,
        max_clusters: int = 8,
        min_size: int = 3,
        method: str = "auto",
    ) -> List[Dict[str, Any]]:
        """Map clusters → suggested wing/room promotions (P3)."""
        from .wings import WingsManager

        wm = WingsManager()
        clusters = self.cluster_memories(
            limit=limit, max_clusters=max_clusters, method=method
        )
        suggestions = []
        for c in clusters:
            s = wm.suggest_room_from_cluster(c, min_size=min_size)
            if s:
                suggestions.append(s)
        return suggestions

    def auto_promote_rooms(
        self,
        *,
        apply: bool = False,
        reassign: bool = False,
        limit: int = 200,
        max_clusters: int = 8,
        min_size: int = 3,
        method: str = "auto",
    ) -> Dict[str, Any]:
        """
        Promote suggested rooms into the wings catalog.

        apply=False → dry-run suggestions only
        reassign=True → also set wing/room metadata on cluster member memories
        """
        from .wings import WingsManager

        wm = WingsManager()
        suggestions = self.suggest_rooms_from_clusters(
            limit=limit,
            max_clusters=max_clusters,
            min_size=min_size,
            method=method,
        )
        promoted = []
        reassigned = 0
        if apply:
            for s in suggestions:
                if s.get("already_in_catalog"):
                    continue
                entry = wm.ensure_room(
                    s["wing"],
                    s["room"],
                    note=s.get("reason") or "cluster_promote",
                )
                promoted.append(entry)
                if reassign:
                    for mid in s.get("ids") or []:
                        if not mid:
                            continue
                        if self.update_metadata(
                            str(mid),
                            {"wing": s["wing"], "room": s["room"]},
                        ):
                            try:
                                wm.assign(
                                    str(mid),
                                    s["wing"],
                                    s["room"],
                                    note="auto_promote_reassign",
                                )
                            except Exception:
                                pass
                            reassigned += 1
        return {
            "apply": apply,
            "reassign": reassign,
            "suggestions": suggestions,
            "promoted": promoted,
            "promoted_count": len(promoted),
            "reassigned": reassigned,
            "catalog": wm.list_wings(),
        }

    def browser_snapshot(
        self,
        *,
        wing: Optional[str] = None,
        room: Optional[str] = None,
        limit: int = 12,
    ) -> Dict[str, Any]:
        """Dashboard / web browser payload for the Memory Palace (P3)."""
        from .wings import WingsManager

        wm = WingsManager()
        layout = self.palace_layout()
        clusters = self.cluster_memories(limit=120, max_clusters=6, method="auto")
        suggestions = self.suggest_rooms_from_clusters(
            limit=120, max_clusters=6, min_size=2
        )
        browse = self.query_by_location(wing=wing, room=room, limit=limit)
        # Top wings by count
        wing_totals = {
            w: sum(rooms.values()) for w, rooms in (layout.get("by_wing") or {}).items()
        }
        top_wings = sorted(wing_totals.items(), key=lambda kv: -kv[1])[:8]
        return {
            "layout": layout,
            "top_wings": [{"wing": w, "count": c} for w, c in top_wings],
            "clusters": clusters,
            "suggestions": suggestions[:8],
            "browse": {
                "wing": wing,
                "room": room,
                "items": [
                    {
                        "id": (m.get("id") or "")[:20],
                        "wing": m.get("wing") or (m.get("metadata") or {}).get("wing"),
                        "room": m.get("room") or (m.get("metadata") or {}).get("room"),
                        "content": ((m.get("content") or "")[:100]).replace("\n", " "),
                    }
                    for m in browse
                ],
            },
            "promotions": wm.recent_promotions(8),
            "stats": wm.stats(),
        }

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
        if self.use_faiss and self.faiss_store is not None:
            return list(self.faiss_store.docs.values())
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
        if self.use_faiss and self.faiss_store is not None:
            st = self.faiss_store.stats()
            return {
                "total_memories": st.get("count", 0),
                "using_chromadb": False,
                "using_faiss": True,
                "faiss": st,
                "embedding": getattr(self, "embedding_id", "unknown"),
            }
        if self.use_chromadb:
            count = self.collection.count()
        else:
            count = len(self.memories)
        return {
            "total_memories": count,
            "using_chromadb": self.use_chromadb,
            "using_faiss": False,
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
