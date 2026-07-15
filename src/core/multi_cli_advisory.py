"""
Multi-CLI review & advisor board (fills product gaps).

- Pick available external AI CLIs as reviewers/advisors
- Structured review protocol (verdict, findings, confidence, summary)
- Merge board opinions for SuperAI consumption
- Used by: council defaults, pr-review, orchestrator critic, CLI commands
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Sequence

# Structured protocol every advisor/reviewer is asked to follow
REVIEW_PROTOCOL_PROMPT = """You are a SuperAI {role} on a multi-CLI advisory board.

Respond with ONLY valid JSON (no markdown fences):
{{
  "verdict": "approve" | "request_changes" | "reject" | "advise",
  "confidence": 0.0-1.0,
  "findings": [
    {{"severity": "high"|"medium"|"low"|"info", "title": "short", "detail": "actionable"}}
  ],
  "summary": "2-5 sentence overall opinion",
  "role": "{role}"
}}

Subject:
{subject}
"""


def parse_structured_opinion(text: str, *, cli: str, role: str) -> Dict[str, Any]:
    """Parse JSON opinion from CLI stdout; degrade gracefully to prose summary."""
    raw = (text or "").strip()
    data: Dict[str, Any] = {}
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                try:
                    data = json.loads(m.group(0))
                except json.JSONDecodeError:
                    data = {}
    if not isinstance(data, dict):
        data = {}

    verdict = str(data.get("verdict") or "").lower().strip()
    if verdict not in {"approve", "request_changes", "reject", "advise"}:
        # heuristic from free text when JSON omitted or invalid verdict
        low = raw.lower()
        if "reject" in low or "do not merge" in low or "blocker" in low:
            verdict = "reject"
        elif (
            "request_changes" in low
            or "changes requested" in low
            or "needs work" in low
        ):
            verdict = "request_changes"
        elif "approve" in low or "lgtm" in low or "looks good" in low:
            verdict = "approve"
        else:
            verdict = "advise"

    try:
        conf = float(data.get("confidence", 0.55))
    except (TypeError, ValueError):
        conf = 0.55
    conf = max(0.0, min(1.0, conf))

    findings = data.get("findings") if isinstance(data.get("findings"), list) else []
    clean_findings = []
    for f in findings[:20]:
        if not isinstance(f, dict):
            continue
        clean_findings.append(
            {
                "severity": str(f.get("severity") or "info").lower(),
                "title": str(f.get("title") or "")[:200],
                "detail": str(f.get("detail") or "")[:2000],
            }
        )

    summary = str(data.get("summary") or raw[:800] or "(empty)").strip()
    return {
        "cli": cli,
        "role": str(data.get("role") or role),
        "verdict": verdict,
        "confidence": conf,
        "findings": clean_findings,
        "summary": summary,
        "raw_preview": raw[:500],
        "structured": bool(data.get("verdict") or data.get("summary")),
    }


def pick_advisory_clis(
    *,
    role: str = "reviewer",
    max_clis: int = 3,
    preferred: Optional[Sequence[str]] = None,
    only_available: bool = True,
) -> List[str]:
    """Choose CLIs for review/advisor board (available first)."""
    from .external_cli import ExternalCLIRegistry

    reg = ExternalCLIRegistry()
    avail = reg.available()
    if preferred:
        ordered = [c for c in preferred if (not only_available) or c in avail]
        if ordered:
            return ordered[:max_clis]
    # Role-aware preference
    prefer_map = {
        "reviewer": ["grok", "claude", "gemini", "codex", "cursor"],
        "advisor": ["gemini", "grok", "claude", "codex", "aider"],
        "architect": ["claude", "gemini", "grok", "cursor"],
        "tester": ["aider", "codex", "claude", "gemini"],
    }
    prefer = prefer_map.get((role or "reviewer").lower(), prefer_map["reviewer"])
    out: List[str] = []
    for p in prefer:
        if p in avail and p not in out:
            out.append(p)
        if len(out) >= max_clis:
            return out
    for a in avail:
        if a not in out:
            out.append(a)
        if len(out) >= max_clis:
            break
    return out[:max_clis]


def run_cli_opinion(
    cli: str,
    subject: str,
    *,
    role: str = "reviewer",
    dry_run: bool = False,
    approve: bool = True,
    timeout_sec: float = 300.0,
) -> Dict[str, Any]:
    """Run one CLI as reviewer/advisor with structured protocol."""
    from .external_cli import ExternalCLIRegistry, ExternalCLITool

    reg = ExternalCLIRegistry()
    if cli not in reg.available() and not dry_run:
        return {
            "ok": False,
            "cli": cli,
            "role": role,
            "error": f"CLI '{cli}' not on PATH",
            "hint": reg.install_hint(cli) if hasattr(reg, "install_hint") else None,
        }

    prompt = REVIEW_PROTOCOL_PROMPT.format(role=role, subject=subject[:12000])
    tool = ExternalCLITool(
        registry=reg,
        auto_approve=approve or dry_run,
        dry_run=dry_run or (cli not in reg.available()),
        timeout_sec=timeout_sec,
        with_context=True,
        write_memory=True,
    )
    env = tool.run(
        cli,
        prompt,
        approve=approve or dry_run,
        role=role,
        source="multi_cli_advisory",
        task_type="review",
        write_memory=True,
    )
    text = env.stdout or env.stderr or env.error or ""
    opinion = parse_structured_opinion(text, cli=cli, role=role)
    opinion["ok"] = bool(env.ok or tool.dry_run)
    opinion["dry_run"] = bool(tool.dry_run or env.metadata.get("dry_run"))
    opinion["exit_code"] = env.exit_code
    opinion["duration_sec"] = env.duration_sec
    opinion["context_id"] = (env.metadata or {}).get("context_id")
    if env.error and not opinion.get("summary"):
        opinion["error"] = env.error
    return opinion


def merge_board(opinions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate multi-CLI opinions into a board decision."""
    from collections import Counter

    usable = [o for o in opinions if o.get("ok") is not False]
    if not usable:
        return {
            "verdict": "advise",
            "confidence": 0.0,
            "summary": "No usable advisor/reviewer outputs",
            "tally": {},
            "findings": [],
            "members": [],
        }

    verdicts = [str(o.get("verdict") or "advise") for o in usable]
    tally = dict(Counter(verdicts))
    # priority: reject > request_changes > approve > advise if ties on severity
    severity_rank = {"reject": 3, "request_changes": 2, "approve": 1, "advise": 0}
    # majority first
    winner, votes = Counter(verdicts).most_common(1)[0]
    # if approve vs request_changes close, escalate to request_changes when any reject
    if tally.get("reject"):
        if tally.get("reject", 0) >= max(1, len(usable) // 2):
            winner = "reject"
    elif tally.get("request_changes") and tally.get("approve"):
        if tally["request_changes"] >= tally.get("approve", 0):
            winner = "request_changes"

    confs = [float(o.get("confidence") or 0.5) for o in usable]
    avg_conf = sum(confs) / len(confs) if confs else 0.5

    findings: List[Dict[str, Any]] = []
    for o in usable:
        for f in o.get("findings") or []:
            ff = dict(f)
            ff["from_cli"] = o.get("cli")
            findings.append(ff)
    # de-dupe by title
    seen = set()
    uniq = []
    for f in findings:
        k = (f.get("title") or "").lower()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)

    summaries = [
        f"- {o.get('cli')} ({o.get('role')}/{o.get('verdict')}): {str(o.get('summary') or '')[:300]}"
        for o in usable
    ]
    board_summary = (
        f"Board verdict={winner} (votes={votes}/{len(usable)}). "
        f"Avg confidence={avg_conf:.2f}.\n" + "\n".join(summaries)
    )

    return {
        "verdict": winner,
        "confidence": round(avg_conf, 3),
        "votes": votes,
        "members_count": len(usable),
        "tally": tally,
        "severity_hint": severity_rank.get(winner, 0),
        "findings": uniq[:40],
        "summary": board_summary,
        "members": [o.get("cli") for o in usable],
    }


def multi_cli_board(
    subject: str,
    *,
    mode: str = "review",  # review | advise
    clis: Optional[Sequence[str]] = None,
    max_clis: int = 3,
    dry_run: bool = False,
    approve: bool = True,
    write_memory: bool = True,
) -> Dict[str, Any]:
    """
    Full multi-CLI advisory/review board.

    mode=review → role reviewer
    mode=advise → role advisor
    """
    role = "reviewer" if (mode or "review").lower().startswith("rev") else "advisor"
    chosen = list(clis) if clis else pick_advisory_clis(role=role, max_clis=max_clis)
    if not chosen:
        return {
            "ok": False,
            "error": "No external AI CLIs available on PATH",
            "hint": "Install gemini/grok/claude/codex or run: superai install --host-tools-profile agentic",
            "mode": mode,
            "opinions": [],
            "board": merge_board([]),
        }

    opinions = [
        run_cli_opinion(
            c,
            subject,
            role=role,
            dry_run=dry_run,
            approve=approve,
        )
        for c in chosen
    ]
    board = merge_board(opinions)
    result: Dict[str, Any] = {
        "ok": True,
        "mode": mode,
        "role": role,
        "clis": chosen,
        "opinions": opinions,
        "board": board,
        "protocol": "superai.multi_cli_review.v1",
    }

    if write_memory:
        try:
            from .central_memory import write_back

            result["memory_write"] = write_back(
                task=subject[:500],
                source="multi_cli_advisory",
                model_or_cli=f"board:{','.join(chosen)}",
                success=True,
                output=str(board.get("summary") or "")[:2500],
                task_type="review",
                tags=["advisory", role, mode],
                metadata={
                    "verdict": board.get("verdict"),
                    "tally": board.get("tally"),
                    "clis": chosen,
                },
            )
        except Exception as e:  # noqa: BLE001
            result["memory_write_error"] = str(e)[:200]

    try:
        from .audit_log import AuditLog

        AuditLog().record(
            "multi_cli_advisory",
            {
                "mode": mode,
                "clis": chosen,
                "verdict": board.get("verdict"),
                "dry_run": dry_run,
            },
        )
    except Exception:
        pass

    return result


def default_council_members(
    n: int = 3,
    *,
    prefer_clis: bool = True,
    registry=None,
) -> List[str]:
    """
    Prefer available external CLIs as council members (cli:name),
    else fall back to API models from registry.
    """
    from .model_registry import ModelRegistry

    reg = registry or ModelRegistry()
    try:
        reg.register_external_clis_as_models()
    except Exception:
        pass

    if prefer_clis:
        clis = pick_advisory_clis(role="advisor", max_clis=n)
        if clis:
            return [f"cli:{c}" if not c.startswith("cli:") else c for c in clis]

    names = [m for m in reg.list_all_models() if not str(m).startswith("cli:")]
    if not names:
        # last resort: any cli registered even if offline (dry-run path)
        clis = [m for m in reg.list_all_models() if str(m).startswith("cli:")]
        if clis:
            return clis[:n]
        return ["gpt-4o"] * max(1, n)
    return names[:n]
