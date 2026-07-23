"""M061–M063 learning product UX: lifecycle status, promote, distill, deprecate."""

from pathlib import Path

import pytest

from core.learning_engine import LearningEngine
from core.memory_palace import MemoryPalace

pytestmark = pytest.mark.unit


@pytest.fixture
def engine(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    (tmp_path / ".superai").mkdir(parents=True)
    mp = MemoryPalace(persist_directory=str(tmp_path / ".superai" / "memory"))
    return LearningEngine(mp)


def _seed(engine: LearningEngine, n: int = 6, model: str = "model-z", ok: bool = True):
    ids = []
    for i in range(n):
        mid = engine.learn_from_task(
            task_description=f"Build FastAPI service carefully variant {i}",
            task_type="coding",
            model_used=model,
            success=ok if i % 2 == 0 else (not ok),
            latency=0.4 + i * 0.1,
            steps_completed=2 if ok else 0,
            steps_failed=0 if ok else 1,
        )
        ids.append(mid)
    return ids


def test_lifecycle_status_and_list(engine: LearningEngine):
    _seed(engine, 4)
    st = engine.lifecycle_status()
    assert st["ok"] is True
    assert st["total_learnings"] >= 4
    assert "active" in st["buckets"]
    assert st["product"] == "learning.lifecycle_status"

    listed = engine.list_lifecycle("all", limit=10)
    assert listed["count"] >= 1
    assert listed["items"]
    assert listed["items"][0].get("lifecycle") in {
        "active",
        "durable",
        "deprecated",
        "distilled",
    }


def test_promote_durable_product(engine: LearningEngine):
    ids = _seed(engine, 5, ok=True)
    # Boost importance so bulk promote can fire
    for mid in ids[:3]:
        engine.memory.update_metadata(mid, {"importance": 0.9, "success": True})
    out = engine.promote_durable(min_importance=0.8, limit=10)
    assert out["ok"] is True
    assert out["count"] >= 1
    assert out.get("product") == "learning.promote_durable"

    durable = engine.list_lifecycle("durable", limit=20)
    assert durable["total_matching"] >= 1


def test_deprecate_and_list_deprecated(engine: LearningEngine):
    ids = _seed(engine, 2)
    mid = ids[0]
    dep = engine.deprecate_memory(mid, reason="test_cleanup")
    assert dep["ok"] is True
    assert dep["deprecated"] is True
    listed = engine.list_lifecycle("deprecated", limit=10)
    assert any(it.get("id") == mid for it in listed["items"])


def test_resolve_conflicts_product_fields(engine: LearningEngine):
    for i, ok in enumerate([True, False, True, False, True]):
        engine.learn_from_task(
            f"conflict task {i}",
            "coding",
            "model-conflict",
            ok,
            1.0,
            steps_completed=1 if ok else 0,
            steps_failed=0 if ok else 1,
        )
    resolved = engine.resolve_conflicts(auto_resolve=True)
    assert "conflicts_found" in resolved
    assert resolved.get("method")


def test_foundation_complete_learning_surface(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    (tmp_path / ".superai").mkdir(parents=True)
    from core import foundation_complete as fc

    st = fc.learning_lifecycle_status()
    assert st.get("ok") is True
    listed = fc.learning_list(kind="all", limit=5)
    assert listed.get("ok") is True
    prom = fc.learning_promote_durable(limit=3)
    assert prom.get("ok") is True
