"""Default Memory Palace backend: pgvector / SQL cosine (SQLite offline)."""

from pathlib import Path

import pytest

from core.memory_palace import MemoryPalace, get_shared_palace
from core.pgvector_store import PgvectorMemoryStore, use_pgvector_backend


@pytest.fixture
def mem_root(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.delenv("SUPERAI_MEMORY_BACKEND", raising=False)
    monkeypatch.delenv("SUPERAI_MEMORY_DSN", raising=False)
    (tmp_path / ".superai").mkdir(parents=True)
    root = tmp_path / ".superai" / "memory"
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_pgvector_is_default_backend():
    assert use_pgvector_backend() is True


def test_sqlite_cosine_store_roundtrip(tmp_path: Path):
    store = PgvectorMemoryStore(
        dsn=f"sqlite:///{(tmp_path / 'p.sqlite').as_posix()}",
        dim=8,
    )
    emb = [0.1] * 8
    mid = store.add(
        "hello palace memory content enough text",
        embedding=emb,
        metadata={"task_type": "coding", "success": True, "wing": "technical", "room": "coding"},
        tags=["learning", "coding"],
        memory_id="m1",
    )
    assert mid == "m1"
    assert store.count() == 1
    hits = store.search(emb, top_k=3)
    assert hits and hits[0]["id"] == "m1"
    assert store.update_metadata("m1", {"importance": 0.9})
    doc = store.get("m1")
    assert doc and float(doc["importance"]) == 0.9
    assert store.delete("m1")
    assert store.count() == 0


def test_memory_palace_default_uses_pgvector_sql(mem_root: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    mp = MemoryPalace(persist_directory=str(mem_root))
    assert mp.use_pgvector is True
    assert mp.use_chromadb is False
    mid = mp.store(
        "Unique alpha beta gamma semantic content for search.",
        tags=["learning"],
        metadata={"task_type": "coding", "success": True},
        wing="technical",
        room="coding",
        auto_wings=False,
    )
    assert mid
    hits = mp.query_semantic("alpha beta gamma", top_k=5)
    assert hits, "semantic search must return at least one hit"
    assert any(h.get("id") == mid for h in hits), f"expected id {mid} in {[h.get('id') for h in hits]}"
    by_wing = mp.query_semantic("alpha beta", top_k=5, wing="technical", room="coding")
    assert any(h.get("id") == mid for h in by_wing)
    stats = mp.get_memory_stats()
    assert stats.get("using_pgvector") is True
    assert stats.get("using_chromadb") is False
    assert stats.get("total_memories", 0) >= 1
    all_m = mp.get_all_memories()
    assert any(m.get("id") == mid for m in all_m)
    mp.delete(mid)
    assert not any(m.get("id") == mid for m in mp.get_all_memories())


def test_shared_palace_singleton(mem_root: Path):
    a = get_shared_palace(str(mem_root))
    b = get_shared_palace(str(mem_root))
    assert a is b


def test_faiss_opt_in_still_works(mem_root: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_MEMORY_BACKEND", "faiss")
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    mp = MemoryPalace(persist_directory=str(mem_root / "faiss-only"))
    assert mp.use_faiss is True
    assert mp.use_pgvector is False


def test_config_memory_dsn_used_by_store(tmp_path: Path, monkeypatch):
    """memory_dsn from config.json is honored (install wizard write path)."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    db = tmp_path / ".superai" / "from_cfg.sqlite"
    dsn = f"sqlite:///{db.as_posix()}"
    from core.config import Config

    cfg = Config()
    cfg.set("memory_dsn", dsn, persist=True)
    cfg.set("memory_backend", "pgvector", persist=True)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.delenv("SUPERAI_MEMORY_DSN", raising=False)

    store = PgvectorMemoryStore(dim=8)
    assert "from_cfg.sqlite" in store.dsn or store.dsn == dsn
    mid = store.add("cfg dsn memory text here", embedding=[0.2] * 8, memory_id="c1")
    assert store.get(mid) is not None
