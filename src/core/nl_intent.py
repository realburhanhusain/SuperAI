"""
Natural-language → SuperAI command intent router.

Maps phrases like:
  "review the auth design with gpt-4o and gemini"
  "let me pick a council for architecture"
  "list available models and clis"
into structured intents and optional execution of review/advise/council/run/members.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence


ACTIONS = (
    "members",
    "review",
    "advise",
    "council",
    "run",
    "discover",
    "cli_run",
    "help",
    "unknown",
)


@dataclass
class SuperAIIntent:
    action: str
    subject: str = ""
    members: List[str] = field(default_factory=list)
    prefer: str = "mixed"  # mixed | api | cli
    pick: bool = False
    dry_run: bool = True
    live: bool = False
    only_available: bool = True
    worker_prefer: Optional[str] = None
    max_members: int = 3
    model: Optional[str] = None  # forced primary for run/cli_run
    confidence: float = 0.0
    raw: str = ""
    planned_command: str = ""
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Known API/CLI tokens for member extraction
_CLI_NAMES = (
    "claude",
    "gemini",
    "grok",
    "codex",
    "aider",
    "cursor",
    "continue",
    "cline",
    "roo",
)

_API_HINTS = (
    "gpt-4o",
    "gpt-4.1",
    "o3-mini",
    "o3",
    "o4-mini",
    "claude-4-sonnet",
    "claude-4-opus",
    "claude-3-5-sonnet",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "grok-3",
    "grok-2",
    "deepseek-coder",
    "deepseek-r1",
    "qwen2.5-coder",
)


def parse_intent(text: str) -> SuperAIIntent:
    """Heuristic NL → SuperAIIntent (offline, deterministic)."""
    raw = (text or "").strip()
    low = raw.lower()
    intent = SuperAIIntent(action="unknown", raw=raw, confidence=0.2)

    if not raw:
        intent.action = "help"
        intent.confidence = 1.0
        intent.planned_command = "superai ask --help"
        return intent

    # Flags from language
    intent.pick = bool(
        re.search(
            r"\b(pick|choose|select|interactive|let me (choose|pick)|which model)\b",
            low,
        )
    )
    if re.search(r"\b(live|for real|actually run|no dry[- ]?run)\b", low):
        intent.dry_run = False
        intent.live = True
    if re.search(r"\b(dry[- ]?run|preview|simulate)\b", low):
        intent.dry_run = True
        intent.live = False

    if re.search(r"\b(prefer\s+cli|cli[- ]only|only clis?)\b", low):
        intent.prefer = "cli"
        intent.worker_prefer = "cli"
    elif re.search(r"\b(prefer\s+api|api[- ]only|only apis?|only models)\b", low):
        intent.prefer = "api"
        intent.worker_prefer = "api"
    elif re.search(r"\b(prefer\s+mixed|mixed)\b", low):
        intent.prefer = "mixed"
        intent.worker_prefer = "mixed"

    intent.members = _extract_members(raw)
    intent.model = intent.members[0] if len(intent.members) == 1 else None

    # Action classification (order matters: specific before run)
    if re.search(
        r"\b(list|show|what|which).{0,40}\b(member|model|cli|available)|"
        r"\bmembers\b|"
        r"\bavailable (models?|clis?)\b|"
        r"\bwhat can i use\b",
        low,
    ):
        intent.action = "members"
        intent.confidence = 0.92
        intent.only_available = "all" not in low and "every" not in low
    elif re.search(r"\b(discover|doctor|environment|what.?s installed)\b", low):
        intent.action = "discover"
        intent.confidence = 0.9
    elif re.search(
        r"\b(council|vote on|multi[- ]model (debate|vote|discuss)|convene)\b",
        low,
    ):
        intent.action = "council"
        intent.confidence = 0.9
        intent.subject = _extract_subject(
            raw,
            drop_prefixes=(
                r"council\s+(on|about|for)?",
                r"convene\s+(a\s+)?council\s+(on|about|for)?",
                r"vote\s+on",
                r"have\s+(a\s+)?council",
            ),
        )
        intent.max_members = 3
    elif re.search(
        r"\b(advise|advice|should we|recommend|what do you think|"
        r"advisor board|ask advisors)\b",
        low,
    ):
        intent.action = "advise"
        intent.confidence = 0.88
        intent.subject = _extract_subject(
            raw,
            drop_prefixes=(
                r"advise\s+(on|about|me\s+on)?",
                r"give\s+advice\s+(on|about)?",
                r"should\s+we",
                r"recommend",
                r"ask\s+advisors?\s+(about|on)?",
            ),
        )
    elif re.search(
        r"\b(review|code review|pr review|critique|look over)\b",
        low,
    ):
        intent.action = "review"
        intent.confidence = 0.9
        intent.subject = _extract_subject(
            raw,
            drop_prefixes=(
                r"(please\s+)?(code\s+)?review\s+(the|this|my)?",
                r"critique\s+(the|this)?",
                r"look\s+over\s+(the|this)?",
                r"pr[- ]review\s+(the|this)?",
            ),
        )
    elif re.search(
        r"\b(cli[- ]run|run\s+(on|via|with)\s+(claude|gemini|grok|codex|aider))\b",
        low,
    ) or (
        re.search(r"\b(ask|tell)\s+(claude|gemini|grok|codex|aider)\b", low)
        and not re.search(r"\b(review|advise|council)\b", low)
    ):
        intent.action = "cli_run"
        intent.confidence = 0.85
        # primary CLI from members or name in text
        for c in _CLI_NAMES:
            if re.search(rf"\b{c}\b", low):
                intent.model = next(
                    (m for m in intent.members if c in m.lower()),
                    f"cli:{c}",
                )
                break
        intent.subject = _extract_subject(
            raw,
            drop_prefixes=(
                r"(please\s+)?(ask|tell|run)\s+\w+\s+(to|about)?",
                r"cli[- ]run",
            ),
        )
    elif re.search(
        r"\b(implement|build|fix|create|write|refactor|run\s+task|"
        r"do\s+this|work\s+on|workers?)\b",
        low,
    ) or low.startswith("run "):
        intent.action = "run"
        intent.confidence = 0.82
        intent.subject = _extract_subject(
            raw,
            drop_prefixes=(
                r"(please\s+)?(run|implement|build|fix|create|write|refactor)\s+",
                r"work\s+on\s+",
                r"do\s+this\s*:\s*",
            ),
        )
        if intent.pick:
            intent.notes.append("pick_workers")
        if intent.worker_prefer is None:
            intent.worker_prefer = intent.prefer
    elif re.search(r"\b(help|how do i|what can superai)\b", low):
        intent.action = "help"
        intent.confidence = 0.85
    else:
        # Default: orchestrated run with the full phrase as task
        intent.action = "run"
        intent.subject = raw
        intent.confidence = 0.55
        intent.notes.append("fallback_run")

    if not intent.subject and intent.action in {
        "review",
        "advise",
        "council",
        "run",
        "cli_run",
    }:
        intent.subject = raw

    intent.planned_command = format_planned_command(intent)
    return intent


def _extract_members(text: str) -> List[str]:
    found: List[str] = []
    # explicit cli:name@model / name@model
    for m in re.finditer(
        r"\b(?:cli:)?([a-z][a-z0-9_-]*)@([a-zA-Z0-9._:/-]+)\b", text, flags=re.I
    ):
        cli, model = m.group(1).lower(), m.group(2)
        if cli in _CLI_NAMES or m.group(0).lower().startswith("cli:"):
            tok = f"cli:{cli}@{model}"
            if tok not in found:
                found.append(tok)
    for m in re.finditer(r"\bcli:([a-z][a-z0-9_-]*)\b", text, flags=re.I):
        tok = f"cli:{m.group(1).lower()}"
        if tok not in found:
            found.append(tok)
    for name in _CLI_NAMES:
        # bare CLI: "with gemini and grok" — not "gemini-2.5-pro" (API id)
        if any(x.startswith(f"cli:{name}") for x in found):
            continue
        if re.search(
            rf"(?:with|using|via|and|,)\s+{name}\b(?![-.])",
            text,
            flags=re.I,
        ) or re.search(rf"\b{name}\s+cli\b", text, flags=re.I):
            tok = f"cli:{name}"
            if tok not in found:
                found.append(tok)
    for api in _API_HINTS:
        if re.search(rf"\b{re.escape(api)}\b", text, flags=re.I):
            if api not in found:
                found.append(api)
    # "with X, Y, and Z" tokens that look like model ids
    for m in re.finditer(
        r"\b([a-z][a-z0-9]+(?:-[a-z0-9.]+){1,4})\b", text, flags=re.I
    ):
        tok = m.group(1)
        low = tok.lower()
        if low in _CLI_NAMES:
            continue
        if any(k in low for k in ("gpt", "claude", "gemini", "grok", "o3", "o4", "deepseek", "qwen")):
            if tok not in found and f"cli:{tok}" not in found:
                found.append(tok)
    return found[:8]


def _extract_subject(text: str, drop_prefixes: Sequence[str] = ()) -> str:
    s = text.strip()
    # strip member list tail "with gpt-4o and cli:gemini"
    s = re.sub(
        r"\b(with|using|via)\s+[\w@:,./\s-]+$",
        "",
        s,
        flags=re.I,
    ).strip()
    for pat in drop_prefixes:
        s2 = re.sub(rf"^{pat}\s*", "", s, flags=re.I).strip()
        if s2 != s:
            s = s2
    # strip pick/prefer/live clauses
    s = re.sub(
        r"\b(and\s+)?(let me pick|interactively|prefer\s+\w+|dry[- ]?run|live)\b.*$",
        "",
        s,
        flags=re.I,
    ).strip(" :,-")
    return s or text.strip()


def format_planned_command(intent: SuperAIIntent) -> str:
    """Human-readable SuperAI CLI equivalent."""
    a = intent.action
    if a == "members":
        cmd = ["superai", "members"]
        if intent.only_available:
            cmd.append("--available")
        if intent.pick:
            cmd.append("--pick")
        if intent.live:
            cmd.append("--live-probe")
        return " ".join(cmd)
    if a == "discover":
        return "superai discover"
    if a == "help":
        return "superai ask --help"
    if a == "review":
        cmd = ["superai", "review", shlex.quote(intent.subject or "")]
        if intent.members:
            cmd += ["-m", ",".join(intent.members)]
        if intent.pick:
            cmd.append("--pick")
        cmd += ["--prefer", intent.prefer]
        cmd.append("--live" if intent.live else "--dry-run")
        return " ".join(cmd)
    if a == "advise":
        cmd = ["superai", "advise", shlex.quote(intent.subject or "")]
        if intent.members:
            cmd += ["-m", ",".join(intent.members)]
        if intent.pick:
            cmd.append("--pick")
        cmd += ["--prefer", intent.prefer]
        cmd.append("--live" if intent.live else "--dry-run")
        return " ".join(cmd)
    if a == "council":
        cmd = ["superai", "council", shlex.quote(intent.subject or "")]
        if intent.members:
            cmd += ["--models", ",".join(intent.members)]
        if intent.pick:
            cmd.append("--pick")
        cmd += ["--prefer", intent.prefer]
        return " ".join(cmd)
    if a == "cli_run":
        name = intent.model or "gemini"
        if name.startswith("cli:"):
            name = name[4:]
        cmd = ["superai", "cli-run", name, shlex.quote(intent.subject or "")]
        if intent.dry_run:
            cmd.append("--dry-run")
        return " ".join(cmd)
    if a == "run":
        cmd = ["superai", "run", shlex.quote(intent.subject or intent.raw)]
        if intent.members:
            cmd += ["--workers", ",".join(intent.members)]
        if intent.pick or "pick_workers" in intent.notes:
            cmd.append("--pick-workers")
        if intent.worker_prefer:
            cmd += ["--worker-prefer", intent.worker_prefer]
        if intent.model and not intent.members:
            cmd += ["-m", intent.model]
        return " ".join(cmd)
    return f"superai run {shlex.quote(intent.raw)}"


def execute_intent(
    intent: SuperAIIntent,
    *,
    execute: bool = True,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Plan and optionally execute the intent against SuperAI core APIs.
    """
    result: Dict[str, Any] = {
        "ok": True,
        "intent": intent.to_dict(),
        "planned_command": intent.planned_command or format_planned_command(intent),
        "executed": False,
        "result": None,
    }
    if not execute:
        return result

    action = intent.action
    try:
        if action == "help":
            result["result"] = {
                "message": (
                    "Try: list available models; review X with gpt-4o and gemini; "
                    "advise whether we should ship; council on architecture --pick; "
                    "implement feature Y with workers"
                ),
                "examples": [
                    "list available models and clis",
                    "review the auth design with gpt-4o and cli:gemini",
                    "advise should we ship tonight prefer cli",
                    "council pick architecture interactively",
                    "implement rate limiting with gpt-4o and claude",
                ],
            }
            result["executed"] = True
            return result

        if action == "members":
            from .member_selection import list_selectable_members

            if intent.pick:
                from .approval_tui import prompt_pick_from_catalog

                chosen = prompt_pick_from_catalog(
                    title="Select members",
                    max_n=intent.max_members,
                    only_available=intent.only_available,
                    prefer=intent.prefer,
                )
                result["result"] = {"selected": chosen}
            else:
                result["result"] = list_selectable_members(
                    only_available=intent.only_available,
                    with_cli_models=True,
                    live_cli_models=bool(intent.live),
                )
            result["executed"] = True
            return result

        if action == "discover":
            from .discovery import discover_environment

            result["result"] = discover_environment()
            result["executed"] = True
            return result

        if action == "review":
            from .multi_cli_advisory import multi_cli_board

            members = list(intent.members)
            if intent.pick and not members:
                from .approval_tui import prompt_pick_from_catalog

                members = prompt_pick_from_catalog(
                    title="Pick review board",
                    max_n=intent.max_members,
                    prefer=intent.prefer,
                )
            result["result"] = multi_cli_board(
                intent.subject or intent.raw,
                mode="review",
                members=members or None,
                max_clis=intent.max_members,
                dry_run=intent.dry_run,
                approve=True,
                prefer=intent.prefer,
            )
            result["executed"] = True
            return result

        if action == "advise":
            from .multi_cli_advisory import multi_cli_board

            members = list(intent.members)
            if intent.pick and not members:
                from .approval_tui import prompt_pick_from_catalog

                members = prompt_pick_from_catalog(
                    title="Pick advisors",
                    max_n=intent.max_members,
                    prefer=intent.prefer,
                )
            result["result"] = multi_cli_board(
                intent.subject or intent.raw,
                mode="advise",
                members=members or None,
                max_clis=intent.max_members,
                dry_run=intent.dry_run,
                approve=True,
                prefer=intent.prefer,
            )
            result["executed"] = True
            return result

        if action == "council":
            from .council import Council
            from .member_selection import resolve_members

            members = list(intent.members)
            if intent.pick and not members:
                from .approval_tui import prompt_pick_from_catalog

                members = prompt_pick_from_catalog(
                    title="Pick council members",
                    max_n=intent.max_members,
                    prefer=intent.prefer,
                )
            if not members:
                specs = resolve_members(
                    None,
                    max_members=intent.max_members,
                    prefer=intent.prefer,
                    role="advisor",
                )
                members = [s.id for s in specs]
            result["result"] = Council().run(
                intent.subject or intent.raw,
                models=members or None,
            )
            result["executed"] = True
            return result

        if action == "cli_run":
            from .config import Config
            from .external_cli import ExternalCLITool

            cfg = Config()
            name = intent.model or "gemini"
            cli_model = None
            if name.startswith("cli:"):
                name = name[4:]
            if "@" in name:
                name, cli_model = name.split("@", 1)
            auto = not cfg.require_human_approval
            tool = ExternalCLITool(
                dry_run=intent.dry_run or cfg.use_mock,
                auto_approve=auto,
            )
            env = tool.run(
                name,
                intent.subject or intent.raw,
                approve=auto,
                cli_model=cli_model,
            )
            result["result"] = env.to_dict() if hasattr(env, "to_dict") else {"ok": env.ok}
            result["executed"] = True
            return result

        if action == "run":
            from .orchestrator import SuperAIOrchestrator

            orch = SuperAIOrchestrator()
            workers = list(intent.members) if intent.members else None
            if (intent.pick or "pick_workers" in intent.notes) and not workers:
                from .approval_tui import prompt_pick_from_catalog

                workers = prompt_pick_from_catalog(
                    title="Pick workers",
                    max_n=5,
                    prefer=intent.worker_prefer or intent.prefer,
                )
            forced = None
            if intent.model and not workers:
                forced = intent.model
            result["result"] = orch.run_task(
                task=intent.subject or intent.raw,
                forced_model=forced,
                verbose=verbose,
                workers=workers,
                worker_prefer=intent.worker_prefer,
            )
            result["executed"] = True
            return result

        result["ok"] = False
        result["error"] = f"Unknown action: {action}"
        return result
    except Exception as e:  # noqa: BLE001
        result["ok"] = False
        result["executed"] = False
        result["error"] = str(e)[:500]
        return result


def ask_superai(
    text: str,
    *,
    execute: bool = True,
    plan_only: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """One-shot NL entrypoint."""
    intent = parse_intent(text)
    return execute_intent(
        intent,
        execute=execute and not plan_only,
        verbose=verbose,
    )
