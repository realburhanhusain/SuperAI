"""Track F: provider health, refresh, smoke, streaming, overrides."""

from pathlib import Path

import pytest

from core.config import Config
from core.history import TaskHistory
from core.load_balancer import LoadBalancer
from core.model_caller import ModelCaller
from core.model_refresh import merge_catalogs, refresh_models
from core.model_registry import ModelRegistry
from core.model_router import ModelRouter
from core.orchestrator import SuperAIOrchestrator
from core.provider_health import ProviderHealthStore
from core.provider_smoke import available_smoke_targets, run_provider_smoke


def test_provider_health_persist(tmp_path: Path):
    store = ProviderHealthStore(path=tmp_path / "health.json")
    store.record_success("openai", latency=0.2, tokens=100)
    store.record_failure("openai", error="boom", latency=0.1)
    store.record_failure("openai", error="boom2")
    store.record_failure("openai", error="boom3")
    assert store.health_score("openai") < 0.5
    assert store._provider("openai")["circuit_open"] is True

    store2 = ProviderHealthStore(path=tmp_path / "health.json")
    assert store2._provider("openai")["failures"] >= 3
    assert store2.health_score("openai") <= 0.35


def test_quota_throttle(tmp_path: Path):
    store = ProviderHealthStore(path=tmp_path / "q.json")
    store.set_quota_limits("groq", max_requests_per_window=2, window_seconds=60)
    store.record_success("groq", tokens=1)
    assert store.can_call("groq") is True
    store.record_success("groq", tokens=1)
    # 2 requests hit max
    assert store._provider("groq")["quota"]["throttled"] is True
    assert store.can_call("groq") is False


def test_merge_and_refresh_models(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_MODELS_URL", "")
    # Point home-ish write via monkeypatch of user path
    user_cfg = tmp_path / "config"
    user_cfg.mkdir()
    monkeypatch.setattr(
        "core.model_refresh.user_models_path",
        lambda: user_cfg / "models.json",
    )
    # Ensure project catalog is used
    models, meta = refresh_models(write_user_copy=True, remote_url=None)
    assert len(models) >= 1
    assert meta.get("count", 0) >= 1
    assert (user_cfg / "models.json").is_file()

    a = [{"name": "a", "provider": "x"}]
    b = [{"name": "a", "provider": "y"}, {"name": "b", "provider": "z"}]
    merged = merge_catalogs(a, b)
    by = {m["name"]: m["provider"] for m in merged}
    assert by["a"] == "y"
    assert by["b"] == "z"


def test_mock_stream_and_smoke(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    caller = ModelCaller(use_mock=True, health_store=ProviderHealthStore(path=tmp_path / "h.json"))
    chunks = list(caller.stream(model="gpt-4o", prompt="hello stream"))
    assert chunks
    assert "".join(chunks)

    summary = run_provider_smoke(use_mock=True, health=ProviderHealthStore(path=tmp_path / "h2.json"))
    assert summary["passed"] >= 1
    assert summary["failed"] == 0


def test_forced_model_override(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    cfg_path = tmp_path / ".superai" / "config.json"
    cfg_path.parent.mkdir(parents=True)
    cfg = Config(config_path=str(cfg_path))
    cfg.set("mock_mode", True, persist=True)
    cfg.initialize()
    orch = SuperAIOrchestrator(config=cfg)
    orch.history = TaskHistory(history_dir=tmp_path / ".superai" / "history")
    orch.health_store = ProviderHealthStore(path=tmp_path / "ph.json")
    orch.model_caller.health_store = orch.health_store
    orch.model_router.health_store = orch.health_store

    result = orch.run_task("Implement a FastAPI app", forced_model="deepseek-coder")
    assert result["success"] is True
    # Forced model must appear on steps
    models = {s.get("model") for s in result.get("steps") or []}
    assert "deepseek-coder" in models


def test_supervisor_preference(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    registry = ModelRegistry()
    router = ModelRouter(registry, LoadBalancer(), health_store=ProviderHealthStore(path=tmp_path / "h.json"))
    chosen = router.select_model("random chat", preferred_model="gpt-4o")
    assert chosen == "gpt-4o"


def test_available_smoke_targets_type():
    targets = available_smoke_targets()
    assert isinstance(targets, list)
