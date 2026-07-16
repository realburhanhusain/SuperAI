"""External CLI deep integration with Memory Palace, learning, orchestrator."""

from pathlib import Path

import pytest

from core.config import Config
from core.external_cli import ExternalCLIRegistry, ExternalCLITool
from core.model_caller import ModelCaller
from core.model_registry import ModelRegistry
from core.orchestrator import SuperAIOrchestrator
from core.task_planner import ExecutionStep


@pytest.fixture
def home(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    (tmp_path / ".superai").mkdir(parents=True)
    return tmp_path


def test_run_injects_and_writes_memory(home: Path):
    tool = ExternalCLITool(
        dry_run=True,
        auto_approve=True,
        with_context=True,
        write_memory=True,
    )
    env = tool.run(
        "claude",
        "implement a small health endpoint",
        approve=True,
        role="implementer",
        source="test",
        task_type="coding",
        workflow_id="wf-test",
    )
    assert env.ok is True
    meta = env.metadata or {}
    assert meta.get("integrated") is True
    assert meta.get("memory_injected") is True or meta.get("context_id")
    assert meta.get("memory_write") or meta.get("memory_write_error") is None
    # dry-run still records observation
    assert meta.get("dry_run") is True or meta.get("audited")


def test_pick_for_role():
    reg = ExternalCLIRegistry()
    # may or may not be available on PATH; pick returns None or str
    name = reg.pick_for_role("implementer")
    assert name is None or isinstance(name, str)


def test_run_as_worker(home: Path):
    tool = ExternalCLITool(dry_run=True, auto_approve=True)
    env = tool.run_as_worker("fix the bug in auth", role="implementer")
    assert env.cli
    assert env.metadata.get("role") == "implementer"


def test_model_caller_cli_integrated(home: Path, monkeypatch):
    reg = ModelRegistry()
    reg.register_external_clis_as_models()
    caller = ModelCaller(use_mock=True, registry=reg)
    out = caller.call(model="cli:claude", prompt="say hello from integrated path")
    assert out.get("provider") == "external_cli"
    assert out.get("integrated") is True
    assert "context_id" in out or out.get("external_cli")


def test_model_caller_cli_inner_model(home: Path, monkeypatch):
    """cli:name@MODEL must reach ExternalCLITool as cli_model (not strip to bare name)."""
    reg = ModelRegistry()
    reg.register_external_clis_as_models()
    caller = ModelCaller(use_mock=True, registry=reg)
    captured = {}

    def _fake_run(self, cli_name, prompt, **kwargs):
        captured["cli_name"] = cli_name
        captured["cli_model"] = kwargs.get("cli_model")
        from core.external_cli import CLIResultEnvelope

        return CLIResultEnvelope(
            ok=True,
            cli=cli_name,
            command=["mock"],
            exit_code=0,
            stdout="ok",
            stderr="",
            duration_sec=0.01,
            modifies_files=False,
            approved=True,
            error=None,
            metadata={"dry_run": True, "cli_model": kwargs.get("cli_model")},
        )

    monkeypatch.setattr(ExternalCLITool, "run", _fake_run)
    out = caller.call(
        model="cli:gemini@gemini-2.5-pro",
        prompt="review this",
    )
    assert out.get("provider") == "external_cli"
    assert captured.get("cli_name") == "gemini"
    assert captured.get("cli_model") == "gemini-2.5-pro"
    assert out.get("cli_model") == "gemini-2.5-pro"
    assert "gemini-2.5-pro" in str(out.get("model") or "")


def test_orchestrator_cli_delegate_flag(home: Path, monkeypatch):
    cfg_path = home / ".superai" / "config.json"
    cfg = Config(config_path=str(cfg_path))
    cfg.set("mock_mode", True, persist=True)
    cfg.set("cli_delegate_workers", True, persist=True)
    cfg.set("max_step_retries", 0, persist=True)
    cfg.set("quality_gate", False, persist=True)
    cfg.initialize()

    orch = SuperAIOrchestrator(config=cfg)
    orch.use_step_cache = False
    monkeypatch.setattr(
        orch.task_planner,
        "create_plan",
        lambda task, use_llm=None: [
            ExecutionStep(
                step_id=1,
                description="implement the feature carefully with enough text",
                depends_on=[],
                recommended_model="auto",
                estimated_complexity="Medium",
                role="implementer",
            )
        ],
    )
    # Claim claude available so delegate path selects cli:claude (still dry via mock)
    monkeypatch.setattr(
        ExternalCLIRegistry,
        "available",
        lambda self: ["claude"],
    )
    monkeypatch.setattr(
        ExternalCLIRegistry,
        "pick_for_role",
        lambda self, role="worker": "claude",
    )

    result = orch.run_task("build feature", verbose=False)
    events = {
        e.get("kind")
        for e in (result.get("metadata") or {}).get("adaptation_events") or []
    }
    assert "cli_delegate" in events or "worker_pool" in events
    assert result.get("steps")
    model = str(result["steps"][0].get("model") or "")
    assert model.startswith("cli:")


def test_orchestrator_worker_pool_mixed(home: Path, monkeypatch):
    """Explicit workers (API + CLI) become primary/failover pool."""
    cfg_path = home / ".superai" / "config.json"
    cfg = Config(config_path=str(cfg_path))
    cfg.set("mock_mode", True, persist=True)
    cfg.set("worker_prefer", "mixed", persist=True)
    cfg.set("max_step_retries", 0, persist=True)
    cfg.set("quality_gate", False, persist=True)
    cfg.initialize()

    orch = SuperAIOrchestrator(config=cfg)
    orch.use_step_cache = False
    monkeypatch.setattr(
        orch.task_planner,
        "create_plan",
        lambda task, use_llm=None: [
            ExecutionStep(
                step_id=1,
                description="implement the feature carefully with enough text",
                depends_on=[],
                recommended_model="auto",
                estimated_complexity="Medium",
                role="implementer",
            )
        ],
    )
    monkeypatch.setattr(
        ExternalCLIRegistry,
        "available",
        lambda self: ["gemini", "grok"],
    )

    result = orch.run_task(
        "build feature",
        verbose=False,
        workers=["gpt-4o", "cli:gemini@flash"],
        worker_prefer="mixed",
    )
    events = (result.get("metadata") or {}).get("adaptation_events") or []
    pool_events = [e for e in events if e.get("kind") == "worker_pool"]
    assert pool_events
    pool = pool_events[0].get("pool") or []
    assert pool[0] == "gpt-4o"
    assert any("gemini" in str(x) for x in pool)
    assert result.get("steps")
    assert str(result["steps"][0].get("model") or "") == "gpt-4o"


def test_envelope_metadata_keys(home: Path):
    tool = ExternalCLITool(dry_run=True, auto_approve=True)
    env = tool.run("aider", "refactor module", role="reviewer", step_id=3, task_id="t9")
    d = env.to_dict()
    assert "metadata" in d
    assert d["metadata"].get("step_id") == 3
