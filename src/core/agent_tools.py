"""
Minimal in-process tools (Improvement Phase 5) — workspace-jailed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def _root() -> Path:
    try:
        from .workspace import workspace_root

        return Path(workspace_root())
    except Exception:
        return Path(os.getenv("SUPERAI_WORKSPACE") or Path.cwd()).resolve()


def _safe(path: str) -> Path:
    root = _root().resolve()
    p = (root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if not str(p).startswith(str(root)):
        raise PermissionError(f"Path escapes workspace: {path}")
    return p


def tool_read(path: str, max_chars: int = 20000) -> Dict[str, Any]:
    p = _safe(path)
    if not p.is_file():
        return {"ok": False, "error": "not_found", "path": str(p)}
    text = p.read_text(encoding="utf-8", errors="replace")[:max_chars]
    return {"ok": True, "path": str(p), "content": text, "chars": len(text)}


def tool_write(path: str, content: str, *, dry_run: bool = False) -> Dict[str, Any]:
    p = _safe(path)
    if dry_run:
        return {"ok": True, "dry_run": True, "path": str(p), "bytes": len(content.encode())}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(p), "bytes": len(content.encode())}


def tool_glob(pattern: str, limit: int = 50) -> Dict[str, Any]:
    root = _root()
    hits = [str(x.relative_to(root)) for x in root.glob(pattern)][:limit]
    return {"ok": True, "pattern": pattern, "hits": hits, "count": len(hits)}


def tool_grep(pattern: str, path: str = ".", limit: int = 40) -> Dict[str, Any]:
    import re

    root = _safe(path) if path not in {".", ""} else _root()
    rx = re.compile(pattern)
    hits: List[str] = []
    if root.is_file():
        files = [root]
    else:
        files = [p for p in root.rglob("*") if p.is_file()][:500]
    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                try:
                    rel = str(fp.relative_to(_root()))
                except Exception:
                    rel = str(fp)
                hits.append(f"{rel}:{i}:{line[:200]}")
                if len(hits) >= limit:
                    return {"ok": True, "hits": hits, "count": len(hits)}
    return {"ok": True, "hits": hits, "count": len(hits)}


def list_tools() -> List[str]:
    return ["read", "write", "glob", "grep", "diff_apply"]


def run_tool(name: str, **kwargs: Any) -> Dict[str, Any]:
    """Dispatch a tool by name with permission-aware dry_run."""
    from .permission_mode import force_dry_run, mode_from_config

    mode = kwargs.pop("permission_mode", None) or mode_from_config()
    dry = force_dry_run(mode) or bool(kwargs.pop("dry_run", False))
    n = (name or "").lower().strip()
    try:
        if n == "read":
            return tool_read(kwargs.get("path") or kwargs.get("file") or "")
        if n == "write":
            return tool_write(
                kwargs.get("path") or "",
                kwargs.get("content") or "",
                dry_run=dry,
            )
        if n == "glob":
            return tool_glob(kwargs.get("pattern") or "**/*")
        if n == "grep":
            return tool_grep(kwargs.get("pattern") or "", kwargs.get("path") or ".")
        if n in {"diff_apply", "apply_diff", "git_apply"}:
            from .git_diff_apply import apply_unified_diff

            return apply_unified_diff(
                kwargs.get("diff") or kwargs.get("content") or "",
                dry_run=dry,
                commit=bool(kwargs.get("commit")),
                message=str(kwargs.get("message") or "superai: apply diff"),
            )
        return {"ok": False, "error": f"unknown_tool:{name}", "tools": list_tools()}
    except Exception as e:
        return {"ok": False, "error": str(e)[:400]}


def parse_tool_directives(text: str) -> List[Dict[str, Any]]:
    """
    Parse simple agent directives:
      /tool read path=src/foo.py
      /tool grep pattern=TODO path=.
      /tool write path=x content=hello
    """
    import re
    import shlex

    out: List[Dict[str, Any]] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line.startswith("/tool"):
            continue
        rest = line[5:].strip()
        if not rest:
            continue
        parts = rest.split(None, 1)
        tname = parts[0]
        kwargs: Dict[str, Any] = {}
        if len(parts) > 1:
            # key=value pairs
            try:
                tokens = shlex.split(parts[1])
            except Exception:
                tokens = parts[1].split()
            for tok in tokens:
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    kwargs[k.strip()] = v.strip()
                else:
                    kwargs.setdefault("path", tok)
        out.append({"tool": tname, "kwargs": kwargs})
    return out


def execute_directives(
    text: str, *, permission_mode: Optional[str] = None
) -> List[Dict[str, Any]]:
    results = []
    for d in parse_tool_directives(text):
        r = run_tool(d["tool"], permission_mode=permission_mode, **d.get("kwargs") or {})
        results.append({"directive": d, "result": r})
    return results
