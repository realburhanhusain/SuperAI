"""
Lightweight progress event stream for run/board (Improvement Phase 5).
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional


class ProgressBus:
    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []
        self._hooks: List[Callable[[Dict[str, Any]], None]] = []

    def on(self, hook: Callable[[Dict[str, Any]], None]) -> None:
        self._hooks.append(hook)

    def emit(self, kind: str, **payload: Any) -> Dict[str, Any]:
        ev = {"ts": time.time(), "kind": kind, **payload}
        self.events.append(ev)
        if len(self.events) > 200:
            self.events = self.events[-200:]
        for h in self._hooks:
            try:
                h(ev)
            except Exception:
                pass
        return ev

    def snapshot(self) -> List[Dict[str, Any]]:
        return list(self.events)


_global_bus: Optional[ProgressBus] = None


def get_progress_bus() -> ProgressBus:
    global _global_bus
    if _global_bus is None:
        _global_bus = ProgressBus()
    return _global_bus
