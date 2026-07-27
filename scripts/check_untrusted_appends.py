#!/usr/bin/env python3
"""Guardrail: retrieved content must not be appended to a prompt bare.

Why this exists
---------------
``SuperAIOrchestrator._build_step_prompt`` assembles the prompt sent to the
model for each plan step. Several of the parts it appends are *retrieved*:
past learnings, past warnings, matched skills, and the output of previous
steps. Any of those can contain text that an earlier run wrote into the
learning store, so text that influenced one run can influence every later run
that retrieves the same memory.

PR #2 wraps those parts in an explicit untrusted-data envelope
(``core.untrusted_data.wrap_untrusted_block``). Nothing in the language or the
test suite stops someone adding a fifth ``prompt_parts.append(...)`` later
that forgets the wrapper, and no unit test can catch an append that does not
exist yet. This script is that missing check.

Behaviour
---------
* If ``src/core/untrusted_data.py`` is absent, the check is skipped and exits
  0. That is the state of ``master`` until PR #2 merges; this guardrail is
  deliberately allowed to land first so the two PRs stay independent.
* Otherwise every ``prompt_parts.append(...)`` inside ``_build_step_prompt``
  must either contain a ``wrap_untrusted_block`` call or be one of the known
  first-party parts on the allowlist below.

Exit codes
----------
0  pass, or skipped because the untrusted-data module is not present yet
1  a bare append of retrieved content was found
2  the file or the function could not be found or parsed

A parse failure is treated as a failure rather than a pass: a guardrail that
silently succeeds when it cannot see the code is worse than no guardrail.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = REPO_ROOT / "src" / "core" / "orchestrator.py"
UNTRUSTED = REPO_ROOT / "src" / "core" / "untrusted_data.py"

FUNCTION_NAME = "_build_step_prompt"
WRAPPER_NAME = "wrap_untrusted_block"

# First-party prompt parts that are authored in this repo rather than
# retrieved from storage. These are safe to append directly.
ALLOWED_TOKENS = (
    "step.description",
    "constitution",
    "Overall task:",
)


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _find_function(tree: ast.AST, name: str) -> ast.AST | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == name:
                return node
    return None


def _is_prompt_parts_append(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    target = node.func
    if not isinstance(target, ast.Attribute) or target.attr != "append":
        return False
    owner = target.value
    return isinstance(owner, ast.Name) and owner.id == "prompt_parts"


def main() -> int:
    if not UNTRUSTED.exists():
        print(
            f"SKIP: {_rel(UNTRUSTED)} is not present yet, so there is no "
            "envelope to enforce. This check activates once the "
            "untrusted-data module lands."
        )
        return 0

    if not ORCHESTRATOR.exists():
        print(f"FAIL: {_rel(ORCHESTRATOR)} not found.")
        return 2

    source = ORCHESTRATOR.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        print(f"FAIL: could not parse {_rel(ORCHESTRATOR)}: {exc}")
        return 2

    function = _find_function(tree, FUNCTION_NAME)
    if function is None:
        print(
            f"FAIL: {FUNCTION_NAME} not found in {_rel(ORCHESTRATOR)}. "
            "If it was renamed, update FUNCTION_NAME in this script rather "
            "than deleting the check."
        )
        return 2

    offenders: list[tuple[int, str]] = []
    for node in ast.walk(function):
        if not _is_prompt_parts_append(node):
            continue
        if not node.args:
            continue
        segment = ast.get_source_segment(source, node.args[0]) or ""
        if WRAPPER_NAME in segment:
            continue
        if any(token in segment for token in ALLOWED_TOKENS):
            continue
        snippet = " ".join(segment.split())
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        offenders.append((node.lineno, snippet))

    if offenders:
        print(
            "FAIL: content is appended to the step prompt without an "
            "untrusted-data envelope.\n"
        )
        for lineno, snippet in offenders:
            print(f"  {_rel(ORCHESTRATOR)}:{lineno}: {snippet}")
        print(
            "\nIf the value is retrieved from memory, skills, or a previous "
            f"step, wrap it with {WRAPPER_NAME}(). If it is first-party text "
            "authored in this repo, add a distinguishing token to "
            "ALLOWED_TOKENS in this script and say why in the commit message."
        )
        return 1

    print(
        f"OK: every retrieved part appended in {FUNCTION_NAME} goes through "
        f"{WRAPPER_NAME}()."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
