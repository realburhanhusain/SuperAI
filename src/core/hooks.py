"""Pre/post tool hooks (V6 N227)."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

_PRE: List[Callable[[str, Dict[str, Any]], Optional[Dict[str, Any]]]] = []
_POST: List[Callable[[str, Dict[str, Any], Dict[str, Any]], None]] = []


def register_pre(fn: Callable[[str, Dict[str, Any]], Optional[Dict[str, Any]]]) -> None:
    _PRE.append(fn)


def register_post(fn: Callable[[str, Dict[str, Any], Dict[str, Any]], None]) -> None:
    _POST.append(fn)


def clear_hooks() -> None:
    _PRE.clear()
    _POST.clear()


def run_pre(name: str, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return dict to short-circuit tool (block); None to continue."""
    for fn in _PRE:
        try:
            r = fn(name, args)
            if isinstance(r, dict):
                return r
        except Exception:
            continue
    return None


def run_post(name: str, args: Dict[str, Any], result: Dict[str, Any]) -> None:
    for fn in _POST:
        try:
            fn(name, args, result)
        except Exception:
            continue
