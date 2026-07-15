"""
pgvector-backed Memory Palace store (default vector backend).

- PostgreSQL + pgvector: real VECTOR column + cosine distance (multi-session safe)
- SQLite (default offline / tests): same schema with JSON embeddings + brute-force cosine

Env:
  SUPERAI_MEMORY_DSN   e.g. postgresql+psycopg://user:pass@localhost/superai
                       or sqlite:////path/to/palace.sqlite
  SUPERAI_MEMORY_BACKEND=pgvector|faiss|memory  (default pgvector)
"""

from __future__ import annotations

import json
import math
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import (
    Float,
    String,
    Text,
    create_engine,
    delete,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.types import TypeDecorator

try:
    from pgvector.sqlalchemy import Vector

    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    Vector = None  # type: ignore


def _normalize(vec: Sequence[float]) -> List[float]:
    n = math.sqrt(sum(float(x) * float(x) for x in vec)) or 1.0
    return [float(x) / n for x in vec]


def _cosine_distance(a: Sequence[float], b: Sequence[float]) -> float:
    # both expected normalized → distance = 1 - dot
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    return 1.0 - float(dot)


class JsonEmbedding(TypeDecorator):
    """JSON list of floats (SQLite / fallback when Vector unavailable)."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps([float(x) for x in value])

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, list):
            return [float(x) for x in value]
        return [float(x) for x in json.loads(value)]


class JsonDict(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return "{}"
        return json.dumps(value, default=str)

    def process_result_value(self, value, dialect):
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        return json.loads(value)


class JsonList(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return "[]"
        return json.dumps(list(value), default=str)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return json.loads(value)


class Base(DeclarativeBase):
    pass


# Cache ORM models so we don't redefine MemoryRow per store instance
_MODEL_CACHE: Dict[str, Any] = {}


def _default_dsn(persist_directory: Optional[str] = None) -> str:
    env = (os.getenv("SUPERAI_MEMORY_DSN") or os.getenv("SUPERAI_DATABASE_URL") or "").strip()
    if env:
        return env
    root = Path(persist_directory or (Path.home() / ".superai" / "memory"))
    root.mkdir(parents=True, exist_ok=True)
    # Absolute SQLite URL (4 slashes after scheme for absolute path on Windows/Unix)
    db = (root / "palace.sqlite").resolve()
    return f"sqlite:///{db.as_posix()}"


def use_pgvector_backend() -> bool:
    """Default is pgvector; explicit faiss/memory opt out."""
    backend = (os.getenv("SUPERAI_MEMORY_BACKEND") or "pgvector").lower().strip()
    if backend in {"faiss", "numpy", "vector", "memory", "mem", "ram"}:
        return False
    if backend in {"chroma", "chromadb"}:
        # chroma removed — treat as pgvector
        return True
    return True  # default pgvector


def use_memory_only_backend() -> bool:
    return (os.getenv("SUPERAI_MEMORY_BACKEND") or "").lower().strip() in {
        "memory",
        "mem",
        "ram",
    }


class PgvectorMemoryStore:
    """
    Concurrent-safe memory store via SQL (Postgres+pgvector preferred).
    """

    def __init__(
        self,
        dsn: Optional[str] = None,
        *,
        persist_directory: Optional[str] = None,
        dim: int = 384,
        collection: str = "superai_memories",
    ):
        self.dsn = dsn or _default_dsn(persist_directory)
        self.dim = dim
        self.collection = collection
        self.is_postgres = self.dsn.startswith("postgresql") or self.dsn.startswith(
            "postgres"
        )
        self.use_native_vector = bool(self.is_postgres and HAS_PGVECTOR)

        connect_args: Dict[str, Any] = {}
        if self.dsn.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        self.engine: Engine = create_engine(
            self.dsn,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self.SessionLocal = sessionmaker(
            self.engine, expire_on_commit=False, future=True
        )
        self._Memory = self._build_model()
        self._ensure_schema()

    def _build_model(self):
        dim = self.dim
        use_vec = self.use_native_vector
        key = f"{'vec' if use_vec else 'json'}:{dim}"
        if key in _MODEL_CACHE:
            return _MODEL_CACHE[key]
        emb_type = Vector(dim) if use_vec else JsonEmbedding()
        cls_name = f"MemoryRow_{key.replace(':', '_').replace('-', '_')}"

        MemoryRow = type(
            cls_name,
            (Base,),
            {
                "__tablename__": "superai_memories",
                "__table_args__": {"extend_existing": True},
                "id": mapped_column(String(128), primary_key=True),
                "content": mapped_column(Text, nullable=False),
                "embedding": mapped_column(emb_type, nullable=False),
                "metadata_json": mapped_column("metadata", JsonDict, default=dict),
                "tags": mapped_column(JsonList, default=list),
                "importance": mapped_column(Float, default=0.7),
                "wing": mapped_column(String(128), nullable=True),
                "room": mapped_column(String(128), nullable=True),
                "created_at": mapped_column(String(64), nullable=True),
                "last_accessed": mapped_column(String(64), nullable=True),
            },
        )
        _MODEL_CACHE[key] = MemoryRow
        return MemoryRow

    def _ensure_schema(self) -> None:
        if self.use_native_vector:
            with self.engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(self.engine, tables=[self._Memory.__table__])
        if self.use_native_vector:
            # Best-effort HNSW index (pgvector >= 0.5)
            try:
                with self.engine.begin() as conn:
                    conn.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS superai_memories_embedding_hnsw "
                            "ON superai_memories USING hnsw (embedding vector_cosine_ops)"
                        )
                    )
            except Exception:
                try:
                    with self.engine.begin() as conn:
                        conn.execute(
                            text(
                                "CREATE INDEX IF NOT EXISTS superai_memories_embedding_ivfflat "
                                "ON superai_memories USING ivfflat (embedding vector_cosine_ops) "
                                "WITH (lists = 100)"
                            )
                        )
                except Exception:
                    pass

    def _row_to_doc(self, row) -> Dict[str, Any]:
        meta = dict(row.metadata_json or {})
        tags = list(row.tags or [])
        return {
            "id": row.id,
            "content": row.content,
            "metadata": meta,
            "tags": tags,
            "importance": float(row.importance if row.importance is not None else 0.7),
            "wing": row.wing or meta.get("wing"),
            "room": row.room or meta.get("room"),
            "created_at": row.created_at or meta.get("created_at"),
        }

    def add(
        self,
        content: str,
        embedding: Sequence[float],
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        memory_id: Optional[str] = None,
    ) -> str:
        mid = memory_id or f"pg-{uuid.uuid4().hex[:12]}"
        vec = _normalize(list(embedding))
        if len(vec) != self.dim:
            if len(vec) < self.dim:
                vec = vec + [0.0] * (self.dim - len(vec))
            else:
                vec = vec[: self.dim]
        meta = dict(metadata or {})
        tags_l = list(tags or [])
        importance = float(meta.get("importance") or 0.7)
        wing = meta.get("wing")
        room = meta.get("room")
        created = meta.get("created_at")
        last_acc = meta.get("last_accessed") or created

        with self.SessionLocal() as session:
            row = self._Memory(
                id=mid,
                content=content,
                embedding=vec,
                metadata_json=meta,
                tags=tags_l,
                importance=importance,
                wing=str(wing) if wing else None,
                room=str(room) if room else None,
                created_at=str(created) if created else None,
                last_accessed=str(last_acc) if last_acc else None,
            )
            session.merge(row)
            session.commit()
        return mid

    def update_metadata(self, memory_id: str, metadata_updates: Dict[str, Any]) -> bool:
        with self.SessionLocal() as session:
            row = session.get(self._Memory, memory_id)
            if not row:
                return False
            meta = dict(row.metadata_json or {})
            meta.update(metadata_updates)
            row.metadata_json = meta
            if "importance" in metadata_updates:
                row.importance = float(metadata_updates["importance"])
            if "wing" in metadata_updates:
                row.wing = str(metadata_updates["wing"]) if metadata_updates["wing"] else None
            if "room" in metadata_updates:
                row.room = str(metadata_updates["room"]) if metadata_updates["room"] else None
            if "last_accessed" in metadata_updates:
                row.last_accessed = str(metadata_updates["last_accessed"])
            if "tags" in metadata_updates:
                t = metadata_updates["tags"]
                if isinstance(t, str):
                    row.tags = [x for x in t.split(",") if x]
                elif isinstance(t, list):
                    row.tags = list(t)
            session.commit()
            return True

    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        with self.SessionLocal() as session:
            row = session.get(self._Memory, memory_id)
            return self._row_to_doc(row) if row else None

    def delete(self, memory_id: str) -> bool:
        with self.SessionLocal() as session:
            res = session.execute(
                delete(self._Memory).where(self._Memory.id == memory_id)
            )
            session.commit()
            return (res.rowcount or 0) > 0

    def get_all(self, limit: int = 50_000) -> List[Dict[str, Any]]:
        with self.SessionLocal() as session:
            rows = session.execute(select(self._Memory).limit(limit)).scalars().all()
            return [self._row_to_doc(r) for r in rows]

    def count(self) -> int:
        from sqlalchemy import func

        with self.SessionLocal() as session:
            return int(
                session.scalar(select(func.count()).select_from(self._Memory)) or 0
            )

    def search(
        self,
        query_embedding: Sequence[float],
        top_k: int = 8,
        *,
        wing: Optional[str] = None,
        room: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        q = _normalize(list(query_embedding))
        if len(q) != self.dim:
            if len(q) < self.dim:
                q = q + [0.0] * (self.dim - len(q))
            else:
                q = q[: self.dim]

        if self.use_native_vector:
            return self._search_pg(q, top_k, wing=wing, room=room)
        return self._search_brute(q, top_k, wing=wing, room=room)

    def _search_pg(
        self,
        q: List[float],
        top_k: int,
        *,
        wing: Optional[str],
        room: Optional[str],
    ) -> List[Dict[str, Any]]:
        # cosine distance operator <=>
        sql = (
            "SELECT id, content, metadata, tags, importance, wing, room, created_at, "
            "embedding <=> :q AS distance "
            "FROM superai_memories WHERE 1=1 "
        )
        params: Dict[str, Any] = {"q": str(q), "k": top_k}
        if wing:
            sql += " AND lower(coalesce(wing,'')) = lower(:wing) "
            params["wing"] = wing
        if room:
            sql += " AND lower(coalesce(room,'')) = lower(:room) "
            params["room"] = room
        sql += " ORDER BY embedding <=> :q LIMIT :k"

        # pgvector accepts vector literal
        vec_lit = "[" + ",".join(str(float(x)) for x in q) + "]"
        params["q"] = vec_lit

        out: List[Dict[str, Any]] = []
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), params)
            for row in result.mappings():
                meta = row["metadata"]
                if isinstance(meta, str):
                    meta = json.loads(meta)
                tags = row["tags"]
                if isinstance(tags, str):
                    tags = json.loads(tags)
                out.append(
                    {
                        "id": row["id"],
                        "content": row["content"],
                        "metadata": meta or {},
                        "tags": tags or [],
                        "importance": float(row["importance"] or 0.7),
                        "wing": row["wing"],
                        "room": row["room"],
                        "distance": float(row["distance"])
                        if row["distance"] is not None
                        else None,
                    }
                )
        return out

    def _search_brute(
        self,
        q: List[float],
        top_k: int,
        *,
        wing: Optional[str],
        room: Optional[str],
    ) -> List[Dict[str, Any]]:
        with self.SessionLocal() as session:
            rows = session.execute(select(self._Memory)).scalars().all()
            scored: List[Tuple[float, Any]] = []
            for row in rows:
                if wing and str(row.wing or "").lower() != str(wing).lower():
                    continue
                if room and str(row.room or "").lower() != str(room).lower():
                    continue
                emb = row.embedding
                if not emb:
                    continue
                if len(emb) != len(q):
                    emb_n = list(emb)
                    if len(emb_n) < len(q):
                        emb_n = emb_n + [0.0] * (len(q) - len(emb_n))
                    else:
                        emb_n = emb_n[: len(q)]
                else:
                    emb_n = list(emb)
                dist = _cosine_distance(q, emb_n)
                scored.append((dist, row))
            scored.sort(key=lambda x: x[0])
            out = []
            for dist, row in scored[:top_k]:
                doc = self._row_to_doc(row)
                doc["distance"] = dist
                out.append(doc)
            return out

    def stats(self) -> Dict[str, Any]:
        n = self.count()
        return {
            "backend": "pgvector" if self.use_native_vector else "sql-cosine",
            "dsn_kind": "postgresql" if self.is_postgres else "sqlite",
            "native_vector": self.use_native_vector,
            "count": n,
            "dim": self.dim,
            "has_pgvector_lib": HAS_PGVECTOR,
            "updated_at": time.time(),
        }
