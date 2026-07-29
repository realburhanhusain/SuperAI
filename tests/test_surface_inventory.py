"""
Phase 0 — public surface inventory.

The point of these tests is not that the enumerator returns a big number. It is
that the enumerator **can fail**. This repo has shipped several completeness
checks that were structurally incapable of failing (see
``test_top30_check_is_not_a_tautology`` below), so every detector here is given
a deliberately-broken fixture and asserted to catch it.

Offline only. No live keys, no subprocesses, no network.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from core import surface_inventory as si

# ---------------------------------------------------------------------------
# Fixture module: two commands, one wrapped, one not.
# ---------------------------------------------------------------------------

FIXTURE_SOURCE = '''
import typer

fixture_app = typer.Typer()
sub_app = typer.Typer()
fixture_app.add_typer(sub_app, name="nested")


@fixture_app.command("wrapped-cmd")
def wrapped_cmd():
    from core.public_surface import emit_public

    return emit_public({"ok": True})


@fixture_app.command("unwrapped-cmd")
def unwrapped_cmd():
    print({"ok": True})


@fixture_app.command("spending-cmd")
def spending_cmd():
    from core.model_bakeoff import bakeoff

    return bakeoff("hi", ["gpt-4o"], use_mock=True)


@sub_app.command("deep-cmd")
def deep_cmd():
    print("deep")


@fixture_app.command("dupe-cmd")
def dupe_first():
    print("first registration — shadowed by the one below")


@fixture_app.command("dupe-cmd")
def dupe_second():
    print("second registration — this is the one Click keeps")
'''


@pytest.fixture()
def fixture_module(tmp_path: Path):
    """Write the fixture source to disk and build a matching Typer app."""
    path = tmp_path / "fixture_cli.py"
    path.write_text(FIXTURE_SOURCE, encoding="utf-8")

    app = typer.Typer()
    sub = typer.Typer()
    app.add_typer(sub, name="nested")

    @app.command("wrapped-cmd")
    def wrapped_cmd():  # pragma: no cover - never invoked
        pass

    @app.command("unwrapped-cmd")
    def unwrapped_cmd():  # pragma: no cover - never invoked
        pass

    @app.command("spending-cmd")
    def spending_cmd():  # pragma: no cover - never invoked
        pass

    @sub.command("deep-cmd")
    def deep_cmd():  # pragma: no cover - never invoked
        pass

    @app.command("dupe-cmd")
    def dupe_first():  # pragma: no cover - never invoked
        pass

    @app.command("dupe-cmd")
    def dupe_second():  # pragma: no cover - never invoked
        pass

    return app, si.call_map_for_source(path)


# ---------------------------------------------------------------------------
# The detector detects
# ---------------------------------------------------------------------------


def test_unwrapped_command_is_detected(fixture_module):
    """A command that never calls a wrapper must be reported unwrapped."""
    app, call_map = fixture_module
    rows = {r["name"]: r for r in si.enumerate_cli_surfaces(app=app, call_map=call_map)}

    assert rows["wrapped-cmd"]["wrapped"] is True
    assert rows["unwrapped-cmd"]["wrapped"] is False, (
        "the detector failed to notice an unwrapped command — a coverage check "
        "that cannot fail is worse than none"
    )


def test_unwrapped_command_shows_up_as_uncovered(fixture_module):
    app, call_map = fixture_module
    rows = si.enumerate_cli_surfaces(app=app, call_map=call_map)
    uncovered = {r["name"] for r in si.uncovered_surfaces(rows)}

    assert "unwrapped-cmd" in uncovered
    assert "wrapped-cmd" not in uncovered


def test_nested_subapp_commands_are_enumerated(fixture_module):
    """``add_typer`` groups must be walked, not just top-level commands."""
    app, call_map = fixture_module
    names = {r["name"] for r in si.enumerate_cli_surfaces(app=app, call_map=call_map)}
    assert "nested deep-cmd" in names


def test_spend_detected_via_function_local_import(fixture_module):
    """Handlers defer heavy imports into the body; the scan must follow that."""
    app, call_map = fixture_module
    rows = {r["name"]: r for r in si.enumerate_cli_surfaces(app=app, call_map=call_map)}
    assert rows["spending-cmd"]["classification"] == si.CLASS_SPEND
    assert rows["unwrapped-cmd"]["classification"] == si.CLASS_READ_ONLY


def test_missing_source_is_unknown_not_wrapped(fixture_module):
    """No source available must degrade to ``None``, never an optimistic True."""
    app, _ = fixture_module
    rows = si.enumerate_cli_surfaces(app=app, call_map={})
    assert all(r["wrapped"] is None for r in rows)
    # ...and unknown must not count as covered. Shadowed rows are the one
    # exclusion: a dead handler cannot be wrapped, so it is not a gap.
    live = [r for r in rows if not r.get("shadowed")]
    assert len(si.uncovered_surfaces(rows)) == len(live)
    assert len(live) == len(rows) - 1


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def test_classify_precedence():
    assert si.classify({"ModelCaller", "write_text"}) == si.CLASS_SPEND
    assert si.classify({"write_text", "Prompt"}) == si.CLASS_MUTATING
    assert si.classify({"Prompt"}) == si.CLASS_INTERACTIVE
    assert si.classify({"json"}) == si.CLASS_READ_ONLY


def test_classify_via_import_signals():
    assert si.classify({"import:core.council"}) == si.CLASS_SPEND
    assert si.classify({"import:core.chat_session"}) == si.CLASS_INTERACTIVE
    # Selecting or listing a model is not spending on one.
    assert si.classify({"import:core.model_router"}) == si.CLASS_READ_ONLY
    assert si.classify({"import:core.model_catalog_refresh"}) == si.CLASS_READ_ONLY


# ---------------------------------------------------------------------------
# Exemptions
# ---------------------------------------------------------------------------


def test_exemption_requires_a_reason(tmp_path: Path):
    doc = tmp_path / "SURFACE_EXEMPTIONS.md"
    doc.write_text(
        "| Surface | Classification | Reason |\n"
        "|---|---|---|\n"
        "| `cli:good` | read_only | Emits a raw shell script |\n"
        "| `cli:blank` | read_only |  |\n"
        "| `cli:dash` | read_only | - |\n"
        "| `cli:todo` | read_only | TODO |\n",
        encoding="utf-8",
    )
    ex = si.load_exemptions(doc)
    assert set(ex) == {"cli:good"}, "a reason-less row must not grant an exemption"
    assert ex["cli:good"]["reason"] == "Emits a raw shell script"


def test_real_exemption_doc_parses_and_is_not_orphaned():
    """Every row in the shipped doc must name a surface that exists."""
    ex = si.load_exemptions()
    assert ex, "docs/SURFACE_EXEMPTIONS.md should parse to at least one row"
    assert all(v["reason"] for v in ex.values())

    ids = {r["id"] for r in si.enumerate_all_surfaces()}
    orphans = sorted(k for k in ex if k not in ids)
    assert not orphans, f"stale exemption rows naming no live surface: {orphans}"


# ---------------------------------------------------------------------------
# Shadowed commands
# ---------------------------------------------------------------------------


def test_shadowed_command_is_detected(fixture_module):
    """
    Registering two handlers under one name leaves the earlier one unreachable.

    Asserted against the fixture, deliberately **not** against the three live
    occurrences in ``main.py``. Pinning the live names here would mean deleting
    a dead handler turns this test red — a test that punishes fixing the bug it
    found. The live finding belongs in ``surface_report()["shadowed_commands"]``,
    which is a report, not a requirement.
    """
    app, call_map = fixture_module
    rows = si.enumerate_cli_surfaces(app=app, call_map=call_map)
    dupes = [r for r in rows if r["name"] == "dupe-cmd"]

    assert len(dupes) == 2
    shadowed = [r for r in dupes if r.get("shadowed")]
    live = [r for r in dupes if not r.get("shadowed")]
    assert len(shadowed) == 1 and len(live) == 1
    # Click keeps the last registration; the first is the dead one.
    assert shadowed[0]["handler"] == "dupe_first"
    assert live[0]["handler"] == "dupe_second"


def test_shadowing_verdict_matches_click_resolution(fixture_module):
    """The 'last registration wins' assumption must match what Click does."""
    import typer as _typer

    app, call_map = fixture_module
    rows = si.enumerate_cli_surfaces(app=app, call_map=call_map)
    live = next(r for r in rows if r["name"] == "dupe-cmd" and not r.get("shadowed"))

    click_app = _typer.main.get_command(app)
    resolved = click_app.get_command(None, "dupe-cmd")
    assert resolved is not None
    assert resolved.callback.__name__ == live["handler"]


def test_no_shadowed_commands_on_the_real_app():
    """
    Zero command names may be registered twice.

    Three were (``debate``, ``onboard``, ``profile``), and each pair turned out
    to be two *different* features colliding on one name — including the
    host-tools/Postgres setup wizard, which no user could reach. They were
    renamed rather than deleted, so nothing was lost. A new collision means
    someone's feature just became unreachable, silently.
    """
    rows = si.enumerate_cli_surfaces()
    shadowed = sorted(
        (r["id"], r["handler"]) for r in rows if r.get("shadowed")
    )
    assert not shadowed, f"command names registered twice; earlier handler dead: {shadowed}"


def test_renamed_shadowed_features_are_reachable():
    """Both halves of each former collision must be invocable."""
    names = {r["name"] for r in si.enumerate_cli_surfaces()}
    for pair in (
        ("debate", "debate-models"),
        ("onboard", "onboard-wizard"),
        ("profile", "profile-config"),
    ):
        for name in pair:
            assert name in names, f"{name} is not registered"


def test_spend_paths_modules_all_import():
    """
    Every ``SPEND_PATHS`` row must name a real, importable module.

    One row pointed at ``cli.web_app`` for months. The package installs as
    ``scli``, so that row proved nothing about the HTTP spend path it claimed
    to cover — and a registry entry that cannot be resolved is worse than a
    missing one, because it reads as coverage.
    """
    dis = si.disagreements()
    assert dis["spend_paths_unimportable"] == []
    assert dis["spend_paths_freeform_module"] == []


def test_shadowed_commands_are_not_counted_as_uncovered(fixture_module):
    """
    Dead handlers cannot be wrapped and must not inflate the gap count.

    Asserted against the fixture: the real app no longer has any shadowed
    commands (see ``test_no_shadowed_commands_on_the_real_app``), so the
    exclusion logic has to be exercised somewhere that still does. Checked per
    row, not per id — a shadowed row shares its id with the live handler that
    won registration, and that live one may legitimately still be uncovered.
    """
    app, call_map = fixture_module
    rows = si.enumerate_cli_surfaces(app=app, call_map=call_map)
    uncovered = si.uncovered_surfaces(rows)

    assert any(r.get("shadowed") for r in rows), "fixture should contain a shadowed row"
    assert not [r for r in uncovered if r.get("shadowed")]

    # The live handler for a shadowed name is still evaluated normally.
    live = [r for r in rows if r["name"] == "dupe-cmd" and not r.get("shadowed")]
    assert len(live) == 1
    assert live[0]["handler"] == "dupe_second"


# ---------------------------------------------------------------------------
# Live inventory sanity
# ---------------------------------------------------------------------------


def test_real_cli_surfaces_enumerated():
    rows = si.enumerate_cli_surfaces()
    names = {r["name"] for r in rows}
    # Top-level
    for expected in ("status", "doctor", "council", "ask", "bakeoff"):
        assert expected in names
    # Nested one level
    assert "learning promote" in names
    # Nested two levels (``budget`` → ``command``)
    assert any(n.startswith("budget command ") for n in names)
    assert len(rows) > 200


def test_report_shape():
    rep = si.surface_report()
    assert rep["ok"] is True
    assert rep["total"] == sum(rep["by_kind"].values())
    assert rep["total"] == sum(rep["by_classification"].values())
    assert set(rep["by_kind"]) <= {si.KIND_CLI, si.KIND_MCP, si.KIND_HTTP}
    assert set(rep["by_classification"]) <= set(si.CLASSIFICATIONS)
    assert rep["uncovered_count"] == len(rep["uncovered"])
    assert rep["source_available"] is True
    assert "disagreements" in rep


def test_known_spend_commands_are_classified_spend():
    """
    Regression guard for the classifier's blind spot.

    A first cut keyed only on direct call names missed ``ask``, ``council``,
    ``bakeoff``, ``review`` and ``advise`` because each defers its import into
    the function body. Function-local import signals fixed that; this test keeps
    it fixed.
    """
    rows = {r["name"]: r for r in si.enumerate_cli_surfaces()}
    for name in ("ask", "council", "bakeoff", "review", "advise", "agent", "compare"):
        assert rows[name]["classification"] == si.CLASS_SPEND, (
            f"{name} can call a model but is classified "
            f"{rows[name]['classification']}"
        )


def test_mcp_tools_are_all_safety_classified():
    rows = si.enumerate_mcp_surfaces()
    assert rows, "MCP tool registry should not be empty"
    unclassified = [r["id"] for r in rows if not r.get("safety_classified")]
    assert not unclassified, f"MCP tools missing a safety classification: {unclassified}"


def test_http_surfaces_enumerated():
    rows = si.enumerate_http_surfaces()
    if not rows:  # FastAPI not installed in this environment
        pytest.skip("web_app unavailable")
    ids = {r["id"] for r in rows}
    assert "http:POST /api/superai/run" in ids
    run = next(r for r in rows if r["id"] == "http:POST /api/superai/run")
    assert run["classification"] == si.CLASS_SPEND


# ---------------------------------------------------------------------------
# TOP_30 check — the tautology regression
# ---------------------------------------------------------------------------


def test_top30_check_is_not_a_tautology():
    """
    ``verify_top_commands_registered`` could not fail.

    It computed ``missing`` against ``known = top_commands() | TOP_30_COMMANDS |
    names``. Since ``expected`` *is* ``TOP_30_COMMANDS``, no expected name could
    ever be absent from ``known``. Handed an app with none of the TOP_30
    commands, it still returned ok. This asserts it now reports them missing.
    """
    from core.public_surface import TOP_30_COMMANDS, verify_top_commands_registered

    empty_app = typer.Typer()

    @empty_app.command("nothing-useful")
    def _nothing():  # pragma: no cover - never invoked
        pass

    result = verify_top_commands_registered(empty_app)
    assert result["ok"] is False
    assert len(result["missing"]) == len(TOP_30_COMMANDS)


def test_top30_all_registered_on_real_app():
    from core.public_surface import verify_top_commands_registered
    from scli.main import app as cli_app

    result = verify_top_commands_registered(cli_app)
    assert not result["missing"], f"TOP_30 names not registered: {result['missing']}"
    assert result["ok"] is True


def test_registered_command_names_excludes_expected_list_seeding():
    """The name set must come from the app, never from the expected list."""
    from core.public_surface import TOP_30_COMMANDS, registered_command_names

    empty_app = typer.Typer()

    @empty_app.command("only-this")
    def _only():  # pragma: no cover - never invoked
        pass

    names = registered_command_names(empty_app)
    assert names == {"only-this"}
    assert not (set(TOP_30_COMMANDS) & names)
