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
from typing import Any, Callable, Dict, List, Optional, Sequence

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
    cli_model: Optional[str] = None,
) -> Dict[str, Any]:
    """Run one CLI as reviewer/advisor with structured protocol."""
    from .external_cli import ExternalCLIRegistry, ExternalCLITool

    reg = ExternalCLIRegistry()
    if cli not in reg.available() and not dry_run:
        return {
            "ok": False,
            "cli": cli,
            "role": role,
            "kind": "cli",
            "cli_model": cli_model,
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
        cli_model=cli_model,
    )
    text = env.stdout or env.stderr or env.error or ""
    label = f"cli:{cli}" + (f"@{cli_model}" if cli_model else "")
    opinion = parse_structured_opinion(text, cli=label, role=role)
    opinion["ok"] = bool(env.ok or tool.dry_run)
    opinion["kind"] = "cli"
    opinion["cli_model"] = cli_model
    opinion["member_id"] = label
    opinion["dry_run"] = bool(tool.dry_run or env.metadata.get("dry_run"))
    opinion["exit_code"] = env.exit_code
    opinion["duration_sec"] = env.duration_sec
    opinion["context_id"] = (env.metadata or {}).get("context_id")
    if env.error and not opinion.get("summary"):
        opinion["error"] = env.error
    return opinion


def run_api_opinion(
    model: str,
    subject: str,
    *,
    role: str = "reviewer",
    use_mock: Optional[bool] = None,
    model_id_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Run one API registry model as reviewer/advisor with structured protocol."""
    from .model_caller import ModelCaller
    from .model_registry import ModelRegistry

    reg = ModelRegistry()
    prompt = REVIEW_PROTOCOL_PROMPT.format(role=role, subject=subject[:12000])
    if model_id_override:
        prompt = (
            f"(Use model variant/id hint: {model_id_override} if applicable.)\n" + prompt
        )
    if use_mock is None:
        try:
            from .config import Config

            use_mock = bool(Config().use_mock)
        except Exception:
            use_mock = True
    caller = ModelCaller(use_mock=bool(use_mock), registry=reg)
    try:
        raw = caller.call(model=model, prompt=prompt)
        text = str(raw.get("response") or raw.get("error") or "")
        ok = str(raw.get("status") or "success") != "error"
        opinion = parse_structured_opinion(text, cli=model, role=role)
        opinion["ok"] = ok
        opinion["kind"] = "api"
        opinion["member_id"] = model
        opinion["model"] = model
        opinion["model_id"] = model_id_override
        opinion["mock"] = bool(raw.get("mock"))
        opinion["provider"] = (reg.get_model(model).provider if reg.get_model(model) else None)
        return opinion
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "kind": "api",
            "member_id": model,
            "cli": model,
            "role": role,
            "error": str(e)[:400],
            "verdict": "advise",
            "confidence": 0.0,
            "summary": "",
            "findings": [],
        }


def run_member_opinion(
    member_raw: str,
    subject: str,
    *,
    role: str = "reviewer",
    dry_run: bool = False,
    approve: bool = True,
    use_mock: Optional[bool] = None,
) -> Dict[str, Any]:
    """Run API or CLI member (unified)."""
    from .member_selection import parse_member_spec

    spec = parse_member_spec(member_raw)
    if spec.kind == "cli":
        return run_cli_opinion(
            spec.cli_name or "",
            subject,
            role=role,
            dry_run=dry_run,
            approve=approve,
            cli_model=spec.model_id,
        )
    return run_api_opinion(
        spec.id,
        subject,
        role=role,
        use_mock=use_mock if use_mock is not None else dry_run,
        model_id_override=spec.model_id,
    )


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
            ff["from_cli"] = o.get("cli") or o.get("member_id")
            ff["from_member"] = o.get("member_id") or o.get("cli")
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
        f"- {o.get('member_id') or o.get('cli')} ({o.get('kind') or '?'}/{o.get('role')}/{o.get('verdict')}): "
        f"{str(o.get('summary') or '')[:300]}"
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
        "members": [o.get("member_id") or o.get("cli") for o in usable],
    }


def multi_cli_board(
    subject: str,
    *,
    mode: str = "review",  # review | advise
    clis: Optional[Sequence[str]] = None,
    members: Optional[Sequence[str]] = None,
    max_clis: int = 3,
    dry_run: bool = False,
    approve: bool = True,
    write_memory: bool = True,
    prefer: str = "mixed",  # mixed | cli | api
    use_cache: bool = True,
    progress: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Full multi-member advisory/review board (API models + external CLIs).

    mode=review → role reviewer
    mode=advise → role advisor

    members: unified selectors e.g. gpt-4o,cli:gemini@MODEL,cli:grok
    clis: legacy CLI-only list (still supported)
    """
    role = "reviewer" if (mode or "review").lower().startswith("rev") else "advisor"

    # Smart sizing when caller left default and subject is short
    try:
        from .board_cache import smart_max_members

        if max_clis == 3:
            max_clis = smart_max_members(subject, default=3, hard_cap=5)
    except Exception:
        pass
    # Diversity hard cap (cost control)
    max_clis = max(1, min(int(max_clis or 3), 5))

    # Build member list: explicit members > clis > auto mixed
    raw: List[str] = []
    if members:
        raw = [str(m).strip() for m in members if str(m).strip()]
    elif clis:
        raw = [
            (c if str(c).startswith("cli:") else f"cli:{c}")
            for c in clis
            if str(c).strip()
        ]
    else:
        try:
            from .member_selection import resolve_members

            specs = resolve_members(
                None, max_members=max_clis, prefer=prefer, role=role
            )
            raw = [s.id for s in specs]
        except Exception:
            raw = [f"cli:{c}" for c in pick_advisory_clis(role=role, max_clis=max_clis)]

    # Deduplicate members (diversity)
    seen = set()
    deduped = []
    for m in raw:
        if m not in seen:
            seen.add(m)
            deduped.append(m)
    raw = deduped[: max(1, max_clis)]

    # Cost router: shrink board if over run budget (Sprint B M3)
    cost_meta = None
    try:
        from .config import Config
        from .cost_router import should_skip_or_shrink

        cfg = Config()
        decision = should_skip_or_shrink(
            raw,
            subject,
            run_usd_limit=float(cfg.get("budget_run_usd") or 1.0),
            prefer_cheap=str(cfg.get("run_profile") or "") in {"cheap", "local-only"},
        )
        cost_meta = decision
        if decision.get("action") == "block":
            return {
                "ok": False,
                "status": "error",
                "error": "board_over_budget",
                "cost_router": decision,
                "mock": bool(dry_run),
                "dry_run": bool(dry_run),
            }
        if decision.get("members"):
            raw = list(decision["members"])[: max(1, max_clis)]
    except Exception:
        pass

    if not raw:
        return {
            "ok": False,
            "error": "No selectable API models or external CLIs available",
            "hint": (
                "Configure provider API keys and/or install gemini/grok/claude/codex. "
                "List options: superai members"
            ),
            "mode": mode,
            "opinions": [],
            "board": merge_board([]),
        }

    # Cache hit (identical subject+members+mode); normalize subject for soft match
    cache_subject = " ".join((subject or "").lower().split())
    if use_cache:
        try:
            from .board_cache import get_board

            hit = get_board(
                cache_subject,
                mode=mode,
                members=raw,
                prefer=prefer,
                dry_run=dry_run,
            )
            if hit:
                return hit
        except Exception:
            pass

    def _prog(msg: str) -> None:
        if callable(progress):
            try:
                progress(msg)
            except Exception:
                pass
        try:
            from .progress_events import get_progress_bus

            get_progress_bus().emit("board", message=msg)
        except Exception:
            pass

    # Parallel opinions (Sprint C S2) with ordered results
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _one(m: str) -> Dict[str, Any]:
        _prog(f"board_member_start:{m}")
        op = run_member_opinion(
            m,
            subject,
            role=role,
            dry_run=dry_run,
            approve=approve,
            use_mock=dry_run,
        )
        _prog(f"board_member_end:{m}:{op.get('verdict')}")
        return op

    opinions: List[Dict[str, Any]] = []
    workers = min(4, max(1, len(raw)))
    if workers == 1:
        opinions = [_one(m) for m in raw]
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_one, m): m for m in raw}
            # preserve input order
            by_m = {}
            for fut in as_completed(futs):
                m = futs[fut]
                try:
                    by_m[m] = fut.result()
                except Exception as e:
                    by_m[m] = {
                        "ok": False,
                        "member_id": m,
                        "cli": m,
                        "verdict": "advise",
                        "error": str(e)[:200],
                    }
            opinions = [by_m[m] for m in raw if m in by_m]
    board = merge_board(opinions)
    # Cost/token rollup from opinions (mock estimates when dry_run)
    tokens = 0
    cost = 0.0
    model_chain: List[str] = []
    any_mock = bool(dry_run)
    for op in opinions:
        if not isinstance(op, dict):
            continue
        mid = op.get("member_id") or op.get("cli") or op.get("model")
        if mid and str(mid) not in model_chain:
            model_chain.append(str(mid))
        if op.get("mock") or op.get("dry_run"):
            any_mock = True
        try:
            tokens += int((op.get("usage") or {}).get("total_tokens") or op.get("tokens") or 0)
        except (TypeError, ValueError):
            pass
        try:
            cost += float(op.get("estimated_cost_usd") or 0.0)
        except (TypeError, ValueError):
            pass
    if tokens <= 0:
        # deterministic offline estimate
        tokens = max(1, len(subject or "") // 4) * max(1, len(opinions))
    if cost <= 0 and opinions:
        cost = round(0.00001 * tokens, 6)

    mem_ids: List[str] = []
    result: Dict[str, Any] = {
        "ok": True,
        "status": "success",
        "mode": mode,
        "role": role,
        "members": raw[: max(1, max_clis)],
        "clis": [m for m in raw if str(m).startswith("cli:") or "@" in str(m)],
        "opinions": opinions,
        "board": board,
        "protocol": "superai.multi_member_review.v2",
        "prefer": prefer,
        "mock": any_mock,
        "dry_run": bool(dry_run),
        "model_chain": model_chain or list(raw[: max(1, max_clis)]),
        "tokens": tokens,
        "estimated_cost_usd": cost,
        "memory_ids": mem_ids,
    }

    if write_memory:
        try:
            from .central_memory import write_back

            result["memory_write"] = write_back(
                task=subject[:500],
                source="multi_cli_advisory",
                model_or_cli=f"board:{','.join(raw[:8])}",
                success=True,
                output=str(board.get("summary") or "")[:2500],
                task_type="review",
                tags=["advisory", role, mode],
                metadata={
                    "verdict": board.get("verdict"),
                    "tally": board.get("tally"),
                    "members": raw[: max(1, max_clis)],
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
                "members": raw[: max(1, max_clis)],
                "verdict": board.get("verdict"),
                "dry_run": dry_run,
            },
        )
    except Exception:
        pass

    # Normalize contract (mock/dry_run never ambiguous)
    try:
        from .result_contract import apply_contract

        mw = result.get("memory_write")
        if isinstance(mw, dict):
            mid = mw.get("id") or mw.get("memory_id") or mw.get("context_id")
            if mid:
                result.setdefault("memory_ids", []).append(str(mid))
        apply_contract(
            result,
            mock=any_mock or bool(dry_run),
            dry_run=bool(dry_run),
            members=raw[: max(1, max_clis)],
            ok=True,
        )
    except Exception:
        result.setdefault("contract", "superai.result.v1")
        result.setdefault("mock", bool(dry_run))
        result.setdefault("dry_run", bool(dry_run))

    if use_cache and result.get("ok"):
        try:
            from .board_cache import put_board

            put_board(
                cache_subject,
                result,
                mode=mode,
                members=raw[: max(1, max_clis)],
                prefer=prefer,
                dry_run=dry_run,
            )
        except Exception:
            pass
    if cost_meta:
        result["cost_router"] = cost_meta

    return result


def default_council_members(
    n: int = 3,
    *,
    prefer_clis: bool = True,
    prefer: Optional[str] = None,  # mixed | cli | api (overrides prefer_clis)
    registry=None,
) -> List[str]:
    """
    Default council/board members: configured API models + available CLIs.

    prefer / prefer_clis:
      prefer="mixed" | "cli" | "api" wins when set
      else prefer_clis=True → "cli", False → "api"
    """
    from .model_registry import ModelRegistry

    reg = registry or ModelRegistry()
    try:
        reg.register_external_clis_as_models()
    except Exception:
        pass

    pref = (prefer or ("cli" if prefer_clis else "api")).lower()
    if pref not in {"mixed", "cli", "api"}:
        pref = "cli" if prefer_clis else "api"

    try:
        from .member_selection import resolve_members

        specs = resolve_members(None, max_members=n, prefer=pref, role="advisor")
        if specs:
            # Preserve full selectors including cli:name@MODEL when present
            return [s.id for s in specs][:n]
    except Exception:
        pass

    # Fallback without member_selection
    if pref in {"cli", "mixed"}:
        clis = pick_advisory_clis(role="advisor", max_clis=n)
        if clis:
            out = [f"cli:{c}" if not c.startswith("cli:") else c for c in clis]
            if pref == "cli" or len(out) >= n:
                return out[:n]
            names = [m for m in reg.list_all_models() if not str(m).startswith("cli:")]
            for nm in names:
                if nm not in out:
                    out.append(nm)
                if len(out) >= n:
                    break
            return out[:n]

    names = [m for m in reg.list_all_models() if not str(m).startswith("cli:")]
    if not names:
        clis = [m for m in reg.list_all_models() if str(m).startswith("cli:")]
        if clis:
            return clis[:n]
        return ["gpt-4o"] * max(1, n)
    return names[:n]
