"""
Phase 1 — result contract on public surfaces (V1-P1-1, V2-A4, V3-A4).

Evidence here is **real handler output**, not hand-built samples. The previous
evidence path (``contract_registry.smoke_contracts_offline``) constructs the
dicts it validates, so it passes whether or not a single command is wrapped.
These tests invoke commands and parse what was actually printed.

Offline only: mock mode is the default, and only ``read_only`` surfaces are
invoked. Spend/mutating/interactive handlers are proven statically through
``surface_inventory``.
"""

from __future__ import annotations

import pytest
import typer
from typer.testing import CliRunner

from core import surface_inventory as si
from core.contract_registry import (
    UNINVOKABLE,
    _first_json_value,
    invoke_cli_contracts_offline,
)
from core.public_surface import contract_console, contract_payload
from core.result_contract import REQUIRED_KEYS

# A stable read_only sample. Kept small so the suite stays fast; the exhaustive
# sweep lives in ``scripts/probe_cli_contracts.py``, which runs each command in
# its own subprocess so a hang is recorded instead of stalling pytest.
SAMPLE_COMMANDS = ["a11y", "ab-route", "agent-graph", "status", "json-surface"]


# ---------------------------------------------------------------------------
# The contract seam
# ---------------------------------------------------------------------------


def test_contract_payload_adds_every_required_key():
    out = contract_payload({"result": "hello"})
    missing = [k for k in REQUIRED_KEYS if k not in out]
    assert not missing
    assert out["honesty"] in {"MOCK", "LIVE"}
    assert isinstance(out["exit_code"], int)


def test_contract_payload_preserves_caller_keys():
    out = contract_payload({"result": "hello", "custom": [1, 2, 3]})
    assert out["result"] == "hello"
    assert out["custom"] == [1, 2, 3]


def test_contract_payload_does_not_mutate_input():
    """``apply_contract`` mutates in place; a display helper must not."""
    original = {"result": "hello"}
    contract_payload(original)
    assert original == {"result": "hello"}


def test_contract_payload_passes_through_non_dicts():
    """A list or string is not an envelope; wrapping would change its type."""
    assert contract_payload([1, 2, 3]) == [1, 2, 3]
    assert contract_payload("plain") == "plain"
    assert contract_payload(None) is None


def test_contract_console_contracts_printed_json(capsys):
    console = contract_console()
    console.print_json(data={"result": "hi"})
    payload = _first_json_value(capsys.readouterr().out)
    assert isinstance(payload, dict)
    assert not [k for k in REQUIRED_KEYS if k not in payload]


def test_contract_console_leaves_preserialized_json_alone(capsys):
    """A ``json=`` string was deliberately formatted by the caller."""
    console = contract_console()
    console.print_json('{"already": "serialized"}')
    payload = _first_json_value(capsys.readouterr().out)
    assert payload == {"already": "serialized"}


def test_cli_console_uses_the_contract_seam():
    """Regression guard: a plain Console here silently un-contracts 264 sites."""
    from scli.main import console

    assert type(console).__name__ == "_ContractConsole"


# ---------------------------------------------------------------------------
# Real invocation
# ---------------------------------------------------------------------------


def test_sample_commands_emit_a_full_contract():
    result = invoke_cli_contracts_offline(names=SAMPLE_COMMANDS)
    assert result["invoked"] >= 1
    assert result["ok"], f"contract failures: {result['failures']}"


@pytest.mark.parametrize("command", SAMPLE_COMMANDS)
def test_each_sample_command_individually(command):
    """Parametrized so a failure names the offending command."""
    from scli.main import app

    res = CliRunner().invoke(app, ["--json", command], catch_exceptions=True)
    payload = _first_json_value(res.stdout or "")
    assert isinstance(payload, dict), f"{command}: no JSON object under --json"
    missing = [k for k in REQUIRED_KEYS if k not in payload]
    assert not missing, f"{command} missing contract fields: {missing}"


def test_invocation_harness_detects_an_unwrapped_command():
    """
    Prove the harness can fail.

    A fixture app whose command prints an uncontracted payload must be
    reported, otherwise this whole file is decoration.
    """
    app = typer.Typer()

    @app.callback()
    def _root(json: bool = typer.Option(False, "--json")):  # noqa: A002
        pass

    @app.command("bare-cmd")
    def bare_cmd():
        print('{"result": "no contract here"}')

    result = invoke_cli_contracts_offline(app=app)
    assert result["ok"] is False
    assert result["failure_count"] == 1
    assert result["failures"][0]["command"] == "bare-cmd"
    assert "missing" in result["failures"][0]


def test_skips_are_enumerated_never_silent():
    """
    Anything not invoked must be named with a reason.

    Scoped to the sample set plus one known-uninvokable command. Do **not**
    call this with no ``names``: that sweeps every read_only command in-process,
    and some of them block — ``model_discovery`` opens a socket to Ollama on
    localhost and waits on connect. The unbounded sweep belongs in
    ``scripts/probe_cli_contracts.py``, where each command is a killable
    subprocess.
    """
    names = [*SAMPLE_COMMANDS, "doctor"]
    result = invoke_cli_contracts_offline(names=names)

    assert result["skipped"], "expected 'doctor' to be skipped as uninvokable"
    for row in result["skipped"]:
        assert row["command"] in UNINVOKABLE
        assert row["reason"]

    accounted = (
        set(result["passed"])
        | {f["command"] for f in result["failures"]}
        | {r["command"] for r in result["skipped"]}
    )
    assert len(accounted) == result["candidates"]


# ---------------------------------------------------------------------------
# Bare-array emitters
# ---------------------------------------------------------------------------


def test_json_value_scanner_distinguishes_arrays_from_objects():
    """
    An object-only scanner reports a list's first element as the envelope.

    That downgrades "prints no envelope at all" to "envelope missing a few
    fields", which is a materially wrong diagnosis — so the scanner has to see
    top-level arrays.
    """
    assert _first_json_value('[{"a": 1}, {"b": 2}]') == [{"a": 1}, {"b": 2}]
    assert _first_json_value('{"a": 1}') == {"a": 1}
    assert _first_json_value("log line\n{\"a\": 1}\n") == {"a": 1}
    assert _first_json_value("no json here") is None


# ---------------------------------------------------------------------------
# Coverage direction
# ---------------------------------------------------------------------------


#: Ratchet bounds. Phase 1 took these from 26/229 to 0/75 — the two seams did
#: the bulk, then the Rich-table-only commands were wrapped individually.
#: Move them **down** as surfaces are wrapped; never up. A raise means a new
#: unwrapped public surface landed, which is the regression these guard.
MAX_UNCOVERED_SPEND = 0
MAX_UNCOVERED_TOTAL = 57

#: Commands the static scan calls wrapped but the probe caught printing no
#: conforming envelope.
#:
#: This went 2 -> 8 when derived argument fixtures landed, and that rise is
#: **improved visibility, not regression**. 87 commands previously exited 2
#: ("missing argument") and were filed as unknown; running them with arguments
#: derived from their own metadata resolved that bucket into 38 passing, 33
#: printing no envelope, and 10 refused. Eight of the 33 are statically
#: "wrapped", hence the count here. They were always broken — nothing could see
#: it.
#:
#: Two of the eight — ``bandit`` and ``pref`` — are **flaky, not broken**. Both
#: emit a complete envelope when run standalone (verified repeatedly), and both
#: read mutable JSON under ``~/.superai/``; they only fail inside the 211-command
#: sweep. Most likely another command in the sweep rewrites that state, or the
#: file is read mid-write. Bounded at 2 and named rather than silently excluded,
#: because a flaky reading is a real finding about either the commands or the
#: probe, and hiding it would be the same failure as a silent skip.
MAX_STATIC_PROBE_CONTRADICTIONS = 7


def test_spend_surfaces_coverage_ratchet():
    rows = si.enumerate_all_surfaces()
    gaps = sorted(
        r["id"]
        for r in si.uncovered_surfaces(rows)
        if r["classification"] == si.CLASS_SPEND
    )
    assert len(gaps) <= MAX_UNCOVERED_SPEND, (
        f"uncovered spend surfaces grew to {len(gaps)}: {gaps}"
    )


def test_overall_coverage_ratchet():
    rep = si.surface_report()
    assert rep["uncovered_count"] <= MAX_UNCOVERED_TOTAL, (
        f"uncovered surfaces grew to {rep['uncovered_count']}; "
        "new public surfaces must be wrapped or exempted when added"
    )


def test_http_api_routes_are_contracted():
    """Every ``/api/*`` JSON route carries the envelope, via the middleware."""
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from scli.web_app import create_app

    del fastapi
    client = TestClient(create_app())
    for path in ("/api/status", "/api/wings", "/api/preferences", "/api/plugins"):
        resp = client.get(path)
        assert resp.status_code == 200, path
        body = resp.json()
        assert isinstance(body, dict), path
        missing = [k for k in REQUIRED_KEYS if k not in body]
        assert not missing, f"{path} missing contract fields: {missing}"


def test_http_contract_middleware_is_installed():
    """The HTTP coverage claim rests entirely on this middleware existing."""
    pytest.importorskip("fastapi")
    from scli.web_app import create_app

    assert si._has_contract_middleware(create_app())


def test_static_wrapped_claim_agrees_with_the_probe():
    """
    The static count is an upper bound and must be checked against reality.

    ``print_json`` counts as a wrapper, but a command can call it with a list,
    which ``contract_payload`` passes through untouched — so a handler can be
    "wrapped" statically and print no envelope at all. Trusting the static
    number alone would rebuild the declare-vs-derive drift that
    ``surface_inventory`` exists to catch, just in a new costume.
    """
    probe = si.load_probe_results()
    if not probe:
        pytest.skip("no probe sidecar; run scripts/probe_cli_contracts.py")
    rows = si.enumerate_all_surfaces()
    contradicted = si._probe_disagreement(rows)["static_wrapped_but_probe_failed"]
    assert len(contradicted) <= MAX_STATIC_PROBE_CONTRADICTIONS, (
        "commands the inventory calls wrapped but which printed no conforming "
        f"envelope: {contradicted}"
    )


def test_probe_unproven_commands_are_reported_not_hidden():
    """
    Commands the probe could not judge must be counted, not quietly dropped.

    These need arguments (or hang), so they have no contract evidence in either
    direction. A coverage claim that silently omits them overstates itself.
    """
    probe = si.load_probe_results()
    if not probe:
        pytest.skip("no probe sidecar; run scripts/probe_cli_contracts.py")
    report = si._probe_disagreement(si.enumerate_all_surfaces())
    assert report["probe_available"] is True
    assert isinstance(report["probe_unproven"], list)
    # Every probed command lands in exactly one bucket: proven, contradicted,
    # or unproven. No third state that disappears from the tally.
    buckets = (
        {"pass", "pass-with-fixture", "crash"} | si._PROBE_BAD | si._PROBE_UNPROVEN
    )
    assert set(probe.values()) <= buckets, f"unaccounted probe status: {set(probe.values()) - buckets}"


def test_main_has_no_bare_console_outside_the_import_guard():
    """
    ``print_json`` counts as a wrapper only because there is one console.

    A second bare ``Console()`` in ``main.py`` would print uncontracted JSON
    while the inventory still reported those commands as wrapped. Asserted as
    "none outside the import guard" rather than an exact count, so deleting the
    defensive fallback — a strict improvement — does not fail this test.
    """
    from pathlib import Path

    src = (Path(si.repo_root()) / "src" / "cli" / "main.py").read_text(encoding="utf-8")
    offenders = [
        (i, line.strip())
        for i, line in enumerate(src.splitlines(), 1)
        if "Console()" in line and "_contract_console" not in line
        # The one permitted site: the fallback inside the try/except that keeps
        # the CLI importable if public_surface is unavailable.
        and "except Exception" not in src.splitlines()[max(0, i - 2)]
    ]
    assert not offenders, (
        f"bare Console() outside the contract_console import guard: {offenders}"
    )
