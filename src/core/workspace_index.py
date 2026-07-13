"""
Lightweight workspace / code map (S19).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .workspace import workspace_root

SKIP_DIRS = {
    ".git",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".superai",
    ".tox",
}


def build_index(
    root: Optional[Path] = None,
    max_files: int = 500,
) -> Dict[str, Any]:
    root = (root or workspace_root()).resolve()
    files: List[Dict[str, Any]] = []
    symbols: List[Dict[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if len(files) >= max_files:
                break
            p = Path(dirpath) / fn
            try:
                rel = str(p.relative_to(root)).replace("\\", "/")
            except ValueError:
                continue
            if p.suffix.lower() in {
                ".py",
                ".ts",
                ".tsx",
                ".js",
                ".jsx",
                ".go",
                ".rs",
                ".java",
                ".md",
            }:
                files.append({"path": rel, "size": p.stat().st_size})
                if p.suffix == ".py" and p.stat().st_size < 200_000:
                    try:
                        text = p.read_text(encoding="utf-8", errors="replace")
                        for m in re.finditer(
                            r"^(?:async\s+)?def\s+(\w+)|class\s+(\w+)",
                            text,
                            re.M,
                        ):
                            name = m.group(1) or m.group(2)
                            symbols.append({"file": rel, "name": name})
                    except OSError:
                        pass
        if len(files) >= max_files:
            break
    return {
        "root": str(root),
        "file_count": len(files),
        "files": files[:max_files],
        "symbols": symbols[:2000],
    }


def search_index(query: str, index: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    index = index or build_index()
    q = (query or "").lower()
    hits = []
    for s in index.get("symbols") or []:
        if q in str(s.get("name") or "").lower() or q in str(s.get("file") or "").lower():
            hits.append(s)
    for f in index.get("files") or []:
        if q in str(f.get("path") or "").lower():
            hits.append({"file": f["path"], "name": "(file)"})
    return hits[:50]
