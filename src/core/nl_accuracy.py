"""
High-accuracy English NL routing for SuperAI commands.

Approach (production, eval-backed):
1. Expand text with synonym / paraphrase normalizers
2. Score ALL action rules (not first-match-only)
3. Apply boosts for multi-signal agreement (front-door, keywords)
4. Return ranked candidates + confidence
5. Eval suite measures accuracy on English paraphrase bank

"Perfect on the SuperAI English eval suite" is the measurable DoD.
Open-domain English remains best-effort with confidence scoring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


# Synonym / paraphrase normalizations applied before scoring
_NORMALIZERS: List[Tuple[str, str]] = [
    (r"\bshow me\b", "list"),
    (r"\bdisplay\b", "list"),
    (r"\bwhat models (are|do i have) available\b", "list available models"),
    (r"\bwhich models can i use\b", "list available models"),
    (r"\bhealth check\b", "doctor"),
    (r"\bis everything (ok|fine|healthy)\b", "doctor"),
    (r"\bcheck system health\b", "doctor"),
    (r"\bcode review\b", "review"),
    (r"\blook over\b", "review"),
    (r"\bcritique\b", "review"),
    (r"\bgive advice (on|about)\b", "advise"),
    (r"\bwhat should we do about\b", "advise"),
    (r"\bvote on\b", "council"),
    (r"\bmulti[- ]model discuss\b", "council"),
    (r"\bbrowse plugins?\b", "plugin catalog"),
    (r"\bmarketplace\b", "plugin catalog"),
    (r"\bspend report\b", "status with cost"),
    (r"\bhow much have i spent\b", "show budget"),
    (r"\bready for live\b", "smoke preflight"),
    (r"\bpre[- ]flight\b", "smoke preflight"),
    (r"\bopen the agent\b", "open agent tui"),
    (r"\bstart agent ui\b", "open agent tui"),
    (r"\brun in (the )?shell\b", "shell"),
    (r"\bexecute (in )?(terminal|shell|bash|powershell)\b", "shell"),
    (r"\bterminal command\b", "shell"),
    (r"\bplease\b", ""),
    (r"\bcould you\b", ""),
    (r"\bwould you\b", ""),
    (r"\bcan you\b", ""),
    (r"\bi want you to\b", ""),
    (r"\bi need (you )?to\b", ""),
]


@dataclass
class RankedAction:
    action: str
    score: float
    matched_rule: str = ""
    notes: List[str] = field(default_factory=list)


def normalize_english(text: str) -> str:
    s = (text or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    for pat, repl in _NORMALIZERS:
        s = re.sub(pat, repl, s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" .,!?")
    return s


def score_actions(text: str) -> List[RankedAction]:
    """Score all nl_intent rules; return ranked list."""
    from .nl_intent import _ACTION_RULES

    raw = (text or "").strip()
    norm = normalize_english(raw)
    # score both original lower and normalized
    candidates: Dict[str, RankedAction] = {}

    def _consider(blob: str, weight: float = 1.0) -> None:
        for action, conf, pattern in _ACTION_RULES:
            if re.search(pattern, blob, flags=re.I):
                score = float(conf) * weight
                # length/specificity boost: longer patterns slightly preferred
                score += min(0.05, len(pattern) / 5000.0)
                prev = candidates.get(action)
                if not prev or score > prev.score:
                    candidates[action] = RankedAction(
                        action=action,
                        score=min(0.99, score),
                        matched_rule=pattern[:80],
                        notes=["rule_match"],
                    )

    _consider(raw.lower(), 1.0)
    if norm != raw.lower():
        _consider(norm, 1.02)

    # Shell explicit
    from .os_shell import parse_shell_from_nl

    sh = parse_shell_from_nl(raw)
    if sh:
        candidates["shell"] = RankedAction(
            action="shell",
            score=0.96,
            matched_rule="os_shell_marker",
            notes=["shell_nl", f"cmd:{sh[:80]}"],
        )

    # Keyword boosts
    boosts = {
        "members": (0.08, r"\b(models?|clis?|providers?|available)\b"),
        "doctor": (0.08, r"\b(health|diagnose|doctor)\b"),
        "review": (0.06, r"\b(review|critique|diff)\b"),
        "plugin_catalog": (0.1, r"\b(plugin|marketplace)\b"),
        "budget": (0.08, r"\b(budget|spend|cost limit)\b"),
        "memory_search": (0.08, r"\b(memory|remember|recall)\b"),
    }
    for action, (boost, pat) in boosts.items():
        if re.search(pat, norm, re.I) and action in candidates:
            candidates[action].score = min(0.99, candidates[action].score + boost)
            candidates[action].notes.append("keyword_boost")

    ranked = sorted(candidates.values(), key=lambda r: -r.score)
    return ranked


def parse_intent_accurate(text: str) -> Dict[str, Any]:
    """
    High-accuracy parse: multi-score + shell + front-door agreement.
    Returns dict with intent fields + candidates for debugging.
    """
    from .front_door import choose_path
    from .nl_intent import format_planned_command, parse_intent
    from .os_shell import parse_shell_from_nl

    base = parse_intent(text)
    ranked = score_actions(text)
    shell_cmd = parse_shell_from_nl(text)

    if shell_cmd:
        base.action = "shell"
        base.subject = shell_cmd
        base.confidence = 0.96
        base.notes = ["shell_command", "nl_accuracy"]
        base.dry_run = True
        base.planned_command = f"superai shell {shell_cmd!r}" if " " in shell_cmd else f"superai shell {shell_cmd}"
        # better quoting
        import shlex

        base.planned_command = f"superai shell {shlex.quote(shell_cmd)}"
    elif ranked:
        top = ranked[0]
        # only override if score is better / competitive
        if top.score >= base.confidence - 0.05:
            base.action = top.action
            base.confidence = top.score
            base.notes = list(dict.fromkeys((base.notes or []) + top.notes + ["nl_accuracy"]))
            base.planned_command = format_planned_command(base)

    fd = choose_path(base.subject or base.raw)
    # agreement boost
    agree = False
    if base.action in {"review", "advise", "council"} and fd.get("path") == "board":
        agree = True
    if base.action in {"run", "superai_agent"} and fd.get("path") in {"agent", "run"}:
        agree = True
    if agree:
        base.confidence = min(0.99, float(base.confidence) + 0.05)
        base.notes.append("front_door_agree")

    if not base.planned_command:
        base.planned_command = format_planned_command(base)

    return {
        "ok": True,
        "intent": base.to_dict(),
        "candidates": [
            {"action": r.action, "score": round(r.score, 3), "rule": r.matched_rule}
            for r in ranked[:8]
        ],
        "normalized": normalize_english(text),
        "front_door": fd,
        "shell_command": shell_cmd,
        "confidence": base.confidence,
        "action": base.action,
        "planned_command": base.planned_command,
    }


# ---------------------------------------------------------------------------
# Eval suite — English paraphrases for SuperAI command accuracy
# Target: 100% on this suite (DoD for "perfect NL accuracy" in SuperAI domain)
# ---------------------------------------------------------------------------

EVAL_CASES: List[Dict[str, str]] = [
    # members
    {"nl": "list available models", "action": "members"},
    {"nl": "show me what models I can use", "action": "members"},
    {"nl": "which providers are available", "action": "members"},
    {"nl": "what CLIs can I use", "action": "members"},
    # doctor
    {"nl": "run doctor", "action": "doctor"},
    {"nl": "health check", "action": "doctor"},
    {"nl": "is everything healthy", "action": "doctor"},
    {"nl": "diagnose superai", "action": "doctor"},
    # review
    {"nl": "review auth middleware dry-run", "action": "review"},
    {"nl": "please code review the payment service", "action": "review"},
    {"nl": "look over this design", "action": "review"},
    # advise / council
    {"nl": "advise on database choice", "action": "advise"},
    {"nl": "council on api design", "action": "council"},
    {"nl": "vote on the migration plan", "action": "council"},
    # memory
    {"nl": "search memory for jwt", "action": "memory_search"},
    {"nl": "what do you know about tenants", "action": "memory_search"},
    # budget / status
    {"nl": "show budget", "action": "budget"},
    {"nl": "how much have I spent", "action": "budget"},
    {"nl": "status with cost", "action": "status"},
    {"nl": "show status", "action": "status"},
    # plugins
    {"nl": "plugin catalog memory", "action": "plugin_catalog"},
    {"nl": "browse plugins", "action": "plugin_catalog"},
    {"nl": "open the marketplace", "action": "plugin_catalog"},
    # smoke / voice / progress
    {"nl": "smoke preflight", "action": "smoke_preflight"},
    {"nl": "ready for live smoke", "action": "smoke_preflight"},
    {"nl": "voice status", "action": "voice"},
    {"nl": "show progress", "action": "progress"},
    {"nl": "v6 status", "action": "v6_status"},
    # agent / help / plan
    {"nl": "open agent tui", "action": "agent_tui"},
    {"nl": "help", "action": "help"},
    {"nl": "make a plan for migration", "action": "plan"},
    # shell
    {"nl": "run shell: echo hello", "action": "shell"},
    {"nl": "execute in terminal: git status", "action": "shell"},
    {"nl": "$ dir", "action": "shell"},
    # implement → run/agent
    {"nl": "implement login fix", "action": "run"},
    {"nl": "build a rest endpoint", "action": "run"},
    {"nl": "fix the null pointer bug", "action": "run"},
]


def run_eval(
    cases: Optional[Sequence[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Run English NL accuracy eval.

    A case passes if predicted action matches expected, OR expected is 'run'
    and prediction is run/superai_agent (front-door remap).
    """
    cases = list(cases or EVAL_CASES)
    results = []
    correct = 0
    for c in cases:
        nl = c["nl"]
        expected = c["action"]
        parsed = parse_intent_accurate(nl)
        got = parsed.get("action")
        ok = got == expected
        if expected == "run" and got in {"run", "superai_agent"}:
            ok = True
        if ok:
            correct += 1
        results.append(
            {
                "nl": nl,
                "expected": expected,
                "got": got,
                "ok": ok,
                "confidence": parsed.get("confidence"),
                "planned": parsed.get("planned_command"),
            }
        )
    total = len(cases)
    acc = (correct / total) if total else 0.0
    return {
        "ok": acc >= 1.0,
        "accuracy": round(acc, 4),
        "correct": correct,
        "total": total,
        "perfect": acc >= 1.0,
        "failures": [r for r in results if not r["ok"]],
        "results": results,
    }
