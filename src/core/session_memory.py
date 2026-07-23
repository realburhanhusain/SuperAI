"""
Session memory buffer + promote (Memory Roadmap P0.3 → P3 / Cognee gap 3).

Short-term working memory is **isolated by session_id** (SQLite under
``~/.superai/memory/sessions.sqlite``). It does **not** pollute the global
Memory Palace until an explicit promote (or threshold promote on end).

Promote can:
  1. Write durable palace chunks (tagged session/promoted)
  2. Optionally run cognify into the knowledge graph
  3. Optionally attach LearningEngine task outcome metadata
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import (
    Float,
    Integer,
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


def _new_id(prefix: str = "s") -> str:
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


class SessionRow(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    dataset_id: Mapped[str] = mapped_column(String(128), default="default", index=True)
    source: Mapped[str] = mapped_column(String(128), default="cli")  # cli|agent-tui|mcp
    status: Mapped[str] = mapped_column(String(32), default="open")  # open|ended|cleared
    created_at: Mapped[str] = mapped_column(String(64), default=_now)
    updated_at: Mapped[str] = mapped_column(String(64), default=_now)
    ended_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    meta: Mapped[dict] = mapped_column(JsonDict, default=dict)


class SessionItemRow(Base):
    __tablename__ = "session_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    kind: Mapped[str] = mapped_column(String(32), default="note")
    # kind: note|user|assistant|tool|decision|preference|outcome|pin
    content: Mapped[str] = mapped_column(Text, default="")
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    pinned: Mapped[int] = mapped_column(Integer, default=0)  # 1 = durable mark
    promoted: Mapped[int] = mapped_column(Integer, default=0)
    palace_memory_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tags: Mapped[str] = mapped_column(Text, default="")  # comma-separated
    meta: Mapped[dict] = mapped_column(JsonDict, default=dict)
    created_at: Mapped[str] = mapped_column(String(64), default=_now)


def default_sessions_path() -> Path:
    root = Path(os.path.expanduser("~/.superai/memory"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "sessions.sqlite"


def resolve_sessions_dsn(explicit: Optional[str] = None) -> str:
    if explicit:
        return explicit
    env = (os.getenv("SUPERAI_SESSION_DSN") or "").strip()
    if env:
        return env
    return f"sqlite:///{default_sessions_path().as_posix()}"


class SessionMemory:
    """Isolated short-term memory with promote-to-palace/graph."""

    def __init__(
        self,
        dsn: Optional[str] = None,
        *,
        lock_root: Optional[Path] = None,
    ):
        self.dsn = resolve_sessions_dsn(dsn)
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
            raw = self.dsn.split("sqlite:///", 1)[-1]
            self._lock_root = Path(raw).expanduser().resolve().parent
        else:
            self._lock_root = Path(os.path.expanduser("~/.superai/memory"))
        self._lock_root.mkdir(parents=True, exist_ok=True)

    def _locked(self, fn):
        with store_lock(self._lock_root, name="sessions.lock", timeout=45.0):
            return fn()

    # ── sessions ──────────────────────────────────────────────────────────

    def start(
        self,
        *,
        session_id: Optional[str] = None,
        title: Optional[str] = None,
        dataset_id: str = "default",
        source: str = "cli",
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        sid = session_id or _new_id("sess")

        def _do() -> Dict[str, Any]:
            with self._Session() as s:
                existing = s.get(SessionRow, sid)
                now = _now()
                if existing:
                    existing.updated_at = now
                    if title:
                        existing.title = title
                    if existing.status == "cleared":
                        existing.status = "open"
                        existing.ended_at = None
                    s.commit()
                    return {
                        "ok": True,
                        "created": False,
                        "session": self._sess_dict(existing),
                    }
                row = SessionRow(
                    id=sid,
                    title=title,
                    dataset_id=dataset_id or "default",
                    source=source or "cli",
                    status="open",
                    created_at=now,
                    updated_at=now,
                    meta=dict(meta or {}),
                )
                s.add(row)
                s.commit()
                return {
                    "ok": True,
                    "created": True,
                    "session": self._sess_dict(row),
                    "message": f"Session started {sid}",
                }

        return self._locked(_do)

    def list_sessions(
        self,
        *,
        status: Optional[str] = None,
        dataset_id: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        with self._Session() as s:
            q = select(SessionRow).order_by(SessionRow.updated_at.desc())
            if status:
                q = q.where(SessionRow.status == status)
            if dataset_id:
                q = q.where(SessionRow.dataset_id == dataset_id)
            rows = list(s.execute(q.limit(max(1, min(limit, 200)))).scalars().all())
            out = []
            for r in rows:
                n = s.execute(
                    text(
                        "SELECT COUNT(*) FROM session_items WHERE session_id = :sid"
                    ),
                    {"sid": r.id},
                ).scalar()
                d = self._sess_dict(r)
                d["item_count"] = int(n or 0)
                out.append(d)
        return {"ok": True, "count": len(out), "sessions": out}

    def get(self, session_id: str) -> Dict[str, Any]:
        with self._Session() as s:
            row = s.get(SessionRow, session_id)
            if not row:
                return {"ok": False, "error": "session not found", "error_code": "not_found"}
            n = s.execute(
                text("SELECT COUNT(*) FROM session_items WHERE session_id = :sid"),
                {"sid": session_id},
            ).scalar()
            d = self._sess_dict(row)
            d["item_count"] = int(n or 0)
            return {"ok": True, "session": d}

    # ── remember / recall ─────────────────────────────────────────────────

    def remember(
        self,
        session_id: str,
        content: str,
        *,
        kind: str = "note",
        importance: float = 0.5,
        pinned: bool = False,
        tags: Optional[Sequence[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
        ensure_session: bool = True,
        dataset_id: str = "default",
        source: str = "cli",
    ) -> Dict[str, Any]:
        content = (content or "").strip()
        if not content:
            return {"ok": False, "error": "content required", "error_code": "validation"}
        if ensure_session:
            self.start(
                session_id=session_id, dataset_id=dataset_id, source=source
            )

        def _do() -> Dict[str, Any]:
            with self._Session() as s:
                sess = s.get(SessionRow, session_id)
                if not sess:
                    return {
                        "ok": False,
                        "error": "session not found",
                        "error_code": "not_found",
                    }
                if sess.status == "cleared":
                    sess.status = "open"
                    sess.ended_at = None
                now = _now()
                item = SessionItemRow(
                    id=_new_id("it"),
                    session_id=session_id,
                    kind=(kind or "note").lower(),
                    content=content,
                    importance=float(max(0.0, min(1.0, importance))),
                    pinned=1 if pinned else 0,
                    promoted=0,
                    tags=",".join(tags or []),
                    meta=dict(meta or {}),
                    created_at=now,
                )
                s.add(item)
                sess.updated_at = now
                s.commit()
                return {
                    "ok": True,
                    "item": self._item_dict(item),
                    "session_id": session_id,
                    "message": f"Remembered item {item.id} in session {session_id}",
                }

        return self._locked(_do)

    def pin(self, session_id: str, item_id: str, pinned: bool = True) -> Dict[str, Any]:
        def _do() -> Dict[str, Any]:
            with self._Session() as s:
                item = s.get(SessionItemRow, item_id)
                if not item or item.session_id != session_id:
                    return {
                        "ok": False,
                        "error": "item not found",
                        "error_code": "not_found",
                    }
                item.pinned = 1 if pinned else 0
                if pinned:
                    item.importance = max(float(item.importance or 0), 0.75)
                s.commit()
                return {
                    "ok": True,
                    "item": self._item_dict(item),
                    "message": f"{'Pinned' if pinned else 'Unpinned'} {item_id}",
                }

        return self._locked(_do)

    def recall(
        self,
        session_id: str,
        query: Optional[str] = None,
        *,
        kind: Optional[str] = None,
        include_promoted: bool = True,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Lexical recall within one session only (no palace bleed)."""
        with self._Session() as s:
            sess = s.get(SessionRow, session_id)
            if not sess:
                return {
                    "ok": False,
                    "error": "session not found",
                    "error_code": "not_found",
                    "items": [],
                }
            q = select(SessionItemRow).where(SessionItemRow.session_id == session_id)
            if kind:
                q = q.where(SessionItemRow.kind == kind.lower())
            if not include_promoted:
                q = q.where(SessionItemRow.promoted == 0)
            rows = list(
                s.execute(
                    q.order_by(SessionItemRow.created_at.desc()).limit(500)
                ).scalars().all()
            )
        items = [self._item_dict(r) for r in rows]
        if query:
            ql = query.lower()
            tokens = [t for t in re.split(r"\W+", ql) if len(t) >= 2]
            scored = []
            for it in items:
                blob = f"{it.get('content')} {it.get('kind')} {it.get('tags')}".lower()
                score = sum(1 for t in tokens if t in blob) if tokens else (1 if ql in blob else 0)
                if score > 0 or (not tokens and ql in blob):
                    it = dict(it)
                    it["score"] = score
                    scored.append(it)
            scored.sort(key=lambda x: (-int(x.get("score") or 0), -float(x.get("importance") or 0)))
            items = scored[: max(1, min(limit, 200))]
        else:
            items = items[: max(1, min(limit, 200))]
        return {
            "ok": True,
            "session_id": session_id,
            "count": len(items),
            "items": items,
            "strategy": "session_lexical",
            "message": f"{len(items)} item(s) in session {session_id}",
        }

    def list_items(
        self,
        session_id: str,
        *,
        limit: int = 100,
        unpromoted_only: bool = False,
    ) -> Dict[str, Any]:
        return self.recall(
            session_id,
            query=None,
            include_promoted=not unpromoted_only,
            limit=limit,
        )

    # ── promote / end / clear ─────────────────────────────────────────────

    def promote(
        self,
        session_id: str,
        *,
        item_ids: Optional[Sequence[str]] = None,
        min_importance: float = 0.0,
        pinned_only: bool = False,
        store_palace: bool = True,
        cognify_graph: bool = False,
        cognify_mode: str = "mock",
        learning_outcome: bool = False,
        task_type: str = "session",
        model_used: str = "session",
    ) -> Dict[str, Any]:
        """
        Promote session items to Memory Palace (+ optional cognify / learning).

        Selection:
          - explicit item_ids, else
          - unpromoted items with importance >= min_importance
          - if pinned_only: only pinned
        """
        with self._Session() as s:
            sess = s.get(SessionRow, session_id)
            if not sess:
                return {
                    "ok": False,
                    "error": "session not found",
                    "error_code": "not_found",
                }
            dataset_id = sess.dataset_id or "default"
            q = select(SessionItemRow).where(SessionItemRow.session_id == session_id)
            if item_ids:
                q = q.where(SessionItemRow.id.in_(list(item_ids)))
            else:
                q = q.where(SessionItemRow.promoted == 0)
                if pinned_only:
                    q = q.where(SessionItemRow.pinned == 1)
                if min_importance > 0:
                    q = q.where(SessionItemRow.importance >= float(min_importance))
            items = list(s.execute(q).scalars().all())

        if not items:
            return {
                "ok": True,
                "promoted": 0,
                "palace_ids": [],
                "cognify": None,
                "message": "No matching unpromoted items",
            }

        palace_ids: List[str] = []
        cognify_reports: List[Dict[str, Any]] = []
        promoted_item_ids: List[str] = []

        mp = None
        if store_palace:
            from .memory_palace import MemoryPalace

            mp = MemoryPalace()

        for it in items:
            tags = [t for t in (it.tags or "").split(",") if t.strip()]
            for extra in (
                "session",
                "promoted",
                f"session:{session_id}",
                f"dataset:{dataset_id}",
                f"kind:{it.kind}",
            ):
                if extra not in tags:
                    tags.append(extra)
            if it.pinned:
                tags.append("pinned")
            mid = None
            if store_palace and mp is not None:
                mid = mp.store(
                    it.content,
                    tags=tags,
                    metadata={
                        "source": "session_promote",
                        "session_id": session_id,
                        "session_item_id": it.id,
                        "kind": it.kind,
                        "dataset_id": dataset_id,
                        "importance": it.importance,
                        "pinned": bool(it.pinned),
                        "durable": True,
                    },
                    importance=float(it.importance or 0.7),
                    wing="learning",
                    room="session",
                )
                palace_ids.append(mid)

            if cognify_graph:
                try:
                    from .cognify import cognify as run_cognify

                    cr = run_cognify(
                        it.content,
                        dataset_id=dataset_id,
                        mode=cognify_mode,
                        dry_run=False,
                        store_palace=False,
                        wing="learning",
                        room="session",
                    )
                    # attach source_memory_id on graph is already done if palace stored;
                    # re-link if we have mid by best-effort note in report
                    if mid and cr.get("ok"):
                        cr["linked_palace_memory_id"] = mid
                    cognify_reports.append(
                        {"item_id": it.id, "ok": cr.get("ok"), "message": cr.get("message")}
                    )
                except Exception as e:  # noqa: BLE001
                    cognify_reports.append(
                        {"item_id": it.id, "ok": False, "error": str(e)[:200]}
                    )

            if learning_outcome:
                try:
                    from .learning_engine import LearningEngine
                    from .memory_palace import MemoryPalace

                    eng = LearningEngine(mp or MemoryPalace())
                    eng.learn_from_task(
                        task_description=it.content[:500],
                        task_type=task_type,
                        model_used=model_used,
                        success=True,
                        latency=0.0,
                        steps_completed=1,
                    )
                except Exception:
                    pass

            promoted_item_ids.append(it.id)

        def _mark() -> None:
            with self._Session() as s:
                for iid in promoted_item_ids:
                    row = s.get(SessionItemRow, iid)
                    if not row:
                        continue
                    row.promoted = 1
                    # map palace id if we stored in order
                    idx = promoted_item_ids.index(iid)
                    if idx < len(palace_ids):
                        row.palace_memory_id = palace_ids[idx]
                sess = s.get(SessionRow, session_id)
                if sess:
                    sess.updated_at = _now()
                s.commit()

        self._locked(_mark)

        return {
            "ok": True,
            "product": "session_promote",
            "session_id": session_id,
            "promoted": len(promoted_item_ids),
            "item_ids": promoted_item_ids,
            "palace_ids": palace_ids,
            "cognify": cognify_reports if cognify_graph else None,
            "dataset_id": dataset_id,
            "message": (
                f"Promoted {len(promoted_item_ids)} item(s) "
                f"(palace={len(palace_ids)}, cognify={bool(cognify_graph)})"
            ),
        }

    def end(
        self,
        session_id: str,
        *,
        auto_promote: bool = True,
        min_importance: float = 0.6,
        cognify_graph: bool = False,
        cognify_mode: str = "mock",
    ) -> Dict[str, Any]:
        """Mark session ended; optionally promote pinned or high-importance items."""
        promo = None
        if auto_promote:
            # promote pinned OR importance threshold
            promo_pin = self.promote(
                session_id,
                pinned_only=True,
                store_palace=True,
                cognify_graph=cognify_graph,
                cognify_mode=cognify_mode,
            )
            promo_imp = self.promote(
                session_id,
                min_importance=min_importance,
                store_palace=True,
                cognify_graph=cognify_graph,
                cognify_mode=cognify_mode,
            )
            promo = {
                "pinned": promo_pin,
                "by_importance": promo_imp,
                "promoted": int(promo_pin.get("promoted") or 0)
                + int(promo_imp.get("promoted") or 0),
            }

        def _do() -> Dict[str, Any]:
            with self._Session() as s:
                sess = s.get(SessionRow, session_id)
                if not sess:
                    return {
                        "ok": False,
                        "error": "session not found",
                        "error_code": "not_found",
                    }
                now = _now()
                sess.status = "ended"
                sess.ended_at = now
                sess.updated_at = now
                s.commit()
                return {
                    "ok": True,
                    "session": self._sess_dict(sess),
                    "auto_promote": promo,
                    "message": f"Session ended {session_id}",
                }

        out = self._locked(_do)
        if promo is not None and out.get("ok"):
            out["auto_promote"] = promo
        return out

    def clear(
        self,
        session_id: str,
        *,
        delete_items: bool = True,
        hard: bool = False,
    ) -> Dict[str, Any]:
        """Clear session items; soft-clear marks status=cleared, hard deletes session row."""

        def _do() -> Dict[str, Any]:
            with self._Session() as s:
                sess = s.get(SessionRow, session_id)
                if not sess:
                    return {
                        "ok": False,
                        "error": "session not found",
                        "error_code": "not_found",
                    }
                n = 0
                if delete_items:
                    n = s.execute(
                        delete(SessionItemRow).where(
                            SessionItemRow.session_id == session_id
                        )
                    ).rowcount
                if hard:
                    s.execute(delete(SessionRow).where(SessionRow.id == session_id))
                else:
                    sess.status = "cleared"
                    sess.updated_at = _now()
                s.commit()
                return {
                    "ok": True,
                    "session_id": session_id,
                    "items_deleted": int(n or 0),
                    "hard": hard,
                    "message": f"Cleared session {session_id} ({n} items)",
                }

        return self._locked(_do)

    def purge_ttl(
        self,
        *,
        max_age_hours: float = 72.0,
        only_ended: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Delete old ended/cleared sessions and their items."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=float(max_age_hours))
        cutoff_s = cutoff.isoformat()

        def _do() -> Dict[str, Any]:
            with self._Session() as s:
                q = select(SessionRow)
                if only_ended:
                    q = q.where(SessionRow.status.in_(["ended", "cleared"]))
                victims = []
                for r in s.execute(q).scalars().all():
                    ts = r.ended_at or r.updated_at or r.created_at
                    if ts and ts < cutoff_s:
                        victims.append(r.id)
                if dry_run:
                    return {
                        "ok": True,
                        "dry_run": True,
                        "sessions": victims,
                        "count": len(victims),
                    }
                n_items = 0
                for sid in victims:
                    n_items += int(
                        s.execute(
                            delete(SessionItemRow).where(
                                SessionItemRow.session_id == sid
                            )
                        ).rowcount
                        or 0
                    )
                    s.execute(delete(SessionRow).where(SessionRow.id == sid))
                s.commit()
                return {
                    "ok": True,
                    "purged_sessions": len(victims),
                    "purged_items": n_items,
                    "session_ids": victims,
                    "message": f"Purged {len(victims)} session(s), {n_items} items",
                }

        return self._locked(_do)

    def status(self) -> Dict[str, Any]:
        with self._Session() as s:
            ns = s.execute(text("SELECT COUNT(*) FROM sessions")).scalar() or 0
            ni = s.execute(text("SELECT COUNT(*) FROM session_items")).scalar() or 0
            open_n = s.execute(
                text("SELECT COUNT(*) FROM sessions WHERE status = 'open'")
            ).scalar() or 0
        return {
            "ok": True,
            "product": "session_memory",
            "dsn": self.dsn if self._is_sqlite else "(sqlalchemy)",
            "sessions": int(ns),
            "items": int(ni),
            "open_sessions": int(open_n),
            "message": f"{ns} sessions ({open_n} open), {ni} items",
        }

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _sess_dict(row: SessionRow) -> Dict[str, Any]:
        return {
            "id": row.id,
            "title": row.title,
            "dataset_id": row.dataset_id,
            "source": row.source,
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "ended_at": row.ended_at,
            "meta": dict(row.meta or {}),
        }

    @staticmethod
    def _item_dict(row: SessionItemRow) -> Dict[str, Any]:
        return {
            "id": row.id,
            "session_id": row.session_id,
            "kind": row.kind,
            "content": row.content,
            "importance": float(row.importance or 0),
            "pinned": bool(row.pinned),
            "promoted": bool(row.promoted),
            "palace_memory_id": row.palace_memory_id,
            "tags": row.tags,
            "meta": dict(row.meta or {}),
            "created_at": row.created_at,
        }


def get_default_session_memory() -> SessionMemory:
    return SessionMemory()
