"""Project-scoped vs global memory (V6 S171)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional


def project_id(root: Optional[Path] = None) -> str:
    p = Path(root or Path.cwd()).resolve()
    return "proj-" + hashlib.sha256(str(p).encode("utf-8")).hexdigest()[:12]


def project_tag(root: Optional[Path] = None) -> str:
    return f"project:{project_id(root)}"


def scope_tags(
    tags: Optional[List[str]] = None,
    *,
    root: Optional[Path] = None,
    global_scope: bool = False,
) -> List[str]:
    out = list(tags or [])
    if not global_scope:
        t = project_tag(root)
        if t not in out:
            out.append(t)
    return out


def write_project_memory(
    content: str,
    *,
    root: Optional[Path] = None,
    global_scope: bool = False,
) -> Dict[str, Any]:
    try:
        from .central_memory import write_back

        tags = scope_tags(["memory"], root=root, global_scope=global_scope)
        return write_back(
            task=content[:200],
            source="project_memory",
            model_or_cli="local",
            success=True,
            output=content[:4000],
            tags=tags,
            metadata={"project_id": project_id(root) if not global_scope else "global"},
        )
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}
