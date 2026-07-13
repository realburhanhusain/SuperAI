"""Hierarchical delegation tests."""

from pathlib import Path

from core.config import Config
from core.hierarchy import HierarchicalDelegator
from core.history import TaskHistory
from core.orchestrator import SuperAIOrchestrator


def test_hierarchical_delegate(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    cfg_path = tmp_path / ".superai" / "config.json"
    cfg_path.parent.mkdir(parents=True)
    cfg = Config(config_path=str(cfg_path))
    cfg.set("mock_mode", True, persist=True)
    cfg.set("max_delegation_depth", 2, persist=True)
    cfg.initialize()
    orch = SuperAIOrchestrator(config=cfg)
    orch.history = TaskHistory(history_dir=tmp_path / ".superai" / "history")
    tree = HierarchicalDelegator(orchestrator=orch, config=cfg).run(
        "Build a small FastAPI service"
    )
    assert tree["goal"]
    assert "leaf" in tree or "children" in tree
