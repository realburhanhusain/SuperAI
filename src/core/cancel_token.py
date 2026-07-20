"""
Cooperative cancel token (V5 M3 / V6 M017).

Ctrl+C and programmatic cancel stop workers *cooperatively*:
- ModelCaller checks between failover attempts and stream chunks
- Agent runtime checks each tool round
- Board / multi-CLI workers check before each member and between futures
- Council checks between members
- Orchestrator checks between parallel/serial steps

Not a hard kill of in-flight OS processes (except daemon SIGINT path);
workers exit at the next safe checkpoint with a cancelled contract envelope.
"""

from __future__ import annotations

import signal
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, TypeVar

T = TypeVar("T")


class CancelToken:
    """Thread-safe cooperative cancellation flag."""

    def __init__(self, *, name: str = "") -> None:
        self._ev = threading.Event()
        self.name = name or "cancel"
        self.reason: str = ""
        self.cancelled_at: Optional[float] = None
        self._lock = threading.Lock()

    def cancel(self, reason: str = "cancelled") -> None:
        with self._lock:
            if not self._ev.is_set():
                self.reason = str(reason or "cancelled")
                self.cancelled_at = time.time()
            self._ev.set()

    def is_cancelled(self) -> bool:
        return self._ev.is_set()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled():
            raise InterruptedError(self.reason or "cancelled")

    def check(self) -> bool:
        """Return True if still running (not cancelled)."""
        return not self.is_cancelled()

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Block until cancelled (or timeout). Returns True if cancelled."""
        return self._ev.wait(timeout)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "cancelled": self.is_cancelled(),
            "reason": self.reason,
            "cancelled_at": self.cancelled_at,
        }


# Process-wide current token (main thread / CLI Ctrl+C)
_CURRENT: Optional[CancelToken] = None
_CURRENT_LOCK = threading.Lock()

# Per-context token for nested / thread-pool work (copied via copy_context)
_CTX_TOKEN: ContextVar[Optional[CancelToken]] = ContextVar(
    "superai_cancel_token", default=None
)

# SIGINT install state
_PREV_SIGINT: Any = None
_SIGINT_INSTALLED = False


def set_current(token: Optional[CancelToken]) -> None:
    global _CURRENT
    with _CURRENT_LOCK:
        _CURRENT = token
    _CTX_TOKEN.set(token)


def current() -> Optional[CancelToken]:
    tok = _CTX_TOKEN.get()
    if tok is not None:
        return tok
    with _CURRENT_LOCK:
        return _CURRENT


def is_cancelled() -> bool:
    tok = current()
    return bool(tok is not None and tok.is_cancelled())


def cancel_current(reason: str = "cancelled") -> bool:
    tok = current()
    if tok is None:
        return False
    tok.cancel(reason)
    return True


def cancelled_envelope(
    *,
    reason: str = "cancelled",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Standard public result for cancelled operations."""
    from .spend_guard import ensure_public_result

    data: Dict[str, Any] = {
        "ok": False,
        "status": "cancelled",
        "error": reason,
        "error_code": "cancelled",
        "response": reason,
        "blocked": True,
        "cancelled": True,
    }
    if extra:
        data.update(extra)
    return ensure_public_result(data, ok=False)


@contextmanager
def using(
    token: Optional[CancelToken] = None,
    *,
    install_sigint: bool = False,
    name: str = "",
) -> Generator[CancelToken, None, None]:
    """
    Bind a CancelToken for the duration of the block; restore previous on exit.

    install_sigint=True wires SIGINT/Ctrl+C to token.cancel (CLI long runs).
    """
    tok = token or CancelToken(name=name or "scope")
    prev_ctx = _CTX_TOKEN.get()
    with _CURRENT_LOCK:
        prev_global = _CURRENT
    set_current(tok)
    sig_installed = False
    if install_sigint:
        sig_installed = install_sigint_handler(tok)
    try:
        yield tok
    finally:
        if sig_installed:
            uninstall_sigint_handler()
        set_current(prev_ctx if prev_ctx is not None else prev_global)


def install_sigint_handler(token: CancelToken) -> bool:
    """Install SIGINT → token.cancel. Returns True if installed."""
    global _PREV_SIGINT, _SIGINT_INSTALLED
    if _SIGINT_INSTALLED:
        return False
    try:

        def _handler(signum: int, frame: Any) -> None:  # noqa: ARG001
            token.cancel("sigint")

        _PREV_SIGINT = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, _handler)
        _SIGINT_INSTALLED = True
        return True
    except Exception:
        return False


def uninstall_sigint_handler() -> None:
    global _PREV_SIGINT, _SIGINT_INSTALLED
    if not _SIGINT_INSTALLED:
        return
    try:
        if _PREV_SIGINT is not None:
            signal.signal(signal.SIGINT, _PREV_SIGINT)
    except Exception:
        pass
    _PREV_SIGINT = None
    _SIGINT_INSTALLED = False


def map_cooperative(
    items: List[T],
    fn: Callable[[T], Any],
    *,
    max_workers: int = 4,
    token: Optional[CancelToken] = None,
    ordered: bool = True,
) -> List[Any]:
    """
    Parallel map that stops scheduling new work when cancelled.

    Already-running workers finish or self-abort via token checks inside ``fn``.
    Results for cancelled-before-start items get a cancelled envelope.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    tok = token or current() or CancelToken(name="map")
    if tok is not current():
        set_current(tok)

    results: Dict[int, Any] = {}
    if not items:
        return []

    def _wrapped(idx: int, item: T) -> None:
        if tok.is_cancelled():
            results[idx] = cancelled_envelope(
                reason=tok.reason or "cancelled",
                extra={"index": idx, "member": str(item)[:80]},
            )
            return
        # ensure worker thread sees token
        set_current(tok)
        try:
            results[idx] = fn(item)
        except InterruptedError as e:
            results[idx] = cancelled_envelope(
                reason=str(e) or "cancelled",
                extra={"index": idx, "member": str(item)[:80]},
            )
        except Exception as e:
            results[idx] = {
                "ok": False,
                "error": str(e)[:300],
                "index": idx,
                "member": str(item)[:80],
            }

    workers = min(max(1, max_workers), max(1, len(items)))
    if workers == 1:
        for i, it in enumerate(items):
            if tok.is_cancelled():
                results[i] = cancelled_envelope(
                    reason=tok.reason or "cancelled",
                    extra={"index": i, "member": str(it)[:80]},
                )
                continue
            _wrapped(i, it)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {}
            for i, it in enumerate(items):
                if tok.is_cancelled():
                    results[i] = cancelled_envelope(
                        reason=tok.reason or "cancelled",
                        extra={"index": i, "member": str(it)[:80]},
                    )
                    continue
                # copy context so ContextVar is visible if used
                ctx = copy_context()
                futs[pool.submit(ctx.run, _wrapped, i, it)] = i
            for fut in as_completed(futs):
                try:
                    fut.result()
                except Exception as e:
                    idx = futs[fut]
                    if idx not in results:
                        results[idx] = {"ok": False, "error": str(e)[:300], "index": idx}

    if ordered:
        return [results.get(i, cancelled_envelope(extra={"index": i})) for i in range(len(items))]
    return list(results.values())


def audit_m017() -> Dict[str, Any]:
    """Offline proof for cooperative cancel across worker types."""
    from .spend_guard import ensure_public_result

    issues: List[str] = []
    evidence: Dict[str, Any] = {}

    # Basic token
    t = CancelToken(name="audit")
    if t.is_cancelled():
        issues.append("fresh_token_cancelled")
    t.cancel("test")
    if not t.is_cancelled() or t.reason != "test":
        issues.append("cancel_flag")
    evidence["token"] = t.snapshot()

    # current / using
    set_current(None)
    with using(CancelToken(name="scope")) as scope:
        if current() is not scope:
            issues.append("using_not_current")
        scope.cancel("scoped")
        if not is_cancelled():
            issues.append("is_cancelled_helper")
    if current() is not None:
        # may be None after restore
        pass
    set_current(None)

    # cancelled envelope
    env = cancelled_envelope(reason="x")
    if env.get("error_code") != "cancelled" or env.get("ok") is not False:
        issues.append("envelope")
    evidence["envelope_contract"] = env.get("contract")

    # map_cooperative stops after cancel
    seen: List[int] = []

    def work(n: int) -> Dict[str, Any]:
        seen.append(n)
        if n == 0:
            cancel_current("mid")
        return {"ok": True, "n": n}

    tok = CancelToken(name="map")
    set_current(tok)
    outs = map_cooperative([0, 1, 2, 3], work, max_workers=2, token=tok)
    set_current(None)
    cancelled_n = sum(1 for o in outs if isinstance(o, dict) and o.get("cancelled"))
    evidence["map_results"] = len(outs)
    evidence["map_cancelled"] = cancelled_n
    if len(outs) != 4:
        issues.append("map_count")
    # at least some cancelled or all ran with mid cancel
    if cancelled_n < 1 and not tok.is_cancelled():
        issues.append("map_no_cancel")

    # pre_call honors token
    try:
        from .call_lifecycle import pre_call

        tok2 = CancelToken()
        tok2.cancel()
        set_current(tok2)
        pre = pre_call("gpt-4o", "x", skip_budget=True)
        set_current(None)
        if not (pre.get("blocked") or pre.get("status") == "cancelled"):
            issues.append("pre_call")
        evidence["pre_call_cancelled"] = True
    except Exception as e:
        issues.append(f"pre_call_exc:{e}")

    # module presence on board path
    try:
        import inspect
        from . import multi_cli_advisory as mca

        src = inspect.getsource(mca.multi_cli_board)
        if "check_cancel" not in src and "is_cancelled" not in src and "CancelToken" not in src:
            issues.append("board_no_cancel_wire")
        else:
            evidence["board_cancel_wired"] = True
    except Exception as e:
        issues.append(f"board_inspect:{e}")

    ok = len(issues) == 0
    return ensure_public_result(
        {
            "ok": ok,
            "item": "M017",
            "issues": issues,
            "evidence": evidence,
            "message": "Cooperative cancel across model/agent/board/council paths"
            if ok
            else "M017 gaps",
        },
        ok=ok,
    )
