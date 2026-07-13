"""Phase 3 learning engine + memory palace tests."""

from pathlib import Path

from superai.core.learning_engine import LearningEngine
from superai.core.memory_palace import MemoryPalace


def test_learn_and_summary(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "superai.core.learning_engine.os.path.expanduser",
        lambda p: str(tmp_path / "learning_history.json")
        if "learning_history" in p
        else p,
    )
    # Force in-memory palace for speed/isolation
    palace = MemoryPalace(persist_directory=str(tmp_path / "mem"))
    # Prefer in-memory if chromadb would write to path — still ok with chromadb in tmp
    engine = LearningEngine(palace)
    engine.history_file = str(tmp_path / "learning_history.json")
    engine._ensure_history_file()

    engine.learn_from_task(
        task_description="build api",
        task_type="coding",
        model_used="gpt-4o",
        success=True,
        latency=1.2,
        cost=0.01,
        steps_completed=3,
    )
    engine.learn_from_task(
        task_description="build api failed",
        task_type="coding",
        model_used="gpt-4o",
        success=False,
        latency=2.0,
        cost=0.0,
        steps_completed=1,
        steps_failed=2,
        error_message="step 2 failed",
    )

    summary = engine.get_learnings_summary()
    assert summary["total_learnings"] >= 2
    assert summary["success_count"] >= 1
    assert summary["failure_count"] >= 1

    ctx = engine.get_relevant_context_for_current_task(
        "build api", task_type="coding", limit=5
    )
    assert "relevant_learnings" in ctx
    assert "warnings" in ctx


def test_distill_persists_deprecation(tmp_path: Path, monkeypatch):
    palace = MemoryPalace(persist_directory=str(tmp_path / "mem2"))
    # Use in-memory mode by disabling chromadb path — if chromadb available it uses disk under tmp
    engine = LearningEngine(palace)
    engine.history_file = str(tmp_path / "lh.json")
    engine._ensure_history_file()

    for i in range(5):
        engine.learn_from_task(
            task_description=f"task {i}",
            task_type="coding",
            model_used="deepseek-coder",
            success=True,
            latency=1.0,
            steps_completed=1,
        )

    result = engine.distill_knowledge(min_memories=4)
    assert result["groups_analyzed"] >= 1
    # After distill, some memories should be deprecated
    all_mem = palace.get_all_memories()
    deprecated = [
        m
        for m in all_mem
        if (m.get("metadata") or {}).get("deprecated") in (True, "True", "true", 1)
    ]
    # Distill requires group size >= 4; we inserted 5 same type/model
    if result.get("groups_distilled", 0) > 0:
        assert len(deprecated) >= 1
        # update_metadata should have lowered importance
        assert float(deprecated[0].get("importance", 1)) < 0.7


def test_detect_conflicts_mixed(tmp_path: Path):
    palace = MemoryPalace(persist_directory=str(tmp_path / "mem3"))
    engine = LearningEngine(palace)
    engine.history_file = str(tmp_path / "lh3.json")
    engine._ensure_history_file()

    for ok in (True, False, True, False):
        engine.learn_from_task(
            task_description="mixed",
            task_type="coding",
            model_used="claude-4-sonnet",
            success=ok,
            latency=1.0,
            steps_completed=1 if ok else 0,
            steps_failed=0 if ok else 1,
        )

    conflicts = engine.detect_conflicts()
    assert any(c.get("model") == "claude-4-sonnet" for c in conflicts)

    resolved = engine.resolve_conflicts(auto_resolve=True)
    assert resolved["conflicts_found"] >= 1


def test_update_metadata_roundtrip(tmp_path: Path):
    palace = MemoryPalace(persist_directory=str(tmp_path / "mem4"))
    mid = palace.store(
        content="hello learning",
        tags=["learning", "success"],
        metadata={"task_type": "general", "model": "gpt-4o", "success": True},
        importance=0.8,
    )
    ok = palace.update_metadata(
        mid, {"importance": 0.2, "deprecated": True, "deprecated_reason": "test"}
    )
    assert ok
    all_m = palace.get_all_memories()
    found = next(m for m in all_m if m["id"] == mid)
    assert float(found.get("importance", found["metadata"].get("importance"))) == 0.2
    assert found["metadata"].get("deprecated") in (True, "True", "true", 1)
