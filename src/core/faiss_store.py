"""
FAISS / numpy vector memory backend (N5).

Uses faiss-cpu when installed; otherwise a pure-Python cosine index
persisted as JSON (works offline without extra deps).
"""

from __future__ import annotations

import json
import math
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .store_lock import atomic_write_json, store_lock

try:
    import faiss  # type: ignore

    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False


def _normalize(vec: List[float]) -> List[float]:
    n = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / n for x in vec]


class FaissMemoryStore:
    """
    Simple id→document store with cosine search.
    Backend: faiss IndexFlatIP if available, else brute-force.
    """

    def __init__(self, root: Optional[Path] = None, dim: int = 384):
        self.root = Path(root or (Path.home() / ".superai" / "memory_faiss"))
        self.root.mkdir(parents=True, exist_ok=True)
        self.dim = dim
        self.meta_path = self.root / "docs.json"
        self.index_path = self.root / "index.faiss"
        self.docs: Dict[str, Dict[str, Any]] = {}
        self.ids: List[str] = []
        self.vectors: List[List[float]] = []
        self._index = None
        self._index_type = "none"
        self._load()

    def _load(self) -> None:
        if self.meta_path.exists():
            try:
                data = json.loads(self.meta_path.read_text(encoding="utf-8"))
                self.docs = data.get("docs") or {}
                self.ids = data.get("ids") or []
                self.vectors = data.get("vectors") or []
                if self.vectors:
                    self.dim = len(self.vectors[0])
            except (OSError, json.JSONDecodeError):
                pass
        if HAS_FAISS and self.vectors:
            self._rebuild_faiss()

    def save(self) -> None:
        payload = {
            "docs": self.docs,
            "ids": self.ids,
            "vectors": self.vectors,
            "updated_at": time.time(),
            "backend": "faiss" if HAS_FAISS else "numpy-brute",
        }
        # Atomic JSON write under store lock (caller may already hold palace lock)
        with store_lock(self.root, name="faiss.lock", timeout=45.0):
            atomic_write_json(self.meta_path, payload)
            if HAS_FAISS and self._index is not None:
                try:
                    # write to tmp then replace
                    tmp_idx = self.index_path.with_suffix(
                        f".{os.getpid()}.tmp.faiss"
                    )
                    faiss.write_index(self._index, str(tmp_idx))
                    os.replace(str(tmp_idx), str(self.index_path))
                except Exception:
                    pass

    def _index_kind(self) -> str:
        """flat (default) | hnsw — via SUPERAI_FAISS_INDEX=hnsw|flat"""
        kind = (os.getenv("SUPERAI_FAISS_INDEX") or "flat").lower().strip()
        if kind in {"hnsw", "hns"}:
            return "hnsw"
        return "flat"

    def _rebuild_faiss(self) -> None:
        if not HAS_FAISS or not self.vectors:
            self._index = None
            return
        import numpy as np

        arr = np.array(self.vectors, dtype="float32")
        kind = self._index_kind()
        if kind == "hnsw" and hasattr(faiss, "IndexHNSWFlat"):
            # Inner-product metric for normalized vectors (cosine-like)
            try:
                m = int(os.getenv("SUPERAI_HNSW_M") or "32")
            except ValueError:
                m = 32
            try:
                ef_c = int(os.getenv("SUPERAI_HNSW_EF_CONSTRUCTION") or "200")
            except ValueError:
                ef_c = 200
            try:
                ef_s = int(os.getenv("SUPERAI_HNSW_EF_SEARCH") or "64")
            except ValueError:
                ef_s = 64
            # METRIC_INNER_PRODUCT when available
            metric = getattr(faiss, "METRIC_INNER_PRODUCT", 0)
            try:
                index = faiss.IndexHNSWFlat(self.dim, m, metric)
            except TypeError:
                index = faiss.IndexHNSWFlat(self.dim, m)
            try:
                index.hnsw.efConstruction = ef_c
                index.hnsw.efSearch = ef_s
            except Exception:
                pass
            index.add(arr)
            self._index = index
            self._index_type = "hnsw"
        else:
            index = faiss.IndexFlatIP(self.dim)
            index.add(arr)
            self._index = index
            self._index_type = "flat"

    def add(
        self,
        content: str,
        embedding: Sequence[float],
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        memory_id: Optional[str] = None,
    ) -> str:
        mid = memory_id or f"f-{uuid.uuid4().hex[:12]}"
        vec = _normalize(list(embedding))
        if self.dim and len(vec) != self.dim and self.vectors:
            # pad/truncate
            if len(vec) < self.dim:
                vec = vec + [0.0] * (self.dim - len(vec))
            else:
                vec = vec[: self.dim]
        elif not self.vectors:
            self.dim = len(vec)

        def _do() -> str:
            self.docs[mid] = {
                "id": mid,
                "content": content,
                "metadata": metadata or {},
                "tags": tags or [],
                "importance": float((metadata or {}).get("importance") or 0.7),
            }
            self.ids.append(mid)
            self.vectors.append(vec)
            if HAS_FAISS:
                self._rebuild_faiss()
            # save without nested double-lock: write files only
            payload = {
                "docs": self.docs,
                "ids": self.ids,
                "vectors": self.vectors,
                "updated_at": time.time(),
                "backend": "faiss" if HAS_FAISS else "numpy-brute",
            }
            atomic_write_json(self.meta_path, payload)
            if HAS_FAISS and self._index is not None:
                try:
                    tmp_idx = self.index_path.with_suffix(
                        f".{os.getpid()}.tmp.faiss"
                    )
                    faiss.write_index(self._index, str(tmp_idx))
                    os.replace(str(tmp_idx), str(self.index_path))
                except Exception:
                    pass
            return mid

        with store_lock(self.root, name="faiss.lock", timeout=45.0):
            return _do()

    def search(
        self, query_embedding: Sequence[float], top_k: int = 8
    ) -> List[Dict[str, Any]]:
        if not self.vectors:
            return []
        q = _normalize(list(query_embedding))
        if len(q) != self.dim:
            if len(q) < self.dim:
                q = q + [0.0] * (self.dim - len(q))
            else:
                q = q[: self.dim]

        if HAS_FAISS and self._index is not None:
            import numpy as np

            D, I = self._index.search(np.array([q], dtype="float32"), min(top_k, len(self.ids)))
            out = []
            for score, idx in zip(D[0], I[0]):
                if idx < 0 or idx >= len(self.ids):
                    continue
                mid = self.ids[idx]
                doc = dict(self.docs.get(mid) or {})
                doc["distance"] = float(1.0 - score)  # IP on normalized ≈ cosine
                out.append(doc)
            return out

        # Brute force cosine
        scored = []
        for i, v in enumerate(self.vectors):
            score = sum(a * b for a, b in zip(q, v))
            mid = self.ids[i]
            doc = dict(self.docs.get(mid) or {})
            doc["distance"] = float(1.0 - score)
            scored.append((score, doc))
        scored.sort(key=lambda x: -x[0])
        return [d for _, d in scored[:top_k]]

    def stats(self) -> Dict[str, Any]:
        return {
            "backend": "faiss" if HAS_FAISS else "brute-force",
            "faiss_installed": HAS_FAISS,
            "index_type": getattr(self, "_index_type", "none"),
            "index_kind_requested": self._index_kind(),
            "hnsw_m": os.getenv("SUPERAI_HNSW_M"),
            "hnsw_ef_construction": os.getenv("SUPERAI_HNSW_EF_CONSTRUCTION"),
            "hnsw_ef_search": os.getenv("SUPERAI_HNSW_EF_SEARCH"),
            "count": len(self.ids),
            "dim": self.dim,
            "path": str(self.root),
            "note": (
                "Set SUPERAI_MEMORY_BACKEND=faiss and SUPERAI_FAISS_INDEX=hnsw "
                "for HNSW; SUPERAI_HNSW_M / EF_* control graph quality."
            ),
        }


def use_faiss_backend() -> bool:
    return os.getenv("SUPERAI_MEMORY_BACKEND", "").lower() in {
        "faiss",
        "numpy",
        "vector",
    }
