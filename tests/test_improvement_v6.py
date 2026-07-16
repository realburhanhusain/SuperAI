"""V6 phases 1–15 foundations unit tests (honest coverage)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_v6_phase_report():
    from core.v6_phase_status import phase_report

    r = phase_report()
    assert r["ok"] is True
    assert r["counts"]["done"] >= 16
    # phases 0-16 done; 17-20 n/a
    statuses = {p["phase"]: p["status"] for p in r["phases"]}
    assert statuses[6] == "done"
    assert statuses[16] == "done"
    assert statuses[20] == "n/a"


def test_agent_todos(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from core.agent_todos import AgentTodoStore

    s = AgentTodoStore(path=tmp_path / "t.json")
    lid = s.ensure()
    it = s.add(lid, "step one")
    assert s.open_count(lid) == 1
    assert s.complete(lid, it["id"]) is True
    assert s.open_count(lid) == 0


def test_spec_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_SESSIONS_ROOT", str(tmp_path / "sess"))
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    (tmp_path / ".superai").mkdir(parents=True)
    from core.spec_mode import run_spec_first

    out = run_spec_first("add hello endpoint", use_mock=True, auto_approve=False)
    assert out.get("ok") is True
    assert out.get("spec_id") or out.get("phase")


def test_quality_gates_empty_ok(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from core.quality_gates import detect_and_run

    r = detect_and_run(tmp_path)
    assert "ok" in r


def test_project_memory_tags(tmp_path):
    from core.project_memory import project_id, scope_tags

    assert project_id(tmp_path).startswith("proj-")
    tags = scope_tags(["a"], root=tmp_path)
    assert any(t.startswith("project:") for t in tags)


def test_capability_tags():
    from core.capability_tags import filter_by_capability, tags_for_model

    assert "local" in tags_for_model("llama3.2")
    assert "cli:claude" in filter_by_capability(["cli:claude", "gpt-4o"], "local")


def test_macros(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.macros import list_macros, set_macro

    set_macro("hi", "superai doctor")
    assert list_macros()["count"] == 1


def test_hooks():
    from core.hooks import clear_hooks, register_pre, run_pre

    clear_hooks()
    register_pre(lambda n, a: {"ok": False, "error": "blocked"} if n == "bash" else None)
    assert run_pre("bash", {})["error"] == "blocked"
    assert run_pre("read", {}) is None
    clear_hooks()


def test_recipes_and_onboard(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.onboarding_quest import mark, status
    from core.recipes import get_recipe, list_recipes

    assert list_recipes()["count"] >= 3
    assert get_recipe("fix-bug")["ok"] is True
    mark("doctor")
    assert status()["completed"] >= 1


def test_ci_why_and_lsp(tmp_path):
    from core.ci_why import analyze_log
    from core.lsp_bridge import diagnostics_stub

    r = analyze_log("FAILED tests/test_x.py\nAssertionError: boom")
    assert r["findings"]
    f = tmp_path / "b.py"
    f.write_text("def ok():\n    return 1\n", encoding="utf-8")
    d = diagnostics_stub(str(f))
    assert d["ok"] is True


def test_exit_codes():
    from core.exit_codes import BUDGET, OK, from_result

    assert from_result({"ok": True, "status": "success"}) == OK
    assert from_result({"ok": False, "error_code": "budget"}) == BUDGET


def test_timeouts(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.tool_timeouts import get, set_timeout

    set_timeout("bash", 99.0)
    assert get("bash") == 99.0


def test_watch_mode(tmp_path):
    from core.watch_mode import run_watch

    (tmp_path / "a.py").write_text("x=1\n", encoding="utf-8")
    r = run_watch(lambda: {"ok": True}, root=tmp_path, interval_sec=0.05, max_iters=2)
    assert r["ok"] is True
    assert r["iters"] >= 1


def test_role_debate_mock(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_SESSIONS_ROOT", str(tmp_path / "s"))
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.role_debate import debate

    out = debate("Should we use Redis?", use_mock=True)
    assert out.get("ok") is True
    assert len(out.get("turns") or []) == 3


def test_whats_new():
    from core.changelog_cli import whats_new

    assert whats_new()["entries"]
