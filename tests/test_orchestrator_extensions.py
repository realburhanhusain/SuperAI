"""HITL replan approval, critic modes, and run --with-clis."""

from pathlib import Path
from typing import Any, Dict, List

import pytest

from core.config import Config
from core.hitl import HITLStore
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
    cfg.set("max_step_retries", 0, persist=True)
    cfg.set("max_replans", 1, persist=True)
    cfg.set("quality_gate", False, persist=True)
    cfg.set("critic_mode", "light", persist=True)
    cfg.set("replan_requires_approval", False, persist=True)
    cfg.set("step_retry_backoff_sec", 0.0, persist=True)
    cfg.initialize()
    return cfg


def _single_fail_then_replan_plans():
    n = {"c": 0}

    def plans(task, use_llm=None):
        n["c"] += 1
        if n["c"] == 1 and "recovery" not in (task or "").lower() and "Failures" not in (
            task or ""
        ):
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

    return plans


def test_replan_awaits_hitl_approval(isolated_home: Config, tmp_path: Path, monkeypatch):
    isolated_home.set("replan_requires_approval", True, persist=True)
    orch = SuperAIOrchestrator(config=isolated_home)
    orch.hitl = HITLStore(path=tmp_path / ".superai" / "hitl.json")
    orch.use_step_cache = False
    monkeypatch.setattr(orch.task_planner, "create_plan", _single_fail_then_replan_plans())
    monkeypatch.setattr(orch, "_failover_candidates", lambda *a, **k: [])

    def call(model, prompt, **kw):
        if "will fail" in prompt:
            return {
                "status": "error",
                "response": "fatal permanent failure",
                "usage": {},
                "estimated_cost_usd": 0.0,
            }
        return {
            "status": "ok",
            "response": "ok recovery output long enough",
            "usage": {},
            "estimated_cost_usd": 0.0,
        }

    monkeypatch.setattr(orch.model_caller, "call", call)
    monkeypatch.setattr(orch.model_router, "select_model", lambda **kw: "m1")
    monkeypatch.setattr(orch.model_router, "explain_selection", lambda *a, **k: [])
    monkeypatch.setattr(orch.model_router, "classify_task", lambda t: "coding")

    result = orch.run_task("needs approval replan", verbose=False)
    assert result["status"] == "waiting_human"
    assert result.get("clarifications")
    assert (result["clarifications"][0] or {}).get("kind") == "replan_approval"
    events = {e.get("kind") for e in (result["metadata"].get("adaptation_events") or [])}
    assert "replan_awaiting_approval" in events


def test_replan_approved_continues(isolated_home: Config, tmp_path: Path, monkeypatch):
    isolated_home.set("replan_requires_approval", True, persist=True)
    orch = SuperAIOrchestrator(config=isolated_home)
    orch.hitl = HITLStore(path=tmp_path / ".superai" / "hitl.json")
    orch.use_step_cache = False
    monkeypatch.setattr(orch.task_planner, "create_plan", _single_fail_then_replan_plans())
    monkeypatch.setattr(orch, "_failover_candidates", lambda *a, **k: [])

    def call(model, prompt, **kw):
        if "will fail" in prompt:
            return {
                "status": "error",
                "response": "fatal permanent failure",
                "usage": {},
                "estimated_cost_usd": 0.0,
            }
        return {
            "status": "ok",
            "response": "ok recovery output long enough for gate",
            "usage": {"total_tokens": 3},
            "estimated_cost_usd": 0.0,
        }

    monkeypatch.setattr(orch.model_caller, "call", call)
    monkeypatch.setattr(orch.model_router, "select_model", lambda **kw: "m1")
    monkeypatch.setattr(orch.model_router, "explain_selection", lambda *a, **k: [])
    monkeypatch.setattr(orch.model_router, "classify_task", lambda t: "coding")

    r1 = orch.run_task("needs approval replan2", verbose=False)
    assert r1["status"] == "waiting_human"
    cid = r1["clarifications"][0]["id"]
    tid = r1["task_id"]
    orch.hitl.answer_clarification(cid, "approve")

    r2 = orch.run_task(
        "needs approval replan2",
        resume_task_id=tid,
        pause_on_clarification=True,
        verbose=False,
    )
    # After approve, recovery steps should run
    assert r2["status"] in {"success", "partial", "failed"}
    events = [e.get("kind") for e in (r2["metadata"].get("adaptation_events") or [])]
    assert "replan_resume_approved" in events or any(
        "[recovery]" in str(s.get("description") or "") for s in r2.get("steps") or []
    ) or r2.get("success")


def test_critic_off_skips_quality(isolated_home: Config, monkeypatch):
    isolated_home.set("critic_mode", "off", persist=True)
    isolated_home.set("quality_gate", True, persist=True)
    orch = SuperAIOrchestrator(config=isolated_home)
    orch.use_step_cache = False
    monkeypatch.setattr(
        orch.task_planner,
        "create_plan",
        lambda task, use_llm=None: [
            ExecutionStep(
                step_id=1,
                description="tiny",
                depends_on=[],
                recommended_model="m",
                estimated_complexity="Low",
            )
        ],
    )
    # Empty-ish output would fail quality if gate on
    monkeypatch.setattr(
        orch.model_caller,
        "call",
        lambda model, prompt, **kw: {
            "status": "ok",
            "response": "x",
            "usage": {},
            "estimated_cost_usd": 0,
        },
    )
    monkeypatch.setattr(orch.model_router, "select_model", lambda **kw: "m1")
    monkeypatch.setattr(orch.model_router, "explain_selection", lambda *a, **k: [])
    monkeypatch.setattr(orch.model_router, "classify_task", lambda t: "general")

    r = orch.run_task("t", critic_mode="off", verbose=False)
    assert r["status"] == "success"
    assert r["steps"][0]["status"] == "success"


def test_with_clis_dry_run(isolated_home: Config, monkeypatch):
    orch = SuperAIOrchestrator(config=isolated_home)
    orch.use_step_cache = False
    monkeypatch.setattr(
        orch.task_planner,
        "create_plan",
        lambda task, use_llm=None: [
            ExecutionStep(
                step_id=1,
                description="main step with enough text here",
                depends_on=[],
                recommended_model="m",
                estimated_complexity="Low",
            )
        ],
    )
    monkeypatch.setattr(
        orch.model_caller,
        "call",
        lambda model, prompt, **kw: {
            "status": "ok",
            "response": "Main orchestration result content here.",
            "usage": {"total_tokens": 5},
            "estimated_cost_usd": 0.0,
        },
    )
    monkeypatch.setattr(orch.model_router, "select_model", lambda **kw: "m1")
    monkeypatch.setattr(orch.model_router, "explain_selection", lambda *a, **k: [])
    monkeypatch.setattr(orch.model_router, "classify_task", lambda t: "coding")

    r = orch.run_task(
        "build feature",
        with_clis=["claude", "aider"],
        cli_dry_run=True,
        cli_approve=True,
        verbose=False,
    )
    assert r.get("success") is True or r.get("status") in {"success", "partial"}
    assert "cli_parallel" in (r.get("metadata") or {})
    events = {e.get("kind") for e in (r["metadata"].get("adaptation_events") or [])}
    assert "with_clis" in events or r["metadata"]["cli_parallel"].get("workflow_id")


def test_hitl_parse_yes_no():
    assert HITLStore._parse_yes_no("approve") == "approved"
    assert HITLStore._parse_yes_no("reject") == "rejected"
    assert HITLStore._parse_yes_no("maybe later") == "unknown"
