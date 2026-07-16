"""
Cooperative cancel token (V5 M3).
"""

from __future__ import annotations

import threading
from typing import Optional


class CancelToken:
    def __init__(self) -> None:
        self._ev = threading.Event()

    def cancel(self) -> None:
        self._ev.set()

    def is_cancelled(self) -> bool:
        return self._ev.is_set()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled():
            raise InterruptedError("cancelled")


# process-optional global for Ctrl+C wiring
_CURRENT: Optional[CancelToken] = None


def set_current(token: Optional[CancelToken]) -> None:
    global _CURRENT
    _CURRENT = token


def current() -> Optional[CancelToken]:
    return _CURRENT
