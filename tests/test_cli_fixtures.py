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


# ---------------------------------------------------------------------------
# Groups are not surfaces
# ---------------------------------------------------------------------------


def test_command_groups_are_not_invokable():
    """
    `superai budget` is a Typer *group*: it prints "Missing command." and has no
    result to contract. Its subcommands are the real surfaces. Enumerating
    groups alongside commands made `budget` read as a permanent coverage gap.
    """
    out = cf.synthesize_args("budget")
    assert out["ok"] is False
    assert out.get("is_group") is True
    assert "group" in out["reason"]


def test_group_names_finds_nested_groups():
    from core.surface_inventory import group_names

    groups = group_names()
    assert "budget" in groups
    assert "check" in groups
    # Nested: `budget command set` lives under `budget command`.
    assert "budget command" in groups
    # A real command must not be listed as a group.
    assert "status" not in groups


# ---------------------------------------------------------------------------
# Options a command needs but does not declare required
# ---------------------------------------------------------------------------


def test_extra_args_are_appended():
    """
    `ci-why` declares --file and --text optional but rejects being called with
    neither. Click cannot express "exactly one of these", so introspection
    alone can never find it.
    """
    out = cf.synthesize_args("ci-why")
    assert out["ok"] is True
    assert "--text" in out["args"]
    assert out["how"].get("<extra_args>") == "extra-args"


def test_extra_args_target_live_commands():
    """A stale EXTRA_ARGS key is a silent no-op, same as a stale override."""
    from scli.main import app

    for command in cf.EXTRA_ARGS:
        assert cf.resolve_command(app, command) is not None, command


def test_workspace_jail_commands_are_refused_not_reported_as_gaps():
    """
    `diff-edit` and `notebook` enforce the workspace jail (M006) — a path
    outside the repo is rejected. The probe deliberately writes fixtures to a
    sandboxed HOME so it cannot touch real state, so satisfying the jail would
    mean writing into the working tree during a read-only sweep. Refusing is
    correct; the jail is a security control working as designed.
    """
    for command in ("diff-edit", "notebook"):
        out = cf.synthesize_args(command)
        assert out["ok"] is False
        assert "workspace jail" in out["reason"]
