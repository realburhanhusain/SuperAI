"""
Suite-wide isolation from the developer's real home directory.

Why this file exists
--------------------
The suite had no ``conftest.py``, so nothing stopped a test from reading and
writing the real ``~/.superai``. Many tests do sandbox themselves with
``monkeypatch.setattr(Path, "home", tmp_path)``, but that is opt-in and several
do not — ``test_central_memory_sanitize`` calls ``central_memory.write_back()``,
which reaches ``get_shared_palace()`` with no patching at all.

The consequences were not theoretical:

1. Running the suite mutated the developer's real memory store.
2. Worse, it took that store's file lock. A run that died mid-write left the
   lock held, and because ``store_lock`` waits 45s before giving up, every
   later run then blocked 45s per write and eventually timed out. That is the
   shape of the Windows CI hang: a full-suite run that stalls for hours and
   then fails.

Sandboxing ``HOME`` for the whole session removes the entire class of problem.
Tests that need particular home content still set it up themselves; they just
do it inside the sandbox now.

Scope
-----
Session-scoped on purpose. A per-test home would be stricter, but several tests
accumulate state across cases within a file, and changing that is a separate
piece of work from stopping the suite touching real user data.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _sandbox_home():
    """Point HOME, USERPROFILE and ``Path.home()`` at a throwaway directory."""
    # ignore_cleanup_errors: on Windows a still-open sqlite handle in the
    # memory store blocks deletion of the sandbox, and a failed cleanup must
    # not turn into a test error. The directory is in the OS temp tree.
    with tempfile.TemporaryDirectory(
        prefix="superai-tests-", ignore_cleanup_errors=True
    ) as tmp:
        sandbox = Path(tmp)
        (sandbox / ".superai").mkdir(parents=True, exist_ok=True)

        real_home = Path.home
        saved_env = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE", "USERNAME")}

        os.environ["HOME"] = str(sandbox)
        os.environ["USERPROFILE"] = str(sandbox)
        # Path.home() is a classmethod; replace it on the class so every call
        # site sees the sandbox, including ones that never take a monkeypatch.
        Path.home = classmethod(lambda cls: cls(str(sandbox)))  # type: ignore[assignment]

        # Anything already cached against the real home must be dropped, or the
        # sandbox is bypassed by a singleton built at import time.
        try:
            from core import memory_palace

            memory_palace._PALACE_SINGLETONS.clear()
        except Exception:
            pass
        try:
            from core import store_lock

            store_lock._RESOLVED_KEYS.clear()
            store_lock._THREAD_LOCKS.clear()
        except Exception:
            pass

        try:
            yield sandbox
        finally:
            Path.home = real_home  # type: ignore[assignment]
            for key, value in saved_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


@pytest.fixture(autouse=True)
def _guard_real_home(_sandbox_home):
    """
    Fail loudly if a test escapes the sandbox.

    A silent escape is how this went unnoticed for so long: the suite passed
    while quietly writing real data. Better to break the test than to keep
    mutating the developer's memory store.
    """
    yield
    resolved = Path.home()
    assert str(resolved).startswith(str(_sandbox_home)), (
        f"a test restored the real home ({resolved}); suite isolation is broken"
    )
