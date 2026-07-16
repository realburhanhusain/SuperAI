"""OS shell + NL accuracy eval + GUI confirm (headless) — thorough tests."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.unit


# --- OS shell ---


def test_parse_shell_from_nl():
    from core.os_shell import parse_shell_from_nl

    assert parse_shell_from_nl("run shell: echo hi") == "echo hi"
    assert parse_shell_from_nl("execute in terminal: git status") == "git status"
    assert parse_shell_from_nl("$ dir") == "dir"
    assert parse_shell_from_nl("just chatting") is None


def test_deny_rm_root():
    from core.os_shell import check_denied, preview_shell

    assert check_denied("rm -rf /") is not None
    p = preview_shell("rm -rf /")
    assert p.get("blocked") is True or p.get("ok") is False


def test_preview_and_dry_run_shell(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    from core.os_shell import preview_shell, run_shell

    prev = preview_shell("echo hello-superai")
    assert prev.get("preview") is True
    assert prev.get("executed") is False
    dry = run_shell("echo hello-superai", dry_run=True)
    assert dry.get("dry_run") is True
    assert dry.get("executed") is False


def test_run_shell_echo(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    from core.os_shell import run_shell

    out = run_shell("echo hello-superai", dry_run=False, permission_mode="yolo")
    assert out.get("executed") is True
    assert out.get("ok") is True
    blob = (out.get("stdout") or "") + (out.get("stderr") or "")
    assert "hello" in blob.lower() or out.get("returncode") == 0


def test_nl_intent_shell():
    from core.nl_intent import parse_intent

    intent = parse_intent("run shell: echo hi")
    assert intent.action == "shell"
    assert "echo" in intent.subject
    assert "shell" in intent.planned_command


# --- NL accuracy ---


def test_normalize_english():
    from core.nl_accuracy import normalize_english

    assert "list" in normalize_english("please show me the models")
    assert "doctor" in normalize_english("health check")


def test_score_and_parse_accurate():
    from core.nl_accuracy import parse_intent_accurate, score_actions

    ranked = score_actions("list available models")
    assert ranked
    assert ranked[0].action == "members"
    p = parse_intent_accurate("show me what models I can use")
    assert p["action"] == "members"
    assert p.get("planned_command")


def test_eval_suite_perfect():
    """DoD: 100% accuracy on SuperAI English paraphrase bank."""
    from core.nl_accuracy import run_eval

    report = run_eval()
    assert report["total"] >= 30
    if not report.get("perfect"):
        # print failures for debugging
        for f in report.get("failures") or []:
            print("FAIL", f)
    assert report["perfect"] is True, report.get("failures")
    assert report["accuracy"] == 1.0


def test_preview_uses_accuracy_engine():
    from core.nl_preview import preview_nl

    p = preview_nl("browse plugins")
    assert p.get("action") == "plugin_catalog" or (p.get("intent") or {}).get(
        "action"
    ) == "plugin_catalog"
    assert "plugin-catalog" in (p.get("planned_command") or "")


# --- GUI confirm (headless) ---


def test_gui_confirm_headless(monkeypatch):
    monkeypatch.setenv("SUPERAI_NO_GUI", "1")
    from core.gui_confirm import confirm_dialog, confirm_nl_preview

    r = confirm_dialog("t", "msg", detail="d")
    assert r.get("backend") == "headless"
    assert r.get("confirmed") is False

    prev = {
        "planned_command": "superai doctor",
        "risk": "low",
        "confidence": 0.9,
        "action": "doctor",
        "summary": "test",
    }
    g = confirm_nl_preview(prev)
    assert g.get("backend") == "headless"
    assert g.get("planned_command") == "superai doctor"


def test_do_gui_confirm_does_not_auto_execute_headless(monkeypatch):
    monkeypatch.setenv("SUPERAI_NO_GUI", "1")
    from core.nl_preview import preview_and_maybe_execute, preview_nl

    # Shell is high-risk → needs_confirm; GUI headless must not auto-approve
    prev = preview_nl("run shell: echo should-not-run-without-confirm")
    assert prev.get("action") == "shell" or (prev.get("intent") or {}).get("action") == "shell"
    out = preview_and_maybe_execute(
        "run shell: echo should-not-run-without-confirm",
        gui_confirm=True,
        yes=False,
    )
    assert out.get("executed") in {False, None}
    assert out.get("blocked_reason") or out.get("preview") is True


def test_preview_shell_nl_integration():
    from core.nl_preview import preview_nl

    p = preview_nl("run shell: echo n202")
    assert p.get("action") == "shell" or (p.get("intent") or {}).get("action") == "shell"
    assert "shell" in (p.get("planned_command") or "")
    assert p.get("shell_preview") is not None or p.get("preview") is True
