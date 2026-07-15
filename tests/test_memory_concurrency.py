"""Concurrent Memory Palace safety (Phase 3 parallel sync)."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from core.memory_palace import MemoryPalace, get_shared_palace
from core.memory_sync import export_encrypted_memory, import_encrypted_memory
from core.store_lock import atomic_write_json, store_lock
from core.wings import WingsManager


@pytest.fixture
def mem_root(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    (tmp_path / ".superai").mkdir(parents=True)
    root = tmp_path / ".superai" / "memory"
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_concurrent_thread_stores(mem_root: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    palace = MemoryPalace(persist_directory=str(mem_root))

    def worker(i: int) -> str:
        return palace.store(
            f"Concurrent memory number {i} with enough text content for search.",
            tags=["learning", "coding"],
            metadata={"task_type": "coding", "success": True, "source": f"t{i}"},
        )

    ids = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(worker, i) for i in range(24)]
        for f in as_completed(futs):
            ids.append(f.result())

    assert len(ids) == 24
    assert len(set(ids)) == 24
    all_m = palace.get_all_memories()
    assert len(all_m) >= 24


def test_store_queued(mem_root: Path):
    palace = MemoryPalace(persist_directory=str(mem_root))
    ids = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = [
            pool.submit(
                palace.store_queued,
                f"Queued write {i} enough content here.",
                ["learning"],
                {"task_type": "general", "success": True},
            )
            for i in range(12)
        ]
        for f in as_completed(futs):
            ids.append(f.result())
    assert len(ids) == 12
    assert len(palace.get_all_memories()) >= 12


def test_shared_singleton(mem_root: Path):
    a = get_shared_palace(str(mem_root))
    b = get_shared_palace(str(mem_root))
    assert a is b


def test_atomic_write_and_lock(tmp_path: Path):
    p = tmp_path / "x.json"
    with store_lock(tmp_path, name="t.lock"):
        atomic_write_json(p, {"a": 1})
    assert p.exists()
    assert "a" in p.read_text(encoding="utf-8")


def test_wings_concurrent_assign(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)

    def worker(i: int):
        wm = WingsManager(path=tmp_path / ".superai" / "wings.json")
        return wm.assign(f"mem-{i}", "technical", "coding", note=str(i))

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(worker, range(20)))
    wm = WingsManager(path=tmp_path / ".superai" / "wings.json")
    # should not corrupt JSON
    assert wm.list_wings()
    assert len(wm.data.get("assignments") or []) >= 1


def test_memory_sync_merge_skip(mem_root: Path, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    # Use shared palace under home so sync sees it
    mp = get_shared_palace()
    mid = mp.store(
        "Unique sync content alpha beta gamma.",
        tags=["learning"],
        metadata={"task_type": "coding", "success": True},
    )
    assert mid
    dest = tmp_path / "bundle.bin"
    export_encrypted_memory("test-pass-word-xx", dest)
    r1 = import_encrypted_memory("test-pass-word-xx", dest, merge="skip")
    assert r1.get("ok") is True
    # second import should skip duplicates
    r2 = import_encrypted_memory("test-pass-word-xx", dest, merge="skip")
    assert r2.get("skipped", 0) >= 1 or r2.get("imported") == 0
