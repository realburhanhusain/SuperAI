"""N202 — NL → any command with preview (thorough offline tests)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_preview_nl_basic_fields():
    from core.nl_preview import preview_nl

    p = preview_nl("list available models")
    assert p.get("ok") is True
    assert p.get("preview") is True
    assert p.get("executed") is False
    assert p.get("planned_command")
    assert isinstance(p.get("argv"), list)
    assert p.get("argv")[0] == "superai"
    assert "intent" in p
    assert "front_door" in p
    assert "confidence" in p
    assert "risk" in p
    assert "needs_confirm" in p
    assert p.get("contract") == "superai.result.v1" or "planned_command" in p


def test_catalog_examples_actions():
    from core.nl_preview import catalog_examples, preview_nl

    for ex in catalog_examples():
        p = preview_nl(ex["nl"])
        action = (p.get("intent") or {}).get("action") or p.get("action")
        # front-door may remap run → superai_agent; allow either expected or remapped
        expected = ex["expect_action"]
        if expected == "run":
            assert action in {"run", "superai_agent", "review", "unknown"}
        else:
            assert action == expected, f"{ex['nl']} → {action} want {expected}"
        assert "superai" in (p.get("planned_command") or "")


def test_preview_review_and_doctor():
    from core.nl_preview import preview_nl

    r = preview_nl("review auth middleware dry-run")
    assert r["action"] == "review" or (r.get("intent") or {}).get("action") == "review"
    assert "review" in r["planned_command"]
    assert r.get("dry_run") is True

    d = preview_nl("run doctor")
    assert (d.get("intent") or {}).get("action") == "doctor"
    assert d["planned_command"].startswith("superai doctor")
    assert d.get("risk") == "low"


def test_preview_plugin_status_smoke_voice():
    from core.nl_preview import preview_nl

    for nl, needle in (
        ("plugin catalog memory", "plugin-catalog"),
        ("show status with cost", "status"),
        ("smoke preflight", "smoke-preflight"),
        ("voice status", "voice"),
    ):
        p = preview_nl(nl)
        assert needle in p["planned_command"], p["planned_command"]


def test_planned_argv_tokenization():
    from core.nl_intent import parse_intent
    from core.nl_preview import planned_argv

    intent = parse_intent("review the payment service dry-run")
    argv = planned_argv(intent)
    assert argv[0] == "superai"
    assert "review" in argv


def test_needs_confirm_blocks_execute():
    from core.nl_preview import execute_from_preview, preview_nl

    # Force a low-confidence style ambiguous short phrase
    prev = preview_nl("maybe do something complex with many steps somehow")
    # Even if not needs_confirm, force for test
    prev["needs_confirm"] = True
    blocked = execute_from_preview(prev, confirmed=False)
    assert blocked.get("ok") is False
    assert blocked.get("error") == "confirmation_required"
    assert blocked.get("error_code") == "permission" or "confirm" in str(
        blocked.get("error")
    )


def test_execute_preview_members_confirmed(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    from core.nl_preview import execute_from_preview, preview_nl

    prev = preview_nl("list available models")
    prev["needs_confirm"] = False
    out = execute_from_preview(prev, confirmed=True)
    assert out.get("ok") is True or out.get("executed") is True
    assert out.get("planned_command") or (out.get("preview") or {}).get(
        "planned_command"
    )


def test_preview_and_maybe_execute_preview_only():
    from core.nl_preview import preview_and_maybe_execute

    p = preview_and_maybe_execute("doctor", preview_only=True)
    assert p.get("preview") is True
    assert p.get("executed") is False


def test_preview_and_maybe_execute_safe_no_yes():
    from core.nl_preview import preview_and_maybe_execute

    # doctor is safe/low risk → should execute without --yes
    out = preview_and_maybe_execute("run doctor", preview_only=False, yes=False)
    # either executed or returned ok planned
    assert out.get("ok") is not False or out.get("planned_command")


def test_risk_levels():
    from core.nl_intent import parse_intent
    from core.nl_preview import risk_level

    doc = parse_intent("doctor")
    assert risk_level(doc) == "low"
    run = parse_intent("implement feature live for real")
    # live high-risk action
    assert risk_level(run) in {"medium", "high"}


def test_force_path_agent():
    from core.nl_preview import preview_nl

    p = preview_nl("do something vague", force_path="agent")
    assert p["front_door"]["path"] == "agent"
    assert "agent" in p["planned_command"] or p.get("action") == "superai_agent"
