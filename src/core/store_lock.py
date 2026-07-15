"""
Cross-process + cross-thread store safety for SuperAI Memory Palace and sidecars.

- FileLock: exclusive lock file (Windows msvcrt / Unix fcntl)
- atomic_write_*: unique tmp + retry replace (Windows-safe)
- Shared thread RLock helpers for in-process multi-thread writers
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Union

# Process-global locks keyed by resolved path (threads within one process)
_THREAD_LOCKS: Dict[str, threading.RLock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def thread_lock_for(path: Union[str, Path]) -> threading.RLock:
    key = str(Path(path).expanduser().resolve())
    with _THREAD_LOCKS_GUARD:
        if key not in _THREAD_LOCKS:
            _THREAD_LOCKS[key] = threading.RLock()
        return _THREAD_LOCKS[key]


class FileLock:
    """
    Exclusive file lock with timeout. Safe across processes on Windows and Unix.
    """

    def __init__(self, lock_path: Union[str, Path], timeout: float = 30.0):
        self.lock_path = Path(lock_path)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self._fh = None

    def acquire(self) -> None:
        self._fh = open(self.lock_path, "a+b")
        # Ensure at least 1 byte exists for msvcrt.locking
        try:
            self._fh.seek(0, os.SEEK_END)
            if self._fh.tell() == 0:
                self._fh.write(b"\0")
                self._fh.flush()
        except OSError:
            pass
        deadline = time.time() + self.timeout
        last_err: Optional[BaseException] = None
        while time.time() < deadline:
            try:
                if sys.platform == "win32":
                    import msvcrt

                    self._fh.seek(0)
                    # lock 1 byte exclusive non-blocking
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except (OSError, BlockingIOError) as e:
                last_err = e
                time.sleep(0.02)
        raise TimeoutError(
            f"Could not acquire lock {self.lock_path} within {self.timeout}s: {last_err}"
        )

    def release(self) -> None:
        if not self._fh:
            return
        try:
            if sys.platform == "win32":
                import msvcrt

                self._fh.seek(0)
                try:
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                import fcntl

                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            try:
                self._fh.close()
            except OSError:
                pass
            self._fh = None

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, *args: Any) -> None:
        self.release()


@contextmanager
def store_lock(
    root: Union[str, Path],
    *,
    name: str = "store.lock",
    timeout: float = 30.0,
) -> Iterator[None]:
    """
    Thread + process lock for a store root directory.
    Hold both so multi-thread and multi-process writers serialize.
    """
    root_p = Path(root).expanduser()
    root_p.mkdir(parents=True, exist_ok=True)
    tlock = thread_lock_for(root_p)
    flock = FileLock(root_p / name, timeout=timeout)
    with tlock:
        with flock:
            yield


def atomic_write_text(
    path: Union[str, Path],
    text: str,
    *,
    encoding: str = "utf-8",
    retries: int = 12,
) -> None:
    """Write text via unique tmp + os.replace with Windows PermissionError retry."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(
        f"{path.stem}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex[:8]}.tmp"
    )
    tmp.write_text(text, encoding=encoding)
    last_err: Optional[BaseException] = None
    for attempt in range(retries):
        try:
            os.replace(str(tmp), str(path))
            return
        except PermissionError as e:
            last_err = e
            time.sleep(0.015 * (attempt + 1))
        except OSError as e:
            last_err = e
            time.sleep(0.015 * (attempt + 1))
    try:
        path.write_text(text, encoding=encoding)
    except OSError:
        if last_err:
            raise last_err
        raise
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def atomic_write_json(
    path: Union[str, Path],
    data: Any,
    *,
    indent: int = 2,
) -> None:
    atomic_write_text(
        path,
        json.dumps(data, indent=indent, default=str),
        encoding="utf-8",
    )


def atomic_write_bytes(path: Union[str, Path], data: bytes, retries: int = 12) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(
        f"{path.stem}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex[:8]}.tmp"
    )
    tmp.write_bytes(data)
    last_err: Optional[BaseException] = None
    for attempt in range(retries):
        try:
            os.replace(str(tmp), str(path))
            return
        except PermissionError as e:
            last_err = e
            time.sleep(0.015 * (attempt + 1))
        except OSError as e:
            last_err = e
            time.sleep(0.015 * (attempt + 1))
    try:
        path.write_bytes(data)
    except OSError:
        if last_err:
            raise last_err
        raise
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


class WriteQueue:
    """
    Serialize write callables on a background thread (optional multi-CLI fan-out).
    Callers can submit(fn) and wait with .result().
    """

    def __init__(self, name: str = "memory"):
        self._q: list = []
        self._cv = threading.Condition()
        self._closed = False
        self._thread = threading.Thread(
            target=self._worker, name=f"superai-writeq-{name}", daemon=True
        )
        self._thread.start()

    def _worker(self) -> None:
        while True:
            with self._cv:
                while not self._q and not self._closed:
                    self._cv.wait(timeout=0.5)
                if not self._q:
                    if self._closed:
                        return
                    continue
                item = self._q.pop(0)
            fn, event, box = item
            try:
                box["result"] = fn()
            except Exception as e:  # noqa: BLE001
                box["error"] = e
            finally:
                event.set()

    def submit(self, fn, timeout: float = 120.0) -> Any:
        event = threading.Event()
        box: Dict[str, Any] = {}
        with self._cv:
            if self._closed:
                raise RuntimeError("WriteQueue closed")
            self._q.append((fn, event, box))
            self._cv.notify()
        if not event.wait(timeout=timeout):
            raise TimeoutError(
                f"WriteQueue submit timed out after {timeout}s "
                "(worker may still be running)"
            )
        if "error" in box:
            raise box["error"]
        return box.get("result")

    def close(self) -> None:
        with self._cv:
            self._closed = True
            self._cv.notify_all()


_memory_write_queue: Optional[WriteQueue] = None
_memory_write_queue_lock = threading.Lock()


def memory_write_queue() -> WriteQueue:
    global _memory_write_queue
    with _memory_write_queue_lock:
        if _memory_write_queue is None:
            _memory_write_queue = WriteQueue("memory")
        return _memory_write_queue
