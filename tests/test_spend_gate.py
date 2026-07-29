"""
CLI-level spend ceiling (Phase 2 / V1-P1-3).

``budget_precheck`` was reachable but never called from ``src/cli/main.py`` —
zero call sites across 8581 lines. Spend was gated only inside
``ModelCaller``/``call_lifecycle``, by which point the command name is gone, so
the S132 per-command ceilings could not bind.
"""

from __future__ import annotations

import pytest

from core import spend_gate


# ---------------------------------------------------------------------------
# Which commands are gated
# ---------------------------------------------------------------------------


def test_gated_set_is_derived_not_hand_listed():
    """The set comes from surface_inventory's classification."""
    gated = spend_gate.spend_commands()
    assert gated, "expected some spend commands"
    for name in ("council", "ask", "bakeoff", "compare", "agent"):
        assert name in gated, f"{name} can spend but is not gated"


def test_exemptions_carry_a_reason_and_are_excluded():
    gated = spend_gate.spend_commands()
    assert spend_gate.GATE_EXEMPT, "expected explicit exemptions"
    for name, reason in spend_gate.GATE_EXEMPT.items():
        assert reason, f"{name} exempted without a reason"
        assert name not in gated


def test_non_spend_commands_are_not_gated():
    assert "status" not in spend_gate.spend_commands()
    assert "doctor" not in spend_gate.spend_commands()


# ---------------------------------------------------------------------------
# argv resolution
# ---------------------------------------------------------------------------


def test_resolves_a_top_level_command():
    assert spend_gate.command_path_from_argv(["council", "a topic"]) == "council"


def test_resolves_a_nested_command():
    """
    ``check upgrades`` is a spend surface two levels deep.

    Matching on the joined path rather than ``ctx.invoked_subcommand`` is what
    makes this work — the root callback only ever sees ``check``.
    """
    assert spend_gate.command_path_from_argv(["check", "upgrades", "x"]) == "check upgrades"


def test_flags_before_the_command_are_skipped():
    assert spend_gate.command_path_from_argv(["--json", "ask", "hi"]) == "ask"


def test_non_spend_argv_resolves_to_none():
    assert spend_gate.command_path_from_argv(["status"]) is None
    assert spend_gate.command_path_from_argv([]) is None


# ---------------------------------------------------------------------------
# Gate behaviour
# ---------------------------------------------------------------------------


def test_gate_is_skipped_in_mock_mode(monkeypatch):
    """Mock mode cannot spend, so it must never be blocked on cost."""
    import core.config as cfg_mod

    monkeypatch.setattr(cfg_mod.Config, "use_mock", property(lambda self: True))
    assert spend_gate.gate_argv(["council", "topic"]) is None


def test_gate_can_be_disabled_by_env(monkeypatch):
    monkeypatch.setenv(spend_gate.DISABLE_ENV, "1")
    assert spend_gate.gate_argv(["council", "topic"]) is None


def test_blocked_envelope_shape(monkeypatch):
    """A block must carry a contract-shaped failure, not a bare bool."""
    monkeypatch.setattr(spend_gate, "command_path_from_argv", lambda _a: "council")
    monkeypatch.setattr(
        "core.spend_guard.budget_precheck",
        lambda **kw: {"ok": False, "blocked": True, "error": "over ceiling"},
    )
    import core.config as cfg_mod

    monkeypatch.setattr(cfg_mod.Config, "use_mock", property(lambda self: False))

    blocked = spend_gate.gate_argv(["council", "topic"])
    assert blocked is not None
    assert blocked["ok"] is False
    assert blocked["blocked"] is True
    assert blocked["error_code"] == "budget"
    assert blocked["command"] == "council"


def test_allowed_returns_none(monkeypatch):
    monkeypatch.setattr(spend_gate, "command_path_from_argv", lambda _a: "council")
    monkeypatch.setattr("core.spend_guard.budget_precheck", lambda **kw: {"ok": True})
    import core.config as cfg_mod

    monkeypatch.setattr(cfg_mod.Config, "use_mock", property(lambda self: False))
    assert spend_gate.gate_argv(["council", "topic"]) is None


def test_gate_never_records_spend():
    """
    The CLI layer pre-checks only.

    ``ModelCaller``/``call_lifecycle`` own ``budget_record`` because only they
    know real token counts; recording here would double-count every call.
    """
    import ast
    from pathlib import Path

    # Checked against the AST, not the text: the module's docstring and its
    # gate_report note both mention budget_record by name, and a substring
    # match would flag the explanation rather than a call.
    tree = ast.parse(Path(spend_gate.__file__).read_text(encoding="utf-8"))
    called = {
        node.func.attr
        if isinstance(node.func, ast.Attribute)
        else getattr(node.func, "id", "")
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "budget_record" not in called, "CLI gate must never record spend"
    assert "budget_record" not in imported, "CLI gate must not import budget_record"


def test_gate_report_shape():
    rep = spend_gate.gate_report()
    assert rep["ok"] is True
    assert rep["gated_count"] == len(rep["gated_commands"])
    assert rep["exempt_count"] == len(rep["exempt"])


# ---------------------------------------------------------------------------
# audit_m001 no longer uses inspect.getsource
# ---------------------------------------------------------------------------


def test_audit_m001_uses_ast_not_getsource():
    """
    ``inspect.getsource`` reads the .py off disk, so it raised under a
    wheel/bytecode-only install and the audit reported a spend gap that was
    really a packaging artefact.
    """
    import ast
    from pathlib import Path

    from core import foundation_safety

    tree = ast.parse(Path(foundation_safety.__file__).read_text(encoding="utf-8"))
    fn = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "audit_m001"
    )
    # Attribute access, not substring: the comment at the old call site
    # explains why getsource was removed and must not trip this.
    getsource_calls = [
        n
        for n in ast.walk(fn)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "getsource"
    ]
    assert not getsource_calls


def test_method_tokens_found_for_model_caller():
    from core.foundation_safety import _source_tokens_for_method

    tokens = _source_tokens_for_method("model_caller.py", "ModelCaller", "call")
    assert tokens is not None
    assert "pre_call" in tokens
    assert "skip_budget" in tokens


def test_missing_source_is_none_not_empty():
    """
    ``None`` means "cannot prove", which must not be read as "proved absent".

    That distinction is the whole point of the change: an unavailable source
    file is a packaging fact, not a missing budget gate.
    """
    from core.foundation_safety import _source_tokens_for_method

    assert _source_tokens_for_method("no_such_file.py", "X", "y") is None


def test_audit_m001_passes():
    from core.foundation_safety import audit_m001

    result = audit_m001()
    assert result["ok"] is True, result["issues"]


@pytest.mark.parametrize("name", ["council", "ask", "bakeoff"])
def test_known_spend_commands_resolve(name):
    assert spend_gate.command_path_from_argv([name, "x"]) == name
