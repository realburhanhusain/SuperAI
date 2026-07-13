"""Must/Should/Nice backlog feature tests."""

from pathlib import Path

from core.audit_log import AuditLog
from core.budget import BudgetGuard
from core.chat_session import ChatSession
from core.constitution import ensure_default_constitution, format_for_prompt, load_constitution
from core.doctor import run_doctor
from core.error_recovery import classify_error
from core.mcp_server import handle_request
from core.policy import PolicyEngine
from core.schedule_store import ScheduleStore
from core.secrets import looks_like_secret, redact_text
from core.tool_schemas import list_tool_schemas
from core.workspace import assert_in_workspace, workspace_root


def test_secrets_redact():
    s = "api_key=sk-abcdefghijklmnopqrstuvwxyz"
    out = redact_text(s)
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in out
    assert looks_like_secret(s)


def test_workspace_jail(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    p = assert_in_workspace(tmp_path / "a.txt")
    assert p.parent == tmp_path or tmp_path in p.parents or p == tmp_path / "a.txt"
    try:
        assert_in_workspace("/etc/passwd")
        assert False, "should raise"
    except ValueError:
        pass


def test_doctor_quick(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    r = run_doctor(quick=True)
    assert "checks" in r
    assert r.get("next_steps")


def test_budget_guard(tmp_path: Path):
    g = BudgetGuard(path=tmp_path / "b.json")
    g.configure(daily_usd=1.0, run_usd=0.5)
    g.record(usd=0.1, tokens=10)
    snap = g.snapshot()
    assert snap["spent_usd_today"] >= 0.1
    try:
        g.check_can_spend(estimated_usd=10.0)
        assert False
    except RuntimeError:
        pass


def test_audit_and_policy(tmp_path: Path):
    a = AuditLog(path=tmp_path / "a.jsonl")
    a.record("test", {"x": 1})
    assert a.recent(5)
    pe = PolicyEngine(path=tmp_path / "p.json")
    assert pe.list_rules()
    pe.set_enabled("workspace_jail", False)
    assert pe.is_enabled("workspace_jail") is False


def test_chat_session(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "true")
    cs = ChatSession(path=tmp_path / "chats")
    sid = cs.start()
    out = cs.ask(sid, "hello world", use_mock=True)
    assert out.get("reply")
    assert cs.history(sid)["messages"]


def test_constitution(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    p = ensure_default_constitution()
    assert p.exists()
    assert "Constitution" in load_constitution() or "rules" in format_for_prompt().lower()


def test_schedule(tmp_path: Path):
    s = ScheduleStore(path=tmp_path / "sched.json")
    j = s.add("daily-doc", "doctor", every_hours=0.0001)
    assert j["id"]
    # force due
    for job in s.data["jobs"]:
        job["next_run"] = 0
    s.save()
    results = s.run_due()
    assert results


def test_mcp_handle():
    r = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert "result" in r
    tools = r["result"]["tools"]
    assert any(t["name"] == "superai_status" for t in tools)


def test_error_classify():
    c = classify_error("401 unauthorized api key")
    assert c["class"] == "auth"
    c2 = classify_error("rate limit 429")
    assert c2["retryable"] is True


def test_tool_schemas():
    schemas = list_tool_schemas()
    assert any(s["function"]["name"] == "edit_file" for s in schemas)


def test_plan_mermaid():
    from core.task_planner import TaskPlanner

    class R:
        pass

    md = TaskPlanner(R()).export_plan_mermaid("build an API")
    assert "mermaid" in md
    assert "flowchart" in md
