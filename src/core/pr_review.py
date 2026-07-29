"""
PR review mode (N26) — review a diff or local git range.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .workspace import workspace_root


def get_git_diff(ref: str = "HEAD~1") -> str:
    root = workspace_root()
    from .subprocess_safety import run as safe_run

    proc = safe_run(
        ["git", "diff", ref],
        kind="git",
        cwd=str(root),
        capture_output=True,
        text=True,
        shell=False,
    )
    return (proc.stdout or proc.stderr or "")[:50000]


def review_diff(
    diff: str,
    use_mock: bool = True,
    *,
    use_clis: bool = True,
    clis: Optional[list] = None,
    dry_run: bool = False,
    code_impact: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Review a diff via multi-CLI advisory board (preferred) and/or model council.

    When use_clis=True and CLIs are available, structured multi-CLI review runs first.
    Council still runs as a model/CLI hybrid for voting consistency.
    """
    from .council import Council
    from .model_caller import ModelCaller
    from .model_registry import ModelRegistry
    from .spend_guard import budget_precheck

    # Spend spine (V4-M1): public thin wrapper must hit budget before fan-out
    block = budget_precheck(
        estimated_usd=0.12 if not use_mock else 0.0,
        tokens=600,
        command_name="pr_review",
        enforce=False if use_mock else None,
    )
    if block.get("blocked") or block.get("ok") is False:
        block.setdefault("product", "pr_review")
        return block

    impact_text = ""
    if isinstance(code_impact, dict) and code_impact.get("ok"):
        changed = [str(x.get("qualified_name") or x.get("name")) for x in (code_impact.get("changed_symbols") or [])[:12] if isinstance(x, dict)]
        affected = [str(x.get("qualified_name") or x.get("name")) for x in (code_impact.get("impacted_symbols") or [])[:12] if isinstance(x, dict)]
        tests = [str(x) for x in (code_impact.get("impacted_tests") or [])[:12]]
        impact_text = (
            "\n\nLocal static code-impact evidence (not model-generated):\n"
            f"risk={code_impact.get('risk') or 'unknown'}\n"
            f"changed_symbols={', '.join(changed) or 'none resolved'}\n"
            f"affected_callers={', '.join(affected) or 'none resolved'}\n"
            f"suggested_tests={', '.join(tests) or 'none'}"
        )
    topic = (
        "Code review this diff. Vote on merge readiness "
        "(approve | request_changes | reject).\n\n"
        f"```diff\n{diff[:12000]}\n```{impact_text}"
    )

    cli_board = None
    if use_clis:
        try:
            from .multi_cli_advisory import multi_cli_board

            cli_board = multi_cli_board(
                topic,
                mode="review",
                clis=clis,
                max_clis=3,
                dry_run=dry_run or use_mock,
                approve=True,
            )
        except Exception as e:  # noqa: BLE001
            cli_board = {"ok": False, "error": str(e)[:300]}

    reg = ModelRegistry()
    try:
        reg.register_external_clis_as_models()
    except Exception:
        pass
    # If CLIs available and not pure mock, allow live ModelCaller for cli:* paths
    caller = ModelCaller(use_mock=use_mock, registry=reg)
    c = Council(caller=caller, registry=reg, voting_mode="majority")
    members = None
    if use_clis:
        try:
            from .multi_cli_advisory import default_council_members

            members = default_council_members(3, prefer_clis=True, registry=reg)
        except Exception:
            members = None
    result = c.run(topic, models=members, with_critique=True)

    # Prefer structured multi-CLI board verdict when present
    board = (cli_board or {}).get("board") or {}
    decision = result.get("decision") or {}
    if board.get("verdict"):
        decision = {
            **decision,
            "mode": "multi_cli_board+council",
            "cli_board_verdict": board.get("verdict"),
            "cli_board_tally": board.get("tally"),
            "summary": board.get("summary") or decision.get("summary"),
            "findings": board.get("findings") or [],
        }

    out = {
        "ok": True,
        "decision": decision,
        "proposals": result.get("proposals"),
        "stage0": result.get("stage0"),
        "members": result.get("members"),
        "cli_board": cli_board,
        "protocol": "superai.pr_review.v2",
        "mock": bool(use_mock),
        "dry_run": bool(dry_run or use_mock),
        "code_impact": code_impact,
    }
    try:
        from .result_contract import apply_contract

        apply_contract(
            out,
            mock=bool(use_mock),
            dry_run=bool(dry_run or use_mock),
            members=list(result.get("members") or []),
            ok=True,
        )
    except Exception:
        out.setdefault("contract", "superai.result.v1")
    return out


def review_local(
    ref: str = "HEAD~1",
    use_mock: bool = True,
    *,
    use_clis: bool = True,
    clis: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    diff = get_git_diff(ref)
    if not diff.strip():
        return {"ok": False, "error": "empty diff", "ref": ref}
    impact = None
    try:
        from .code_intelligence import code_impact
        impact = code_impact(root=workspace_root(), ref=ref)
    except Exception as e:  # noqa: BLE001
        impact = {"ok": False, "error": str(e)[:300]}
    out = review_diff(
        diff, use_mock=use_mock, use_clis=use_clis, clis=clis, dry_run=dry_run,
        code_impact=impact,
    )
    out["ref"] = ref
    out["diff_chars"] = len(diff)
    return out
