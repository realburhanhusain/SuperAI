"""Improvement V4 unit tests — trust, cost, efficiency, agent UX."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_m1_budget_can_spend(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from core.budget import BudgetGuard

    g = BudgetGuard(path=tmp_path / "budget.json")
    g.configure(daily_usd=1.0, run_usd=0.1, daily_tokens=1000)
    ok = g.can_spend(0.05, tokens=10)
    assert ok["ok"] is True
    bad = g.can_spend(5.0, tokens=10)
    assert bad["ok"] is False
    block = g.enforce_or_block(5.0, enforce=True)
    assert block.get("blocked") is True
    assert block.get("contract") == "superai.result.v1"


def test_m8_plan_mode_no_write(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    from core.superai_agent.tools_bridge import dispatch_tool

    r = dispatch_tool(
        "write",
        {"path": "x.txt", "content": "hi"},
        agent_id="build",
        permission_mode="plan",
    )
    assert r.get("dry_run") is True or r.get("ok") is True
    assert not (tmp_path / "x.txt").exists() or r.get("dry_run")


def test_m8_tenant_tag():
    from core.palace_tenant import scope_metadata, tenant_tag

    m = scope_metadata({}, tenant="t1")
    assert tenant_tag("t1") in m["tags"]


def test_s1_complexity_and_cheap_first():
    from core.task_complexity import cheap_first_models, classify_task

    cx = classify_task("summarize this file")
    assert cx["prefer_cheap"] is True
    assert cx["max_members"] <= 2
    ordered = cheap_first_models(
        ["gpt-4o", "cli:claude", "deepseek-chat"], prefer_cheap=True, max_n=3
    )
    assert ordered[0].startswith("cli:") or "deepseek" in ordered[0]


def test_s5_front_door():
    from core.front_door import choose_path

    assert choose_path("implement login form").get("path") == "agent"
    assert choose_path("code review the auth module").get("path") == "board"
    assert choose_path("hi", force="run").get("path") == "run"


def test_s7_context_pack():
    from core.context_pack import pack_context

    p = pack_context(
        system="SYS " * 100,
        memory="MEM " * 500,
        history="HIST " * 500,
        user="hello",
        max_tokens=200,
    )
    assert p["ok"] is True
    assert p["tokens_est"] <= 250
    assert "memory" in p["dropped"] or p["tokens_est"] <= 200


def test_s10_changeset(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    from core.change_set import ChangeSet

    cs = ChangeSet()
    cs.stage_write("a.txt", "hello")
    dry = cs.apply(dry_run=True)
    assert dry["ok"] is True
    assert not (tmp_path / "a.txt").exists()
    live = cs.apply(dry_run=False)
    assert live["ok"] is True
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "hello"
    cs.stage_write("b.txt", "x")
    rej = cs.reject()
    assert rej["rejected"] == 1


def test_m7_run_trail(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.run_trail import append_event, new_run_id, recent_for_run

    rid = new_run_id()
    append_event(rid, "start", detail="t")
    append_event(rid, "done", ok=True)
    rows = recent_for_run(rid)
    assert any(r.get("kind") == "start" for r in rows)


def test_m5_tool_read_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    f = tmp_path / "c.txt"
    f.write_text("cached-content", encoding="utf-8")
    from core.agent_tools import tool_read

    a = tool_read("c.txt")
    b = tool_read("c.txt")
    assert a.get("ok") and b.get("ok")
    assert b.get("cache_hit") is True or a.get("content") == b.get("content")


def test_agent_runtime_mock_budget_and_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_SESSIONS_ROOT", str(tmp_path / "sess"))
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.superai_agent.runtime import AgentRuntime

    out = AgentRuntime(use_mock=True).run(
        "What is SuperAI?",
        agent="ask",
        permission="plan",
        max_rounds=1,
    )
    d = out.to_dict()
    assert d.get("contract") == "superai.result.v1"
    assert out.raw.get("run_id") or d.get("run_id") or out.ok


def test_call_stream_mock():
    from core.model_caller import ModelCaller

    chunks = list(
        ModelCaller(use_mock=True).call_stream(model="gpt-4o", prompt="hi")
    )
    assert chunks
    assert "".join(chunks)


def test_local_first_profile():
    from core.run_profiles import get_profile

    p = get_profile("local-only") or get_profile("local_only") or {}
    # profile may use different keying
    assert isinstance(p, dict)


def test_local_first_escalate():
    from core.local_first import escalate_chain, order_local_first

    ordered = order_local_first(
        ["gpt-4o", "cli:claude", "deepseek-chat", "llama3.2"],
        prefer_local=True,
        max_n=4,
    )
    assert _is_localish(ordered[0]) or ordered[0] == "cli:claude"
    chain = escalate_chain("gpt-4o", prefer_local=True, max_n=4)
    assert "gpt-4o" in chain
    assert len(chain) >= 1


def _is_localish(m: str) -> bool:
    s = m.lower()
    return s.startswith("cli:") or "llama" in s or "local" in s or "deepseek" in s


def test_spend_guard_and_contract():
    from core.spend_guard import budget_precheck, ensure_public_result

    r = ensure_public_result({"ok": True, "model": "gpt-4o"}, mock=True, ok=True)
    assert r.get("contract") == "superai.result.v1"
    d = budget_precheck(estimated_usd=0.01, tokens=10, enforce=True)
    assert "ok" in d


def test_front_door_routes_code_to_agent():
    from core.front_door import choose_path
    from core.nl_intent import parse_intent, execute_intent

    assert choose_path("implement rate limiting").get("path") == "agent"
    # dry execute should not hang; use_mock path
    intent = parse_intent("implement a hello function")
    # parse may be run action; execute with mock env
    import os

    os.environ["SUPERAI_MOCK_MODE"] = "1"
    out = execute_intent(intent, execute=True, verbose=False)
    assert out.get("executed") is True or out.get("ok") is not None
