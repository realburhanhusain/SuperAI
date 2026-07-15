"""
Local embedding providers for Memory Palace (Phase 3 / F3.1).

Priority:
1. SUPERAI_EMBEDDING_MODEL / config embedding_model
2. sentence-transformers EmbeddingGemma or all-MiniLM fallback
3. Deterministic hash embedding (always available offline)

Embedding functions implement name() + __call__(texts) -> list[list[float]].
Used by the default pgvector Memory Palace backend (and optional FAISS).
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
from typing import Any, List, Optional, Sequence

logger = logging.getLogger(__name__)

# Common EmbeddingGemma HF ids (user may override)
DEFAULT_GEMMA_CANDIDATES = [
    "google/embeddinggemma-300m",
    "google/embedding-gemma-300m",
]
DEFAULT_ST_FALLBACK = "sentence-transformers/all-MiniLM-L6-v2"
HASH_DIM = 384


def _normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


class HashEmbeddingFunction:
    """Offline deterministic bag-of-hashes embedding (no network)."""

    def __init__(self, dim: int = HASH_DIM):
        self.dim = dim
        self._name = "superai-hash-embedding"

    def name(self) -> str:
        return self._name

    def __call__(self, input: Sequence[str]) -> List[List[float]]:
        out: List[List[float]] = []
        for text in input:
            vec = [0.0] * self.dim
            tokens = (text or "").lower().split()
            if not tokens:
                tokens = [""]
            for tok in tokens:
                h = hashlib.sha256(tok.encode("utf-8")).digest()
                # Use multiple bytes for index + sign
                idx = int.from_bytes(h[:4], "little") % self.dim
                sign = 1.0 if h[4] % 2 == 0 else -1.0
                vec[idx] += sign
            out.append(_normalize(vec))
        return out


class SentenceTransformerEmbeddingFunction:
    """Wrap sentence-transformers model for Chroma-compatible API."""

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self._name = f"st:{model_name}"

    def name(self) -> str:
        return self._name

    def __call__(self, input: Sequence[str]) -> List[List[float]]:
        vectors = self._model.encode(
            list(input),
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return [v.tolist() for v in vectors]


def resolve_embedding_model_name() -> str:
    return (
        os.getenv("SUPERAI_EMBEDDING_MODEL")
        or os.getenv("SUPERAI_EMBEDDING")
        or "auto"
    )


def create_embedding_function(
    model_name: Optional[str] = None,
    prefer_hash: bool = False,
) -> Any:
    """
    Build an embedding function.

    model_name:
      - "auto" | None: try EmbeddingGemma, then MiniLM, then hash
      - "hash": force hash
      - any HF / ST model id
    """
    name = (model_name or resolve_embedding_model_name() or "auto").strip()

    if prefer_hash or name.lower() in {"hash", "local-hash", "offline"}:
        logger.info("Using hash embedding function (offline)")
        return HashEmbeddingFunction()

    if name.lower() == "auto":
        candidates = DEFAULT_GEMMA_CANDIDATES + [DEFAULT_ST_FALLBACK]
    else:
        candidates = [name]

    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        logger.warning(
            "sentence-transformers not installed; using hash embeddings. "
            "pip install sentence-transformers for EmbeddingGemma/MiniLM."
        )
        return HashEmbeddingFunction()

    last_err: Optional[Exception] = None
    for cand in candidates:
        try:
            fn = SentenceTransformerEmbeddingFunction(cand)
            logger.info("Loaded embedding model: %s", cand)
            return fn
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning("Failed to load embedding model %s: %s", cand, e)

    logger.warning(
        "All embedding models failed (%s); using hash embeddings", last_err
    )
    return HashEmbeddingFunction()


def describe_embedding(fn: Any) -> str:
    if hasattr(fn, "name"):
        try:
            return str(fn.name())
        except Exception:
            pass
    return type(fn).__name__
