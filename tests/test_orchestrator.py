"""Orchestrator mock-path tests (Phase 1)."""

from pathlib import Path

import pytest

from core.config import Config
from core.errors import UserInputError
from core.history import TaskHistory
from core.orchestrator import SuperAIOrchestrator


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    cfg_path = tmp_path / ".superai" / "config.json"
    cfg_path.parent.mkdir(parents=True)
    cfg = Config(config_path=str(cfg_path))
    cfg.set("mock_mode", True, persist=True)
    cfg.initialize()
    return cfg


def test_run_task_mock_success(isolated_home: Config, tmp_path: Path):
    orch = SuperAIOrchestrator(config=isolated_home)
    orch.history = TaskHistory(history_dir=tmp_path / ".superai" / "history")

    result = orch.run_task("Create a FastAPI hello world", verbose=False)

    assert result["success"] is True
    assert result["status"] == "success"
    assert result["mode"] == "mock"
    assert result["task_id"]
    assert isinstance(result["steps"], list)
    assert len(result["steps"]) >= 1
    assert result["result"]

    # History persisted
    listed = orch.history.list(limit=5)
    assert any(r.get("task_id") == result["task_id"] for r in listed)


def test_empty_task_raises(isolated_home: Config):
    orch = SuperAIOrchestrator(config=isolated_home)
    with pytest.raises(UserInputError):
        orch.run_task("   ")
