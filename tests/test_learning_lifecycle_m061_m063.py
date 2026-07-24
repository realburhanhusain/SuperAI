"""M061–M063 learning product UX: lifecycle, promote dry-run, conflicts, distill."""

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
    emb = st.get("embedding") or {}
    assert emb.get("is_hash") is True
    assert emb.get("quality") == "lexical_hash"
    assert st.get("honesty", {}).get("conflict_resolve")
    assert "deprecates" in st["honesty"]["conflict_resolve"].lower()

    listed = engine.list_lifecycle("all", limit=10)
    assert listed["count"] >= 1
    assert listed["items"]
    assert listed["items"][0].get("lifecycle") in {
        "active",
        "durable",
        "deprecated",
        "distilled",
    }


def test_distill_noop_clear_message(engine: LearningEngine):
    _seed(engine, 2)
    out = engine.distill_knowledge(min_memories=10)
    assert out.get("distilled") is False
    assert out.get("noop") is True
    assert "Not enough memories" in (out.get("message") or "")
    assert out.get("deletes_rows") is False
    assert out.get("embedding", {}).get("is_hash") is True


def test_promote_durable_product(engine: LearningEngine):
    ids = _seed(engine, 5, ok=True)
    for mid in ids[:3]:
        engine.memory.update_metadata(mid, {"importance": 0.9, "success": True})
    out = engine.promote_durable(min_importance=0.8, limit=10)
    assert out["ok"] is True
    assert out["count"] >= 1
    assert out.get("product") == "learning.promote_durable"
    assert out.get("dry_run") is False
    # In-place: original ids promoted, no silent re-store required
    assert any(mid in out["promoted"] for mid in ids[:3])

    durable = engine.list_lifecycle("durable", limit=20)
    assert durable["total_matching"] >= 1


def test_promote_dry_run_no_mutate(engine: LearningEngine):
    ids = _seed(engine, 4, ok=True)
    for mid in ids:
        engine.memory.update_metadata(mid, {"importance": 0.9, "success": True})
    before = engine.list_lifecycle("durable", limit=50)["total_matching"]
    out = engine.promote_durable(min_importance=0.8, limit=10, dry_run=True)
    assert out["ok"] is True
    assert out["dry_run"] is True
    assert out["count"] >= 1
    assert out.get("promoted") == []
    assert out.get("would_promote")
    assert out.get("candidates")
    after = engine.list_lifecycle("durable", limit=50)["total_matching"]
    assert after == before


def test_promote_below_threshold_skipped(engine: LearningEngine):
    ids = _seed(engine, 3, ok=True)
    for mid in ids:
        engine.memory.update_metadata(mid, {"importance": 0.2, "success": True})
    out = engine.promote_durable(min_importance=0.9, limit=10)
    assert out["ok"] is True
    assert out["count"] == 0
    assert any("below_min_importance" in (s.get("reason") or "") for s in out.get("skipped") or [])


def test_promote_id_not_found(engine: LearningEngine):
    out = engine.promote_durable(memory_id="does-not-exist-xyz", min_importance=0.1)
    assert out["ok"] is False
    assert out.get("not_found") is True
    assert out["count"] == 0


def test_deprecate_and_list_deprecated(engine: LearningEngine):
    ids = _seed(engine, 2)
    mid = ids[0]
    dep = engine.deprecate_memory(mid, reason="test_cleanup")
    assert dep["ok"] is True
    assert dep["deprecated"] is True
    assert dep.get("deletes_rows") is False
    listed = engine.list_lifecycle("deprecated", limit=10)
    assert any(it.get("id") == mid for it in listed["items"])


def test_undeprecate_restores(engine: LearningEngine):
    ids = _seed(engine, 2)
    mid = ids[0]
    engine.deprecate_memory(mid, reason="temp")
    und = engine.undeprecate_memory(mid)
    assert und["ok"] is True
    assert und.get("deprecated") is False
    listed = engine.list_lifecycle("deprecated", limit=20)
    assert not any(it.get("id") == mid for it in listed["items"])


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
    assert resolved.get("deletes_rows") is False
    assert resolved.get("action") == "deprecate_metadata_only"
    assert "not deleted" in (resolved.get("message") or "").lower() or resolved.get(
        "conflicts_resolved", 0
    ) == 0


def test_resolve_list_only_no_mutate(engine: LearningEngine):
    for i, ok in enumerate([True, False, True, False]):
        engine.learn_from_task(
            f"list only {i}",
            "coding",
            "model-list",
            ok,
            1.0,
            steps_completed=1 if ok else 0,
            steps_failed=0 if ok else 1,
        )
    before_dep = engine.list_lifecycle("deprecated", limit=100)["total_matching"]
    out = engine.resolve_conflicts(auto_resolve=False)
    assert out.get("action") == "list_only"
    assert out.get("conflicts_resolved") == 0
    assert out.get("deletes_rows") is False
    after_dep = engine.list_lifecycle("deprecated", limit=100)["total_matching"]
    assert after_dep == before_dep


def test_detect_conflicts_include_samples_and_scores(engine: LearningEngine):
    for i, ok in enumerate([True, False, True, False, True]):
        engine.learn_from_task(
            f"sample conflict {i} with enough words for score",
            "coding",
            "model-samples",
            ok,
            0.5,
            steps_completed=1 if ok else 0,
            steps_failed=0 if ok else 1,
        )
    conflicts = engine.detect_conflicts("coding")
    hit = next(c for c in conflicts if c.get("model") == "model-samples")
    assert hit.get("samples")
    assert hit["samples"][0].get("score") is not None
    assert hit.get("suggested_keep_id")
    assert "score_factors" in hit["samples"][0]


def test_resolve_keep_override(engine: LearningEngine):
    ids = []
    for i, ok in enumerate([True, False, True, False]):
        mid = engine.learn_from_task(
            f"keep override {i}",
            "coding",
            "model-keep",
            ok,
            1.0,
            steps_completed=1 if ok else 0,
            steps_failed=0 if ok else 1,
        )
        ids.append(mid)
    # Force keep the second success if present, else first id
    keep_id = ids[2] if len(ids) > 2 else ids[0]
    out = engine.resolve_conflicts(auto_resolve=True, keep_memory_id=keep_id)
    if out.get("resolved_details"):
        # When the keep id is in a resolved group, override should be noted
        details = out["resolved_details"]
        matched = [d for d in details if d.get("kept_memory_id") == keep_id]
        if matched:
            assert matched[0].get("keep_override") is True
            assert matched[0].get("kept_score_factors")


def test_resolve_never_deletes_rows(engine: LearningEngine):
    for i, ok in enumerate([True, False, True, False, True]):
        engine.learn_from_task(
            f"no delete {i}",
            "coding",
            "model-nd",
            ok,
            1.0,
            steps_completed=1 if ok else 0,
            steps_failed=0 if ok else 1,
        )
    before = len(engine.memory.get_all_memories() or [])
    engine.resolve_conflicts(auto_resolve=True)
    after = len(engine.memory.get_all_memories() or [])
    assert after >= before  # may add nothing, never shrinks from deprecate


def test_distill_dry_run_preview(engine: LearningEngine):
    base = (
        "Successful FastAPI hello world with uvicorn and health route "
        "and pydantic models carefully."
    )
    for i in range(5):
        engine.learn_from_task(
            task_description=base + f" run {i}",
            task_type="coding",
            model_used="model-distill",
            success=True,
            latency=0.5,
            steps_completed=3,
        )
    before = len(engine.memory.get_all_memories() or [])
    out = engine.distill_knowledge(
        task_type="coding", min_memories=4, dry_run=True
    )
    assert out.get("dry_run") is True
    assert out.get("deletes_rows") is False
    assert out.get("embedding", {}).get("is_hash") is True
    assert "similarity_method" in out or out.get("noop")
    after = len(engine.memory.get_all_memories() or [])
    assert after == before
    dep = engine.list_lifecycle("deprecated", limit=50)["total_matching"]
    assert dep == 0


def test_distill_creates_summary_and_deprecates_not_delete(engine: LearningEngine):
    base = (
        "Successful FastAPI hello world with uvicorn and health route "
        "and pydantic models carefully for distill."
    )
    for i in range(5):
        engine.learn_from_task(
            task_description=base + f" variant {i}",
            task_type="coding",
            model_used="model-d2",
            success=True,
            latency=0.5,
            steps_completed=3,
        )
    before = len(engine.memory.get_all_memories() or [])
    out = engine.distill_knowledge(task_type="coding", min_memories=4)
    assert out.get("deletes_rows") is False
    after = len(engine.memory.get_all_memories() or [])
    # Deprecate keeps rows; summary may add rows
    assert after >= before
    if out.get("distilled"):
        assert out.get("summary_memory_ids") or out.get("groups_distilled", 0) >= 1
        distilled = engine.list_lifecycle("distilled", limit=20)
        assert distilled["total_matching"] >= 1


def test_full_lifecycle_product_loop(engine: LearningEngine):
    """Operator story: learn → promote → conflict → distill → list buckets."""
    ids = []
    for i, ok in enumerate([True, True, False, True, False, True]):
        mid = engine.learn_from_task(
            f"Full loop FastAPI service carefully path {i}",
            "coding",
            "model-loop",
            ok,
            0.8,
            steps_completed=2 if ok else 0,
            steps_failed=0 if ok else 1,
        )
        ids.append(mid)
        if ok:
            engine.memory.update_metadata(mid, {"importance": 0.85, "success": True})

    st0 = engine.lifecycle_status()
    assert st0["total_learnings"] >= 6

    prev = engine.promote_durable(min_importance=0.8, limit=5, dry_run=True)
    assert prev["count"] >= 1
    prom = engine.promote_durable(min_importance=0.8, limit=5)
    assert prom["count"] >= 1
    assert engine.list_lifecycle("durable")["total_matching"] >= 1

    conflicts = engine.detect_conflicts("coding")
    assert isinstance(conflicts, list)
    resolved = engine.resolve_conflicts(auto_resolve=True, task_type="coding")
    assert resolved.get("deletes_rows") is False

    dprev = engine.distill_knowledge(
        task_type="coding", min_memories=3, dry_run=True
    )
    assert dprev.get("embedding")
    engine.distill_knowledge(task_type="coding", min_memories=3)

    buckets = {
        k: engine.list_lifecycle(k, limit=50)["total_matching"]
        for k in ("active", "durable", "deprecated", "distilled", "all")
    }
    assert buckets["all"] >= 6
    st1 = engine.lifecycle_status()
    assert st1["ok"] is True
    assert st1["buckets"]["durable"] >= 1 or buckets["durable"] >= 1


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
    prom = fc.learning_promote_durable(limit=3, dry_run=True)
    assert prom.get("ok") is True
    assert prom.get("dry_run") is True
    # foundation wrappers use default palace; only assert contract shape
    dist = fc.learning_distill(dry_run=True, min_memories=5)
    assert dist.get("ok") is True
    assert dist.get("dry_run") is True
    assert dist.get("deletes_rows") is False
    assert "embedding" in dist or dist.get("noop") is not None


def test_promote_reports_error_on_store_failure(engine: LearningEngine, monkeypatch):
    """P1.2: store unreachable → ok False, not silent zero success."""

    def boom(*a, **k):
        raise RuntimeError("palace down")

    monkeypatch.setattr(engine.memory, "retrieve_by_tags", boom)
    out = engine.promote_durable(min_importance=0.5, limit=5)
    assert out["ok"] is False
    assert out.get("error_code") == "store_unreachable"
    assert out["count"] == 0


def test_distill_rollback_on_summary_store_failure(engine: LearningEngine, monkeypatch):
    """P0.1: if summary store fails, originals must remain active (not deprecated)."""
    base = (
        "Successful FastAPI hello world with uvicorn and health route "
        "and pydantic models carefully for distill rollback."
    )
    ids = []
    for i in range(5):
        mid = engine.learn_from_task(
            task_description=base + f" variant {i}",
            task_type="coding",
            model_used="model-rb",
            success=True,
            latency=0.5,
            steps_completed=3,
        )
        ids.append(mid)

    real_store = engine.memory.store

    def fail_summary(content, *a, **k):
        if isinstance(content, str) and content.startswith("Distilled knowledge"):
            raise RuntimeError("simulated summary store failure")
        return real_store(content, *a, **k)

    monkeypatch.setattr(engine.memory, "store", fail_summary)
    out = engine.distill_knowledge(task_type="coding", min_memories=4)
    assert out.get("ok") is False
    assert out.get("error_code") == "summary_store_failed"
    # Originals still active (not deprecated)
    dep = engine.list_lifecycle("deprecated", limit=50)
    assert not any(it.get("id") in ids for it in dep.get("items") or [])


def test_apply_learning_update_logs_warning_on_failure(engine: LearningEngine, monkeypatch, caplog):
    """P1.3 / P2.2: update failures log a warning and return False."""
    import logging

    mid = engine.learn_from_task(
        "log warning path",
        "coding",
        "m1",
        True,
        0.5,
        steps_completed=1,
    )

    def boom(*a, **k):
        raise RuntimeError("update denied")

    monkeypatch.setattr(engine.memory, "update_metadata", boom)
    # Clear in-memory fallback so update path is forced to fail hard
    if hasattr(engine.memory, "memories"):
        engine.memory.memories = [
            m for m in (engine.memory.memories or []) if m.get("id") != mid
        ]

    with caplog.at_level(logging.WARNING):
        ok = engine._apply_learning_update(
            mid, metadata={"deprecated": True}, tags=["deprecated"]
        )
    assert ok is False
    assert any("metadata update" in r.message.lower() or "failed" in r.message.lower() for r in caplog.records)


def test_post_call_idempotency(tmp_path: Path, monkeypatch):
    """P2.3: second post_call does not double-update bandit."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.bandit_router import EpsilonGreedyBandit
    from core.call_lifecycle import post_call

    r1 = post_call(
        {"ok": True, "response": "hi", "mock": True},
        model="m-test",
        prompt="p",
        update_bandit=True,
        record_spend=False,
    )
    assert r1.get("_post_call_done") is True
    n1 = float(EpsilonGreedyBandit().state.get("m-test", {}).get("n") or 0)
    r2 = post_call(r1, model="m-test", prompt="p", update_bandit=True, record_spend=False)
    assert r2.get("_post_call_done") is True
    n2 = float(EpsilonGreedyBandit().state.get("m-test", {}).get("n") or 0)
    assert n2 == n1
