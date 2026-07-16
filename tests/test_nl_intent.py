"""Natural-language → SuperAI command routing."""

from core.nl_intent import ask_superai, format_planned_command, parse_intent


def test_parse_members_list():
    i = parse_intent("list available models and clis")
    assert i.action == "members"
    assert i.confidence >= 0.8
    assert "members" in i.planned_command


def test_parse_review_with_members():
    i = parse_intent(
        "review the auth design with gpt-4o and gemini dry-run"
    )
    assert i.action == "review"
    assert "auth" in i.subject.lower() or "design" in i.subject.lower()
    assert "gpt-4o" in i.members
    assert any("gemini" in m for m in i.members)
    assert i.dry_run is True
    assert "review" in i.planned_command


def test_parse_advise_and_council_pick():
    a = parse_intent("advise should we ship tonight prefer cli")
    assert a.action == "advise"
    assert a.prefer == "cli"

    c = parse_intent("council on architecture let me pick")
    assert c.action == "council"
    assert c.pick is True
    assert "--pick" in c.planned_command


def test_parse_run_implement():
    i = parse_intent("implement rate limiting with gpt-4o and claude")
    assert i.action == "run"
    assert "rate" in i.subject.lower() or "limiting" in i.subject.lower()
    assert "gpt-4o" in i.members
    assert any("claude" in m for m in i.members)


def test_universal_agent_fallback_any_phrase():
    """Free-form requests become agentic run (Claude Code style)."""
    i = parse_intent("explain the tradeoffs of using SQLite vs Postgres here")
    assert i.action == "run"
    assert i.confidence >= 0.5


def test_parse_doctor_plan_memory():
    assert parse_intent("run doctor health check").action == "doctor"
    assert parse_intent("plan a FastAPI hello service").action == "plan"
    assert parse_intent("search memory for postgres setup").action == "memory_search"
    assert parse_intent("pr-review the last commit").action == "pr_review"


def test_parse_does_not_treat_api_id_as_bare_cli():
    i = parse_intent("review design with gemini-2.5-pro")
    assert i.action == "review"
    # should pick API-style id, not force only cli:gemini from substring alone
    assert "gemini-2.5-pro" in i.members or any("gemini" in m for m in i.members)


def test_plan_only_no_execute():
    out = ask_superai(
        "list available models",
        plan_only=True,
        execute=False,
    )
    assert out.get("planned_command")
    assert out.get("executed") is False
    assert out["intent"]["action"] == "members"


def test_execute_members_offline(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    monkeypatch.setenv("SUPERAI_NON_INTERACTIVE", "1")
    out = ask_superai("list available models and clis", execute=True)
    assert out.get("ok") is True
    assert out.get("executed") is True
    assert out.get("result", {}).get("ok") is True


def test_execute_review_dry(tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("SUPERAI_NON_INTERACTIVE", "1")
    out = ask_superai(
        "review the login flow with gpt-4o dry-run",
        execute=True,
    )
    assert out.get("ok") is True
    assert out.get("executed") is True
    res = out.get("result") or {}
    assert res.get("ok") is True
    assert res.get("mode") == "review"


def test_format_planned_command_stable():
    i = parse_intent("advise shipping prefer mixed")
    cmd = format_planned_command(i)
    assert cmd.startswith("superai advise")
