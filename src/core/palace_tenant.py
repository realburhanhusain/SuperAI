"""
Multi-user Memory Palace tenant context (Phase 8 N7 / MoSCoW N7).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def current_tenant(config: Any = None) -> str:
    env = (os.getenv("SUPERAI_TENANT_ID") or "").strip()
    if env:
        return env
    try:
        if config is None:
            from .config import Config

            config = Config()
        t = (config.get("tenant_id") or config.get("palace_tenant") or "").strip()
        if t:
            return t
    except Exception:
        pass
    return "default"


def tenant_tag(tenant: Optional[str] = None) -> str:
    t = (tenant or current_tenant()).strip() or "default"
    return f"tenant:{t}"


def scope_metadata(meta: Optional[Dict[str, Any]] = None, tenant: Optional[str] = None) -> Dict[str, Any]:
    m = dict(meta or {})
    m["tenant_id"] = (tenant or current_tenant())
    tag = tenant_tag(m["tenant_id"])
    tags = m.get("tags")
    if isinstance(tags, list):
        if tag not in tags:
            tags = list(tags) + [tag]
        m["tags"] = tags
    else:
        m["tags"] = [tag]
    return m


def export_tenant_memories(
    tenant: Optional[str] = None,
    dest: Optional[Path] = None,
    *,
    limit: int = 5000,
) -> Dict[str, Any]:
    """
    N7: export memories tagged for a tenant to a JSON file.
    """
    tid = (tenant or current_tenant()).strip() or "default"
    tag = tenant_tag(tid)
    out_path = Path(
        dest
        or (
            Path.home()
            / ".superai"
            / "tenants"
            / f"export_{tid}_{int(time.time())}.json"
        )
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, Any]] = []
    try:
        from .memory_palace import MemoryPalace

        mp = MemoryPalace()
        # Prefer list API; fall back to in-memory list
        memories = []
        if hasattr(mp, "list_memories"):
            memories = mp.list_memories(limit=limit) or []
        elif hasattr(mp, "memories"):
            memories = list(mp.memories or [])[:limit]
        for mem in memories:
            if not isinstance(mem, dict):
                continue
            meta = mem.get("metadata") if isinstance(mem.get("metadata"), dict) else {}
            tags = meta.get("tags") or mem.get("tags") or []
            if isinstance(tags, str):
                tags = [tags]
            tid_meta = str(meta.get("tenant_id") or "")
            if tag in tags or tid_meta == tid or tid == "default":
                # for default, still filter if other tenant tags present
                if tid != "default" and tag not in tags and tid_meta != tid:
                    continue
                if tid == "default" and any(
                    str(t).startswith("tenant:") and t != tag for t in tags
                ):
                    continue
                rows.append(mem)
            if len(rows) >= limit:
                break
    except Exception as e:
        return {"ok": False, "error": str(e)[:300], "tenant_id": tid}
    payload = {
        "version": 1,
        "tenant_id": tid,
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "count": len(rows),
        "memories": rows,
    }
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return {
        "ok": True,
        "tenant_id": tid,
        "path": str(out_path),
        "count": len(rows),
    }


def import_tenant_memories(
    src: Path,
    *,
    tenant: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    N7: import memories from export JSON into palace with tenant tags.
    """
    p = Path(src)
    if not p.is_file():
        return {"ok": False, "error": "not_found", "path": str(p)}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": f"bad_json:{e}"}
    tid = (tenant or data.get("tenant_id") or current_tenant()).strip() or "default"
    mems = data.get("memories") if isinstance(data, dict) else None
    if not isinstance(mems, list):
        return {"ok": False, "error": "no_memories"}
    if dry_run:
        return {"ok": True, "dry_run": True, "tenant_id": tid, "would_import": len(mems)}
    imported = 0
    errors = 0
    try:
        from .central_memory import write_back
    except Exception:
        write_back = None  # type: ignore
    try:
        from .memory_palace import MemoryPalace

        mp = MemoryPalace()
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}

    for mem in mems:
        if not isinstance(mem, dict):
            continue
        content = (
            mem.get("content")
            or mem.get("text")
            or mem.get("summary")
            or mem.get("output")
            or ""
        )
        if not content:
            continue
        meta = scope_metadata(
            mem.get("metadata") if isinstance(mem.get("metadata"), dict) else {},
            tenant=tid,
        )
        try:
            if write_back:
                write_back(
                    task=str(mem.get("task") or content)[:500],
                    source=str(mem.get("source") or "tenant_import"),
                    model_or_cli=str(mem.get("model_or_cli") or "import"),
                    success=True,
                    output=str(content)[:4000],
                    tags=list(meta.get("tags") or []),
                    metadata=meta,
                )
            elif hasattr(mp, "add_memory"):
                mp.add_memory(str(content)[:4000], metadata=meta)
            else:
                errors += 1
                continue
            imported += 1
        except Exception:
            errors += 1
    return {
        "ok": True,
        "tenant_id": tid,
        "imported": imported,
        "errors": errors,
        "source": str(p),
    }
