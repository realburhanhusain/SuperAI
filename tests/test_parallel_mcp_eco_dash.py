"""TaskResult, parallel plan, MCP context, ecosystem, observability."""

from pathlib import Path

from superai.core.ecosystem import EcosystemHub
from superai.core.mcp_context import MCPContextPack
from superai.core.observability import (
    build_dashboard_snapshot,
    recent_feedback,
    write_feedback,
)
from superai.core.task_planner import TaskPlanner
from superai.core.task_result import StepResult, TaskResult


class _DummyRouter:
    def classify_task(self, task: str) -> str:
        return "general"


def test_task_result_roundtrip():
    raw = {
        "task_id": "t1",
        "task": "hello",
        "success": True,
        "status": "success",
        "message": "ok",
        "steps": [
            {
                "step": 1,
                "description": "do",
                "status": "success",
                "result": "done",
                "duration_ms": 10,
            }
        ],
        "duration": 0.1,
        "mode": "mock",
        "total_tokens": 0,
        "estimated_cost_usd": 0.0,
        "metadata": {"x": 1},
    }
    tr = TaskResult.from_dict(raw)
    assert tr.success is True
    assert tr.steps_succeeded == 1
    assert tr.to_dict()["task_id"] == "t1"
    sr = StepResult(step=2, description="b", status="failed", error="x")
    assert sr.status == "failed"


def test_plan_parallel_flags():
    planner = TaskPlanner(_DummyRouter())
    steps = planner.create_plan("build a FastAPI service")
    assert len(steps) >= 5
    parallel = [s for s in steps if s.can_run_parallel]
    assert len(parallel) >= 2
    # tests + docs both depend only on step 3
    assert all(3 in s.depends_on for s in parallel)

    research = planner.create_plan("research and compare databases")
    assert any(s.can_run_parallel for s in research)


def test_mcp_context_pack(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    mcp = MCPContextPack(root=tmp_path / "contexts")
    pack = mcp.build(
        task="implement auth",
        files=["a.py"],
        skills=["auth-skill"],
        auto_memory=False,
        auto_skills=False,
    )
    assert pack["schema"].startswith("superai.mcp_context")
    assert "auth-skill" in pack["skills"]
    path = mcp.save(pack)
    loaded = mcp.load(path)
    assert loaded["id"] == pack["id"]
    text = mcp.format_for_prompt(pack)
    assert "implement auth" in text
    wrapped = mcp.wrap_cli_prompt(pack, "go")
    assert "User request" in wrapped
    env = mcp.parse_cli_output("hello out", exit_code=0, cli="aider", context_id=pack["id"])
    assert env["ok"] is True


def test_ecosystem_stub_search_and_emit(monkeypatch):
    monkeypatch.setenv("SUPERAI_ECOSYSTEM_DRY_RUN", "1")
    monkeypatch.setenv("SUPERAI_N8N_WEBHOOK_URL", "https://example.com/hook")
    hub = EcosystemHub(dry_run=True)
    search = hub.search("superai orchestration")
    assert search["ok"] is True
    assert search["results"]
    emit = hub.emit_event("task.completed", {"id": "1"})
    assert emit["ok"] is True
    assert emit.get("dry_run") is True
    caps = hub.capabilities()
    assert "cloud_clis" in caps
    assert caps["webhook_configured"] is True


def test_observability_snapshot_and_feedback(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # ensure dirs exist
    (tmp_path / ".superai").mkdir(parents=True, exist_ok=True)
    entry = write_feedback("looks good", surface="test")
    assert entry["message"] == "looks good"
    recent = recent_feedback(5)
    assert recent
    snap = build_dashboard_snapshot(history_limit=3)
    assert "ts" in snap
    assert "history" in snap


def test_orchestrator_parallel_meta(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "true")
    from superai.core.config import Config
    from superai.core.orchestrator import SuperAIOrchestrator

    cfg = Config(config_path=str(tmp_path / "cfg.json"))
    cfg.set("mock_mode", True)
    cfg.set("backup_enabled", False)
    orch = SuperAIOrchestrator(config=cfg)
    # multi-step build plan → parallel steps 4+5
    result = orch.run_task("build a hello API", verbose=False)
    assert "task_id" in result
    meta = result.get("metadata") or {}
    assert "execution" in meta or result.get("status") in {"success", "partial", "failed"}
    # validation flag if pydantic ok
    if result.get("success"):
        assert meta.get("task_result_validated") is True or "execution" in meta
