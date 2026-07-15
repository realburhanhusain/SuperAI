"""Parallel multi-CLI pool + dashboard snapshot."""

from pathlib import Path

from core.cli_pool import ParallelCLIManager
from core.agentic import AgenticWorkflows
from core.observability import build_dashboard_snapshot


def test_parallel_cli_dry_run(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir()
    mgr = ParallelCLIManager(path=tmp_path / ".superai" / "cli_jobs.json")
    result = mgr.run_parallel(
        [
            {"cli": "claude", "prompt": "design API", "role": "architect"},
            {"cli": "aider", "prompt": "implement API", "role": "implementer"},
            {"cli": "gemini", "prompt": "test API", "role": "tester"},
        ],
        max_workers=3,
        dry_run=True,
        auto_approve=True,
        with_context=False,
    )
    assert result["total"] == 3
    assert result["succeeded"] + result.get("dry_run_count", 0) == 3
    assert result.get("workflow_id")
    snap = mgr.snapshot_for_dashboard()
    assert snap["totals"]["done"] >= 3
    jobs = mgr.list_jobs()
    assert len(jobs) >= 3
    assert all(j["status"] in {"done", "dry_run"} for j in jobs)


def test_agentic_parallel_cli(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir()
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    # Force manager path via home
    result = AgenticWorkflows().parallel_cli_workflow(
        "build a hello CLI",
        clis=["claude", "aider"],
        max_workers=2,
        dry_run=True,
        auto_approve=True,
    )
    assert result.get("jobs")
    assert "synthesis" in result
    assert result.get("succeeded", 0) + result.get("dry_run_count", 0) >= 1


def test_dashboard_includes_cli_pool(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir()
    mgr = ParallelCLIManager(path=tmp_path / ".superai" / "cli_jobs.json")
    mgr.run_parallel(
        [{"cli": "cursor", "prompt": "x", "role": "worker"}],
        dry_run=True,
        auto_approve=True,
        with_context=False,
    )
    # observability uses default path under home
    snap = build_dashboard_snapshot()
    assert "cli_pool" in snap


def test_parallel_save_stress(tmp_path: Path, monkeypatch):
    """Many concurrent workers must not corrupt or fail Windows file replace."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir()
    mgr = ParallelCLIManager(path=tmp_path / ".superai" / "cli_jobs.json")
    work = [
        {"cli": f"cli{i}", "prompt": f"task {i}", "role": "worker"}
        for i in range(8)
    ]
    result = mgr.run_parallel(
        work,
        max_workers=8,
        dry_run=True,
        auto_approve=True,
        with_context=False,
    )
    assert result["total"] == 8
    assert result["succeeded"] + result.get("dry_run_count", 0) == 8
    assert mgr.path.exists()
    assert len(mgr.list_jobs()) >= 8
