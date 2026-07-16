"""
PATH resolution hardened for Windows (Improvement Phase 6).

shutil.which sometimes misses .CMD/.BAT shims under npm/AppData.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Optional, Sequence


def which_cmd(name: str) -> Optional[str]:
    """Resolve executable on PATH; try Windows extensions explicitly."""
    if not name:
        return None
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        # PATHEXT order
        exts = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")
        for ext in exts:
            e = ext if ext.startswith(".") else f".{ext}"
            cand = name if name.lower().endswith(e.lower()) else f"{name}{e}"
            found = shutil.which(cand)
            if found:
                return found
        # Common npm global locations
        appdata = os.environ.get("APPDATA") or ""
        local = os.environ.get("LOCALAPPDATA") or ""
        extras = [
            Path(appdata) / "npm",
            Path(local) / "Programs",
            Path.home() / "AppData" / "Roaming" / "npm",
            Path.home() / ".grok" / "bin",
            Path.home() / "AppData" / "Local" / "Programs" / "cursor" / "resources" / "app" / "bin",
        ]
        for folder in extras:
            if not folder.is_dir():
                continue
            for ext in ("", ".exe", ".cmd", ".bat", ".CMD", ".EXE"):
                p = folder / f"{name}{ext}"
                if p.is_file():
                    return str(p)
    return None


def which_any(names: Sequence[str]) -> Optional[str]:
    for n in names:
        p = which_cmd(n)
        if p:
            return p
    return None


def resolve_candidates(command: str, detects: Optional[List[str]] = None) -> Optional[str]:
    for cand in [command, *(detects or [])]:
        p = which_cmd(cand)
        if p:
            return p
    return None
