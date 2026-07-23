"""
Multi-strategy recall (Memory Roadmap P4 / Cognee gap 4).

Strategies:
  vector   — MemoryPalace semantic search
  keyword  — token/tag substring over palace memories
  graph    — KG name match + neighbor expand
  hybrid   — vector seeds + graph expand
  session  — session buffer first, optional fall-through
  auto     — heuristic router (always reports strategy used)

Honesty: every response includes ``strategy`` and ``strategy_reason``.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Set

_STRATEGIES = frozenset(
    {"auto", "vector", "keyword", "graph", "hybrid", "session"}
)


def choose_strategy(query: str, *, session_id: Optional[str] = None) -> Dict[str, str]:
    """Heuristic auto-router. Returns {strategy, reason}."""
    q = (query or "").strip()
    ql = q.lower()

    if session_id and any(
        x in ql
        for x in (
            "this session",
            "last time",
            "just now",
            "we said",
            "i said",
            "prefer",
            "preference",
            "earlier today",
        )
    ):
        return {
            "strategy": "session",
            "reason": "session cues + session_id present",
        }

    if any(
        x in ql
        for x in (
            "related to",
            "connected to",
            "depends on",
            "who owns",
            "path to",
            "linked to",
            "relationship",
            "graph",
        )
    ):
        return {"strategy": "hybrid", "reason": "relational / connection language"}

    # ticket-like / quoted ids → keyword first
    if re.search(r"[\"'`][^\"'`]{2,}[\"'`]", q) or re.search(
        r"\b[A-Z]{2,10}-\d+\b", q
    ):
        return {"strategy": "keyword", "reason": "quoted phrase or ticket-like id"}

    if session_id and len(q.split()) <= 4:
        return {
            "strategy": "session",
            "reason": "short query with active session (try session first)",
        }

    return {"strategy": "hybrid", "reason": "default hybrid when graph may help; falls back to vector"}


def _keyword_search(
    palace: Any,
    query: str,
    *,
    top_k: int = 10,
    tags: Optional[Sequence[str]] = None,
    wing: Optional[str] = None,
    room: Optional[str] = None,
    dataset_id: Optional[str] = None,
    include_shared: bool = True,
    errors: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    tokens = [t for t in re.split(r"\W+", (query or "").lower()) if len(t) >= 2]
    if not tokens:
        return []
    try:
        all_m = palace.get_all_memories() or []
    except Exception as e:  # noqa: BLE001
        if errors is not None:
            errors.append(f"keyword_palace:{type(e).__name__}:{str(e)[:120]}")
        return []
    if dataset_id:
        try:
            from .memory_dataset import filter_by_dataset

            all_m = filter_by_dataset(
                all_m, dataset_id, include_shared=include_shared
            )
        except Exception as e:  # noqa: BLE001
            if errors is not None:
                errors.append(f"keyword_dataset_filter:{type(e).__name__}")
    scored: List[Dict[str, Any]] = []
    tag_set = {t.lower() for t in (tags or [])}
    for m in all_m:
        meta = m.get("metadata") or {}
        if wing and str(meta.get("wing") or "") != wing:
            continue
        if room and str(meta.get("room") or "") != room:
            continue
        mtags = m.get("tags") or []
        if isinstance(mtags, str):
            mtags = [x.strip() for x in mtags.split(",") if x.strip()]
        if tag_set and not tag_set.intersection({str(t).lower() for t in mtags}):
            continue
        blob = f"{m.get('content')} {meta} {mtags}".lower()
        score = sum(1 for t in tokens if t in blob)
        if score <= 0:
            continue
        scored.append(
            {
                "id": m.get("id"),
                "content": m.get("content"),
                "metadata": meta,
                "tags": mtags,
                "score": float(score),
                "distance": max(0.0, 1.0 - min(1.0, score / max(3.0, len(tokens)))),
                "source": "keyword",
            }
        )
    scored.sort(key=lambda x: -float(x.get("score") or 0))
    return scored[: max(1, top_k)]


def _vector_search(
    palace: Any,
    query: str,
    *,
    top_k: int = 10,
    tags: Optional[Sequence[str]] = None,
    wing: Optional[str] = None,
    room: Optional[str] = None,
    dataset_id: Optional[str] = None,
    include_shared: bool = True,
    errors: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    try:
        hits = palace.query_semantic(
            query,
            top_k=top_k,
            tags=list(tags) if tags else None,
            wing=wing,
            room=room,
            dataset_id=dataset_id,
            include_shared=include_shared,
        )
    except TypeError:
        try:
            hits = palace.query_semantic(query, top_k=top_k)
        except Exception as e:  # noqa: BLE001
            if errors is not None:
                errors.append(f"vector:{type(e).__name__}:{str(e)[:120]}")
            return []
    except Exception as e:  # noqa: BLE001
        if errors is not None:
            errors.append(f"vector:{type(e).__name__}:{str(e)[:120]}")
        return []
    out = []
    for h in hits or []:
        if not isinstance(h, dict):
            continue
        item = dict(h)
        item.setdefault("source", "vector")
        out.append(item)
    return out


def _graph_search(
    kg: Any,
    query: str,
    *,
    top_k: int = 10,
    dataset_id: Optional[str] = None,
    hops: int = 1,
) -> List[Dict[str, Any]]:
    if kg is None:
        return []
    # find nodes by name tokens / full query
    q = (query or "").strip()
    nodes = kg.query_nodes(name=q, dataset_id=dataset_id, limit=top_k).get("nodes") or []
    if not nodes:
        # try significant tokens (Title Case or long words)
        tokens = re.findall(r"\b[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)?\b", q)
        if not tokens:
            tokens = [t for t in re.split(r"\W+", q) if len(t) >= 4][:5]
        seen: Set[str] = set()
        for t in tokens:
            for n in kg.query_nodes(name=t, dataset_id=dataset_id, limit=5).get("nodes") or []:
                if n.get("id") not in seen:
                    seen.add(n["id"])
                    nodes.append(n)
    results: List[Dict[str, Any]] = []
    for n in nodes[:top_k]:
        results.append(
            {
                "id": n.get("id"),
                "content": f"[{n.get('type')}] {n.get('name')}",
                "metadata": {
                    "graph_node": True,
                    "type": n.get("type"),
                    "name": n.get("name"),
                    "dataset_id": n.get("dataset_id"),
                    "source_memory_id": n.get("source_memory_id"),
                    "wing": n.get("wing"),
                    "room": n.get("room"),
                },
                "score": 1.0,
                "source": "graph_node",
            }
        )
        if hops >= 1 and n.get("id"):
            nb = kg.neighbors(n["id"], dataset_id=dataset_id, limit=10)
            for e in (nb.get("out") or []) + (nb.get("in") or []):
                other_id = e.get("to_id") if e.get("from_id") == n.get("id") else e.get("from_id")
                other = kg.get_node(other_id) if other_id else None
                if not other:
                    continue
                results.append(
                    {
                        "id": other.get("id"),
                        "content": (
                            f"[{other.get('type')}] {other.get('name')} "
                            f"via {e.get('relation')} from {n.get('name')}"
                        ),
                        "metadata": {
                            "graph_node": True,
                            "type": other.get("type"),
                            "name": other.get("name"),
                            "via_relation": e.get("relation"),
                            "from_node": n.get("name"),
                            "source_memory_id": other.get("source_memory_id"),
                        },
                        "score": 0.8,
                        "source": "graph_neighbor",
                    }
                )
    # dedupe by id
    seen_ids: Set[str] = set()
    deduped = []
    for r in results:
        rid = str(r.get("id") or "")
        if rid and rid in seen_ids:
            continue
        if rid:
            seen_ids.add(rid)
        deduped.append(r)
    return deduped[: max(1, top_k * 2)]


def _session_search(
    sm: Any,
    session_id: str,
    query: str,
    *,
    top_k: int = 10,
) -> List[Dict[str, Any]]:
    if sm is None or not session_id:
        return []
    out = sm.recall(session_id, query=query or None, limit=top_k)
    if not out.get("ok"):
        return []
    hits = []
    for it in out.get("items") or []:
        hits.append(
            {
                "id": it.get("id"),
                "content": it.get("content"),
                "metadata": {
                    "session_id": session_id,
                    "kind": it.get("kind"),
                    "importance": it.get("importance"),
                    "pinned": it.get("pinned"),
                    "promoted": it.get("promoted"),
                },
                "score": float(it.get("score") or it.get("importance") or 0.5),
                "source": "session",
            }
        )
    return hits


def _merge_hits(*lists: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
    seen: Set[str] = set()
    merged: List[Dict[str, Any]] = []
    for lst in lists:
        for h in lst:
            key = str(h.get("id") or "") + "|" + str(h.get("content") or "")[:80]
            if key in seen:
                continue
            seen.add(key)
            merged.append(h)
    # prefer higher score if present
    merged.sort(key=lambda x: -float(x.get("score") or 0))
    return merged[: max(1, top_k)]


def recall(
    query: str,
    *,
    strategy: str = "auto",
    top_k: int = 10,
    session_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
    tags: Optional[Sequence[str]] = None,
    wing: Optional[str] = None,
    room: Optional[str] = None,
    fallthrough: bool = True,
    palace: Any = None,
    kg: Any = None,
    session_memory: Any = None,
) -> Dict[str, Any]:
    """
    Run multi-strategy recall.

    ``strategy=auto`` picks via heuristics and may fall through session → hybrid.
    """
    q = (query or "").strip()
    strat = (strategy or "auto").lower().strip()
    if strat not in _STRATEGIES:
        return {
            "ok": False,
            "error": f"unknown strategy {strategy}; use {sorted(_STRATEGIES)}",
            "error_code": "validation",
            "hits": [],
        }
    if not q and strat != "session":
        return {
            "ok": False,
            "error": "query required",
            "error_code": "validation",
            "hits": [],
        }

    reason = "explicit"
    if strat == "auto":
        choice = choose_strategy(q, session_id=session_id)
        strat = choice["strategy"]
        reason = choice["reason"]

    # P7: default dataset scope (active + shared)
    if dataset_id is None:
        try:
            from .memory_dataset import resolve_dataset_id

            dataset_id = resolve_dataset_id(None)
        except Exception:
            dataset_id = None

    # lazy load defaults (surface init failures as degraded, not silent abort)
    subsystem_errors: List[str] = []
    if palace is None and strat in {"vector", "keyword", "hybrid", "auto", "session"}:
        try:
            from .memory_palace import MemoryPalace

            palace = MemoryPalace()
        except Exception as e:  # noqa: BLE001
            palace = None
            subsystem_errors.append(f"palace_init:{type(e).__name__}:{str(e)[:120]}")
    if kg is None and strat in {"graph", "hybrid"}:
        try:
            from .knowledge_graph import get_default_graph

            kg = get_default_graph()
        except Exception as e:  # noqa: BLE001
            kg = None
            subsystem_errors.append(f"kg_init:{type(e).__name__}:{str(e)[:120]}")
    if session_memory is None and strat == "session" and session_id:
        try:
            from .session_memory import get_default_session_memory

            session_memory = get_default_session_memory()
        except Exception as e:  # noqa: BLE001
            session_memory = None
            subsystem_errors.append(f"session_init:{type(e).__name__}:{str(e)[:120]}")

    hits: List[Dict[str, Any]] = []
    used = strat
    notes: List[str] = []
    search_errors: List[str] = []

    if strat == "vector":
        if not palace:
            notes.append("vector strategy degraded: palace unavailable")
            hits = []
        else:
            hits = _vector_search(
                palace,
                q,
                top_k=top_k,
                tags=tags,
                wing=wing,
                room=room,
                dataset_id=dataset_id,
                errors=search_errors,
            )
    elif strat == "keyword":
        if not palace:
            notes.append("keyword strategy degraded: palace unavailable")
            hits = []
        else:
            hits = _keyword_search(
                palace,
                q,
                top_k=top_k,
                tags=tags,
                wing=wing,
                room=room,
                dataset_id=dataset_id,
                errors=search_errors,
            )
    elif strat == "graph":
        hits = _graph_search(kg, q, top_k=top_k, dataset_id=dataset_id)
    elif strat == "hybrid":
        v = (
            _vector_search(
                palace,
                q,
                top_k=top_k,
                tags=tags,
                wing=wing,
                room=room,
                dataset_id=dataset_id,
                errors=search_errors,
            )
            if palace
            else []
        )
        if not palace:
            notes.append("hybrid: palace unavailable (vector/keyword skipped)")
        g = _graph_search(kg, q, top_k=top_k, dataset_id=dataset_id)
        k = (
            _keyword_search(
                palace,
                q,
                top_k=max(3, top_k // 2),
                tags=tags,
                wing=wing,
                room=room,
                dataset_id=dataset_id,
                errors=search_errors,
            )
            if palace
            else []
        )
        hits = _merge_hits(v, g, k, top_k=top_k)
        # expand graph from vector hits that mention names
        if kg and v:
            extra = []
            for h in v[:5]:
                content = str(h.get("content") or "")[:200]
                extra.extend(
                    _graph_search(kg, content, top_k=3, dataset_id=dataset_id)[:3]
                )
            hits = _merge_hits(hits, extra, top_k=top_k)
        notes.append(f"vector={len(v)} graph={len(g)} keyword={len(k)}")
    elif strat == "session":
        hits = _session_search(session_memory, session_id or "", q, top_k=top_k)
        if fallthrough and not hits:
            # fall through to hybrid
            notes.append("session empty → fallthrough hybrid")
            used = "session+hybrid"
            v = (
                _vector_search(
                    palace,
                    q,
                    top_k=top_k,
                    tags=tags,
                    wing=wing,
                    room=room,
                    dataset_id=dataset_id,
                    errors=search_errors,
                )
                if palace
                else []
            )
            g = _graph_search(kg, q, top_k=top_k, dataset_id=dataset_id)
            hits = _merge_hits(v, g, top_k=top_k)
            notes.append(f"vector={len(v)} graph={len(g)}")
        elif not session_id:
            notes.append("no session_id; session strategy returned empty")

    degraded = bool(subsystem_errors or search_errors)
    if degraded:
        notes.extend(subsystem_errors)
        notes.extend(search_errors)

    out = {
        "ok": True,
        "product": "recall_router",
        "query": q,
        "dataset_id": dataset_id,
        "strategy": used,
        "strategy_requested": strategy,
        "strategy_reason": reason,
        "count": len(hits),
        "hits": hits,
        "session_id": session_id,
        "notes": notes,
        "degraded": degraded,
        "subsystem_errors": subsystem_errors or None,
        "search_errors": search_errors or None,
        "message": (
            f"{len(hits)} hit(s) via strategy={used} ({reason})"
            + ("; DEGRADED" if degraded else "")
        ),
    }
    try:
        from .memory_otel import instrument_report

        out = instrument_report("recall", out)
    except Exception:
        pass
    return out
