"""Orchestrator mock-path tests (Phase 1 + adaptation gaps)."""

from pathlib import Path
from typing import Any, Dict, List

import pytest

from core.config import Config
from core.errors import UserInputError
from core.history import TaskHistory
from core.orchestrator import SuperAIOrchestrator
from core.task_planner import ExecutionStep


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    cfg_path = tmp_path / ".superai" / "config.json"
    cfg_path.parent.mkdir(parents=True)
    cfg = Config(config_path=str(cfg_path))
    cfg.set("mock_mode", True, persist=True)
    cfg.set("adapt_on_failure", True, persist=True)
    cfg.set("max_step_retries", 2, persist=True)
    cfg.set("max_replans", 1, persist=True)
    cfg.set("quality_gate", True, persist=True)
    cfg.set("mid_task_memory_refresh", True, persist=True)
    cfg.set("step_retry_backoff_sec", 0.0, persist=True)
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
    # Gap close: structured metadata always present
    assert "degraded" in result["metadata"]
    assert "adaptation_events" in result["metadata"]
    assert "replans_used" in result["metadata"]

    listed = orch.history.list(limit=5)
    assert any(r.get("task_id") == result["task_id"] for r in listed)


def test_empty_task_raises(isolated_home: Config):
    orch = SuperAIOrchestrator(config=isolated_home)
    with pytest.raises(UserInputError):
        orch.run_task("   ")


def test_quality_ok_gate(isolated_home: Config):
    orch = SuperAIOrchestrator(config=isolated_home)
    assert orch._quality_ok("This is a solid implementation plan.")[0] is True
    assert orch._quality_ok("")[0] is False
    assert orch._quality_ok("Error: boom")[0] is False
    assert orch._quality_ok("x")[0] is False


def test_step_retry_and_recover(isolated_home: Config, monkeypatch):
    """First calls fail with retryable error; later succeeds → recovered step."""
    orch = SuperAIOrchestrator(config=isolated_home)
    calls: List[str] = []

    def flaky_call(model: str, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        calls.append(model)
        if len(calls) < 2:
            return {
                "status": "error",
                "response": "rate limit 429 too many requests",
                "usage": {},
                "estimated_cost_usd": 0.0,
            }
        return {
            "status": "ok",
            "response": "Recovered successful step output with enough detail.",
            "usage": {"total_tokens": 10},
            "estimated_cost_usd": 0.001,
        }

    monkeypatch.setattr(orch.model_caller, "call", flaky_call)
    # Force single-step plan
    monkeypatch.setattr(
        orch.task_planner,
        "create_plan",
        lambda task, use_llm=None: [
            ExecutionStep(
                step_id=1,
                description="Do the work carefully",
                depends_on=[],
                recommended_model="mock",
                estimated_complexity="Low",
                can_run_parallel=False,
                role="worker",
            )
        ],
    )
    # Disable step cache so flaky path is exercised
    orch.use_step_cache = False
    monkeypatch.setattr(
        orch.model_router,
        "select_model",
        lambda **kw: "primary-model",
    )
    monkeypatch.setattr(
        orch.model_router,
        "explain_selection",
        lambda *a, **k: [{"model": "primary-model", "score": 1, "provider": "x"}],
    )
    monkeypatch.setattr(
        orch.model_router,
        "classify_task",
        lambda t: "coding",
    )

    result = orch.run_task("implement feature X", verbose=False)
    assert result["status"] in {"success", "partial"}
    assert len(calls) >= 2
    events = result["metadata"].get("adaptation_events") or []
    kinds = {e.get("kind") for e in events}
    assert "step_attempt_failed" in kinds or "step_recovered" in kinds or result["success"]


def test_soft_fail_records_degraded(isolated_home: Config):
    orch = SuperAIOrchestrator(config=isolated_home)
    result: Dict[str, Any] = {"metadata": {}}

    def boom():
        raise RuntimeError("optional subsystem down")

    out = orch._soft("unit_test_feature", boom, result=result)
    assert out is None
    assert any(d["feature"] == "unit_test_feature" for d in orch._degraded)
    assert any(
        d["feature"] == "unit_test_feature"
        for d in result["metadata"]["degraded"]
    )


def test_dep_repair_progresses(isolated_home: Config, monkeypatch):
    """Broken depends_on should not deadlock forever."""
    orch = SuperAIOrchestrator(config=isolated_home)
    orch.use_step_cache = False
    monkeypatch.setattr(
        orch.task_planner,
        "create_plan",
        lambda task, use_llm=None: [
            ExecutionStep(
                step_id=1,
                description="step one with enough output text",
                depends_on=[99],  # impossible dep
                recommended_model="mock",
                estimated_complexity="Low",
            ),
            ExecutionStep(
                step_id=2,
                description="step two with enough output text",
                depends_on=[1],
                recommended_model="mock",
                estimated_complexity="Low",
            ),
        ],
    )
    monkeypatch.setattr(
        orch.model_caller,
        "call",
        lambda model, prompt, **kw: {
            "status": "ok",
            "response": "Completed step output with sufficient content here.",
            "usage": {"total_tokens": 5},
            "estimated_cost_usd": 0.0,
        },
    )
    monkeypatch.setattr(orch.model_router, "select_model", lambda **kw: "m1")
    monkeypatch.setattr(
        orch.model_router, "explain_selection", lambda *a, **k: []
    )
    monkeypatch.setattr(orch.model_router, "classify_task", lambda t: "general")

    result = orch.run_task("broken deps task", verbose=False)
    assert len(result["steps"]) >= 1
    exec_meta = result["metadata"].get("execution") or {}
    # either dep_repairs counted or adaptation event recorded
    events = result["metadata"].get("adaptation_events") or []
    assert exec_meta.get("dep_repairs", 0) >= 1 or any(
        e.get("kind") == "dep_repair" for e in events
    )


def test_replan_after_hard_failure(isolated_home: Config, monkeypatch):
    orch = SuperAIOrchestrator(config=isolated_home)
    orch.use_step_cache = False
    orch.config.set("max_replans", 1)
    orch.config.set("max_step_retries", 0)
    orch.config.set("adapt_on_failure", True)
    orch.config.set("quality_gate", False)

    plan_calls = {"n": 0}

    def plans(task, use_llm=None):
        plan_calls["n"] += 1
        if plan_calls["n"] == 1:
            return [
                ExecutionStep(
                    step_id=1,
                    description="will fail step",
                    depends_on=[],
                    recommended_model="mock",
                    estimated_complexity="Low",
                )
            ]
        return [
            ExecutionStep(
                step_id=1,
                description="recovery step with enough output",
                depends_on=[],
                recommended_model="mock",
                estimated_complexity="Low",
            )
        ]

    monkeypatch.setattr(orch.task_planner, "create_plan", plans)

    def call(model, prompt, **kw):
        if "will fail" in prompt or "will fail step" in prompt:
            return {
                "status": "error",
                "response": "fatal permanent model not found",
                "usage": {},
                "estimated_cost_usd": 0.0,
            }
        return {
            "status": "ok",
            "response": "Recovery completed successfully with full details.",
            "usage": {"total_tokens": 8},
            "estimated_cost_usd": 0.0,
        }

    monkeypatch.setattr(orch.model_caller, "call", call)
    monkeypatch.setattr(orch.model_router, "select_model", lambda **kw: "m1")
    monkeypatch.setattr(orch.model_router, "explain_selection", lambda *a, **k: [])
    monkeypatch.setattr(orch.model_router, "classify_task", lambda t: "coding")
    # Failover empty so first step dies hard
    monkeypatch.setattr(orch, "_failover_candidates", lambda *a, **k: [])

    result = orch.run_task("task needing replan", verbose=False)
    events = result["metadata"].get("adaptation_events") or []
    # replan attempted or recovery step present
    assert result["metadata"].get("replans_used", 0) >= 1 or any(
        e.get("kind") == "replan" for e in events
    ) or any(
        "[recovery]" in str(s.get("description") or "") for s in result["steps"]
    )