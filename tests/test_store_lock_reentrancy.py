"""
Store-lock re-entrancy and PATH resolution performance.

Both were found by profiling commands the contract sweep reported as "hangs".
They turned out not to be hangs at all — ``superai metrics`` took 60s and
``superai reflect`` ~57s, exceeding the 20s probe timeout. Two distinct causes,
one a latent deadlock and one a 14x redundant filesystem scan.
"""

from __future__ import annotations

import os
import shutil
import time

import pytest

from core import store_lock
from core.path_which import which_cmd


# ---------------------------------------------------------------------------
# Re-entrancy
# ---------------------------------------------------------------------------


def test_nested_store_lock_does_not_deadlock(tmp_path):
    """
    A nested acquire from the same thread must be a no-op, not a timeout.

    ``FileLock`` uses ``msvcrt.locking`` / ``flock`` on a file *handle*. A
    nested acquire opens a second handle, fails to take the byte range, and
    spins until it raises TimeoutError. That made it impossible to batch writes
    under one outer lock: every helper that locks internally had to be called
    unlocked, so a decay pass over N memories paid N full lock cycles.
    """
    start = time.time()
    with store_lock.store_lock(tmp_path, name="t.lock", timeout=5):
        with store_lock.store_lock(tmp_path, name="t.lock", timeout=5):
            with store_lock.store_lock(tmp_path, name="t.lock", timeout=5):
                pass
    # Without re-entrancy this would burn 5s per nested level, then raise.
    assert time.time() - start < 2.0


def test_nested_lock_releases_cleanly(tmp_path):
    """After nesting unwinds, the lock must be free for a fresh acquire."""
    with store_lock.store_lock(tmp_path, name="t.lock", timeout=5):
        with store_lock.store_lock(tmp_path, name="t.lock", timeout=5):
            pass
    assert not store_lock._HELD_LOCKS.roots
    with store_lock.store_lock(tmp_path, name="t.lock", timeout=5):
        pass
    assert not store_lock._HELD_LOCKS.roots


def test_held_key_cleared_on_exception(tmp_path):
    """An exception inside the lock must not strand the held-key marker."""
    with pytest.raises(RuntimeError):
        with store_lock.store_lock(tmp_path, name="t.lock", timeout=5):
            raise RuntimeError("boom")
    assert not store_lock._HELD_LOCKS.roots
    # Still acquirable afterwards.
    with store_lock.store_lock(tmp_path, name="t.lock", timeout=5):
        pass


def test_distinct_names_are_independent_locks(tmp_path):
    """Re-entrancy is keyed on (root, name), not root alone."""
    with store_lock.store_lock(tmp_path, name="a.lock", timeout=5):
        assert len(store_lock._HELD_LOCKS.roots) == 1
        with store_lock.store_lock(tmp_path, name="b.lock", timeout=5):
            assert len(store_lock._HELD_LOCKS.roots) == 2
    assert not store_lock._HELD_LOCKS.roots


def test_resolved_key_cache_is_consistent(tmp_path):
    """The resolve cache must return the same key it computed uncached."""
    raw = str(tmp_path)
    uncached = str(tmp_path.expanduser().resolve())
    assert store_lock._resolved_key(raw) == uncached
    assert store_lock._resolved_key(raw) == uncached  # second hit is cached


def test_thread_lock_identity_per_path(tmp_path):
    a = store_lock.thread_lock_for(tmp_path)
    b = store_lock.thread_lock_for(str(tmp_path))
    other = store_lock.thread_lock_for(tmp_path / "sub")
    assert a is b
    assert a is not other


# ---------------------------------------------------------------------------
# PATH resolution
# ---------------------------------------------------------------------------


def test_which_cmd_miss_is_not_far_slower_than_shutil():
    """
    A miss must not re-scan PATH once per PATHEXT entry.

    ``which_cmd`` used to retry every extension in PATHEXT, and each retry
    re-scans every PATH directory. With 14 PATHEXT entries and 52 PATH
    directories that was a 14x multiplier for no extra coverage: measured
    0.079s for ``shutil.which`` versus 1.089s here, which made
    ``ExternalCLIRegistry.discover()`` take 25.8s and ``superai metrics`` 60s.

    Generous bound — this guards against the 14x regression, not against
    ordinary filesystem variance.
    """
    name = "superai-definitely-not-installed-xyz"

    start = time.time()
    shutil.which(name)
    baseline = time.time() - start

    start = time.time()
    which_cmd(name)
    ours = time.time() - start

    assert ours < max(baseline * 6 + 0.30, 0.75), (
        f"which_cmd miss took {ours:.3f}s vs shutil {baseline:.3f}s — "
        "the PATHEXT fan-out regression is back"
    )


def test_which_cmd_still_finds_a_real_executable():
    """The speedup must not cost resolution coverage."""
    found = which_cmd("git") or which_cmd("python")
    assert found, "expected to resolve at least one of git/python on PATH"


def test_which_cmd_handles_empty_name():
    assert which_cmd("") is None


def test_shim_extensions_are_tried_when_pathext_omits_them(monkeypatch):
    """
    The hardening intent survives: a truncated PATHEXT still gets a fallback.

    This is the case the original loop existed for — npm ``.CMD`` shims on a
    machine whose PATHEXT does not list ``.CMD``.
    """
    if os.name != "nt":
        pytest.skip("Windows-only PATHEXT behaviour")

    monkeypatch.setenv("PATHEXT", ".EXE")
    tried: list = []

    def _fake_which(cand, *a, **k):
        tried.append(cand)
        return None

    monkeypatch.setattr(shutil, "which", _fake_which)
    which_cmd("sometool")

    # .EXE is already covered by PATHEXT, so it must not be retried;
    # .CMD and .BAT are not covered and must be.
    assert "sometool.CMD" in tried
    assert "sometool.BAT" in tried
    assert "sometool.EXE" not in tried
