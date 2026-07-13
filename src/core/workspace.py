"""
Hard workspace jail (M3).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union


def workspace_root(override: Optional[str] = None) -> Path:
    raw = override or os.getenv("SUPERAI_WORKSPACE") or os.getcwd()
    return Path(raw).expanduser().resolve()


def assert_in_workspace(
    path: Union[str, Path],
    root: Optional[Path] = None,
    *,
    label: str = "path",
) -> Path:
    """Resolve path and ensure it is under workspace root."""
    base = root or workspace_root()
    p = Path(path).expanduser()
    # Allow relative paths from workspace
    if not p.is_absolute():
        p = base / p
    resolved = p.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as e:
        raise ValueError(
            f"{label} must be under workspace {base} (got {resolved}). "
            "Set SUPERAI_WORKSPACE or cd into project."
        ) from e
    return resolved


def safe_join(root: Path, *parts: str) -> Path:
    candidate = root.joinpath(*parts).resolve()
    candidate.relative_to(root.resolve())
    return candidate
