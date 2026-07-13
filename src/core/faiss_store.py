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
        self.meta_path.write_text(json.dumps(payload), encoding="utf-8")
        if HAS_FAISS and self._index is not None:
            try:
                faiss.write_index(self._index, str(self.index_path))
            except Exception:
                pass

    def _rebuild_faiss(self) -> None:
        if not HAS_FAISS or not self.vectors:
            self._index = None
            return
        import numpy as np

        arr = np.array(self.vectors, dtype="float32")
        index = faiss.IndexFlatIP(self.dim)
        index.add(arr)
        self._index = index

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
        self.save()
        return mid

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
            "count": len(self.ids),
            "dim": self.dim,
            "path": str(self.root),
        }


def use_faiss_backend() -> bool:
    return os.getenv("SUPERAI_MEMORY_BACKEND", "").lower() in {
        "faiss",
        "numpy",
        "vector",
    }
