"""
Public surface inventory (Phase 0 of the contract/spend residual plan).

Every completeness check in this repo has historically been a *hand-maintained
list* (``foundation_safety.SPEND_PATHS``, ``public_surface.TOP_30_COMMANDS``,
``public_surface.JSON_CAPABLE_COMMANDS``) or a set of synthetic sample dicts
(``contract_registry.smoke_contracts_offline``). Lists declare intent; they
cannot detect the surface somebody added last week. That drift is the root
cause behind V1-P1-1 / V1-P1-3 / V1-P1-4 / V2-A4 / V3-A4 all sitting at 85%
through several "done" waves.

This module derives the surface set instead of declaring it:

- **CLI** — recursive walk of the live Typer app (root + every ``add_typer``
  group, including nested ones).
- **MCP** — the registered tool list, reusing ``mcp_safety.safety_matrix()``.
- **HTTP** — the FastAPI route table from ``cli.web_app.create_app()``.

Wrapper detection is done by parsing ``src/cli/main.py`` with :mod:`ast`, not
with :func:`inspect.getsource`. Runtime source introspection breaks under
wheel/bytecode installs — that is the M001 audit fragility this plan replaces,
so it is not reintroduced here. When the source file is genuinely unavailable
(installed wheel, no ``src/``), detection degrades to ``None`` ("unknown")
rather than silently reporting "wrapped".

Nothing in this module enforces coverage. It reports. The zero-tolerance
assertions land in Phase 1 (``tests/test_surface_contract_coverage.py``).
"""

from __future__ import annotations

import ast
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

KIND_CLI = "cli"
KIND_MCP = "mcp"
KIND_HTTP = "http"

CLASS_SPEND = "spend"
CLASS_MUTATING = "mutating"
CLASS_INTERACTIVE = "interactive"
CLASS_READ_ONLY = "read_only"

CLASSIFICATIONS = (CLASS_SPEND, CLASS_MUTATING, CLASS_INTERACTIVE, CLASS_READ_ONLY)

#: A public result is "wrapped" when the handler routes through one of these.
#:
#: ``print_json`` counts because ``src/cli/main.py`` binds its module-level
#: ``console`` to ``public_surface.contract_console()``, which contracts every
#: ``data=`` payload it prints. That holds only while ``main.py`` has exactly
#: one Console — ``test_cli_console_uses_the_contract_seam`` and
#: ``test_main_has_a_single_console`` guard both halves of that assumption.
WRAPPER_CALLS: Set[str] = {
    "emit_public",
    "render_public",
    "ensure_public_result",
    "wrap_public_result",
    "apply_contract",
    "print_json",
}

#: Calling any of these means the handler can cause model/provider spend.
SPEND_MARKERS: Set[str] = {
    "ModelCaller",
    "AgentRuntime",
    "call_model",
    "call_stream",
    "call_stream_complete",
    "run_council",
    "run_board",
    "multi_cli_advisory",
    "run_bakeoff",
    "model_bakeoff",
    "compare_models",
    "SuperAIOrchestrator",
    "orchestrate",
    "run_phase6_smoke",
    "live_smoke",
}

#: Importing any of these (usually function-locally) means the handler can spend.
#: Modules that only *select* a model (``model_router``, ``load_balancer``) or
#: fetch a public catalogue (``model_catalog_refresh``) are deliberately absent —
#: routing and listing are not spend.
SPEND_MODULES: Set[str] = {
    "core.model_caller",
    "core.council",
    "core.model_bakeoff",
    "core.model_compare",
    "core.orchestrator",
    "core.multi_cli_advisory",
    "core.ask_session",
    "core.agentic",
    "core.superai_agent.runtime",
    "core.superai_agent.agents",
    "core.superai_agent.tui",
    "core.live_smoke_complete",
    "core.provider_smoke",
    "core.smoke_preflight",
    "core.eval_golden",
    "core.memory_eval",
    "core.pr_review",
    "core.task_planner",
    "core.nl_preview",
    "core.worktree_subagent",
    # External vendor CLIs bill against the user's own vendor account.
    "core.external_cli",
    "core.cli_pool",
}

#: Calling any of these means the handler writes disk/git/memory state.
MUTATING_MARKERS: Set[str] = {
    "write_text",
    "write_bytes",
    "mkdir",
    "unlink",
    "rmtree",
    "store_memory",
    "write_back",
    "learn_from_step",
    "apply_change_set",
    "apply_patch",
    "commit",
    "atomic_write_json",
    # Found the hard way: `backup` classified read_only, so the contract sweep
    # invoked it 211 times over and created a real encrypted archive each run.
    "create_backup",
    "restore_backup",
    "restore_from_cloud",
    "apply_retention",
    "sync_to_cloud",
}

#: Calling any of these means the handler blocks on a human at a terminal.
INTERACTIVE_MARKERS: Set[str] = {
    "Prompt",
    "Confirm",
    "input",
    "run_tui",
    "AgentTUI",
    "split_pane_tui",
    "tui_mux",
    "live_input",
}

#: Importing any of these means the handler owns a terminal session. These
#: commands cannot emit a single JSON envelope and are the legitimate
#: human-only exceptions — but they must still be listed in the exemption doc.
INTERACTIVE_MODULES: Set[str] = {
    "core.chat_session",
    "core.memory_chat",
    "core.onboarding",
    "core.onboarding_quest",
    "core.install_wizard",
    "core.tui_live_session",
    "core.tui_mouse",
    "core.tui_raw_input",
    "core.approval_tui",
    "core.superai_agent.tui",
}

_EXEMPTION_DOC = "docs/SURFACE_EXEMPTIONS.md"

#: A clean dotted module path, e.g. ``core.model_caller``.
_DOTTED_PATH = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")

# ``| id | classification | reason |`` rows in the exemption doc.
_EXEMPT_ROW = re.compile(
    r"^\|\s*`(?P<id>[^`]+)`\s*\|\s*(?P<classification>[a-z_]+)\s*\|\s*(?P<reason>[^|]+?)\s*\|\s*$"
)


# ---------------------------------------------------------------------------
# Repo location
# ---------------------------------------------------------------------------


def repo_root() -> Path:
    """Best-effort repo root (``src/core/surface_inventory.py`` → three up)."""
    return Path(__file__).resolve().parents[2]


def _cli_source_path() -> Optional[Path]:
    p = repo_root() / "src" / "cli" / "main.py"
    return p if p.is_file() else None


# ---------------------------------------------------------------------------
# AST call-graph over the CLI module
# ---------------------------------------------------------------------------


def _signals(node: ast.AST) -> Set[str]:
    """
    Every signal under ``node``: callee names plus function-local imports.

    Local imports matter more than call names in this codebase. Handlers
    consistently defer their heavy imports into the function body
    (``def bakeoff_cmd(...): from core.model_bakeoff import bakeoff``), so the
    imported *module path* identifies what a command really touches even when
    the call is made through a rebound local name. Import signals are recorded
    as ``import:<module>`` so they cannot collide with a callee name.
    """
    out: Set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            fn = sub.func
            if isinstance(fn, ast.Name):
                out.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                out.add(fn.attr)
                # Also record the receiver so ``ModelCaller().call()`` is seen.
                base = fn.value
                if isinstance(base, ast.Name):
                    out.add(base.id)
                elif isinstance(base, ast.Call) and isinstance(base.func, ast.Name):
                    out.add(base.func.id)
        elif isinstance(sub, ast.ImportFrom):
            if sub.module:
                out.add(f"import:{sub.module}")
            for alias in sub.names:
                out.add(alias.asname or alias.name)
        elif isinstance(sub, ast.Import):
            for alias in sub.names:
                out.add(f"import:{alias.name}")
                out.add((alias.asname or alias.name).split(".")[0])
    return out


@lru_cache(maxsize=4)
def _function_calls(source_path: str) -> Dict[str, frozenset]:
    """
    Map ``function name`` → callee names in its body.

    Nested definitions merge into the enclosing function on purpose: a command
    that delegates to a local closure still counts as wrapped when the closure
    wraps. Same-named functions merge rather than overwrite.
    """
    try:
        tree = ast.parse(Path(source_path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return {}
    acc: Dict[str, Set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            acc.setdefault(node.name, set()).update(_signals(node))
    return {k: frozenset(v) for k, v in acc.items()}


#: How many local helper hops to follow when deciding "is this wrapped".
_HELPER_DEPTH = 3


def resolve_local_helpers(
    call_map: Dict[str, frozenset], depth: int = _HELPER_DEPTH
) -> Dict[str, frozenset]:
    """
    Fold each function's locally-defined callees into its own signal set.

    Without this the scan reports false negatives wherever a module shares a
    rendering helper. ``kg status`` calls ``_print_kg``, which calls
    ``emit_public`` — the command is genuinely wrapped, but a one-level scan
    sees only ``_print_kg`` and reports it uncovered. That mislabelled 48
    commands across the ``kg``, ``capture``, ``dataset`` and ``learning``
    families, every one of which the dynamic probe proved was fine.

    Bounded at ``depth`` hops and iterated to a fixed point, so recursion
    between helpers terminates rather than spinning.
    """
    resolved = {k: set(v) for k, v in call_map.items()}
    for _ in range(depth):
        changed = False
        for name, signals in resolved.items():
            # Only follow names defined in this module — an arbitrary callee
            # is not evidence of anything.
            for callee in list(signals & resolved.keys()):
                if callee == name:
                    continue
                new = resolved[callee] - signals
                if new:
                    signals |= new
                    changed = True
        if not changed:
            break
    return {k: frozenset(v) for k, v in resolved.items()}


def _cli_call_map() -> Dict[str, frozenset]:
    path = _cli_source_path()
    if path is None:
        return {}
    return resolve_local_helpers(_function_calls(str(path)))


def call_map_for_source(path: Path) -> Dict[str, frozenset]:
    """Public wrapper around the AST scan, for fixture modules in tests."""
    return _function_calls(str(path))


# ---------------------------------------------------------------------------
# Exemptions
# ---------------------------------------------------------------------------


def load_exemptions(path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """
    Parse ``docs/SURFACE_EXEMPTIONS.md``.

    A surface may only be skipped by contract-coverage checks if it appears
    here **with a reason**. Silent skips are the failure mode this file exists
    to prevent, so a row with an empty reason is ignored (i.e. not exempt).
    """
    doc = path or (repo_root() / _EXEMPTION_DOC)
    out: Dict[str, Dict[str, str]] = {}
    try:
        text = doc.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        m = _EXEMPT_ROW.match(line.strip())
        if not m:
            continue
        reason = m.group("reason").strip()
        if not reason or reason in {"-", "—", "TODO"}:
            continue  # no reason given → not a valid exemption
        out[m.group("id")] = {
            "classification": m.group("classification").strip(),
            "reason": reason,
        }
    return out


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify(calls: Iterable[str]) -> str:
    """
    Classify a handler from its signals. Precedence: spend > mutating > interactive.

    Known limitation, stated rather than hidden: this reads one module's AST and
    does not resolve calls transitively across modules. A handler that spends
    only via a helper in a third module, importing neither a spend module nor a
    spend name directly, is classified ``read_only``. Treat the counts as a
    lower bound on spend surfaces, and see ``disagreements()`` for the
    cross-check against the hand-maintained registries.
    """
    names = set(calls)
    if names & SPEND_MARKERS:
        return CLASS_SPEND
    if any(n.startswith("import:") and n[7:] in SPEND_MODULES for n in names):
        return CLASS_SPEND
    if names & MUTATING_MARKERS:
        return CLASS_MUTATING
    if names & INTERACTIVE_MARKERS:
        return CLASS_INTERACTIVE
    if any(n.startswith("import:") and n[7:] in INTERACTIVE_MODULES for n in names):
        return CLASS_INTERACTIVE
    return CLASS_READ_ONLY


def _surface(
    *,
    kind: str,
    surface_id: str,
    name: str,
    handler: str,
    classification: str,
    wrapped: Optional[bool],
    exemptions: Dict[str, Dict[str, str]],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ex = exemptions.get(surface_id)
    row: Dict[str, Any] = {
        "kind": kind,
        "id": surface_id,
        "name": name,
        "handler": handler,
        "classification": classification,
        "wrapped": wrapped,
        "exempt": bool(ex),
        "exempt_reason": ex["reason"] if ex else None,
    }
    if extra:
        row.update(extra)
    return row


# ---------------------------------------------------------------------------
# CLI surfaces
# ---------------------------------------------------------------------------


def _typer_command_name(cmd: Any) -> str:
    from typer.main import get_command_name

    if getattr(cmd, "name", None):
        return str(cmd.name)
    cb = getattr(cmd, "callback", None)
    if cb is not None and getattr(cb, "__name__", None):
        return get_command_name(cb.__name__)
    return "<unnamed>"


def _walk_typer(app: Any, prefix: Tuple[str, ...] = ()) -> List[Tuple[Tuple[str, ...], Any]]:
    """Depth-first walk yielding ``(path_parts, command)`` for nested Typer apps."""
    found: List[Tuple[Tuple[str, ...], Any]] = []
    for cmd in getattr(app, "registered_commands", []) or []:
        found.append((prefix + (_typer_command_name(cmd),), cmd))
    for group in getattr(app, "registered_groups", []) or []:
        sub = getattr(group, "typer_instance", None)
        if sub is None:
            continue
        gname = getattr(group, "name", None) or getattr(
            getattr(sub, "info", None), "name", None
        )
        found.extend(_walk_typer(sub, prefix + (str(gname or "<group>"),)))
    return found


def enumerate_cli_surfaces(
    app: Any = None,
    *,
    call_map: Optional[Dict[str, frozenset]] = None,
) -> List[Dict[str, Any]]:
    """
    Every registered CLI command, including nested sub-app commands.

    ``call_map`` overrides the AST scan of ``src/cli/main.py``. Tests use it to
    point the enumerator at a fixture module, which is how the detector proves
    it can actually detect an unwrapped surface.
    """
    if app is None:
        from scli.main import app as cli_app

        app = cli_app
    if call_map is None:
        call_map = _cli_call_map()
    exemptions = load_exemptions()
    rows: List[Dict[str, Any]] = []
    for parts, cmd in _walk_typer(app):
        cb = getattr(cmd, "callback", None)
        handler = getattr(cb, "__name__", "") if cb is not None else ""
        calls = call_map.get(handler, frozenset())
        # No source available → unknown, never an optimistic True.
        wrapped: Optional[bool] = None if not call_map else bool(calls & WRAPPER_CALLS)
        rows.append(
            _surface(
                kind=KIND_CLI,
                surface_id="cli:" + " ".join(parts),
                name=" ".join(parts),
                handler=handler,
                classification=classify(calls),
                wrapped=wrapped,
                exemptions=exemptions,
                extra={"hidden": bool(getattr(cmd, "hidden", False)), "shadowed": False},
            )
        )
    _mark_shadowed(rows)
    rows.sort(key=lambda r: r["id"])
    return rows


def _mark_shadowed(rows: List[Dict[str, Any]]) -> None:
    """
    Flag commands registered more than once under the same name.

    Click keeps the **last** registration for a given name, so every earlier
    handler is unreachable dead code. Registration order is decoration order,
    so all but the final occurrence are shadowed. Mutates ``rows`` in place;
    call before sorting, while list order still reflects registration order.
    """
    seen: Dict[str, int] = {}
    for i, row in enumerate(rows):
        seen[row["id"]] = i  # last index wins
    for i, row in enumerate(rows):
        if seen.get(row["id"]) != i:
            row["shadowed"] = True


# ---------------------------------------------------------------------------
# MCP surfaces
# ---------------------------------------------------------------------------


def enumerate_mcp_surfaces() -> List[Dict[str, Any]]:
    """Registered MCP tools, classified from the existing mcp_safety matrix."""
    exemptions = load_exemptions()
    rows: List[Dict[str, Any]] = []
    try:
        from .mcp_safety import (
            CLI_PARITY,
            FREE_TOOLS,
            MUTATING_TOOLS,
            SPEND_TOOLS,
            list_registered_mcp_tools,
        )

        registered = list(list_registered_mcp_tools())
    except Exception:
        return rows
    for tool in sorted(registered):
        if tool in SPEND_TOOLS:
            cls = CLASS_SPEND
        elif tool in MUTATING_TOOLS:
            cls = CLASS_MUTATING
        else:
            cls = CLASS_READ_ONLY
        # ``wrapped=True`` here is audited, not assumed. Dispatch audit on
        # 2026-07-28: ``_call_tool_impl`` has exactly one caller in the tree
        # (``mcp_server.py:629``), and that call sits inside the closure
        # ``call_tool`` hands to ``wrap_mcp_tool`` (``mcp_server.py:636``). The
        # HTTP bridge reaches it the same way — ``web_app.mcp_http`` →
        # ``mcp_server.handle_request`` → ``call_tool`` (``mcp_server.py:584``).
        # No path reaches a raw tool handler. Re-run ``rg "_call_tool_impl"``
        # before trusting this if dispatch is refactored.
        classified = tool in SPEND_TOOLS or tool in MUTATING_TOOLS or tool in FREE_TOOLS
        rows.append(
            _surface(
                kind=KIND_MCP,
                surface_id=f"mcp:{tool}",
                name=tool,
                handler=tool,
                classification=cls,
                wrapped=True,
                exemptions=exemptions,
                extra={
                    "safety_classified": bool(classified),
                    "cli_parity": CLI_PARITY.get(tool),
                },
            )
        )
    return rows


# ---------------------------------------------------------------------------
# HTTP surfaces
# ---------------------------------------------------------------------------

_HTTP_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

#: Name of the response middleware that contracts ``/api/*`` JSON bodies.
CONTRACT_MIDDLEWARE = "contract_middleware"


def _has_contract_middleware(app: Any) -> bool:
    """True when the contract response middleware is installed on ``app``."""
    for mw in getattr(app, "user_middleware", []) or []:
        dispatch = (getattr(mw, "kwargs", {}) or {}).get("dispatch")
        if dispatch is None:
            args = getattr(mw, "args", None) or ()
            dispatch = args[0] if args else None
        if getattr(dispatch, "__name__", "") == CONTRACT_MIDDLEWARE:
            return True
    return False


def enumerate_http_surfaces() -> List[Dict[str, Any]]:
    """FastAPI routes from ``cli.web_app.create_app()`` (empty if unavailable)."""
    exemptions = load_exemptions()
    rows: List[Dict[str, Any]] = []
    create_app = None
    # The package is installed as ``scli`` (``src/cli`` → ``scli``); some older
    # call sites still say ``cli.web_app``, which is not importable.
    for mod in ("scli.web_app", "cli.web_app"):
        try:
            create_app = __import__(mod, fromlist=["create_app"]).create_app
            break
        except Exception:
            continue
    if create_app is None:
        return rows
    try:
        app = create_app()
        routes = list(getattr(app, "routes", []) or [])
    except Exception:
        return rows

    src_calls: Dict[str, frozenset] = {}
    web_src = repo_root() / "src" / "cli" / "web_app.py"
    if web_src.is_file():
        src_calls = _function_calls(str(web_src))

    has_contract_mw = _has_contract_middleware(app)

    for route in routes:
        path = getattr(route, "path", None)
        endpoint = getattr(route, "endpoint", None)
        if not path or endpoint is None:
            continue
        methods = sorted(getattr(route, "methods", None) or [])
        methods = [m for m in methods if m not in {"HEAD", "OPTIONS"}]
        if not methods:
            continue
        handler = getattr(endpoint, "__name__", "")
        calls = src_calls.get(handler, frozenset())
        cls = classify(calls)
        if cls == CLASS_READ_ONLY and set(methods) & _HTTP_MUTATING_METHODS:
            cls = CLASS_MUTATING
        method = "|".join(methods)

        wrapped: Optional[bool] = None if not src_calls else bool(calls & WRAPPER_CALLS)
        wrapped_by = "handler" if wrapped else None
        # ``/api/*`` JSON responses are contracted by the response middleware,
        # so the handler itself need not call a wrapper. Only counted when the
        # middleware is actually installed on this app — remove it and these
        # go straight back to uncovered.
        if not wrapped and has_contract_mw and str(path).startswith("/api/"):
            wrapped = True
            wrapped_by = "contract_middleware"

        rows.append(
            _surface(
                kind=KIND_HTTP,
                surface_id=f"http:{method} {path}",
                name=f"{method} {path}",
                handler=handler,
                classification=cls,
                wrapped=wrapped,
                exemptions=exemptions,
                extra={"methods": methods, "path": path, "wrapped_by": wrapped_by},
            )
        )
    rows.sort(key=lambda r: r["id"])
    return rows


# ---------------------------------------------------------------------------
# Aggregate report
# ---------------------------------------------------------------------------


def enumerate_all_surfaces(app: Any = None) -> List[Dict[str, Any]]:
    return (
        enumerate_cli_surfaces(app=app)
        + enumerate_mcp_surfaces()
        + enumerate_http_surfaces()
    )


def uncovered_surfaces(surfaces: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Surfaces that are neither wrapped nor exempt-with-a-reason.

    ``wrapped is None`` (source unavailable) is **not** treated as covered.
    """
    rows = enumerate_all_surfaces() if surfaces is None else surfaces
    return [
        r
        for r in rows
        if not r["exempt"] and not r.get("shadowed") and r["wrapped"] is not True
    ]


_PROBE_JSON = "docs/public_surface_coverage.json"

#: Probe outcomes that mean "no conforming envelope was printed".
#:
#: ``fail-with-fixture`` belongs here: the command ran with arguments derived
#: from its own metadata and still printed no valid envelope. Before fixtures
#: existed those commands hid behind ``usage-error``, counted as "unknown"
#: rather than "broken" — so including them makes the contradiction count rise
#: even though coverage did not regress. Visibility improved; the number
#: follows.
_PROBE_BAD = {"no-json", "json-array", "missing-fields", "fail-with-fixture"}

#: Probe outcomes carrying no contract evidence in either direction.
_PROBE_UNPROVEN = {"usage-error", "hang", "no-safe-fixture"}


def load_probe_results(path: Optional[Path] = None) -> Dict[str, str]:
    """Command → probe status, from the sweep sidecar. Empty if never run."""
    doc = path or (repo_root() / _PROBE_JSON)
    try:
        import json

        data = json.loads(doc.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {
        str(r.get("command")): str(r.get("status"))
        for r in data.get("results", [])
        if r.get("command")
    }


def _probe_disagreement(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Commands the static scan calls wrapped but the probe found uncontracted."""
    probe = load_probe_results()
    if not probe:
        return {
            "probe_available": False,
            "static_wrapped_but_probe_failed": None,
            "probe_unproven": None,
        }
    wrapped_names = {
        r["name"] for r in rows if r["kind"] == KIND_CLI and r["wrapped"] is True
    }
    contradicted = sorted(
        name
        for name, status in probe.items()
        if status in _PROBE_BAD and name in wrapped_names
    )
    # Commands the probe could not judge either way: it never got them to run
    # with the arguments they need. Not evidence of coverage in either direction.
    unproven = sorted(
        name for name, status in probe.items() if status in _PROBE_UNPROVEN
    )
    return {
        "probe_available": True,
        "static_wrapped_but_probe_failed": contradicted,
        "static_wrapped_but_probe_failed_count": len(contradicted),
        "probe_unproven": unproven,
        "probe_unproven_count": len(unproven),
    }


def disagreements(surfaces: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Cross-check the derived inventory against the hand-maintained registries.

    Two independent sources that disagree is information; one source that
    everybody trusts is how ``SPEND_PATHS`` and ``TOP_30_COMMANDS`` drifted out
    of sync with the code in the first place. This reports the conflicts rather
    than picking a winner.
    """
    rows = enumerate_all_surfaces() if surfaces is None else surfaces
    cli_names = {r["name"] for r in rows if r["kind"] == KIND_CLI}
    derived_spend = {
        r["name"] for r in rows if r["kind"] == KIND_CLI and r["classification"] == CLASS_SPEND
    }

    out: Dict[str, Any] = {}

    # Static verdict vs. what the commands actually printed. This is the most
    # important row here: ``print_json`` counts as a wrapper, but a command can
    # call it with a *list*, which ``contract_payload`` passes through
    # untouched. Those show as wrapped statically and emit no envelope at all.
    # Trusting the static count alone would rebuild, in a new costume, exactly
    # the declare-vs-derive drift this module exists to catch.
    out.update(_probe_disagreement(rows))

    # Exemption rows pointing at a surface that no longer exists. A stale
    # exemption is indistinguishable from an unnoticed regression.
    all_ids = {r["id"] for r in rows}
    out["orphan_exemptions"] = sorted(k for k in load_exemptions() if k not in all_ids)

    # TOP_30 rows that name a command the CLI does not register.
    try:
        from .public_surface import TOP_30_COMMANDS

        out["top30_ghost_commands"] = sorted(
            c for c in TOP_30_COMMANDS if c not in cli_names
        )
    except Exception:
        out["top30_ghost_commands"] = None

    # CLI commands the MCP side treats as spend but the AST scan does not.
    try:
        from .mcp_safety import CLI_PARITY, SPEND_TOOLS

        mcp_spend_cli = set()
        for tool, cli in CLI_PARITY.items():
            if tool in SPEND_TOOLS and cli:
                mcp_spend_cli.add(str(cli).replace("superai ", "").strip())
        out["mcp_says_spend_ast_says_not"] = sorted(
            c for c in mcp_spend_cli if c in cli_names and c not in derived_spend
        )
    except Exception:
        out["mcp_says_spend_ast_says_not"] = None

    # SPEND_PATHS rows whose module no longer imports.
    try:
        from importlib import import_module

        from .foundation_safety import SPEND_PATHS

        stale: List[str] = []
        freeform: List[str] = []
        for row in SPEND_PATHS:
            rid = str(row.get("id") or "")
            # ``also`` carries a second module for rows that genuinely span two.
            # Checked as well, so it cannot become a place stale names hide.
            for field in ("module", "also"):
                mod = str(row.get(field) or "").strip()
                if not mod:
                    continue
                # A row carrying a prose label ("core.a / b") rather than a dotted
                # path would be reported as stale, which is a false alarm — the
                # same disease this module exists to cure. Bucket it separately.
                if not _DOTTED_PATH.match(mod):
                    freeform.append(rid)
                    continue
                base = ".".join(mod.split(".")[:2])
                try:
                    import_module(base)
                except Exception:
                    stale.append(f"{rid}.{field}" if field != "module" else rid)
        out["spend_paths_unimportable"] = sorted(x for x in stale if x)
        out["spend_paths_freeform_module"] = sorted(x for x in freeform if x)
    except Exception:
        out["spend_paths_unimportable"] = None
        out["spend_paths_freeform_module"] = None

    return out


def surface_report(app: Any = None) -> Dict[str, Any]:
    """Offline inventory report. Reporting only — enforcement lands in Phase 1."""
    rows = enumerate_all_surfaces(app=app)
    by_kind: Dict[str, int] = {}
    by_class: Dict[str, int] = {}
    for r in rows:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
        by_class[r["classification"]] = by_class.get(r["classification"], 0) + 1
    uncovered = uncovered_surfaces(rows)
    unclassified_mcp = [
        r["id"] for r in rows if r["kind"] == KIND_MCP and not r.get("safety_classified")
    ]
    spend_uncovered = [r["id"] for r in uncovered if r["classification"] == CLASS_SPEND]
    return {
        "ok": True,
        "product": "surface_inventory",
        "total": len(rows),
        "by_kind": by_kind,
        "by_classification": by_class,
        "exempt": sum(1 for r in rows if r["exempt"]),
        # ``wrapped`` is the STATIC verdict: the handler calls a wrapper. It is
        # an upper bound. ``probe_*`` below carries the dynamic evidence, and
        # the two are reported side by side rather than reconciled into one
        # reassuring number — see ``disagreements.static_wrapped_but_probe_failed``.
        "wrapped": sum(1 for r in rows if r["wrapped"] is True),
        "wrapped_basis": "static: handler calls a wrapper (upper bound)",
        "uncovered_count": len(uncovered),
        "uncovered": [r["id"] for r in uncovered],
        "uncovered_spend": spend_uncovered,
        "unclassified_mcp": unclassified_mcp,
        "shadowed_commands": [
            {"id": r["id"], "dead_handler": r["handler"]} for r in rows if r.get("shadowed")
        ],
        "disagreements": disagreements(rows),
        "source_available": _cli_source_path() is not None,
        "exemption_doc": _EXEMPTION_DOC,
        "note": (
            "Reporting only. Zero-tolerance enforcement lands in Phase 1 "
            "(tests/test_surface_contract_coverage.py)."
        ),
    }
