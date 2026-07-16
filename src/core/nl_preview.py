"""
N202 — NL → any command with preview.

Production surface:
  1) Parse natural language → SuperAIIntent
  2) Front-door policy path (agent|board|run|ask)
  3) Build planned CLI string + argv list
  4) Risk / dry-run / confidence / needs_confirm
  5) Optional execute after confirm

CLI:
  superai preview "review auth dry-run"
  superai do "…" --preview
  superai do "…" --confirm   # print preview, execute only if confirmed
"""

from __future__ import annotations

import shlex
from typing import Any, Dict, List, Optional, Sequence


# Side-effect classification for preview UX
_HIGH_RISK_ACTIONS = {
    "run",
    "superai_agent",
    "cli_run",
    "tdd",
    "install",
    "backup",
    "github",
}
_MED_RISK_ACTIONS = {
    "review",
    "advise",
    "council",
    "bakeoff",
    "debate",
    "pr_review",
    "goals",
}
_SAFE_ACTIONS = {
    "members",
    "discover",
    "doctor",
    "help",
    "palace",
    "memory_search",
    "budget",
    "host_tools",
    "plan",
    "status",
    "plugin_catalog",
    "smoke_preflight",
    "voice",
    "progress",
    "v6_status",
    "profile",
    "agent_tui",
    "search_web",
}


def planned_argv(intent: Any) -> List[str]:
    """
    Convert intent.planned_command (or format_planned_command) into argv list.
    Uses shlex for correct quoting on Windows/Unix.
    """
    from .nl_intent import format_planned_command

    cmd = getattr(intent, "planned_command", None) or format_planned_command(intent)
    try:
        return shlex.split(cmd, posix=True)
    except Exception:
        return cmd.split()


def risk_level(intent: Any, front_door: Optional[Dict[str, Any]] = None) -> str:
    action = str(getattr(intent, "action", "") or "")
    live = bool(getattr(intent, "live", False))
    dry = bool(getattr(intent, "dry_run", True))
    if action in _HIGH_RISK_ACTIONS and live and not dry:
        return "high"
    if action in _HIGH_RISK_ACTIONS:
        return "medium"
    if action in _MED_RISK_ACTIONS:
        return "medium" if live else "low"
    if action in _SAFE_ACTIONS:
        return "low"
    path = (front_door or {}).get("path")
    if path == "board":
        return "medium"
    if path == "agent":
        return "medium"
    return "low"


def preview_nl(
    text: str,
    *,
    force_path: Optional[str] = None,
    live: bool = False,
) -> Dict[str, Any]:
    """
    Build a full command preview for a natural-language request.

    Does not execute product actions (preview-only).
    """
    from .front_door import choose_path
    from .nl_intent import format_planned_command, parse_intent
    from .spend_guard import ensure_public_result

    raw = (text or "").strip()
    intent = parse_intent(raw)
    if live and not intent.live:
        intent.live = True
        intent.dry_run = False
        intent.planned_command = format_planned_command(intent)

    # Front-door for free-form / run
    fd = choose_path(intent.subject or intent.raw, force=force_path)
    if intent.action in {"run", "unknown"} or "universal_agent" in (intent.notes or []):
        p = fd.get("path")
        if p == "board":
            intent.action = "review"
            intent.notes = list(intent.notes or []) + ["preview_front_door:board"]
        elif p == "agent":
            intent.action = "superai_agent"
            intent.extras["agent_role"] = fd.get("agent_role") or "build"
            intent.notes = list(intent.notes or []) + ["preview_front_door:agent"]
        elif p == "ask":
            intent.action = "superai_agent"
            intent.extras["agent_role"] = "ask"
            intent.notes = list(intent.notes or []) + ["preview_front_door:ask"]
        intent.planned_command = format_planned_command(intent)

    # Re-format planned command for agent path
    if intent.action == "superai_agent":
        role = intent.extras.get("agent_role") or "build"
        subj = intent.subject or intent.raw
        intent.planned_command = (
            f"superai agent {shlex.quote(subj)} --agent {role} --permission plan"
        )

    conf = float(intent.confidence or 0)
    fd_conf = float(fd.get("confidence") or conf)
    confidence = round(min(conf, fd_conf) if fd.get("needs_confirm") else max(conf, fd_conf), 2)
    needs_confirm = bool(fd.get("needs_confirm")) or confidence < 0.55 or risk_level(intent, fd) == "high"

    argv = planned_argv(intent)
    planned = intent.planned_command or format_planned_command(intent)

    preview = {
        "ok": True,
        "preview": True,
        "executed": False,
        "nl": raw,
        "intent": intent.to_dict(),
        "planned_command": planned,
        "argv": argv,
        "front_door": fd,
        "confidence": confidence,
        "needs_confirm": needs_confirm,
        "risk": risk_level(intent, fd),
        "dry_run": bool(intent.dry_run),
        "live": bool(intent.live),
        "action": intent.action,
        "summary": (
            f"Action={intent.action} · risk={risk_level(intent, fd)} · "
            f"confidence={confidence} · cmd={planned}"
        ),
        "confirm_hint": (
            "superai do " + shlex.quote(raw) + " --yes"
            if needs_confirm
            else "superai do " + shlex.quote(raw)
        ),
    }
    return ensure_public_result(preview, mock=True, dry_run=True, ok=True)


def execute_from_preview(
    preview: Dict[str, Any],
    *,
    confirmed: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Execute a previously built preview.

    If preview.needs_confirm and not confirmed → blocked (safe default).
    """
    from .nl_intent import SuperAIIntent, execute_intent
    from .spend_guard import ensure_public_result

    if not isinstance(preview, dict):
        return ensure_public_result(
            {"ok": False, "error": "invalid_preview"}, ok=False
        )
    needs = bool(preview.get("needs_confirm"))
    if needs and not confirmed:
        return ensure_public_result(
            {
                "ok": False,
                "error": "confirmation_required",
                "error_code": "permission",
                "needs_confirm": True,
                "preview": preview,
                "hint": "Re-run with --yes after reviewing planned_command",
            },
            ok=False,
            dry_run=True,
        )

    intent_data = preview.get("intent") or {}
    try:
        intent = SuperAIIntent(
            action=str(intent_data.get("action") or "run"),
            subject=str(intent_data.get("subject") or ""),
            members=list(intent_data.get("members") or []),
            prefer=str(intent_data.get("prefer") or "mixed"),
            pick=bool(intent_data.get("pick")),
            dry_run=bool(intent_data.get("dry_run", True)),
            live=bool(intent_data.get("live")),
            only_available=bool(intent_data.get("only_available", True)),
            worker_prefer=intent_data.get("worker_prefer"),
            max_members=int(intent_data.get("max_members") or 3),
            model=intent_data.get("model"),
            confidence=float(intent_data.get("confidence") or 0),
            raw=str(intent_data.get("raw") or preview.get("nl") or ""),
            planned_command=str(
                intent_data.get("planned_command")
                or preview.get("planned_command")
                or ""
            ),
            notes=list(intent_data.get("notes") or []),
            extras=dict(intent_data.get("extras") or {}),
        )
    except Exception as e:
        return ensure_public_result(
            {"ok": False, "error": f"intent_rebuild_failed:{e}"[:200]}, ok=False
        )

    out = execute_intent(intent, execute=True, verbose=verbose)
    if isinstance(out, dict):
        out["preview"] = {
            "planned_command": preview.get("planned_command"),
            "confidence": preview.get("confidence"),
            "risk": preview.get("risk"),
            "confirmed": confirmed,
        }
        out["executed"] = True
        return ensure_public_result(out, ok=bool(out.get("ok", True)))
    return ensure_public_result({"ok": True, "result": out, "executed": True})


def preview_and_maybe_execute(
    text: str,
    *,
    preview_only: bool = False,
    confirm: bool = False,
    yes: bool = False,
    live: bool = False,
    force_path: Optional[str] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    One-shot N202 entry: always builds preview; executes only when allowed.
    """
    prev = preview_nl(text, force_path=force_path, live=live)
    if preview_only:
        return prev
    # Execute if: --yes, or not needs_confirm, or confirm mode with yes
    if prev.get("needs_confirm") and not yes:
        prev["ok"] = True
        prev["executed"] = False
        prev["blocked_reason"] = "needs_confirm"
        prev["hint"] = "Review planned_command then pass --yes to execute"
        return prev
    return execute_from_preview(prev, confirmed=True, verbose=verbose)


def catalog_examples() -> List[Dict[str, str]]:
    """Documented NL → command examples for docs/tests."""
    return [
        {"nl": "list available models", "expect_action": "members"},
        {"nl": "run doctor", "expect_action": "doctor"},
        {"nl": "review auth middleware dry-run", "expect_action": "review"},
        {"nl": "council on api design", "expect_action": "council"},
        {"nl": "search memory for jwt", "expect_action": "memory_search"},
        {"nl": "show budget", "expect_action": "budget"},
        {"nl": "plugin catalog memory", "expect_action": "plugin_catalog"},
        {"nl": "status with cost", "expect_action": "status"},
        {"nl": "smoke preflight", "expect_action": "smoke_preflight"},
        {"nl": "implement login fix", "expect_action": "run"},
        {"nl": "open agent tui", "expect_action": "agent_tui"},
        {"nl": "help", "expect_action": "help"},
    ]
