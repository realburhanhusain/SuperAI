"""LearningEngine gap close: mid-task learning, smarter conflict/distill."""

from pathlib import Path

import pytest

from core.learning_engine import LearningEngine
from core.memory_palace import MemoryPalace


@pytest.fixture
def engine(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    (tmp_path / ".superai").mkdir(parents=True)
    mp = MemoryPalace(persist_directory=str(tmp_path / ".superai" / "memory"))
    return LearningEngine(mp)


def test_learn_from_step_mid_task(engine: LearningEngine):
    mid = engine.learn_from_step(
        "Build API",
        step_id=2,
        step_description="Implement routes",
        task_type="coding",
        model_used="gpt-test",
        success=True,
        output="Created /health and /items endpoints successfully.",
        task_id="t-1",
    )
    assert mid
    ctx = engine.refresh_context_mid_task(
        "Build API",
        task_type="coding",
        recent_step_outputs=["scaffold done", "routes done"],
        limit=8,
    )
    assert ctx.get("adapted") is True
    assert ctx.get("live_buffer_count", 0) >= 1
    assert ctx.get("relevant_learnings")


def test_conflict_entropy_and_resolve(engine: LearningEngine):
    # Mixed outcomes for same type/model
    for i, ok in enumerate([True, False, True, False, True]):
        engine.learn_from_task(
            task_description=f"task variant {i}",
            task_type="coding",
            model_used="model-x",
            success=ok,
            latency=1.0 + i,
            steps_completed=1 if ok else 0,
            steps_failed=0 if ok else 1,
        )
    conflicts = engine.detect_conflicts("coding")
    assert any(c.get("model") == "model-x" for c in conflicts)
    assert any("entropy" in c for c in conflicts)

    resolved = engine.resolve_conflicts(auto_resolve=True)
    assert resolved.get("method") == "multi_factor_score+entropy"
    assert "conflicts_found" in resolved


def test_distill_jaccard(engine: LearningEngine):
    base = (
        "Successful FastAPI hello world with uvicorn and health route "
        "and pydantic models carefully."
    )
    for i in range(5):
        engine.learn_from_task(
            task_description=base + f" run {i}",
            task_type="coding",
            model_used="model-y",
            success=True,
            latency=0.5,
            steps_completed=3,
        )
    out = engine.distill_knowledge(task_type="coding", min_memories=4)
    assert "method" in out
    # Hash backend → jaccard; ST backend → embedding_cosine
    assert "jaccard" in out["method"] or "embedding" in out["method"]
    assert out.get("deletes_rows") is False
    # May or may not distill depending on similarity; should not crash
    assert "groups_analyzed" in out


def test_get_relevant_scores(engine: LearningEngine):
    engine.learn_from_task(
        "prefer tests",
        "testing",
        "m1",
        True,
        0.2,
        steps_completed=2,
    )
    ctx = engine.get_relevant_context_for_current_task("write unit tests", "testing")
    assert "relevant_learnings" in ctx or "warnings" in ctx


def test_wings_on_store_via_learn(engine: LearningEngine, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    mid = engine.learn_from_task(
        "Implement FastAPI feature",
        "coding",
        "m1",
        True,
        1.0,
        steps_completed=2,
    )
    mems = engine.memory.get_all_memories()
    found = next((m for m in mems if m.get("id") == mid), None)
    assert found is not None
    meta = found.get("metadata") or {}
    # Wings assigned by MemoryPalace.store — not a silent no-op path
    assert meta.get("wing")
    assert meta.get("room")
