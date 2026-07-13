"""Task history tests (Phase 1)."""

from pathlib import Path

from superai.core.history import TaskHistory


def test_save_and_list(tmp_path: Path):
    store = TaskHistory(history_dir=tmp_path)
    r1 = {
        "task_id": "t1",
        "task": "hello",
        "status": "success",
        "success": True,
        "model_used": "gpt-4o",
        "duration": 0.5,
    }
    r2 = {
        "task_id": "t2",
        "task": "world",
        "status": "failed",
        "success": False,
        "model_used": "gpt-4o",
        "duration": 0.1,
    }
    store.save(r1)
    store.save(r2)

    assert store.count() == 2
    listed = store.list(limit=10)
    assert len(listed) == 2
    ids = {x["task_id"] for x in listed}
    assert ids == {"t1", "t2"}

    got = store.get("t1")
    assert got is not None
    assert got["task"] == "hello"


def test_new_task_id_unique():
    a = TaskHistory.new_task_id()
    b = TaskHistory.new_task_id()
    assert a != b
    assert len(a) > 10
