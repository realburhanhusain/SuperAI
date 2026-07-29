"""
PATH resolution hardened for Windows (Improvement Phase 6).

shutil.which sometimes misses .CMD/.BAT shims under npm/AppData.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Optional, Sequence


#: Shim extensions worth probing when PATHEXT does not already cover them.
_SHIM_EXTS = (".CMD", ".BAT", ".EXE", ".COM")


def which_cmd(name: str) -> Optional[str]:
    """
    Resolve executable on PATH; try Windows extensions explicitly.

    Performance note, because this sits on a hot path. ``shutil.which`` already
    tries every extension in ``PATHEXT``. This function used to re-try *all* of
    them itself, and each retry re-scans every PATH directory — with 14 PATHEXT
    entries and 52 PATH directories that is a 14x multiplier buying no extra
    coverage. Measured: 0.079s for ``shutil.which`` on a miss versus 1.089s
    here, which made ``ExternalCLIRegistry.discover()`` take 25.8s for nine
    tools and ``superai metrics`` take 60s.

    The hardening intent is kept. A truncated or customised ``PATHEXT`` really
    can omit ``.CMD``, which is how npm shims get missed — so the fallback still
    runs, but only for extensions ``PATHEXT`` does not already list. On a
    default Windows install that is none of them.
    """
    if not name:
        return None
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        covered = {
            e if e.startswith(".") else f".{e}"
            for e in (
                x.strip().upper()
                for x in os.environ.get("PATHEXT", "").split(";")
                if x.strip()
            )
        }
        for ext in _SHIM_EXTS:
            if ext in covered:
                continue  # shutil.which already tried this one
            cand = name if name.upper().endswith(ext) else f"{name}{ext}"
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
