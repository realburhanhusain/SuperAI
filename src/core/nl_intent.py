"""
Universal natural-language front door for SuperAI (Claude Code / Gemini / Codex style).

Any user phrase is understood as either:
  - a specialized SuperAI product action (review, council, doctor, memory, …), or
  - a general agent task executed by the orchestrator (`run`)

Entry points:
  superai ask "…"
  superai ask                 # interactive REPL
  superai chat "…"            # routes product intents here
"""

from __future__ import annotations

import re
import shlex
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


# Specialized product actions + universal agent run
ACTIONS = (
    "members",
    "review",
    "advise",
    "council",
    "run",  # universal agent (default)
    "discover",
    "doctor",
    "cli_run",
    "plan",
    "tdd",
    "pr_review",
    "memory_search",
    "palace",
    "backup",
    "budget",
    "host_tools",
    "install",
    "debate",
    "search_web",
    "github",
    "goals",
    "bakeoff",
    "agent_tui",
    "profile",
    "plugin_catalog",
    "status",
    "smoke_preflight",
    "voice",
    "progress",
    "v6_status",
    "shell",
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
    model: Optional[str] = None
    confidence: float = 0.0
    raw: str = ""
    planned_command: str = ""
    notes: List[str] = field(default_factory=list)
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
    "deepseek-chat",
    "qwen2.5-coder",
    "qwen2.5-72b",
    "kimi",
    "kimi-k2",
    "glm-4",
    "glm-4-flash",
    "minimax-text",
    "gemma2-9b",
    "llama3.2",
    "nvidia-llama-3.1-70b-instruct",
    "nvidia-nemotron-mini",
    "openrouter-auto",
    "lmstudio-local",
    "vllm-local",
)

# (action, confidence, regex) — first match wins (order = priority)
_ACTION_RULES: List[Tuple[str, float, str]] = [
    ("help", 0.95, r"\b(help|how do i|what can superai|commands?)\b"),
    (
        "members",
        0.93,
        r"\b(list|show|what|which).{0,48}\b(member|model|cli|available|provider)|"
        r"\bmembers\b|\bavailable (models?|clis?)\b|\bwhat can i use\b|"
        r"\bproviders?\b|\blist[- ]models\b",
    ),
    ("doctor", 0.92, r"\b(doctor|health check|diagnose|is (superai|everything) (ok|healthy))\b"),
    (
        "discover",
        0.9,
        r"\b(discover|what.?s installed|environment|scan (path|clis?))\b",
    ),
    ("install", 0.9, r"\b(install (superai|postgres|host tools)|setup wizard|onboard)\b"),
    ("host_tools", 0.88, r"\b(host[- ]tools|check (git|docker|rclone)|tool matrix)\b"),
    ("budget", 0.9, r"\b(budget|spend limit|cost limit|how much (have i|did i) spend)\b"),
    ("backup", 0.9, r"\b(backup|restore|export (my )?profile)\b"),
    # N202 expanded command map
    (
        "plugin_catalog",
        0.93,
        r"\b(plugin[- ]catalog|plugin marketplace|browse plugins?|list plugins?|"
        r"marketplace plugins?)\b",
    ),
    (
        "voice",
        0.94,
        r"\b(voice status|voice (on|off)|voice (tts|stt)|/speak|/listen)\b",
    ),
    (
        "smoke_preflight",
        0.93,
        r"\b(smoke[- ]preflight|preflight|ready for live smoke)\b",
    ),
    (
        "v6_status",
        0.93,
        r"\b(v6[- ]status|improvement v6 status)\b",
    ),
    (
        "status",
        0.92,
        r"\b(show status|system status|spend status|cost status|"
        r"status with cost|status --cost|^status$)\b",
    ),
    (
        "progress",
        0.9,
        r"\b(show progress|progress snapshot|recent progress)\b",
    ),
    # S9: dedicated goals / bakeoff / agent-tui / profile intents
    (
        "goals",
        0.93,
        r"\b(goals? execute|run due goals|list goals|assistant goals?|daemon tick|"
        r"execute (due )?goals?)\b",
    ),
    (
        "bakeoff",
        0.92,
        r"\b(bake[- ]?off|model bakeoff|compare models|eval models)\b",
    ),
    (
        "agent_tui",
        0.93,
        r"\b(agent[- ]tui|open agent (ui|tui)|interactive agent)\b",
    ),
    (
        "profile",
        0.9,
        r"\b(use profile|set profile|switch profile|cheap mode|local[- ]only mode|"
        r"quality mode|permission (plan|yolo|ask|auto))\b",
    ),
    (
        "palace",
        0.88,
        r"\b(memory palace|palace (layout|browse)|wings?|rooms?)\b",
    ),
    (
        "memory_search",
        0.88,
        r"\b(search memory|remember|what do (we|you) know|recall|memory search)\b",
    ),
    ("pr_review", 0.91, r"\b(pr[- ]review|review (the )?(pr|pull request|diff|git diff))\b"),
    ("tdd", 0.9, r"\b(tdd|test[- ]driven|write tests (for|and)|red green refactor)\b"),
    (
        "plan",
        0.9,
        r"\b((make|show|create|write)\s+(me\s+)?(a\s+)?plan|"
        r"plan\s+(only|this|the|a|an|my|for)|"
        r"break\s+down|decompose)\b",
    ),
    ("debate", 0.88, r"\b(debate|argue (both|two) sides)\b"),
    ("search_web", 0.88, r"\b(search (the )?web|web search|look up online|duckduckgo)\b"),
    ("github", 0.88, r"\b(github|list (issues|prs)|create (issue|pr)|open prs?)\b"),
    (
        "council",
        0.91,
        r"\b(council|vote on|multi[- ]model (debate|vote|discuss)|convene)\b",
    ),
    (
        "advise",
        0.9,
        r"\b(advise|advice|should we|recommend|what do you think|"
        r"advisor board|ask advisors)\b",
    ),
    (
        "review",
        0.91,
        r"\b(code\s+review|\breview\b|critique|look over)\b",
    ),
    (
        "cli_run",
        0.86,
        r"\b(cli[- ]run|run\s+(on|via|with)\s+(claude|gemini|grok|codex|aider)|"
        r"(ask|tell)\s+(claude|gemini|grok|codex|aider)\b)",
    ),
    (
        "run",
        0.84,
        r"\b(implement|build|fix|create|write|refactor|run\s+task|"
        r"do\s+this|work\s+on|workers?|add feature|ship)\b",
    ),
]


def parse_intent(text: str) -> SuperAIIntent:
    """NL → SuperAIIntent. Unknown phrases become universal agent `run`."""
    raw = (text or "").strip()
    low = raw.lower()
    intent = SuperAIIntent(action="run", raw=raw, confidence=0.5, notes=["agent_default"])

    if not raw:
        intent.action = "help"
        intent.confidence = 1.0
        intent.notes = []
        intent.planned_command = "superai ask --help"
        return intent

    # Arbitrary OS shell (explicit NL markers) — high priority
    try:
        from .os_shell import parse_shell_from_nl

        shell_cmd = parse_shell_from_nl(raw)
        if shell_cmd:
            intent.action = "shell"
            intent.subject = shell_cmd
            intent.confidence = 0.96
            intent.notes = ["os_shell"]
            intent.dry_run = True
            intent.planned_command = format_planned_command(intent)
            return intent
    except Exception:
        pass

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

    # Profile / permission from NL (Sprint D S9)
    if re.search(r"\b(cheap mode|use cheap|profile cheap)\b", low):
        intent.extras["run_profile"] = "cheap"
        intent.notes.append("profile:cheap")
    elif re.search(r"\b(local[- ]only|profile local)\b", low):
        intent.extras["run_profile"] = "local-only"
        intent.notes.append("profile:local-only")
    elif re.search(r"\b(quality mode|profile quality)\b", low):
        intent.extras["run_profile"] = "quality"
        intent.notes.append("profile:quality")
    if re.search(r"\b(yolo|auto[- ]approve all)\b", low):
        intent.extras["permission_mode"] = "yolo"
        intent.notes.append("permission:yolo")
    elif re.search(r"\b(plan only|permission plan|dry[- ]run only)\b", low):
        intent.extras["permission_mode"] = "plan"
        intent.dry_run = True
        intent.notes.append("permission:plan")

    intent.members = _extract_members(raw)
    intent.model = intent.members[0] if len(intent.members) == 1 else None

    matched = False
    for action, conf, pattern in _ACTION_RULES:
        if re.search(pattern, low):
            intent.action = action
            intent.confidence = conf
            intent.notes = []
            matched = True
            break

    if not matched:
        # Universal agent: any free-form request (Claude Code style)
        intent.action = "run"
        intent.subject = raw
        intent.confidence = 0.72
        intent.notes = ["universal_agent"]

    # Subject extraction per action
    if intent.action == "members":
        intent.only_available = "all" not in low and "every" not in low
    elif intent.action == "council":
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
    elif intent.action == "advise":
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
    elif intent.action == "review":
        intent.subject = _extract_subject(
            raw,
            drop_prefixes=(
                r"(please\s+)?(code\s+)?review\s+(the|this|my)?",
                r"critique\s+(the|this)?",
                r"look\s+over\s+(the|this)?",
            ),
        )
    elif intent.action == "cli_run":
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
    elif intent.action == "run":
        if "universal_agent" not in intent.notes and "agent_default" not in intent.notes:
            intent.subject = _extract_subject(
                raw,
                drop_prefixes=(
                    r"(please\s+)?(run|implement|build|fix|create|write|refactor)\s+",
                    r"work\s+on\s+",
                    r"do\s+this\s*:\s*",
                ),
            )
        else:
            intent.subject = raw
        if intent.pick:
            intent.notes.append("pick_workers")
        if intent.worker_prefer is None:
            intent.worker_prefer = intent.prefer
    elif intent.action in {
        "plan",
        "tdd",
        "memory_search",
        "search_web",
        "debate",
        "pr_review",
    }:
        intent.subject = _extract_subject(
            raw,
            drop_prefixes=(
                r"(please\s+)?(plan|tdd|search memory|search (the )?web|"
                r"debate|pr[- ]review|review (the )?diff)\s+(for|about|on)?",
                r"what do (we|you) know about\s+",
                r"remember\s+",
            ),
        )
    elif intent.action == "github":
        intent.subject = raw
        if re.search(r"\bissues?\b", low):
            intent.extras["github_action"] = "issues"
        elif re.search(r"\bprs?|pull requests?\b", low):
            intent.extras["github_action"] = "prs"
        else:
            intent.extras["github_action"] = "status"

    if intent.action == "goals":
        intent.subject = intent.subject or raw
    elif intent.action == "bakeoff":
        intent.subject = _extract_subject(
            raw,
            drop_prefixes=(
                r"(please\s+)?(bake[- ]?off|compare models|eval models)\s*(on|for|with)?",
            ),
        ) or raw
    elif intent.action == "agent_tui":
        intent.subject = ""
    elif intent.action == "profile":
        intent.subject = raw

    if not intent.subject and intent.action not in {
        "members",
        "discover",
        "doctor",
        "help",
        "backup",
        "budget",
        "host_tools",
        "install",
        "palace",
        "goals",
        "agent_tui",
        "profile",
    }:
        intent.subject = raw

    intent.planned_command = format_planned_command(intent)
    return intent


def _extract_members(text: str) -> List[str]:
    found: List[str] = []
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
    for m in re.finditer(
        r"\b([a-z][a-z0-9]+(?:-[a-z0-9.]+){1,4})\b", text, flags=re.I
    ):
        tok = m.group(1)
        low = tok.lower()
        if low in _CLI_NAMES:
            continue
        if any(
            k in low
            for k in (
                "gpt",
                "claude",
                "gemini",
                "grok",
                "o3",
                "o4",
                "deepseek",
                "qwen",
                "kimi",
                "glm",
                "minimax",
                "gemma",
                "llama",
                "nvidia",
                "nemotron",
                "openrouter",
            )
        ):
            if tok not in found and f"cli:{tok}" not in found:
                found.append(tok)
    # vendor shorthand → preferred registry name
    vendor_map = {
        r"\bdeepseek\b": "deepseek-chat",
        r"\bkimi\b": "kimi-k2",
        r"\bglm\b": "glm-4",
        r"\bminimax\b": "minimax-text",
        r"\bgemma\b": "gemma2-9b",
        r"\bnvidia\b": "nvidia-llama-3.1-70b-instruct",
        r"\bopenrouter\b": "openrouter-auto",
        r"\bollama\b": "llama3.2",
    }
    for pat, reg_name in vendor_map.items():
        if re.search(pat, text, flags=re.I):
            if reg_name not in found and not any(
                reg_name.split("-")[0] in x for x in found if not x.startswith("cli:")
            ):
                # only add if no more specific already present
                if not any(reg_name in x or x.startswith(reg_name.split("-")[0]) for x in found):
                    found.append(reg_name)
    return found[:8]


def _extract_subject(text: str, drop_prefixes: Sequence[str] = ()) -> str:
    s = text.strip()
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
    s = re.sub(
        r"\b(and\s+)?(let me pick|interactively|prefer\s+\w+|dry[- ]?run|live)\b.*$",
        "",
        s,
        flags=re.I,
    ).strip(" :,-")
    return s or text.strip()


def format_planned_command(intent: SuperAIIntent) -> str:
    a = intent.action
    q = lambda s: shlex.quote(s or "")  # noqa: E731

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
    if a == "doctor":
        return "superai doctor"
    if a == "install":
        return "superai install"
    if a == "host_tools":
        return "superai host-tools check"
    if a == "budget":
        return "superai budget show"
    if a == "backup":
        return "superai backup"
    if a == "palace":
        return "superai memory-palace layout"
    if a == "memory_search":
        return f"superai memory-palace search {q(intent.subject)}"
    if a == "plan":
        return f"superai plan {q(intent.subject)}"
    if a == "tdd":
        return f"superai tdd {q(intent.subject)}"
    if a == "pr_review":
        return "superai pr-review"
    if a == "debate":
        return f"superai debate {q(intent.subject)}"
    if a == "search_web":
        return f'superai search-web {q(intent.subject)}'
    if a == "github":
        act = intent.extras.get("github_action") or "status"
        return f"superai github {act}"
    if a == "help":
        return "superai ask --help"
    if a == "goals":
        if "list" in (intent.raw or "").lower():
            return "superai goals list"
        if "tick" in (intent.raw or "").lower() or "daemon" in (intent.raw or "").lower():
            return "superai goals tick"
        return "superai goals execute"
    if a == "bakeoff":
        models = ",".join(intent.members) if intent.members else "gpt-4o,deepseek-chat"
        return f"superai bakeoff {q(intent.subject or 'hello')} -m {models}"
    if a == "agent_tui":
        return "superai agent-tui"
    if a == "profile":
        prof = intent.extras.get("run_profile") or "balanced"
        return f"superai profile use {prof}"
    if a == "plugin_catalog":
        subj = (intent.subject or "").strip()
        if subj:
            return f"superai plugin-catalog -q {q(subj)}"
        # allow "plugin catalog memory" subject via raw
        raw_l = (intent.raw or "").lower()
        for token in ("memory", "security", "voice", "data"):
            if token in raw_l:
                return f"superai plugin-catalog -q {token}"
        return "superai plugin-catalog --status"
    if a == "status":
        if "cost" in (intent.raw or "").lower() or "spend" in (intent.raw or "").lower():
            return "superai status --cost"
        return "superai status --cost"
    if a == "smoke_preflight":
        return "superai smoke-preflight"
    if a == "voice":
        return "superai voice status"
    if a == "progress":
        return "superai progress"
    if a == "v6_status":
        return "superai v6-status"
    if a == "superai_agent":
        role = intent.extras.get("agent_role") or "build"
        return f"superai agent {q(intent.subject or intent.raw)} --agent {role} --permission plan"
    if a == "shell":
        return f"superai shell {q(intent.subject or intent.raw)}"
    if a == "review":
        cmd = ["superai", "review", q(intent.subject)]
        if intent.members:
            cmd += ["-m", ",".join(intent.members)]
        if intent.pick:
            cmd.append("--pick")
        cmd += ["--prefer", intent.prefer]
        cmd.append("--live" if intent.live else "--dry-run")
        return " ".join(cmd)
    if a == "advise":
        cmd = ["superai", "advise", q(intent.subject)]
        if intent.members:
            cmd += ["-m", ",".join(intent.members)]
        if intent.pick:
            cmd.append("--pick")
        cmd += ["--prefer", intent.prefer]
        cmd.append("--live" if intent.live else "--dry-run")
        return " ".join(cmd)
    if a == "council":
        cmd = ["superai", "council", q(intent.subject)]
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
        cmd = ["superai", "cli-run", name, q(intent.subject)]
        if intent.dry_run:
            cmd.append("--dry-run")
        return " ".join(cmd)
    # run / universal agent
    cmd = ["superai", "run", q(intent.subject or intent.raw)]
    if intent.members:
        cmd += ["--workers", ",".join(intent.members)]
    if intent.pick or "pick_workers" in intent.notes:
        cmd.append("--pick-workers")
    if intent.worker_prefer:
        cmd += ["--worker-prefer", intent.worker_prefer]
    if intent.model and not intent.members:
        cmd += ["-m", intent.model]
    return " ".join(cmd)


def execute_intent(
    intent: SuperAIIntent,
    *,
    execute: bool = True,
    verbose: bool = False,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "ok": True,
        "intent": intent.to_dict(),
        "planned_command": intent.planned_command or format_planned_command(intent),
        "executed": False,
        "result": None,
        "agent_mode": intent.action == "run",
    }
    if not execute:
        try:
            from .result_contract import apply_contract

            apply_contract(result, mock=True, dry_run=True, ok=True)
            result["status"] = "planned"
        except Exception:
            pass
        return result

    # Apply NL-derived profile/permission
    try:
        from .config import Config
        from .run_profiles import apply_profile_to_config
        from .permission_mode import normalize_mode

        cfg = Config()
        if intent.extras.get("run_profile"):
            apply_profile_to_config(cfg, str(intent.extras["run_profile"]))
        if intent.extras.get("permission_mode"):
            cfg.config["permission_mode"] = normalize_mode(
                str(intent.extras["permission_mode"])
            )
    except Exception:
        pass

    action = intent.action
    try:
        # DoD-strict: front-door policy re-routes free-form run/default tasks
        if action in {"run", "unknown"} or "universal_agent" in (intent.notes or []):
            try:
                from .front_door import choose_path

                path = choose_path(intent.subject or intent.raw)
                intent.extras["front_door"] = path
                p = path.get("path")
                if p == "board" and action == "run":
                    intent.action = "review"
                    action = "review"
                elif p == "agent":
                    # Prefer coding agent runtime over orchestrator for code/plan
                    intent.extras["agent_role"] = path.get("agent_role") or "build"
                    action = "superai_agent"
                    intent.action = "superai_agent"
                elif p == "ask" and action == "run":
                    # keep run for simple tasks via orchestrator/tools is heavy;
                    # light path still agent ask role
                    intent.extras["agent_role"] = "ask"
                    action = "superai_agent"
                    intent.action = "superai_agent"
                elif p == "run":
                    action = "run"
                    intent.action = "run"
            except Exception:
                pass

        handler = _HANDLERS.get(action)
        if handler is None and action == "superai_agent":
            handler = _h_superai_agent
        if handler is None:
            # Safety: anything unmapped → universal agent run
            handler = _HANDLERS["run"]
            intent.action = "run"
            intent.subject = intent.subject or intent.raw
        out = handler(intent, verbose=verbose)
        result["result"] = out
        result["executed"] = True
        result["agent_mode"] = action == "run" or "universal_agent" in intent.notes
        # Bubble contract fields from nested result
        if isinstance(out, dict):
            for k in (
                "mock",
                "dry_run",
                "tokens",
                "estimated_cost_usd",
                "model_chain",
                "members",
                "memory_ids",
                "status",
            ):
                if k in out and k not in result:
                    result[k] = out[k]
            if "ok" in out:
                result["ok"] = bool(out["ok"])
        try:
            from .config import Config
            from .result_contract import apply_contract

            cfg = Config()
            apply_contract(
                result,
                mock=bool(result.get("mock", cfg.use_mock)),
                dry_run=bool(result.get("dry_run", intent.dry_run)),
                ok=bool(result.get("ok", True)),
            )
        except Exception:
            result.setdefault("contract", "superai.result.v1")
        return result
    except Exception as e:  # noqa: BLE001
        result["ok"] = False
        result["executed"] = False
        result["error"] = str(e)[:500]
        try:
            from .result_contract import apply_contract

            apply_contract(result, mock=False, dry_run=False, ok=False)
            result["status"] = "error"
        except Exception:
            pass
        return result


def _h_help(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    return {
        "message": (
            "SuperAI understands natural language like Claude Code / Gemini / Codex. "
            "Say what you want; specialized features are auto-routed, everything else "
            "runs as an agentic task."
        ),
        "examples": [
            "list available models and clis",
            "review the auth design with gpt-4o and gemini",
            "advise should we ship tonight",
            "council on architecture let me pick",
            "implement rate limiting",
            "run doctor / health check",
            "search memory for postgres setup",
            "plan a FastAPI service",
            "tdd for the login form",
            "pr-review the last commit",
            "what should I refactor in the orchestrator?",  # universal agent
        ],
        "tip": 'superai ask "…"   or   superai ask   # interactive REPL',
    }


def _h_members(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .member_selection import list_selectable_members

    if intent.pick:
        from .approval_tui import prompt_pick_from_catalog

        return {
            "selected": prompt_pick_from_catalog(
                title="Select members",
                max_n=intent.max_members,
                only_available=intent.only_available,
                prefer=intent.prefer,
            )
        }
    return list_selectable_members(
        only_available=intent.only_available,
        with_cli_models=True,
        live_cli_models=bool(intent.live),
    )


def _h_discover(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .discovery import discover_environment

    return discover_environment()


def _h_doctor(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .doctor import run_doctor

    return run_doctor(quick=True)


def _h_board(mode: str) -> Callable[..., Dict[str, Any]]:
    def _inner(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
        from .multi_cli_advisory import multi_cli_board

        members = list(intent.members)
        if intent.pick and not members:
            from .approval_tui import prompt_pick_from_catalog

            members = prompt_pick_from_catalog(
                title=f"Pick {mode} board",
                max_n=intent.max_members,
                prefer=intent.prefer,
            )
        return multi_cli_board(
            intent.subject or intent.raw,
            mode=mode,
            members=members or None,
            max_clis=intent.max_members,
            dry_run=intent.dry_run,
            approve=True,
            prefer=intent.prefer,
        )

    return _inner


def _h_council(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
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
    return Council().run(intent.subject or intent.raw, models=members or None)


def _h_cli_run(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
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
    data = env.to_dict() if hasattr(env, "to_dict") else {"ok": getattr(env, "ok", False)}
    try:
        from .result_contract import apply_contract

        return apply_contract(
            data if isinstance(data, dict) else {"payload": data},
            mock=bool(cfg.use_mock),
            dry_run=bool(intent.dry_run or cfg.use_mock),
            members=[f"cli:{name}"],
            ok=bool(getattr(env, "ok", data.get("ok") if isinstance(data, dict) else False)),
        )
    except Exception:
        return data


def _h_run(intent: SuperAIIntent, *, verbose: bool = False, **_: Any) -> Dict[str, Any]:
    """Universal agentic path — tool protocol first for code-like tasks, else orchestrator."""
    task = intent.subject or intent.raw
    # Prefer model tool loop for short coding requests
    low = (task or "").lower()
    if any(
        k in low
        for k in (
            "read file",
            "edit ",
            "fix ",
            "implement",
            "refactor",
            "write ",
            "grep ",
            "diff",
        )
    ):
        try:
            from .tool_protocol import agent_with_tools

            forced = intent.model or (
                intent.members[0] if intent.members else None
            )
            tool_out = agent_with_tools(
                task,
                model=forced,
                max_rounds=2,
            )
            if tool_out.get("tool_rounds", 0) > 0 or tool_out.get("ok"):
                return tool_out
        except Exception:
            pass

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
    return orch.run_task(
        task=task,
        forced_model=forced,
        verbose=verbose,
        workers=workers,
        worker_prefer=intent.worker_prefer,
    )


def _h_plan(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .model_caller import ModelCaller
    from .model_registry import ModelRegistry
    from .model_router import ModelRouter
    from .task_planner import TaskPlanner

    reg = ModelRegistry()
    planner = TaskPlanner(ModelRouter(reg), model_caller=ModelCaller(use_mock=True, registry=reg))
    steps = planner.create_plan(intent.subject or intent.raw)
    return {
        "ok": True,
        "task": intent.subject or intent.raw,
        "steps": [
            {
                "step_id": getattr(s, "step_id", i + 1),
                "description": getattr(s, "description", str(s)),
                "role": getattr(s, "role", None),
            }
            for i, s in enumerate(steps or [])
        ],
    }


def _h_tdd(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .tdd_loop import tdd_cycle

    return tdd_cycle(intent.subject or intent.raw)


def _h_pr_review(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .config import Config
    from .pr_review import get_git_diff, review_diff

    cfg = Config()
    diff = get_git_diff("HEAD~1")
    if not (diff or "").strip():
        return {"ok": False, "error": "empty_diff", "hint": "No git diff for HEAD~1"}
    return review_diff(
        diff,
        use_mock=cfg.use_mock,
        use_clis=True,
        dry_run=intent.dry_run or cfg.use_mock,
    )


def _h_memory_search(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .memory_palace import MemoryPalace

    q = intent.subject or intent.raw
    palace = MemoryPalace()
    hits: Any = []
    if hasattr(palace, "query_semantic"):
        hits = palace.query_semantic(q, n_results=8)
    elif hasattr(palace, "search"):
        hits = palace.search(q, n_results=8)
    return {"ok": True, "query": q, "hits": hits}


def _h_palace(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .memory_palace import MemoryPalace

    palace = MemoryPalace()
    layout = palace.palace_layout() if hasattr(palace, "palace_layout") else {}
    return {"ok": True, "layout": layout}


def _h_backup(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .backup_manager import BackupManager

    mgr = BackupManager()
    try:
        if hasattr(mgr, "create_backup"):
            path = mgr.create_backup(quiet=True)
            return {"ok": True, "backup_path": str(path)}
        if hasattr(mgr, "backup"):
            return {"ok": True, "result": mgr.backup()}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300], "hint": "superai backup"}
    return {"ok": False, "hint": "superai backup"}


def _h_budget(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .budget import BudgetGuard

    return BudgetGuard().snapshot()


def _h_host_tools(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from . import host_tools as ht

    try:
        if hasattr(ht, "checklist"):
            return ht.checklist(profile="core")
        if hasattr(ht, "list_catalog"):
            return {"ok": True, "catalog": ht.list_catalog(profile="core")}
    except TypeError:
        try:
            return ht.checklist()  # type: ignore[misc]
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)[:300]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300]}
    return {"ok": True, "hint": "superai host-tools check --profile core"}


def _h_install(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    return {
        "ok": True,
        "message": "Run interactive install wizard",
        "command": "superai install",
        "hint": "superai install --non-interactive --skip-postgres",
    }


def _h_debate(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .agentic import AgenticWorkflows

    return AgenticWorkflows().debate(
        intent.subject or intent.raw,
        models=intent.members or None,
    )


def _h_search_web(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    try:
        from .ecosystem import EcosystemHub

        hub = EcosystemHub()
        if hasattr(hub, "web_search"):
            return hub.web_search(intent.subject or intent.raw)
    except Exception:
        pass
    return {
        "ok": True,
        "query": intent.subject or intent.raw,
        "note": "Use: superai search-web \"query\"",
        "planned": format_planned_command(intent),
    }


def _h_github(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    try:
        from .github_api import GitHubClient

        client = GitHubClient()
        act = intent.extras.get("github_action") or "status"
        if act == "issues" and hasattr(client, "list_issues"):
            return {"ok": True, "issues": client.list_issues()}
        if act == "prs" and hasattr(client, "list_prs"):
            return {"ok": True, "prs": client.list_prs()}
        if hasattr(client, "status"):
            return client.status()
        return {"ok": True, "action": act, "hint": f"superai github {act}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300], "hint": "superai github status"}


def _h_goals(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    """S9: goals list / execute / daemon tick."""
    from .assistant_goals import GoalStore

    store = GoalStore()
    low = (intent.raw or "").lower()
    if "list" in low:
        goals = store.list(None)
        return {"ok": True, "goals": goals, "count": len(goals)}
    if "tick" in low or "daemon" in low:
        return store.daemon_tick(execute=False, notify=False, schedule_due=True)
    return store.execute_due(max_goals=2, use_ask=True)


def _h_bakeoff(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    """S9: model bakeoff with report."""
    from .config import Config
    from .model_bakeoff import bakeoff

    cfg = Config()
    models = list(intent.members) or ["gpt-4o", "deepseek-chat"]
    return bakeoff(
        intent.subject or intent.raw or "Reply with pong",
        models,
        use_mock=True if intent.dry_run else bool(cfg.use_mock),
        report=True,
    )


def _h_agent_tui(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    """S9: open agent TUI (or plan-only description)."""
    if intent.dry_run and not intent.live:
        return {
            "ok": True,
            "dry_run": True,
            "message": "Would start: superai agent",
            "command": "superai agent",
        }
    try:
        from .superai_agent.tui import run_superai_agent_tui

        run_superai_agent_tui()
        return {"ok": True, "message": "agent session ended"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300], "command": "superai agent"}


def _h_superai_agent(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    """Front-door coding agent one-shot (DoD-strict routing)."""
    from .spend_guard import budget_precheck, ensure_public_result
    from .superai_agent.runtime import AgentRuntime

    role = str(intent.extras.get("agent_role") or "build")
    if not intent.live and intent.dry_run:
        # still allow mock agent work in dry_run for usefulness
        pass
    block = budget_precheck(estimated_usd=0.12 if intent.live else 0.02, tokens=600)
    if block.get("blocked"):
        return block
    rt = AgentRuntime(use_mock=not intent.live)
    out = rt.run(
        intent.subject or intent.raw,
        agent=role,
        model=intent.model,
        permission=str(intent.extras.get("permission_mode") or ("plan" if intent.dry_run else "ask")),
        max_rounds=2 if role == "ask" else 3,
    )
    data = out.to_dict()
    data["front_door"] = intent.extras.get("front_door")
    return ensure_public_result(
        data,
        mock=bool(data.get("mock", not intent.live)),
        dry_run=bool(intent.dry_run and not intent.live),
        ok=bool(data.get("ok", True)),
    )


def _h_profile(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    """S9: apply run profile / permission from NL."""
    from .config import Config
    from .permission_mode import normalize_mode
    from .run_profiles import apply_profile_to_config, get_profile

    cfg = Config()
    prof = intent.extras.get("run_profile") or "balanced"
    applied = apply_profile_to_config(cfg, str(prof))
    if intent.extras.get("permission_mode"):
        cfg.config["permission_mode"] = normalize_mode(
            str(intent.extras["permission_mode"])
        )
    return {
        "ok": True,
        "run_profile": applied.get("run_profile") or prof,
        "permission_mode": cfg.config.get("permission_mode")
        or intent.extras.get("permission_mode"),
        "profile": get_profile(str(prof)),
    }


def _h_plugin_catalog(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .plugin_catalog import browse_catalog, marketplace_status

    raw = (intent.raw or "").lower()
    for token in ("memory", "security", "voice", "data", "messaging"):
        if token in raw:
            return browse_catalog(query=token)
    if intent.subject:
        return browse_catalog(query=intent.subject)
    return marketplace_status()


def _h_status(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .budget import BudgetGuard
    from .config import Config

    cfg = Config()
    return {
        "ok": True,
        "mock_mode": cfg.use_mock,
        "budget": BudgetGuard().snapshot(),
        "planned": format_planned_command(intent),
    }


def _h_smoke_preflight(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .smoke_preflight import smoke_preflight

    return smoke_preflight()


def _h_voice(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .voice_io import status as voice_status

    return voice_status()


def _h_progress(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    try:
        from .progress_events import get_progress_bus

        bus = get_progress_bus()
        if hasattr(bus, "recent"):
            return {"ok": True, "events": bus.recent(20)}
    except Exception:
        pass
    return {"ok": True, "events": [], "hint": "superai progress"}


def _h_v6_status(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .v6_phase_status import phase_report

    return phase_report()


def _h_shell(intent: SuperAIIntent, **_: Any) -> Dict[str, Any]:
    from .os_shell import run_shell

    cmd = intent.subject or intent.raw
    return run_shell(cmd, dry_run=bool(intent.dry_run) and not intent.live)


_HANDLERS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "help": _h_help,
    "members": _h_members,
    "discover": _h_discover,
    "doctor": _h_doctor,
    "review": _h_board("review"),
    "advise": _h_board("advise"),
    "council": _h_council,
    "cli_run": _h_cli_run,
    "run": _h_run,
    "plan": _h_plan,
    "tdd": _h_tdd,
    "pr_review": _h_pr_review,
    "memory_search": _h_memory_search,
    "palace": _h_palace,
    "backup": _h_backup,
    "budget": _h_budget,
    "host_tools": _h_host_tools,
    "install": _h_install,
    "debate": _h_debate,
    "search_web": _h_search_web,
    "github": _h_github,
    "goals": _h_goals,
    "bakeoff": _h_bakeoff,
    "agent_tui": _h_agent_tui,
    "superai_agent": _h_superai_agent,
    "profile": _h_profile,
    "plugin_catalog": _h_plugin_catalog,
    "status": _h_status,
    "smoke_preflight": _h_smoke_preflight,
    "voice": _h_voice,
    "progress": _h_progress,
    "v6_status": _h_v6_status,
    "shell": _h_shell,
}


def ask_superai(
    text: str,
    *,
    execute: bool = True,
    plan_only: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """One-shot NL entrypoint (universal agent + specialized routes)."""
    intent = parse_intent(text)
    return execute_intent(
        intent,
        execute=execute and not plan_only,
        verbose=verbose,
    )


def interactive_repl(
    *,
    execute: bool = True,
    verbose: bool = False,
    print_fn: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Interactive SuperAI session (Claude Code / Gemini style).
    Type natural language; 'exit' / 'quit' / Ctrl-C to leave.
    """
    out = print_fn or print
    from .approval_tui import is_interactive

    out("SuperAI agent — natural language (type help, exit to quit)")
    out("Examples: list models | review X | implement Y | doctor | plan Z")
    if not is_interactive():
        out("(non-interactive: no REPL)")
        return
    while True:
        try:
            line = input("superai> ").strip()
        except (EOFError, KeyboardInterrupt):
            out("")
            break
        if not line:
            continue
        if line.lower() in {"exit", "quit", "q", ":q"}:
            break
        if line.lower() in {"help", "?"}:
            r = ask_superai("help", execute=True)
            out(str((r.get("result") or {}).get("message") or r))
            for ex in (r.get("result") or {}).get("examples") or []:
                out(f"  · {ex}")
            continue
        res = ask_superai(line, execute=execute, verbose=verbose)
        out(f"→ {res.get('planned_command')}")
        if res.get("error"):
            out(f"Error: {res['error']}")
        elif res.get("result") is not None:
            # compact preview
            import json

            try:
                preview = json.dumps(res.get("result"), default=str)[:2500]
            except Exception:
                preview = str(res.get("result"))[:2500]
            out(preview)
