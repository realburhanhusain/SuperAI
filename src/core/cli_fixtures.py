"""
Derive safe invocation arguments for CLI commands that require them.

87 commands exit 2 ("missing argument") under the contract sweep, which means
41% of the surface had no contract evidence in either direction — neither
proven nor proven-broken. Hand-writing 87 fixtures would create yet another
hand-maintained list of exactly the kind this codebase keeps drifting out of
sync with the code.

So the arguments are **derived from Click's own parameter metadata** instead:
required params, their types, their declared choices, and the ``a | b | c``
enumerations their help strings already contain. A small override table covers
the cases where a syntactically valid value would still be semantically wrong
(a URL, a real file path), and a refusal table covers the ones that should not
be invoked at all with any argument.

Every command is therefore in exactly one bucket — derived, overridden, or
refused-with-a-reason. Nothing is silently skipped.
"""

from __future__ import annotations

import inspect
import re
from typing import Any, Dict, List, Optional, Tuple

#: Generic filler for a free-text parameter. Recognisable in logs if it leaks.
PLACEHOLDER_TEXT = "superai-contract-probe"

#: ``a | b | c`` or ``a|b|c`` in a help string — the codebase's usual way of
#: documenting an action argument that has no Click ``Choice`` type.
_CHOICE_IN_HELP = re.compile(
    r"^\s*([A-Za-z][\w-]*(?:\s*\|\s*[A-Za-z][\w-]*)+)\s*$"
)

#: Parameter names that want a filesystem path rather than free text.
_PATH_HINTS = ("path", "file", "dest", "dir", "output", "out")

#: Parameter names that want something URL-shaped.
_URL_HINTS = ("url", "endpoint", "uri")

#: Explicit values where a derived one would be valid but meaningless, keyed by
#: ``"<command> <param>"``. Kept small on purpose — every entry here is a place
#: the derivation could not reach.
OVERRIDES: Dict[str, str] = {
    # A JSON-shaped argument: any plain string parses as a usage error later.
    "capture stream turns_json": '[{"hook":"user_prompt","content":"probe"}]',
    "capture turn hook": "user_prompt",
    "backup-key action": "export",
    "budget command set max_usd": "0.01",
    # The parameter is ``text``, not ``payload`` — caught by
    # ``test_overrides_target_live_parameters``, which exists precisely because
    # an override naming a non-existent parameter is a silent no-op.
    "validate-json text": "{}",
}

#: Commands that must not be invoked even with valid arguments, and why.
#: These are contract gaps that stay open rather than being probed unsafely.
REFUSE: Dict[str, str] = {
    "browse": "fetches a live URL; the sweep is offline by contract",
    "search-web": "performs a live web search",
    "backup-key": "exports or imports the backup encryption key",
    "tt-restore": "restores a time-travel snapshot over current state",
    "restore": "overwrites files from a backup archive",
    "update": "self-update; mutates the installed package",
    "shell": "executes an arbitrary shell command",
}


def _first_choice(text: str) -> Optional[str]:
    """First option from an ``a | b | c`` enumeration, if that is what this is."""
    if not text:
        return None
    # Help strings often read "action: list | clear" or "list | clear".
    tail = text.split(":")[-1]
    m = _CHOICE_IN_HELP.match(tail)
    if not m:
        return None
    return m.group(1).split("|")[0].strip()


def _value_for(param: Any, command: str, tmp_path: Optional[str], annotation: Any = None) -> Tuple[Optional[str], str]:
    """Derive one parameter value. Returns ``(value, how)``."""
    name = str(getattr(param, "name", "") or "")

    key = f"{command} {name}"
    if key in OVERRIDES:
        return OVERRIDES[key], "override"

    # A real Click Choice knows its own options.
    ptype = getattr(param, "type", None)
    choices = getattr(ptype, "choices", None)
    if choices:
        return str(list(choices)[0]), "choice-type"

    # The codebase documents most action arguments as "a | b | c" in help.
    from_help = _first_choice(str(getattr(param, "help", "") or ""))
    if from_help:
        return from_help, "choice-in-help"

    type_name = getattr(ptype, "name", "") or ""
    if type_name == "float":
        return "0.01", "type-default"
    if type_name == "integer":
        return "1", "type-default"

    if annotation is float:
        return "0.01", "type-default"
    if annotation is int:
        return "1", "type-default"

    lowered = name.lower()
    if any(h in lowered for h in _URL_HINTS):
        # No safe derived URL exists — a probe must not make a network call.
        return None, "needs-url"
    if any(h in lowered for h in _PATH_HINTS):
        if tmp_path is None:
            return None, "needs-path"
        return tmp_path, "temp-path"

    return PLACEHOLDER_TEXT, "placeholder"


def resolve_command(app: Any, command: str) -> Any:
    """Walk a dotted/spaced command path to its Click command object."""
    import typer

    node = typer.main.get_command(app)
    for part in command.split():
        if not hasattr(node, "get_command"):
            return None
        node = node.get_command(None, part)
        if node is None:
            return None
    return node


def synthesize_args(
    command: str,
    *,
    app: Any = None,
    tmp_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build an argv tail that satisfies ``command``'s required parameters.

    Returns a dict with ``ok``, ``args`` and ``how`` (per-parameter provenance),
    or ``ok=False`` plus ``reason`` when no safe invocation exists.
    """
    root = command.split()[0]
    if root in REFUSE:
        return {"ok": False, "command": command, "reason": REFUSE[root], "args": None}
    if command in REFUSE:
        return {"ok": False, "command": command, "reason": REFUSE[command], "args": None}

    if app is None:
        from scli.main import app as cli_app

        app = cli_app

    node = resolve_command(app, command)
    if node is None:
        return {"ok": False, "command": command, "reason": "command not resolvable", "args": None}

    args: List[str] = []
    how: Dict[str, str] = {}
    try:
        annotations = inspect.get_annotations(getattr(node, "callback", None), eval_str=False)
    except Exception:
        annotations = {}
    for param in getattr(node, "params", []) or []:
        if not getattr(param, "required", False):
            continue
        value, provenance = _value_for(param, command, tmp_path, annotations.get(str(param.name)))
        if value is None:
            return {
                "ok": False,
                "command": command,
                "reason": f"no safe value for '{param.name}' ({provenance})",
                "args": None,
            }
        opts = list(getattr(param, "opts", []) or [])
        is_option = bool(opts) and str(opts[0]).startswith("-")
        if is_option:
            args.extend([str(opts[0]), value])
        else:
            args.append(value)
        how[str(param.name)] = provenance

    return {"ok": True, "command": command, "args": args, "how": how}


def fixture_report(app: Any = None, commands: Optional[List[str]] = None) -> Dict[str, Any]:
    """Offline summary of which commands can be given derived arguments."""
    if commands is None:
        from .surface_inventory import CLASS_READ_ONLY, enumerate_cli_surfaces

        commands = [
            r["name"]
            for r in enumerate_cli_surfaces(app=app)
            if r["classification"] == CLASS_READ_ONLY
            and not r["exempt"]
            and not r.get("shadowed")
        ]

    derived: List[str] = []
    refused: List[Dict[str, str]] = []
    for name in commands:
        out = synthesize_args(name, app=app, tmp_path="probe.tmp")
        if out["ok"]:
            if out["args"]:
                derived.append(name)
        else:
            refused.append({"command": name, "reason": out["reason"]})
    return {
        "ok": True,
        "product": "cli_fixtures",
        "derived": sorted(derived),
        "derived_count": len(derived),
        "refused": sorted(refused, key=lambda r: r["command"]),
        "refused_count": len(refused),
        "considered": len(commands),
    }