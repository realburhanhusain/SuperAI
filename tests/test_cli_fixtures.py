"""
Derived CLI argument fixtures (Phase 1 tail).

87 commands exited 2 under the contract sweep — "missing argument" — which
left 41% of the surface with no contract evidence in either direction. Rather
than hand-write 87 fixtures (another hand-maintained list to drift), the
arguments are derived from Click's own parameter metadata.

These tests hold the derivation honest: it must produce values, it must refuse
rather than guess when no safe value exists, and every command must land in
exactly one bucket.
"""

from __future__ import annotations

import typer

from core import cli_fixtures as cf


# ---------------------------------------------------------------------------
# Derivation rules
# ---------------------------------------------------------------------------


def _app_with(fn):
    """
    Build a Typer app exposing ``fn`` as ``probe-cmd``.

    A second command is registered deliberately: Typer collapses a
    single-command app into a bare Click ``Command``, which has no
    ``get_command`` and so cannot be walked by path.
    """
    app = typer.Typer()
    app.command("probe-cmd")(fn)

    @app.command("filler")
    def _filler():  # pragma: no cover - never invoked
        pass

    return app


def test_choice_in_help_is_used():
    """The codebase documents action arguments as "a | b | c" in help text."""

    def cmd(action: str = typer.Argument(..., help="list | clear | reset")):
        pass

    out = cf.synthesize_args("probe-cmd", app=_app_with(cmd))
    assert out["ok"]
    assert out["args"] == ["list"]
    assert out["how"]["action"] == "choice-in-help"


def test_choice_after_a_colon_in_help():
    def cmd(mode: str = typer.Argument(..., help="mode: fast | slow")):
        pass

    out = cf.synthesize_args("probe-cmd", app=_app_with(cmd))
    assert out["args"] == ["fast"]


def test_prose_help_is_not_mistaken_for_choices():
    """A sentence containing a pipe must not be parsed as an enumeration."""

    def cmd(topic: str = typer.Argument(..., help="Subject to research")):
        pass

    out = cf.synthesize_args("probe-cmd", app=_app_with(cmd))
    assert out["args"] == [cf.PLACEHOLDER_TEXT]
    assert out["how"]["topic"] == "placeholder"


def test_numeric_types_get_numeric_values():
    def cmd(
        amount: float = typer.Argument(...),
        count: int = typer.Argument(...),
    ):
        pass

    out = cf.synthesize_args("probe-cmd", app=_app_with(cmd))
    assert out["args"] == ["0.01", "1"]


def test_path_parameters_get_the_temp_path():
    def cmd(dest: str = typer.Argument(...)):
        pass

    out = cf.synthesize_args("probe-cmd", app=_app_with(cmd), tmp_path="X:/tmp/f.txt")
    assert out["args"] == ["X:/tmp/f.txt"]
    assert out["how"]["dest"] == "temp-path"


def test_url_parameters_refuse_rather_than_guess():
    """A probe must never make a network call, so no URL is ever derived."""

    def cmd(url: str = typer.Argument(...)):
        pass

    out = cf.synthesize_args("probe-cmd", app=_app_with(cmd))
    assert out["ok"] is False
    assert "needs-url" in out["reason"]


def test_required_options_are_emitted_with_their_flag():
    def cmd(session_id: str = typer.Option(..., "--session")):
        pass

    out = cf.synthesize_args("probe-cmd", app=_app_with(cmd))
    assert out["args"] == ["--session", cf.PLACEHOLDER_TEXT]


def test_optional_parameters_are_left_alone():
    def cmd(
        needed: str = typer.Argument(...),
        extra: str = typer.Option("default", "--extra"),
    ):
        pass

    out = cf.synthesize_args("probe-cmd", app=_app_with(cmd))
    assert out["args"] == [cf.PLACEHOLDER_TEXT]


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------


def test_refused_commands_carry_a_reason():
    for name in cf.REFUSE:
        out = cf.synthesize_args(name)
        assert out["ok"] is False
        assert out["reason"], f"{name} refused without a reason"


def test_refusal_applies_to_subcommands_of_a_refused_root():
    out = cf.synthesize_args("shell something")
    assert out["ok"] is False


def test_unknown_command_is_reported_not_guessed():
    out = cf.synthesize_args("no-such-command-anywhere")
    assert out["ok"] is False
    assert "resolvable" in out["reason"]


# ---------------------------------------------------------------------------
# Against the real CLI
# ---------------------------------------------------------------------------


def test_every_read_only_command_lands_in_exactly_one_bucket():
    """Derived, refused-with-a-reason, or needs-no-arguments. No fourth state."""
    report = cf.fixture_report()
    assert report["considered"] > 100
    overlap = set(report["derived"]) & {r["command"] for r in report["refused"]}
    assert not overlap, f"commands in two buckets: {sorted(overlap)}"
    for row in report["refused"]:
        assert row["reason"]


def test_known_commands_derive_expected_shapes():
    out = cf.synthesize_args("board-preflight")
    assert out["ok"] and out["args"] == [cf.PLACEHOLDER_TEXT]

    out = cf.synthesize_args("capture turn")
    assert out["ok"]
    # hook comes from the override table; session is a required option.
    assert "user_prompt" in out["args"]
    assert "--session" in out["args"]


def test_overrides_target_live_parameters():
    """A stale override is a silent no-op, so every key must still resolve."""
    from scli.main import app

    for key in cf.OVERRIDES:
        parts = key.split()
        command, param = " ".join(parts[:-1]), parts[-1]
        node = cf.resolve_command(app, command)
        assert node is not None, f"override for unknown command: {command}"
        names = {str(p.name) for p in getattr(node, "params", []) or []}
        assert param in names, f"override for unknown param: {key}"
