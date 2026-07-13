"""F3.1 embeddings + F3.5 evolution tests."""

from pathlib import Path

from superai.core.embeddings import (
    HashEmbeddingFunction,
    create_embedding_function,
    describe_embedding,
)
from superai.core.learning_engine import LearningEngine
from superai.core.memory_palace import MemoryPalace


def test_hash_embedding_deterministic():
    fn = HashEmbeddingFunction(dim=64)
    a = fn(["hello world"])
    b = fn(["hello world"])
    assert a == b
    assert len(a[0]) == 64
    # Different text → different vector
    c = fn(["goodbye moon"])
    assert a[0] != c[0]


def test_create_embedding_hash_force():
    fn = create_embedding_function("hash")
    assert "hash" in describe_embedding(fn).lower() or isinstance(
        fn, HashEmbeddingFunction
    )


def test_memory_palace_with_hash_embeddings(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    palace = MemoryPalace(persist_directory=str(tmp_path / "mem"))
    mid = palace.store(
        content="FastAPI routing tutorial knowledge",
        tags=["learning", "coding"],
        metadata={"task_type": "coding", "model": "gpt-4o", "success": True},
    )
    assert mid
    stats = palace.get_memory_stats()
    assert stats["total_memories"] >= 1
    assert "embedding" in stats
    hits = palace.query_semantic("FastAPI routing", top_k=3)
    assert isinstance(hits, list)


def test_knowledge_evolution(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    palace = MemoryPalace(persist_directory=str(tmp_path / "mem2"))
    engine = LearningEngine(palace)
    engine.history_file = str(tmp_path / "lh.json")
    engine._ensure_history_file()
    engine.learn_from_task(
        "build fastapi app v1",
        "coding",
        "gpt-4o",
        True,
        1.0,
        steps_completed=2,
    )
    engine.learn_from_task(
        "build fastapi app v2 improved",
        "coding",
        "claude-4-sonnet",
        True,
        1.2,
        steps_completed=3,
    )
    result = engine.track_knowledge_evolution("fastapi")
    assert result["evolution_detected"] is True
    assert result["total_memories"] >= 2
    assert len(result["timeline"]) >= 2
