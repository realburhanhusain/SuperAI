"""
Knowledge graph foundation (Memory Roadmap P0.1 → P1 / Cognee gap 1).

Stores entity nodes and directed edges alongside the Memory Palace (default:
SQLite file under ``~/.superai/memory/kg.sqlite``). Same process-lock discipline
as the palace. Postgres DSN support mirrors pgvector_store when
``SUPERAI_KG_DSN`` or ``SUPERAI_MEMORY_DSN`` is a Postgres URL.

Does **not** replace MemoryPalace — chunks stay there; nodes can link via
``source_memory_id``.
"""

from __future__ import annotations

import json
import os
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

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

from .store_lock import store_lock


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "n") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


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


class Base(DeclarativeBase):
    pass


class KGNodeRow(Base):
    __tablename__ = "kg_nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    type: Mapped[str] = mapped_column(String(128), index=True, default="Entity")
    name: Mapped[str] = mapped_column(String(512), index=True, default="")
    properties: Mapped[dict] = mapped_column(JsonDict, default=dict)
    source_memory_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    dataset_id: Mapped[str] = mapped_column(String(128), index=True, default="default")
    wing: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    room: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), default=_now)
    updated_at: Mapped[str] = mapped_column(String(64), default=_now)


class KGEdgeRow(Base):
    __tablename__ = "kg_edges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    from_id: Mapped[str] = mapped_column(String(64), index=True)
    to_id: Mapped[str] = mapped_column(String(64), index=True)
    relation: Mapped[str] = mapped_column(String(128), index=True, default="RELATED_TO")
    properties: Mapped[dict] = mapped_column(JsonDict, default=dict)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    source_memory_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    dataset_id: Mapped[str] = mapped_column(String(128), index=True, default="default")
    created_at: Mapped[str] = mapped_column(String(64), default=_now)


def default_kg_path() -> Path:
    root = Path(os.path.expanduser("~/.superai/memory"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "kg.sqlite"


def resolve_kg_dsn(explicit: Optional[str] = None) -> str:
    """
    Resolve SQLAlchemy URL for the knowledge graph.

    Priority: explicit → SUPERAI_KG_DSN → SUPERAI_MEMORY_DSN (if postgres) →
    sqlite under ~/.superai/memory/kg.sqlite
    """
    if explicit:
        return explicit
    kg = (os.getenv("SUPERAI_KG_DSN") or "").strip()
    if kg:
        return kg
    mem = (os.getenv("SUPERAI_MEMORY_DSN") or "").strip()
    if mem.startswith("postgresql") or mem.startswith("postgres"):
        # Separate schema/table names (kg_*) avoid clashing with superai_memories
        return mem
    path = default_kg_path()
    # four slashes for absolute path on Windows
    return f"sqlite:///{path.as_posix()}"


class KnowledgeGraph:
    """Entity–relation graph with upsert + BFS path query."""

    def __init__(
        self,
        dsn: Optional[str] = None,
        *,
        lock_root: Optional[Path] = None,
    ):
        self.dsn = resolve_kg_dsn(dsn)
        self._is_sqlite = self.dsn.startswith("sqlite")
        connect_args: Dict[str, Any] = {}
        if self._is_sqlite:
            connect_args["check_same_thread"] = False
        self.engine: Engine = create_engine(
            self.dsn, future=True, connect_args=connect_args
        )
        Base.metadata.create_all(self.engine)
        self._Session = sessionmaker(self.engine, expire_on_commit=False, future=True)
        if lock_root is not None:
            self._lock_root = Path(lock_root)
        elif self._is_sqlite and "///" in self.dsn:
            # sqlite:///C:/path/kg.sqlite
            raw = self.dsn.split("sqlite:///", 1)[-1]
            self._lock_root = Path(raw).expanduser().resolve().parent
        else:
            self._lock_root = Path(os.path.expanduser("~/.superai/memory"))
        self._lock_root.mkdir(parents=True, exist_ok=True)

    def _locked(self, fn):
        with store_lock(self._lock_root, name="kg.lock", timeout=45.0):
            return fn()

    def status(self) -> Dict[str, Any]:
        with self._Session() as s:
            n_nodes = s.execute(text("SELECT COUNT(*) FROM kg_nodes")).scalar() or 0
            n_edges = s.execute(text("SELECT COUNT(*) FROM kg_edges")).scalar() or 0
            datasets = [
                r[0]
                for r in s.execute(
                    text(
                        "SELECT DISTINCT dataset_id FROM kg_nodes "
                        "ORDER BY dataset_id LIMIT 50"
                    )
                ).fetchall()
            ]
        return {
            "ok": True,
            "product": "knowledge_graph",
            "dsn": self._redact_dsn(),
            "backend": "sqlite" if self._is_sqlite else "sqlalchemy",
            "nodes": int(n_nodes),
            "edges": int(n_edges),
            "datasets": datasets,
            "message": f"{n_nodes} nodes, {n_edges} edges",
        }

    def _redact_dsn(self) -> str:
        d = self.dsn
        if "@" in d and "://" in d:
            # hide password
            try:
                scheme, rest = d.split("://", 1)
                if "@" in rest and ":" in rest.split("@", 1)[0]:
                    creds, host = rest.split("@", 1)
                    user = creds.split(":", 1)[0]
                    return f"{scheme}://{user}:***@{host}"
            except Exception:
                pass
        return d

    def _upsert_node_unlocked(
        self,
        s: Session,
        *,
        name: str,
        type: str = "Entity",
        node_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        source_memory_id: Optional[str] = None,
        dataset_id: str = "default",
        wing: Optional[str] = None,
        room: Optional[str] = None,
    ) -> Tuple[KGNodeRow, bool]:
        name_n = (name or "").strip()
        row = None
        if node_id:
            row = s.get(KGNodeRow, node_id)
        if row is None:
            row = s.execute(
                select(KGNodeRow).where(
                    KGNodeRow.type == type,
                    KGNodeRow.name == name_n,
                    KGNodeRow.dataset_id == dataset_id,
                )
            ).scalar_one_or_none()
        now = _now()
        if row is None:
            row = KGNodeRow(
                id=node_id or _new_id("n"),
                type=type or "Entity",
                name=name_n,
                properties=dict(properties or {}),
                source_memory_id=source_memory_id,
                dataset_id=dataset_id or "default",
                wing=wing,
                room=room,
                created_at=now,
                updated_at=now,
            )
            s.add(row)
            return row, True
        row.name = name_n
        row.type = type or row.type
        if properties:
            merged = dict(row.properties or {})
            merged.update(properties)
            row.properties = merged
        if source_memory_id:
            row.source_memory_id = source_memory_id
        if wing is not None:
            row.wing = wing
        if room is not None:
            row.room = room
        row.updated_at = now
        return row, False

    def upsert_node(
        self,
        *,
        name: str,
        type: str = "Entity",
        node_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        source_memory_id: Optional[str] = None,
        dataset_id: str = "default",
        wing: Optional[str] = None,
        room: Optional[str] = None,
    ) -> Dict[str, Any]:
        name_n = (name or "").strip()
        if not name_n:
            return {"ok": False, "error": "name required", "error_code": "validation"}

        def _do() -> Dict[str, Any]:
            with self._Session() as s:
                try:
                    row, created = self._upsert_node_unlocked(
                        s,
                        name=name_n,
                        type=type,
                        node_id=node_id,
                        properties=properties,
                        source_memory_id=source_memory_id,
                        dataset_id=dataset_id,
                        wing=wing,
                        room=room,
                    )
                    s.commit()
                    return {
                        "ok": True,
                        "created": created,
                        "node": self._node_dict(row),
                    }
                except Exception as e:  # noqa: BLE001
                    try:
                        s.rollback()
                    except Exception:
                        pass
                    return {
                        "ok": False,
                        "error": str(e)[:300],
                        "error_code": "db",
                        "message": f"upsert_node failed: {type(e).__name__}",
                    }

        return self._locked(_do)

    def upsert_edge(
        self,
        *,
        from_id: Optional[str] = None,
        to_id: Optional[str] = None,
        from_name: Optional[str] = None,
        to_name: Optional[str] = None,
        from_type: str = "Entity",
        to_type: str = "Entity",
        relation: str = "RELATED_TO",
        properties: Optional[Dict[str, Any]] = None,
        weight: float = 1.0,
        source_memory_id: Optional[str] = None,
        dataset_id: str = "default",
        create_nodes: bool = True,
    ) -> Dict[str, Any]:
        rel = (relation or "RELATED_TO").strip() or "RELATED_TO"

        def _do() -> Dict[str, Any]:
            with self._Session() as s:
                fid = from_id
                tid = to_id
                if not fid and from_name and create_nodes:
                    row, _ = self._upsert_node_unlocked(
                        s, name=from_name, type=from_type, dataset_id=dataset_id
                    )
                    fid = row.id
                elif not fid and from_name:
                    row = s.execute(
                        select(KGNodeRow).where(
                            KGNodeRow.name == from_name.strip(),
                            KGNodeRow.type == from_type,
                            KGNodeRow.dataset_id == dataset_id,
                        )
                    ).scalar_one_or_none()
                    fid = row.id if row else None
                if not tid and to_name and create_nodes:
                    row, _ = self._upsert_node_unlocked(
                        s, name=to_name, type=to_type, dataset_id=dataset_id
                    )
                    tid = row.id
                elif not tid and to_name:
                    row = s.execute(
                        select(KGNodeRow).where(
                            KGNodeRow.name == to_name.strip(),
                            KGNodeRow.type == to_type,
                            KGNodeRow.dataset_id == dataset_id,
                        )
                    ).scalar_one_or_none()
                    tid = row.id if row else None
                if not fid or not tid:
                    return {
                        "ok": False,
                        "error": "from and to nodes required (id or name)",
                        "error_code": "validation",
                    }
                existing = s.execute(
                    select(KGEdgeRow).where(
                        KGEdgeRow.from_id == fid,
                        KGEdgeRow.to_id == tid,
                        KGEdgeRow.relation == rel,
                        KGEdgeRow.dataset_id == dataset_id,
                    )
                ).scalar_one_or_none()
                now = _now()
                if existing is None:
                    edge = KGEdgeRow(
                        id=_new_id("e"),
                        from_id=fid,
                        to_id=tid,
                        relation=rel,
                        properties=dict(properties or {}),
                        weight=float(weight),
                        source_memory_id=source_memory_id,
                        dataset_id=dataset_id or "default",
                        created_at=now,
                    )
                    s.add(edge)
                    created = True
                else:
                    edge = existing
                    edge.weight = float(weight)
                    if properties:
                        merged = dict(edge.properties or {})
                        merged.update(properties)
                        edge.properties = merged
                    if source_memory_id:
                        edge.source_memory_id = source_memory_id
                    created = False
                try:
                    s.commit()
                except Exception as e:  # noqa: BLE001
                    try:
                        s.rollback()
                    except Exception:
                        pass
                    return {
                        "ok": False,
                        "error": str(e)[:300],
                        "error_code": "db",
                        "message": f"upsert_edge failed: {type(e).__name__}",
                    }
                return {
                    "ok": True,
                    "created": created,
                    "edge": self._edge_dict(edge),
                }

        return self._locked(_do)

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        with self._Session() as s:
            row = s.get(KGNodeRow, node_id)
            return self._node_dict(row) if row else None

    def query_nodes(
        self,
        *,
        type: Optional[str] = None,
        name: Optional[str] = None,
        dataset_id: Optional[str] = None,
        wing: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        with self._Session() as s:
            q = select(KGNodeRow)
            if type:
                q = q.where(KGNodeRow.type == type)
            if name:
                q = q.where(KGNodeRow.name.ilike(f"%{name}%") if not self._is_sqlite else KGNodeRow.name.like(f"%{name}%"))
            if dataset_id:
                q = q.where(KGNodeRow.dataset_id == dataset_id)
            if wing:
                q = q.where(KGNodeRow.wing == wing)
            # P7: pagination — allow larger pages (was hard-capped at 500)
            page = max(1, min(int(limit), 2000))
            off = max(0, int(offset or 0))
            q = q.offset(off).limit(page)
            rows = list(s.execute(q).scalars().all())
        return {
            "ok": True,
            "count": len(rows),
            "offset": off,
            "limit": page,
            "nodes": [self._node_dict(r) for r in rows],
        }

    def neighbors(
        self,
        node_id: str,
        *,
        direction: str = "both",
        dataset_id: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        with self._Session() as s:
            edges_out: List[KGEdgeRow] = []
            edges_in: List[KGEdgeRow] = []
            if direction in ("out", "both"):
                q = select(KGEdgeRow).where(KGEdgeRow.from_id == node_id)
                if dataset_id:
                    q = q.where(KGEdgeRow.dataset_id == dataset_id)
                edges_out = list(s.execute(q.limit(limit)).scalars().all())
            if direction in ("in", "both"):
                q = select(KGEdgeRow).where(KGEdgeRow.to_id == node_id)
                if dataset_id:
                    q = q.where(KGEdgeRow.dataset_id == dataset_id)
                edges_in = list(s.execute(q.limit(limit)).scalars().all())
        return {
            "ok": True,
            "node_id": node_id,
            "out": [self._edge_dict(e) for e in edges_out],
            "in": [self._edge_dict(e) for e in edges_in],
        }

    def path(
        self,
        *,
        from_id: Optional[str] = None,
        to_id: Optional[str] = None,
        from_name: Optional[str] = None,
        to_name: Optional[str] = None,
        hops: int = 2,
        dataset_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """BFS shortest path up to ``hops`` (default 2)."""
        fid = from_id or self._find_id_by_name(from_name or "", dataset_id=dataset_id)
        tid = to_id or self._find_id_by_name(to_name or "", dataset_id=dataset_id)
        if not fid or not tid:
            return {
                "ok": False,
                "error": "from/to node not found",
                "error_code": "not_found",
            }
        max_hops = max(1, min(int(hops), 6))
        # Load adjacency + node rows in ONE session (avoid N+1 get_node queries)
        adj: Dict[str, List[Tuple[str, str]]] = {}
        nodes_by_id: Dict[str, Dict[str, Any]] = {}
        with self._Session() as s:
            q = select(KGEdgeRow)
            if dataset_id:
                q = q.where(KGEdgeRow.dataset_id == dataset_id)
            edge_rows = list(s.execute(q).scalars().all())
            for e in edge_rows:
                adj.setdefault(e.from_id, []).append((e.to_id, e.relation))
                adj.setdefault(e.to_id, []).append((e.from_id, f"~{e.relation}"))

            # BFS on in-memory adj (no per-hop SQL)
            prev: Dict[str, Optional[Tuple[str, str]]] = {fid: None}
            queue: deque[str] = deque([fid])
            depth = {fid: 0}
            found = False
            while queue:
                cur = queue.popleft()
                if cur == tid:
                    found = True
                    break
                if depth[cur] >= max_hops:
                    continue
                for nxt, rel in adj.get(cur, []):
                    if nxt in prev:
                        continue
                    prev[nxt] = (cur, rel)
                    depth[nxt] = depth[cur] + 1
                    queue.append(nxt)
            if not found or tid not in prev:
                return {
                    "ok": True,
                    "found": False,
                    "from_id": fid,
                    "to_id": tid,
                    "hops": max_hops,
                    "path": [],
                    "message": f"No path within {max_hops} hops",
                    "edges_loaded": len(edge_rows),
                    "bfs_mode": "batch_adjacency",
                }

            # Collect path ids then batch-fetch node rows (single IN query)
            path_ids: List[str] = []
            cur_id: Optional[str] = tid
            while cur_id is not None:
                path_ids.append(cur_id)
                p = prev.get(cur_id)
                if p is None:
                    break
                cur_id = p[0]
            path_ids.reverse()

            if path_ids:
                nq = select(KGNodeRow).where(KGNodeRow.id.in_(path_ids))
                for row in s.execute(nq).scalars().all():
                    nodes_by_id[row.id] = self._node_dict(row)

            chain: List[Dict[str, Any]] = []
            for nid in path_ids:
                node = nodes_by_id.get(nid) or {"id": nid}
                step: Dict[str, Any] = {"node": node}
                p = prev.get(nid)
                if p is not None:
                    step["via_relation_from_prev"] = p[1]
                chain.append(step)

            return {
                "ok": True,
                "found": True,
                "from_id": fid,
                "to_id": tid,
                "length": len(chain) - 1,
                "path": chain,
                "message": f"Path length {len(chain) - 1}",
                "edges_loaded": len(edge_rows),
                "bfs_mode": "batch_adjacency",
            }

    def _find_id_by_name(
        self, name: str, *, dataset_id: Optional[str] = None
    ) -> Optional[str]:
        name = (name or "").strip()
        if not name:
            return None
        with self._Session() as s:
            q = select(KGNodeRow).where(KGNodeRow.name == name)
            if dataset_id:
                q = q.where(KGNodeRow.dataset_id == dataset_id)
            row = s.execute(q.limit(1)).scalar_one_or_none()
            if row:
                return row.id
            # case-insensitive fallback — SQL lower() when available (no full table scan)
            try:
                q2 = select(KGNodeRow).where(
                    text("lower(name) = lower(:n)")
                ).params(n=name)
                if dataset_id:
                    q2 = q2.where(KGNodeRow.dataset_id == dataset_id)
                row2 = s.execute(q2.limit(1)).scalar_one_or_none()
                if row2:
                    return row2.id
            except Exception:
                # last resort limited scan
                q3 = select(KGNodeRow)
                if dataset_id:
                    q3 = q3.where(KGNodeRow.dataset_id == dataset_id)
                for r in s.execute(q3.limit(2000)).scalars().all():
                    if r.name.lower() == name.lower():
                        return r.id
        return None

    def delete_node(self, node_id: str) -> Dict[str, Any]:
        def _do() -> Dict[str, Any]:
            with self._Session() as s:
                s.execute(delete(KGEdgeRow).where(KGEdgeRow.from_id == node_id))
                s.execute(delete(KGEdgeRow).where(KGEdgeRow.to_id == node_id))
                n = s.execute(delete(KGNodeRow).where(KGNodeRow.id == node_id)).rowcount
                s.commit()
            return {"ok": True, "deleted": int(n or 0), "node_id": node_id}

        return self._locked(_do)

    def delete_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Delete all nodes and edges for a dataset_id (P7 forget)."""
        did = (dataset_id or "").strip() or "default"

        def _do() -> Dict[str, Any]:
            with self._Session() as s:
                e = s.execute(
                    delete(KGEdgeRow).where(KGEdgeRow.dataset_id == did)
                ).rowcount
                n = s.execute(
                    delete(KGNodeRow).where(KGNodeRow.dataset_id == did)
                ).rowcount
                s.commit()
            return {
                "ok": True,
                "dataset_id": did,
                "nodes_deleted": int(n or 0),
                "edges_deleted": int(e or 0),
            }

        return self._locked(_do)

    def count_edges(self, dataset_id: Optional[str] = None) -> int:
        with self._Session() as s:
            q = select(KGEdgeRow)
            if dataset_id:
                q = q.where(KGEdgeRow.dataset_id == dataset_id)
            return len(list(s.execute(q.limit(10000)).scalars().all()))

    @staticmethod
    def _node_dict(row: KGNodeRow) -> Dict[str, Any]:
        return {
            "id": row.id,
            "type": row.type,
            "name": row.name,
            "properties": dict(row.properties or {}),
            "source_memory_id": row.source_memory_id,
            "dataset_id": row.dataset_id,
            "wing": row.wing,
            "room": row.room,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def _edge_dict(row: KGEdgeRow) -> Dict[str, Any]:
        return {
            "id": row.id,
            "from_id": row.from_id,
            "to_id": row.to_id,
            "relation": row.relation,
            "properties": dict(row.properties or {}),
            "weight": float(row.weight or 1.0),
            "source_memory_id": row.source_memory_id,
            "dataset_id": row.dataset_id,
            "created_at": row.created_at,
        }


def get_default_graph() -> KnowledgeGraph:
    return KnowledgeGraph()
