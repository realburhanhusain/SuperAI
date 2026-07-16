"""Universal model/CLI/tool timeouts (V6 M018)."""

from __future__ import annotations

import concurrent.futures
from typing import Any, Callable, Dict, Optional, TypeVar

from .tool_timeouts import get as get_timeout

T = TypeVar("T")


def run_with_timeout(
    fn: Callable[[], T],
    *,
    seconds: Optional[float] = None,
    kind: str = "model",
) -> T:
    timeout = float(seconds if seconds is not None else get_timeout(kind))
    if timeout <= 0:
        return fn()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn)
        try:
            return fut.result(timeout=timeout)
        except concurrent.futures.TimeoutError as e:
            raise TimeoutError(f"{kind}_timeout_after_{timeout}s") from e


def timeout_error_result(kind: str = "model", seconds: float = 0) -> Dict[str, Any]:
    from .spend_guard import ensure_public_result

    return ensure_public_result(
        {
            "ok": False,
            "status": "error",
            "error": f"timeout after {seconds}s",
            "error_code": "timeout",
            "blocked": False,
        },
        ok=False,
    )
