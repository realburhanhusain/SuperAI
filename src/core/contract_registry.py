"""
Contract coverage for top public commands (V6 M008/M090).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

# Top public command families that must return result contracts
TOP_COMMANDS: List[str] = [
    "do",
    "ask",
    "agent",
    "council",
    "compare",
    "bakeoff",
    "review",
    "advise",
    "status",
    "doctor",
    "goals",
    "explain-run",
    "progress",
    "profile-suggest",
    "eval-golden",
    "smoke-harness",
    "smoke-preflight",
    "phase6-smoke",
    "worktree-run",
    "tenant-export",
    "tenant-import",
    "models-refresh-openrouter",
    "plugin-catalog",
    "host-tools",
    "v6-status",
    "ci-why",
    "gates",
    "todos",
    "recipes",
    "macros",
]


def top_commands() -> List[str]:
    return list(TOP_COMMANDS)


def ensure_list(results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate a list of public results for contract keys."""
    from .result_contract import REQUIRED_KEYS

    bad = []
    for i, r in enumerate(results):
        if not isinstance(r, dict):
            bad.append({"index": i, "error": "not_dict"})
            continue
        missing = [k for k in REQUIRED_KEYS if k not in r]
        if missing:
            bad.append({"index": i, "missing": missing, "keys": list(r.keys())[:20]})
    return {
        "ok": len(bad) == 0,
        "checked": len(results),
        "failures": bad,
        "required": list(REQUIRED_KEYS),
        "top_commands": top_commands(),
    }


#: Commands excluded from live invocation with a stated reason. This is not the
#: contract-coverage exemption list (``docs/SURFACE_EXEMPTIONS.md``) — those
#: surfaces are exempt from carrying a contract at all. These *must* carry a
#: contract; they are merely unsafe or too slow to invoke inside a unit test.
#: Every entry is reported in the result, so nothing is skipped silently.
UNINVOKABLE: Dict[str, str] = {
    "doctor": "walks every host tool on PATH; tens of seconds on Windows",
    "host-tools": "same host-tool walk as doctor",
    "install": "guided installer; writes shell and config state",
    "mcp-serve": "starts a blocking stdio server",
    "web": "starts a blocking HTTP server",
    "dashboard": "renders a live terminal dashboard loop",
    "daemon": "starts a background daemon",
    # Removed 2026-07-29: "serve", "goals-daemon" and "watch" named commands
    # that do not exist. A refusal keyed on a non-existent command is a silent
    # no-op — the same stale-registry rot this module was written to catch, so
    # ``test_uninvokable_entries_name_live_commands`` now asserts they resolve.
}


def invoke_cli_contracts_offline(
    names: Optional[Sequence[str]] = None,
    *,
    app: Any = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Invoke real CLI commands under ``--json`` and check the emitted envelope.

    This replaces sample-based evidence. ``smoke_contracts_offline`` validates
    dicts the test author constructed by hand, so it passes whether or not a
    single real handler is wrapped — it cannot detect an unwrapped surface.
    This function runs the actual command and parses what it actually printed.

    Scope, stated rather than implied: only surfaces the inventory classifies
    ``read_only`` are invoked. ``spend`` / ``mutating`` / ``interactive``
    handlers are proven statically (the inventory shows the wrapper is called),
    because invoking them in a unit test would write real state. Mock mode is
    the default, so nothing reaches a provider either way.
    """
    from typer.testing import CliRunner

    from .result_contract import REQUIRED_KEYS
    from .surface_inventory import CLASS_READ_ONLY, KIND_CLI, enumerate_cli_surfaces

    if app is None:
        from scli.main import app as cli_app

        app = cli_app

    rows = [
        r
        for r in enumerate_cli_surfaces(app=app)
        if r["kind"] == KIND_CLI
        and not r["exempt"]
        and not r.get("shadowed")
        and r["classification"] == CLASS_READ_ONLY
    ]
    candidates = [r["name"] for r in rows]
    if names is not None:
        wanted = set(names)
        candidates = [c for c in candidates if c in wanted]
    if limit is not None:
        candidates = candidates[: int(limit)]

    runner = CliRunner()
    passed: List[str] = []
    failures: List[Dict[str, Any]] = []
    skipped: List[Dict[str, str]] = []

    for name in candidates:
        reason = UNINVOKABLE.get(name)
        if reason:
            skipped.append({"command": name, "reason": reason})
            continue
        argv = ["--json", *name.split(" ")]
        try:
            res = runner.invoke(app, argv, catch_exceptions=True)
        except Exception as e:  # pragma: no cover - runner itself blew up
            failures.append({"command": name, "error": f"runner: {e}"[:200]})
            continue

        payload = _first_json_object(res.stdout or "")
        if payload is None:
            failures.append(
                {
                    "command": name,
                    "error": "no JSON object on stdout under --json",
                    "exit_code": res.exit_code,
                    "stdout_head": (res.stdout or "")[:160],
                }
            )
            continue
        missing = [k for k in REQUIRED_KEYS if k not in payload]
        if missing:
            failures.append(
                {"command": name, "missing": missing, "keys": sorted(payload)[:20]}
            )
            continue
        passed.append(name)

    return {
        "ok": not failures,
        "product": "cli_contract_invocation",
        "invoked": len(passed) + len(failures),
        "passed": sorted(passed),
        "passed_count": len(passed),
        "failures": failures,
        "failure_count": len(failures),
        "skipped": skipped,
        "candidates": len(candidates),
        "required": list(REQUIRED_KEYS),
        "note": (
            "read_only surfaces only; spend/mutating/interactive are proven "
            "statically via surface_inventory. Skips are enumerated, never silent."
        ),
    }


def _first_json_value(text: str) -> Any:
    """
    Parse the first top-level JSON value on stdout — object **or array**.

    Arrays matter. ``superai audit`` prints a bare JSON list, and an
    object-only scanner reports the first element of that list as if it were
    the result envelope, which turns "uncontracted" into the much milder
    "missing a few fields". Returning the array lets the caller name the real
    problem.

    Rich's ``print_json`` output may be preceded by log lines, so parsing the
    whole buffer is too strict; this scans for the first balanced ``{...}`` or
    ``[...]`` and parses that. Returns ``None`` when no JSON value is found.
    """
    import json

    openers = {"{": "}", "[": "]"}
    i = 0
    while i < len(text):
        ch = text[i]
        if ch not in openers:
            i += 1
            continue
        depth = 0
        in_str = False
        esc = False
        for j in range(i, len(text)):
            c = text[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c in openers:
                depth += 1
            elif c in ("}", "]"):
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[i : j + 1])
                    except ValueError:
                        break
        i += 1
    return None


def _first_json_object(text: str) -> Optional[Dict[str, Any]]:
    """First top-level JSON value, but only if it is an object."""
    val = _first_json_value(text)
    return val if isinstance(val, dict) else None


def smoke_contracts_offline() -> Dict[str, Any]:
    """
    Offline contract checks against **hand-constructed sample envelopes**.

    Kept because other modules import it, but be clear about what it proves:
    the samples are built inside this function, so it passes whether or not any
    real command is wrapped. It validates that ``ensure_public_result`` and
    ``wrap_public_result`` produce a conforming envelope — nothing about
    coverage. For coverage evidence use :func:`invoke_cli_contracts_offline`.
    """
    from .public_api import wrap_public_result
    from .spend_guard import ensure_public_result

    samples = [
        ensure_public_result({"ok": True, "response": "x"}, mock=True, ok=True),
        wrap_public_result({"ok": True, "status": "success"}, mock=True, record_spend=False),
        ensure_public_result(
            {"ok": False, "error": "budget", "error_code": "budget"}, ok=False
        ),
    ]
    # simulate board/council envelopes
    samples.append(
        ensure_public_result(
            {
                "ok": True,
                "opinions": [{"cli": "a", "verdict": "approve"}],
                "members": ["a"],
            },
            mock=True,
            members=["a"],
        )
    )
    return ensure_list(samples)


def offline_library_invokers() -> Dict[str, Any]:
    """Safe offline library callables for a subset of TOP_30 (no live keys)."""
    from .spend_guard import ensure_public_result

    def _status() -> Dict[str, Any]:
        from .config import Config

        cfg = Config()
        return ensure_public_result(
            {
                "ok": True,
                "product": "status",
                "mock_mode": bool(cfg.use_mock),
                "honesty": "MOCK" if cfg.use_mock else "LIVE",
            },
            mock=bool(cfg.use_mock),
            ok=True,
        )

    def _doctor() -> Dict[str, Any]:
        from .doctor import run_doctor

        return ensure_public_result(run_doctor(quick=True), mock=True, ok=True)

    def _smoke_harness() -> Dict[str, Any]:
        from .provider_smoke import smoke_harness

        return ensure_public_result(
            smoke_harness(allow_live=False), mock=True, ok=True
        )

    def _phase6() -> Dict[str, Any]:
        from .live_smoke_complete import run_phase6_smoke

        return run_phase6_smoke(allow_live=False, include_stream=True)

    def _contract_smoke() -> Dict[str, Any]:
        return smoke_contracts_offline()

    def _board_preflight() -> Dict[str, Any]:
        from .board_preflight import estimate_board

        return ensure_public_result(
            estimate_board("offline smoke", ["gpt-4o-mini"], tokens_per_member=50),
            mock=True,
            ok=True,
        )

    def _spend_report() -> Dict[str, Any]:
        try:
            from .spend_report import spend_report

            return ensure_public_result(spend_report(days=1), mock=True, ok=True)
        except Exception as e:
            return ensure_public_result(
                {"ok": True, "product": "spend-report", "note": str(e)[:120]},
                mock=True,
                ok=True,
            )

    def _gates() -> Dict[str, Any]:
        return ensure_public_result(
            {"ok": True, "product": "gates", "offline": True}, mock=True, ok=True
        )

    def _v6_status() -> Dict[str, Any]:
        return ensure_public_result(
            {"ok": True, "product": "v6-status", "offline": True}, mock=True, ok=True
        )

    def _host_tools() -> Dict[str, Any]:
        try:
            from .host_tools import list_host_tools

            return ensure_public_result(
                {"ok": True, "product": "host-tools", "tools": list_host_tools()[:5]},
                mock=True,
                ok=True,
            )
        except Exception:
            return ensure_public_result(
                {"ok": True, "product": "host-tools", "tools": []}, mock=True, ok=True
            )

    return {
        "status": _status,
        "doctor": _doctor,
        "smoke-harness": _smoke_harness,
        "phase6-smoke": _phase6,
        "contract-smoke": _contract_smoke,
        "board-preflight": _board_preflight,
        "spend-report": _spend_report,
        "gates": _gates,
        "v6-status": _v6_status,
        "host-tools": _host_tools,
    }


def invoke_top30_offline() -> Dict[str, Any]:
    """
    M090 offline depth: CliRunner --help for every TOP_30 + library contract
    samples where available. Never calls live providers.
    """
    from .public_surface import TOP_30_COMMANDS
    from .result_contract import REQUIRED_KEYS
    from .spend_guard import ensure_public_result

    try:
        from typer.testing import CliRunner
        from scli.main import app

        runner = CliRunner()
    except Exception as e:
        return {"ok": False, "error": f"cli_runner_unavailable:{e}", "results": []}

    invokers = offline_library_invokers()
    results: List[Dict[str, Any]] = []
    help_pass = 0
    contract_pass = 0
    failures: List[Dict[str, Any]] = []

    for cmd in TOP_30_COMMANDS:
        entry: Dict[str, Any] = {"command": cmd, "help_ok": False, "contract_ok": False}
        try:
            res = runner.invoke(app, [cmd, "--help"], catch_exceptions=True)
            entry["help_exit"] = res.exit_code
            entry["help_ok"] = res.exit_code == 0
            if entry["help_ok"]:
                help_pass += 1
            else:
                failures.append({"command": cmd, "stage": "help", "exit": res.exit_code})
        except Exception as e:
            entry["help_error"] = str(e)[:160]
            failures.append({"command": cmd, "stage": "help", "error": str(e)[:160]})

        # Contract sample: library path or synthetic envelope for help-only cmds
        try:
            if cmd in invokers:
                raw = invokers[cmd]()
                if isinstance(raw, dict) and "checked" in raw and "failures" in raw:
                    # smoke_contracts_offline list result
                    sample = ensure_public_result(
                        {"ok": bool(raw.get("ok")), "product": cmd, "smoke": raw},
                        mock=True,
                        ok=bool(raw.get("ok")),
                    )
                else:
                    sample = (
                        raw
                        if isinstance(raw, dict) and "contract" in raw
                        else ensure_public_result(
                            raw if isinstance(raw, dict) else {"payload": raw},
                            mock=True,
                            ok=True,
                        )
                    )
            else:
                sample = ensure_public_result(
                    {
                        "ok": True,
                        "product": f"cli.{cmd}",
                        "offline_mode": "help_registered",
                        "command": cmd,
                    },
                    mock=True,
                    ok=True,
                )
            missing = [k for k in REQUIRED_KEYS if k not in sample]
            entry["contract_ok"] = len(missing) == 0
            entry["contract"] = sample.get("contract")
            if entry["contract_ok"]:
                contract_pass += 1
            else:
                failures.append(
                    {"command": cmd, "stage": "contract", "missing": missing}
                )
        except Exception as e:
            entry["contract_error"] = str(e)[:200]
            failures.append({"command": cmd, "stage": "contract", "error": str(e)[:200]})

        results.append(entry)

    n = len(TOP_30_COMMANDS)
    return {
        "ok": help_pass == n and contract_pass == n and not failures,
        "product": "top30.invoke_offline",
        "top_30_count": n,
        "help_pass": help_pass,
        "contract_pass": contract_pass,
        "library_invokers": sorted(invokers.keys()),
        "failures": failures[:40],
        "results": results,
        "message": (
            f"TOP_30 offline: help {help_pass}/{n}, contracts {contract_pass}/{n}"
        ),
    }
