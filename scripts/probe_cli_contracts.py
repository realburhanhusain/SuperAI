"""
Sweep every invokable CLI surface under ``--json`` and record what came back.

Why a subprocess per command rather than an in-process ``CliRunner`` loop:
some commands hang. ``superai gates`` was found to never return during this
sweep, and an in-process runner has no way to bound that — the whole suite
stops. A subprocess can be killed, the hang recorded as a result, and the sweep
continues. Hangs become data instead of a stalled CI job.

Writes ``docs/PUBLIC_SURFACE_COVERAGE.md`` and prints a summary.

Usage::

    python scripts/probe_cli_contracts.py                # read_only sweep
    python scripts/probe_cli_contracts.py --timeout 20
    python scripts/probe_cli_contracts.py --limit 25     # quick pass
    python scripts/probe_cli_contracts.py --all-classes  # include spend/mutating (writes state!)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.contract_registry import UNINVOKABLE, _first_json_value  # noqa: E402
from core.result_contract import REQUIRED_KEYS  # noqa: E402
from core.surface_inventory import (  # noqa: E402
    CLASS_READ_ONLY,
    KIND_CLI,
    enumerate_cli_surfaces,
)

OUT_DOC = ROOT / "docs" / "PUBLIC_SURFACE_COVERAGE.md"
#: Machine-readable sidecar. ``surface_inventory.disagreements()`` reads this to
#: cross-check its static verdict against what the commands actually printed.
OUT_JSON = ROOT / "docs" / "public_surface_coverage.json"

STATUS_PASS = "pass"
STATUS_NO_JSON = "no-json"
STATUS_ARRAY = "json-array"
STATUS_MISSING = "missing-fields"
STATUS_USAGE = "usage-error"
STATUS_HANG = "hang"
STATUS_CRASH = "crash"
STATUS_FIXTURE_PASS = "pass-with-fixture"
STATUS_FIXTURE_FAIL = "fail-with-fixture"
STATUS_NO_FIXTURE = "no-safe-fixture"


def probe(
    name: str,
    timeout: float,
    *,
    extra_args: Optional[List[str]] = None,
    home: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run one command in a subprocess and classify the outcome.

    ``home`` redirects HOME/USERPROFILE at the OS level, which is what makes a
    fixture run safe: ``Config`` resolves its state directory from
    ``Path.home()``, so a sandboxed home means a command invoked with
    synthesized arguments cannot touch the real ``~/.superai``.
    """
    argv = [sys.executable, "-m", "scli", "--json", *name.split(" "), *(extra_args or [])]
    env = None
    if home:
        env = dict(os.environ)
        env["HOME"] = home
        env["USERPROFILE"] = home
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(ROOT),
            encoding="utf-8",
            errors="replace",
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {"command": name, "status": STATUS_HANG, "detail": f">{timeout}s, killed"}
    except Exception as e:  # pragma: no cover - environment failure
        return {"command": name, "status": STATUS_CRASH, "detail": str(e)[:200]}

    payload = _first_json_value(proc.stdout or "")
    if payload is None:
        # Exit code 2 is Click's usage error — a missing required argument, not
        # a contract failure. Recorded separately so it does not inflate the gap.
        status = STATUS_USAGE if proc.returncode == 2 else STATUS_NO_JSON
        return {
            "command": name,
            "status": status,
            "exit_code": proc.returncode,
            "detail": (proc.stdout or proc.stderr or "")[:140].replace("\n", " "),
        }
    if not isinstance(payload, dict):
        return {
            "command": name,
            "status": STATUS_ARRAY,
            "exit_code": proc.returncode,
            "detail": f"top-level JSON {type(payload).__name__}, not an envelope",
        }

    missing = [k for k in REQUIRED_KEYS if k not in payload]
    if missing:
        return {
            "command": name,
            "status": STATUS_MISSING,
            "exit_code": proc.returncode,
            "missing": missing,
        }
    return {"command": name, "status": STATUS_PASS, "exit_code": proc.returncode}


def probe_with_fixture(name: str, timeout: float) -> Dict[str, Any]:
    """
    Retry a usage-erroring command with arguments derived from its own metadata.

    Runs against a throwaway HOME so a command invoked with synthesized
    arguments cannot write to the real ``~/.superai``. Without that isolation
    this pass would mutate live state 80+ times per sweep — the same mistake
    that had ``backup`` writing a real archive on every run.
    """
    from core.cli_fixtures import synthesize_args

    # ignore_cleanup_errors: on Windows the just-exited CLI subprocess can still
    # hold a handle on its own log file inside the sandbox, and a failed cleanup
    # must not abort the sweep. The leftover directory is in the OS temp tree.
    with tempfile.TemporaryDirectory(
        prefix="superai-probe-", ignore_cleanup_errors=True
    ) as home:
        (Path(home) / ".superai").mkdir(parents=True, exist_ok=True)
        tmp_file = Path(home) / "fixture.txt"
        tmp_file.write_text("probe", encoding="utf-8")

        spec = synthesize_args(name, tmp_path=str(tmp_file))
        if not spec["ok"]:
            return {
                "command": name,
                "status": STATUS_NO_FIXTURE,
                "detail": spec["reason"],
            }

        res = probe(name, timeout, extra_args=spec["args"], home=home)

    res["fixture_args"] = spec["args"]
    res["fixture_how"] = spec.get("how")
    if res["status"] == STATUS_PASS:
        res["status"] = STATUS_FIXTURE_PASS
    elif res["status"] == STATUS_USAGE:
        # Still a usage error with derived args: the derivation produced a
        # syntactically valid but semantically rejected value.
        res["status"] = STATUS_NO_FIXTURE
        res["detail"] = "derived arguments still rejected as invalid usage"
    else:
        res["status"] = STATUS_FIXTURE_FAIL
        res.setdefault("detail", "")
        res["detail"] = f"[{res.get('exit_code')}] {res['detail']}"[:140]
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument(
        "--no-fixtures",
        action="store_true",
        help="Do not retry usage-erroring commands with derived arguments.",
    )
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument(
        "--all-classes",
        action="store_true",
        help="Include spend/mutating/interactive surfaces. These write real state.",
    )
    args = ap.parse_args()

    rows = [
        r
        for r in enumerate_cli_surfaces()
        if r["kind"] == KIND_CLI and not r["exempt"] and not r.get("shadowed")
    ]
    if not args.all_classes:
        rows = [r for r in rows if r["classification"] == CLASS_READ_ONLY]

    names = [r["name"] for r in rows]
    if args.limit:
        names = names[: args.limit]

    results: List[Dict[str, Any]] = []
    skipped: List[Dict[str, str]] = []
    for i, name in enumerate(names, 1):
        reason = UNINVOKABLE.get(name)
        if reason:
            skipped.append({"command": name, "reason": reason})
            print(f"[{i}/{len(names)}] {name}: skip ({reason})", flush=True)
            continue
        res = probe(name, args.timeout)
        # A command that only failed for want of an argument has no contract
        # evidence either way. Retry it with derived arguments in a sandboxed
        # home so the gap resolves to a real verdict instead of "unknown".
        if res["status"] == STATUS_USAGE and not args.no_fixtures:
            res = probe_with_fixture(name, args.timeout)
        results.append(res)
        print(f"[{i}/{len(names)}] {name}: {res['status']}", flush=True)

    write_doc(results, skipped, rows, args)
    tally: Dict[str, int] = {}
    for r in results:
        tally[r["status"]] = tally.get(r["status"], 0) + 1
    OUT_JSON.write_text(
        json.dumps(
            {
                "scope": "all-classes" if args.all_classes else "read_only",
                "timeout": args.timeout,
                "tally": tally,
                "results": results,
                "skipped": skipped,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("\n" + json.dumps(tally, indent=2))
    print(f"skipped (with reason): {len(skipped)}")
    print(f"wrote {OUT_DOC.relative_to(ROOT)} and {OUT_JSON.relative_to(ROOT)}")
    return 0


def write_doc(
    results: List[Dict[str, Any]],
    skipped: List[Dict[str, str]],
    rows: List[Dict[str, Any]],
    args: argparse.Namespace,
) -> None:
    by_status: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r)

    lines: List[str] = []
    lines.append("# Public surface coverage")
    lines.append("")
    lines.append(
        "Generated by `python scripts/probe_cli_contracts.py`. Each command was "
        "run in its own subprocess under `--json` and the emitted envelope "
        "checked against `result_contract.REQUIRED_KEYS`."
    )
    lines.append("")
    lines.append(
        f"Scope: {'all classes' if args.all_classes else '`read_only` surfaces only'}; "
        f"per-command timeout {args.timeout:g}s."
    )
    lines.append("")
    lines.append("| Outcome | Count | Meaning |")
    lines.append("|---|---:|---|")
    meanings = {
        STATUS_PASS: "Emitted a JSON object carrying every required contract field",
        STATUS_MISSING: "Emitted JSON, but the contract envelope is incomplete",
        STATUS_NO_JSON: "Printed no JSON at all despite `--json` — unwrapped",
        STATUS_ARRAY: "Printed a bare JSON array; needs an envelope around it",
        STATUS_USAGE: "Needs a required argument (exit 2); not a contract failure",
        STATUS_FIXTURE_PASS: "Passed once given arguments derived from its own metadata",
        STATUS_FIXTURE_FAIL: "Ran with derived arguments but emitted no valid envelope",
        STATUS_NO_FIXTURE: "No safe argument could be derived; reason recorded",
        STATUS_HANG: "Did not return before the timeout and was killed",
        STATUS_CRASH: "Subprocess could not be run",
    }
    for status, meaning in meanings.items():
        lines.append(f"| `{status}` | {len(by_status.get(status, []))} | {meaning} |")
    lines.append(f"| `skipped` | {len(skipped)} | Listed as uninvokable, with a reason |")
    lines.append("")

    if by_status.get(STATUS_HANG):
        lines.append("## Hangs")
        lines.append("")
        lines.append(
            "These never returned. Relevant beyond contract coverage: a command "
            "that hangs here hangs in CI too."
        )
        lines.append("")
        for r in sorted(by_status[STATUS_HANG], key=lambda x: x["command"]):
            lines.append(f"- `{r['command']}` — {r['detail']}")
        lines.append("")

    for status in (
        STATUS_NO_JSON,
        STATUS_ARRAY,
        STATUS_MISSING,
        STATUS_FIXTURE_FAIL,
        STATUS_NO_FIXTURE,
    ):
        items = by_status.get(status, [])
        if not items:
            continue
        lines.append(f"## {status}")
        lines.append("")
        lines.append("| Command | Exit | Detail |")
        lines.append("|---|---:|---|")
        for r in sorted(items, key=lambda x: x["command"]):
            detail = r.get("detail") or ("missing: " + ", ".join(r.get("missing", [])))
            lines.append(
                f"| `{r['command']}` | {r.get('exit_code', '')} | {str(detail)[:110]} |"
            )
        lines.append("")

    if by_status.get(STATUS_USAGE):
        lines.append("## Needs arguments (not a contract failure)")
        lines.append("")
        lines.append(
            "These exit 2 without a required argument. Proving their contract "
            "needs per-command fixtures, which is follow-up work, not a gap to "
            "silently drop."
        )
        lines.append("")
        for r in sorted(by_status[STATUS_USAGE], key=lambda x: x["command"]):
            lines.append(f"- `{r['command']}`")
        lines.append("")

    if skipped:
        lines.append("## Skipped, with reason")
        lines.append("")
        lines.append("| Command | Reason |")
        lines.append("|---|---|")
        for s in sorted(skipped, key=lambda x: x["command"]):
            lines.append(f"| `{s['command']}` | {s['reason']} |")
        lines.append("")

    if by_status.get(STATUS_PASS):
        lines.append("## Passing")
        lines.append("")
        lines.append(
            ", ".join(f"`{r['command']}`" for r in sorted(by_status[STATUS_PASS], key=lambda x: x["command"]))
        )
        lines.append("")

    OUT_DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
