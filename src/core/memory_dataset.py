"""
Dataset / namespace product model (Memory Roadmap P7 / Cognee gap 7).

Datasets are multi-topic namespaces under a tenant:
  tenant  ⊇ multi-user isolation (palace_tenant)
  dataset ⊇ multi-topic isolation (this module)

Defaults: personal, d360, superai, scratch (+ default, shared).

``shared`` is always visible alongside the active dataset when
``include_shared=True`` (default query mode).

Registry lives at ``~/.superai/memory/datasets_registry.json``.
Active dataset: SUPERAI_DATASET_ID env > config active_dataset > default.
"""

from __future__ import annotations

import json
import os
import re
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

# Built-in catalog (always present after ensure_defaults)
BUILTIN_DATASETS: Dict[str, Dict[str, Any]] = {
    "default": {
        "description": "Legacy / unspecified namespace (backward compatible)",
        "builtin": True,
    },
    "personal": {
        "description": "Personal notes and preferences",
        "builtin": True,
    },
    "d360": {
        "description": "D360 work knowledge",
        "builtin": True,
    },
    "superai": {
        "description": "SuperAI product / engineering memory",
        "builtin": True,
    },
    "scratch": {
        "description": "Ephemeral experiments — safe to forget",
        "builtin": True,
    },
    "shared": {
        "description": "Cross-dataset readable shared facts",
        "builtin": True,
        "shared": True,
    },
}

_ID_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_\-.]{0,63}$")


def registry_path() -> Path:
    env = (os.getenv("SUPERAI_DATASETS_PATH") or "").strip()
    if env:
        return Path(env).expanduser()
    root = Path(os.path.expanduser("~/.superai/memory"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "datasets_registry.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def validate_dataset_id(dataset_id: str) -> Optional[str]:
    """Return error string or None if valid."""
    d = (dataset_id or "").strip()
    if not d:
        return "empty dataset_id"
    if not _ID_RE.match(d):
        return (
            "dataset_id must start with a letter and use only "
            "letters, digits, _ - . (max 64 chars)"
        )
    if d.lower() in {"all", "none", "null"}:
        return f"reserved dataset_id: {d}"
    return None


def dataset_tag(dataset_id: str) -> str:
    return f"dataset:{(dataset_id or 'default').strip() or 'default'}"


class DatasetRegistry:
    """JSON-backed dataset catalog + active pointer."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else registry_path()
        self._data: Dict[str, Any] = {"version": 1, "active": "default", "datasets": {}}
        self._load()
        self.ensure_defaults()

    def _load(self) -> None:
        if self.path.is_file():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._data = raw
                    self._data.setdefault("version", 1)
                    self._data.setdefault("active", "default")
                    self._data.setdefault("datasets", {})
            except Exception:
                pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self._data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def ensure_defaults(self) -> None:
        changed = False
        ds = self._data.setdefault("datasets", {})
        for name, meta in BUILTIN_DATASETS.items():
            if name not in ds:
                ds[name] = {
                    "id": name,
                    "description": meta.get("description") or "",
                    "builtin": bool(meta.get("builtin")),
                    "shared": bool(meta.get("shared")),
                    "created_at": _now(),
                }
                changed = True
            else:
                # keep builtin flags honest
                if meta.get("builtin") and not ds[name].get("builtin"):
                    ds[name]["builtin"] = True
                    changed = True
        if not self._data.get("active"):
            self._data["active"] = "default"
            changed = True
        if changed:
            try:
                self.save()
            except Exception:
                pass

    def list_datasets(self) -> Dict[str, Any]:
        rows = []
        active = self.get_active()
        for name, meta in sorted((self._data.get("datasets") or {}).items()):
            rows.append(
                {
                    "id": name,
                    "description": meta.get("description") or "",
                    "builtin": bool(meta.get("builtin")),
                    "shared": bool(meta.get("shared")) or name == "shared",
                    "created_at": meta.get("created_at"),
                    "active": name == active,
                }
            )
        return {
            "ok": True,
            "product": "dataset_list",
            "active": active,
            "count": len(rows),
            "datasets": rows,
            "message": f"{len(rows)} dataset(s); active={active}",
        }

    def create(
        self,
        dataset_id: str,
        *,
        description: str = "",
        force: bool = False,
    ) -> Dict[str, Any]:
        err = validate_dataset_id(dataset_id)
        if err:
            return {"ok": False, "error": err, "error_code": "validation"}
        name = dataset_id.strip()
        ds = self._data.setdefault("datasets", {})
        if name in ds and not force:
            return {
                "ok": True,
                "created": False,
                "id": name,
                "message": f"Dataset already exists: {name}",
                "dataset": ds[name],
            }
        ds[name] = {
            "id": name,
            "description": description or f"User dataset {name}",
            "builtin": name in BUILTIN_DATASETS,
            "shared": name == "shared",
            "created_at": (ds.get(name) or {}).get("created_at") or _now(),
            "updated_at": _now(),
        }
        self.save()
        return {
            "ok": True,
            "created": True,
            "id": name,
            "dataset": ds[name],
            "message": f"Created dataset {name}",
        }

    def get_active(self) -> str:
        env = (os.getenv("SUPERAI_DATASET_ID") or "").strip()
        if env:
            return env
        try:
            from .config import Config

            cfg = Config()
            c = (cfg.get("active_dataset") or "").strip()
            if c:
                return c
        except Exception:
            pass
        return str(self._data.get("active") or "default")

    def use(self, dataset_id: str, *, persist: bool = True) -> Dict[str, Any]:
        err = validate_dataset_id(dataset_id)
        if err:
            return {"ok": False, "error": err, "error_code": "validation"}
        name = dataset_id.strip()
        # auto-create unknown ids so use is convenient
        if name not in (self._data.get("datasets") or {}):
            self.create(name, description=f"Auto-created via use {name}")
        self._data["active"] = name
        if persist:
            self.save()
            try:
                from .config import Config

                Config().set("active_dataset", name, persist=True)
            except Exception:
                pass
        return {
            "ok": True,
            "active": name,
            "message": f"Active dataset set to {name}",
        }

    def exists(self, dataset_id: str) -> bool:
        return (dataset_id or "").strip() in (self._data.get("datasets") or {})


def get_registry(path: Optional[Path] = None) -> DatasetRegistry:
    return DatasetRegistry(path=path)


def resolve_dataset_id(
    explicit: Optional[str] = None,
    *,
    registry: Optional[DatasetRegistry] = None,
    allow_none: bool = False,
) -> Optional[str]:
    """
    Resolve dataset for writes/queries.

    Priority: explicit arg > env SUPERAI_DATASET_ID > config/registry active > default.
    If allow_none and explicit is the empty sentinel '*'/all, returns None (no filter).
    """
    if explicit is not None:
        e = str(explicit).strip()
        if allow_none and e.lower() in {"*", "all", ""}:
            return None if e.lower() in {"*", "all"} else e or None
        if e:
            return e
    env = (os.getenv("SUPERAI_DATASET_ID") or "").strip()
    if env:
        return env
    try:
        reg = registry or get_registry()
        return reg.get_active()
    except Exception:
        return "default"


def scope_dataset_metadata(
    meta: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    *,
    dataset_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Stamp metadata + tags with dataset_id (like palace_tenant.scope_metadata)."""
    did = resolve_dataset_id(dataset_id) or "default"
    m = dict(meta or {})
    m["dataset_id"] = did
    tag = dataset_tag(did)
    tlist = list(tags or m.get("tags") or [])
    if isinstance(m.get("tags"), list) and not tags:
        tlist = list(m["tags"])
    if tag not in tlist:
        tlist.append(tag)
    m["tags"] = tlist
    return m


def memory_dataset_id(mem: Dict[str, Any]) -> str:
    meta = mem.get("metadata") if isinstance(mem.get("metadata"), dict) else {}
    if meta.get("dataset_id"):
        return str(meta["dataset_id"])
    tags = mem.get("tags") or meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    for t in tags:
        ts = str(t)
        if ts.startswith("dataset:"):
            return ts.split(":", 1)[1] or "default"
    return "default"


def filter_by_dataset(
    items: Iterable[Dict[str, Any]],
    dataset_id: Optional[str],
    *,
    include_shared: bool = True,
    id_getter=memory_dataset_id,
) -> List[Dict[str, Any]]:
    """
    Default isolation: keep active dataset (+ shared when include_shared).

    If dataset_id is None → no filter (explicit all-datasets mode).
    """
    if dataset_id is None:
        return list(items)
    allowed: Set[str] = {dataset_id}
    if include_shared and dataset_id != "shared":
        allowed.add("shared")
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        did = id_getter(it)
        if did in allowed:
            out.append(it)
    return out


def export_dataset(
    dataset_id: str,
    dest: Optional[Path] = None,
    *,
    limit: int = 5000,
    palace: Any = None,
    kg: Any = None,
) -> Dict[str, Any]:
    """Export palace memories + KG nodes/edges for one dataset as a zip of JSON."""
    err = validate_dataset_id(dataset_id)
    if err:
        return {"ok": False, "error": err, "error_code": "validation"}
    did = dataset_id.strip()
    out_path = Path(
        dest
        or (
            Path.home()
            / ".superai"
            / "datasets"
            / f"export_{did}_{int(time.time())}.zip"
        )
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    memories: List[Dict[str, Any]] = []
    try:
        from .memory_palace import MemoryPalace

        mp = palace or MemoryPalace()
        all_m = mp.get_all_memories() or []
        memories = filter_by_dataset(all_m, did, include_shared=False)[:limit]
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"palace:{e}"[:300], "error_code": "palace"}

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    try:
        from .knowledge_graph import KnowledgeGraph, get_default_graph

        graph = kg or get_default_graph()
        q = graph.query_nodes(dataset_id=did, limit=limit)
        nodes = q.get("nodes") or []
        # collect edges for those nodes
        seen_e: Set[str] = set()
        for n in nodes:
            if not n.get("id"):
                continue
            nb = graph.neighbors(n["id"], dataset_id=did, limit=200)
            for e in (nb.get("out") or []) + (nb.get("in") or []):
                eid = str(e.get("id") or "")
                if eid and eid not in seen_e:
                    seen_e.add(eid)
                    edges.append(e)
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "error": f"kg:{e}"[:300],
            "error_code": "kg",
            "memories_partial": len(memories),
        }

    manifest = {
        "version": 1,
        "product": "superai_dataset_export",
        "dataset_id": did,
        "exported_at": _now(),
        "counts": {
            "memories": len(memories),
            "nodes": len(nodes),
            "edges": len(edges),
        },
    }
    try:
        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2, default=str))
            zf.writestr(
                "memories.json",
                json.dumps({"memories": memories}, indent=2, default=str),
            )
            zf.writestr(
                "kg_nodes.json",
                json.dumps({"nodes": nodes}, indent=2, default=str),
            )
            zf.writestr(
                "kg_edges.json",
                json.dumps({"edges": edges}, indent=2, default=str),
            )
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300], "error_code": "zip"}

    return {
        "ok": True,
        "product": "dataset_export",
        "dataset_id": did,
        "path": str(out_path.resolve()),
        "counts": manifest["counts"],
        "message": (
            f"Exported dataset {did}: {manifest['counts']['memories']} memories, "
            f"{manifest['counts']['nodes']} nodes, {manifest['counts']['edges']} edges"
        ),
    }


def import_dataset(
    src: Path,
    *,
    dataset_id: Optional[str] = None,
    dry_run: bool = False,
    palace: Any = None,
    kg: Any = None,
) -> Dict[str, Any]:
    """Import a dataset zip produced by export_dataset."""
    p = Path(src)
    if not p.is_file():
        return {"ok": False, "error": "not_found", "path": str(p)}
    try:
        with zipfile.ZipFile(p, "r") as zf:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            mems = json.loads(zf.read("memories.json").decode("utf-8")).get(
                "memories"
            ) or []
            nodes = json.loads(zf.read("kg_nodes.json").decode("utf-8")).get(
                "nodes"
            ) or []
            edges = json.loads(zf.read("kg_edges.json").decode("utf-8")).get(
                "edges"
            ) or []
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"bad_archive:{e}"[:300], "error_code": "zip"}

    did = (
        dataset_id
        or manifest.get("dataset_id")
        or "imported"
    ).strip()
    err = validate_dataset_id(did)
    if err:
        return {"ok": False, "error": err, "error_code": "validation"}

    get_registry().create(did, description=f"Imported from {p.name}")

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "dataset_id": did,
            "would_import": {
                "memories": len(mems),
                "nodes": len(nodes),
                "edges": len(edges),
            },
            "message": f"Dry-run import into {did}",
        }

    mem_ok = node_ok = edge_ok = 0
    errors = 0
    try:
        from .memory_palace import MemoryPalace

        mp = palace or MemoryPalace()
        for mem in mems:
            if not isinstance(mem, dict):
                continue
            content = mem.get("content") or ""
            if not content:
                continue
            meta = dict(mem.get("metadata") or {})
            meta["dataset_id"] = did
            tags = list(mem.get("tags") or [])
            tag = dataset_tag(did)
            if tag not in tags:
                tags.append(tag)
            try:
                mp.store(
                    str(content),
                    tags=tags,
                    metadata=meta,
                    importance=float(mem.get("importance") or meta.get("importance") or 0.5),
                    wing=meta.get("wing"),
                    room=meta.get("room"),
                    auto_wings=False,
                )
                mem_ok += 1
            except Exception:
                errors += 1
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"palace_import:{e}"[:300]}

    try:
        from .knowledge_graph import KnowledgeGraph, get_default_graph

        graph = kg or get_default_graph()
        for n in nodes:
            if not isinstance(n, dict) or not n.get("name"):
                continue
            try:
                out = graph.upsert_node(
                    name=str(n["name"]),
                    type=str(n.get("type") or "Entity"),
                    properties=dict(n.get("properties") or {}),
                    source_memory_id=n.get("source_memory_id"),
                    dataset_id=did,
                    wing=n.get("wing"),
                    room=n.get("room"),
                )
                if out.get("ok"):
                    node_ok += 1
            except Exception:
                errors += 1
        for e in edges:
            if not isinstance(e, dict):
                continue
            # edges in export may only have ids — skip if no names
            # re-link by finding from export edge properties is limited;
            # neighbors export includes from/to ids only. Skip pure-id edges.
            # Prefer relations stored with names if present.
            frm = e.get("from_name")
            to = e.get("to_name")
            if not frm or not to:
                continue
            try:
                out = graph.upsert_edge(
                    from_name=str(frm),
                    to_name=str(to),
                    from_type=str(e.get("from_type") or "Entity"),
                    to_type=str(e.get("to_type") or "Entity"),
                    relation=str(e.get("relation") or "RELATED_TO"),
                    properties=dict(e.get("properties") or {}),
                    dataset_id=did,
                )
                if out.get("ok"):
                    edge_ok += 1
            except Exception:
                errors += 1
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "error": f"kg_import:{e}"[:300],
            "memories_imported": mem_ok,
        }

    return {
        "ok": True,
        "product": "dataset_import",
        "dataset_id": did,
        "imported": {
            "memories": mem_ok,
            "nodes": node_ok,
            "edges": edge_ok,
        },
        "errors": errors,
        "source": str(p),
        "message": (
            f"Imported into {did}: {mem_ok} memories, {node_ok} nodes, "
            f"{edge_ok} edges ({errors} errors)"
        ),
    }


def forget_dataset(
    dataset_id: str,
    *,
    yes: bool = False,
    palace: Any = None,
    kg: Any = None,
    protect_builtins: bool = False,
) -> Dict[str, Any]:
    """
    Delete palace memories and KG rows for a dataset.

    Requires yes=True. Builtin datasets can be emptied but not removed from registry
    when protect_builtins=True (default False for scratch forget use-case —
    builtin flag only prevents deleting the registry entry).
    """
    err = validate_dataset_id(dataset_id)
    if err:
        return {"ok": False, "error": err, "error_code": "validation"}
    if not yes:
        return {
            "ok": False,
            "error": "refusing to forget without --yes",
            "error_code": "confirmation",
            "hint": "superai dataset forget NAME --yes",
        }
    did = dataset_id.strip()
    if did == "shared" and protect_builtins:
        return {
            "ok": False,
            "error": "refusing to forget shared (protect_builtins)",
            "error_code": "protected",
        }

    deleted_m = 0
    deleted_n = 0
    deleted_e = 0
    try:
        from .memory_palace import MemoryPalace

        mp = palace or MemoryPalace()
        for mem in list(mp.get_all_memories() or []):
            if memory_dataset_id(mem) != did:
                continue
            mid = mem.get("id")
            if not mid:
                continue
            try:
                mp.delete(str(mid))
                deleted_m += 1
            except Exception:
                pass
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"palace_forget:{e}"[:300]}

    try:
        from .knowledge_graph import get_default_graph

        graph = kg or get_default_graph()
        if hasattr(graph, "delete_dataset"):
            out = graph.delete_dataset(did)
            deleted_n = int(out.get("nodes_deleted") or 0)
            deleted_e = int(out.get("edges_deleted") or 0)
        else:
            nodes = graph.query_nodes(dataset_id=did, limit=5000).get("nodes") or []
            for n in nodes:
                if n.get("id"):
                    r = graph.delete_node(str(n["id"]))
                    deleted_n += int(r.get("deleted") or 0)
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "error": f"kg_forget:{e}"[:300],
            "memories_deleted": deleted_m,
        }

    # remove non-builtin registry entry
    reg = get_registry()
    meta = (reg._data.get("datasets") or {}).get(did) or {}
    removed_registry = False
    if meta and not meta.get("builtin"):
        del reg._data["datasets"][did]
        if reg._data.get("active") == did:
            reg._data["active"] = "default"
        reg.save()
        removed_registry = True

    return {
        "ok": True,
        "product": "dataset_forget",
        "dataset_id": did,
        "memories_deleted": deleted_m,
        "nodes_deleted": deleted_n,
        "edges_deleted": deleted_e,
        "registry_removed": removed_registry,
        "message": (
            f"Forgot dataset {did}: {deleted_m} memories, "
            f"{deleted_n} nodes, {deleted_e} edges"
        ),
    }


def status(dataset_id: Optional[str] = None) -> Dict[str, Any]:
    """Counts for active (or named) dataset across palace + kg."""
    reg = get_registry()
    did = resolve_dataset_id(dataset_id, registry=reg) or "default"
    mem_n = 0
    try:
        from .memory_palace import MemoryPalace

        mems = MemoryPalace().get_all_memories() or []
        mem_n = len(filter_by_dataset(mems, did, include_shared=False))
    except Exception:
        pass
    node_n = edge_n = 0
    try:
        from .knowledge_graph import get_default_graph

        g = get_default_graph()
        node_n = int(g.query_nodes(dataset_id=did, limit=5000).get("count") or 0)
        # approximate edges via neighbors aggregation is expensive; use status datasets
        st = g.status()
        _ = st
        edge_n = 0
        if hasattr(g, "count_edges"):
            edge_n = int(g.count_edges(dataset_id=did) or 0)
    except Exception:
        pass
    return {
        "ok": True,
        "product": "dataset_status",
        "active": reg.get_active(),
        "dataset_id": did,
        "palace_memories": mem_n,
        "kg_nodes": node_n,
        "kg_edges": edge_n,
        "message": f"Dataset {did}: {mem_n} memories, {node_n} kg nodes",
    }
