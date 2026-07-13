"""N5 FAISS backend, N8 report, container sandbox helpers."""

from pathlib import Path

from core.container_sandbox import docker_available, sandbox_enabled
from core.faiss_store import FaissMemoryStore
from core.model_compare import benchmark_models, benchmark_report_markdown


def test_faiss_store_brute(tmp_path: Path):
    store = FaissMemoryStore(root=tmp_path / "f", dim=8)
    # simple one-hot-ish vectors
    v1 = [1.0, 0, 0, 0, 0, 0, 0, 0]
    v2 = [0, 1.0, 0, 0, 0, 0, 0, 0]
    store.add("hello world", v1, metadata={"task_type": "a"}, tags=["t"])
    store.add("other doc", v2, metadata={"task_type": "b"}, tags=["u"])
    hits = store.search(v1, top_k=2)
    assert hits
    assert "hello" in (hits[0].get("content") or "")
    st = store.stats()
    assert st["count"] == 2


def test_memory_palace_faiss_backend(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_MEMORY_BACKEND", "faiss")
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    from core.memory_palace import MemoryPalace

    mp = MemoryPalace(persist_directory=str(tmp_path / "mem"))
    assert mp.use_faiss
    mid = mp.store("fastapi routing knowledge", tags=["coding"])
    assert mid
    hits = mp.query_semantic("fastapi", top_k=3)
    assert hits
    stats = mp.get_memory_stats()
    assert stats.get("using_faiss") is True


def test_benchmark_markdown():
    data = benchmark_models(models=["gpt-4o"], use_mock=True)
    md = benchmark_report_markdown(data)
    assert "Benchmark Report" in md
    assert "gpt-4o" in md or "Model" in md


def test_sandbox_helpers():
    # should not raise
    assert isinstance(docker_available(), bool)
    assert sandbox_enabled(False) is False
