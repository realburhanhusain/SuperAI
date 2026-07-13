"""Parallel multi-terminal pool + dashboard snapshot."""

import sys
from pathlib import Path

from core.terminal_pool import ParallelTerminalManager
from core.agentic import AgenticWorkflows
from core.observability import build_dashboard_snapshot


def test_parallel_terminals_dry_run(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir()
    mgr = ParallelTerminalManager(path=tmp_path / ".superai" / "terminal_sessions.json")
    result = mgr.run_parallel(
        [
            {"title": "a", "role": "architect", "command": [sys.executable, "-c", "print(1)"]},
            {"title": "b", "role": "tester", "command": [sys.executable, "-c", "print(2)"]},
            {"title": "c", "role": "reviewer", "command": [sys.executable, "-c", "print(3)"]},
        ],
        max_workers=3,
        dry_run=True,
        auto_approve=True,
        cwd=str(tmp_path),
    )
    assert result["total"] == 3
    assert result["succeeded"] == 3
    assert result.get("workflow_id")
    snap = mgr.snapshot_for_dashboard()
    assert snap["totals"]["done"] >= 3
    sessions = mgr.list_sessions()
    assert len(sessions) >= 3
    assert all(s["status"] == "done" for s in sessions)
    assert all("[dry-run]" in (s.get("stdout_tail") or "") for s in sessions)


def test_parallel_terminals_live_safe(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir()
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    mgr = ParallelTerminalManager(path=tmp_path / ".superai" / "terminal_sessions.json")
    result = mgr.run_parallel(
        [
            {
                "title": "echo1",
                "role": "worker",
                "command": [sys.executable, "-c", "print('hello-term')"],
            },
            {
                "title": "echo2",
                "role": "worker",
                "command": [sys.executable, "-c", "print('world-term')"],
            },
        ],
        max_workers=2,
        dry_run=False,
        auto_approve=True,
        cwd=str(tmp_path),
    )
    assert result["total"] == 2
    assert result["succeeded"] == 2
    outs = " ".join(s.get("stdout_tail") or "" for s in result["sessions"])
    assert "hello-term" in outs
    assert "world-term" in outs


def test_agentic_parallel_terminals(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir()
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    result = AgenticWorkflows().parallel_terminal_workflow(
        "build a hello CLI",
        max_workers=4,
        dry_run=True,
        auto_approve=True,
        cwd=str(tmp_path),
    )
    assert result.get("sessions")
    assert "synthesis" in result
    assert result.get("succeeded", 0) >= 1


def test_dashboard_includes_terminal_pool(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir()
    mgr = ParallelTerminalManager(path=tmp_path / ".superai" / "terminal_sessions.json")
    mgr.run_parallel(
        [{"title": "t", "command": [sys.executable, "-c", "print(1)"], "role": "worker"}],
        dry_run=True,
        auto_approve=True,
        cwd=str(tmp_path),
    )
    snap = build_dashboard_snapshot()
    assert "terminal_pool" in snap


def test_blocks_shell_meta(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir()
    monkeypatch.delenv("SUPERAI_ALLOW_SHELL_META", raising=False)
    mgr = ParallelTerminalManager(path=tmp_path / ".superai" / "terminal_sessions.json")
    result = mgr.run_parallel(
        [{"title": "bad", "command": ["cmd", "/c", "echo hi"], "role": "worker"}],
        dry_run=False,
        auto_approve=True,
        cwd=str(tmp_path),
    )
    assert result["failed"] == 1
    assert "Blocked" in (result["sessions"][0].get("error") or "")
