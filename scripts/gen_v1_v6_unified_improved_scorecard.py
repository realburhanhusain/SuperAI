"""
Generate docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md

STRICT completion bar (user rule):
  COMPLETE only if ALL of:
    1) production-ready code
    2) thorough documentation
    3) fully tested
  Otherwise INCOMPLETE.

Does NOT modify docs/V1_V6_UNIFIED_SCORECARD.md (left for concurrent validation).
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "V1_V6_UNIFIED_SCORECARD.md"  # read-only inventory
OUT = ROOT / "docs" / "V1_V6_UNIFIED_IMPROVED_SCORECARD.md"

# (code_ok, docs_ok, tests_ok) each bool — complete only if all True
# pct_code/docs/tests 0-100; overall = min of three when all required, else weighted

Triple = tuple[bool, bool, bool, int, str, str, str, str]
# code, docs, tests, overall_pct, code_note, docs_note, tests_note, gap


def T(
    code: bool,
    docs: bool,
    tests: bool,
    pct: int,
    code_n: str,
    docs_n: str,
    tests_n: str,
    gap: str,
) -> Triple:
    """
    code/docs/tests = pillar evidence present (not auto-complete).
    pct==100 only when caller asserts production-ready for full intent.
    """
    pct = int(pct)
    if pct >= 100 and not (code and docs and tests):
        pct = 99
    return (code, docs, tests, pct, code_n, docs_n, tests_n, gap)


def is_complete(t: Triple) -> bool:
    """Complete only when all pillars true AND overall percent is 100."""
    return bool(t[0] and t[1] and t[2] and t[3] == 100)


# ---------------------------------------------------------------------------
# Strict completes: only items with real module + plan/docs + unit tests
# ---------------------------------------------------------------------------

# MoSCoW items with test_moscow_100 + MOSCOW_100_PLAN + modules
MOSCOW_COMPLETE = {
    "MOS-M1", "MOS-M2", "MOS-M3", "MOS-M4", "MOS-M5", "MOS-M6", "MOS-M7", "MOS-M8",
    "MOS-S1", "MOS-S2", "MOS-S3", "MOS-S4", "MOS-S5", "MOS-S6", "MOS-S7", "MOS-S8",
    "MOS-S9", "MOS-S10",
    "MOS-N1", "MOS-N2", "MOS-N3", "MOS-N4", "MOS-N5", "MOS-N6", "MOS-N7",
    # MOS-N8 host — not complete without live
}

# V4/V5 with dedicated test files + plan docs
V4_COMPLETE = {
    "V4-M3", "V4-M5", "V4-M6", "V4-M7", "V4-M8",
    "V4-S1", "V4-S4", "V4-S5", "V4-S6", "V4-S7", "V4-S8", "V4-S9", "V4-S10",
    "V4-DOD-2", "V4-DOD-3",
    # V4-M1/M2/M4/S3/DOD-1: code strong but "every path" docs/tests not exhaustive → incomplete
}
V5_COMPLETE = {
    "V5-M5", "V5-M6", "V5-M7", "V5-M8",
    "V5-S1", "V5-S2", "V5-S3", "V5-S4", "V5-S5", "V5-S6", "V5-S7", "V5-S10",
}
W_COMPLETE = {"W1", "W2", "W3", "W4", "W5", "W6", "W8", "W-SA"}  # test_not_important; W7 thin

# V1 phase items with plan + targeted tests (narrow DoD)
V1_COMPLETE = {
    "V1-P0", "V1-P1-2", "V1-P2-1", "V1-P2-2", "V1-P2-3",
    "V1-P3-1", "V1-P3-2", "V1-P3-3", "V1-P4-1", "V1-P4-2", "V1-P4-3",
    "V1-P5-1", "V1-P5-3", "V1-P6-1", "V1-P6-2", "V1-P6-3", "V1-P7",
    "V1-N1", "V1-N2", "V1-N3", "V1-N4", "V1-N5", "V1-N6", "V1-N7",
}
# V2/V3 sprint items with test_sprint_abcd / test_improvement_v3
V2_COMPLETE = {
    "V2-A1", "V2-A2", "V2-A3", "V2-B1", "V2-B2", "V2-B4",
    "V2-C1", "V2-C2", "V2-C3", "V2-C4", "V2-C6", "V2-D1", "V2-D2", "V2-D3",
}
V3_COMPLETE = {
    "V3-A1", "V3-A2", "V3-A3", "V3-B1", "V3-B2", "V3-B3", "V3-B4",
    "V3-C1", "V3-C2", "V3-C3", "V3-C4", "V3-D2", "V3-D3",
}

# V6 Must with strong tests + backlog + modules (strict)
V6_MUST_COMPLETE = {
    "M004", "M005", "M006", "M007", "M009", "M010", "M011", "M013", "M014", "M016",
    "M019", "M020", "M021", "M022", "M023", "M024", "M025", "M026", "M028", "M030",
    "M031", "M032", "M033", "M034", "M035", "M036", "M037", "M038", "M039", "M040",
    "M041", "M042", "M043", "M044", "M045", "M046", "M047", "M048", "M049",
    "M051", "M052", "M053", "M054", "M055", "M056", "M057", "M058", "M059", "M060",
    "M064", "M065", "M066", "M069", "M070", "M071", "M072", "M073", "M074", "M075",
    "M076", "M077", "M078", "M083", "M084", "M085", "M086", "M087", "M088",
    "M095", "M096", "M097", "M098",
    # Newly triple-bar after MOS-N6 style work where docs+tests+code exist:
    "M003",  # board_preflight + tests + backlog
    "M012",  # secrets + logger filter + tests
    "M029",  # session_compact + tests
    "M067",  # history search + tests
    "M092",  # mock_fixtures + tests
    "M094",  # web auth + web_app
    "M099",  # THREAT_MODEL.md thorough doc
    # MOS-N6 voice: code + tests + this session (docs: MOSCOW plan N6 section)
    # V6 N213 maps separately
}

# V6 Should complete (narrow, tested)
V6_SHOULD_COMPLETE = {
    "M101": None,  # placeholder wrong
}
# fix - S ids
V6_S_COMPLETE = {
    "S101", "S102", "S107", "S118", "S122", "S125", "S126",
    "S151", "S152", "S157", "S161", "S171", "S177", "S196", "S198", "S199", "S200",
    "S103", "S130", "S131", "S133", "S134", "S135",
}
V6_N_COMPLETE = {
    "N203", "N227", "N260", "N261",
    "N213",  # voice — code+tests+MOSCOW N6 docs
}

COMPLETE_IDS = (
    MOSCOW_COMPLETE
    | V4_COMPLETE
    | V5_COMPLETE
    | W_COMPLETE
    | V1_COMPLETE
    | V2_COMPLETE
    | V3_COMPLETE
    | V6_MUST_COMPLETE
    | V6_S_COMPLETE
    | V6_N_COMPLETE
)

# Explicit incomplete notes for borderline items that were previously over-claimed as full
STRICT_INCOMPLETE: dict[str, Triple] = {
    # Pillars may be True but pct<100 ⇒ incomplete (intent not fully production-met)
    "M001": T(True, True, True, 85, "call_lifecycle + spend_guard on major paths", "V6 backlog M001", "test_foundation_lift/complete_must", "Not proven on literally every CLI subcommand"),
    "M002": T(True, True, True, 90, "cost_accounting on ModelCaller post_call", "V6 M002", "test_foundation_lift", "Some paths still estimate when provider omits usage"),
    "M008": T(True, True, True, 85, "result_contract + MCP wrap + emit_public", "V6 M008", "test_result_contract", "Not every interactive TUI command returns envelope"),
    "M015": T(True, False, True, 70, "injection_defense on tool results", "Backlog only; no dedicated security doc depth", "test_foundation_complete_must", "Thorough injection threat docs incomplete"),
    "M017": T(True, True, True, 90, "CancelToken agent+boards+stream", "V6 M017", "tests cancel", "Edge cases on all worker types"),
    "M018": T(True, True, True, 90, "model_timeouts + tool_timeouts", "V6 M018", "test_foundation_complete_must", "Not every subprocess path instrumented"),
    "M027": T(True, True, True, 85, "call_stream SSE + fallback", "V6 M027", "test_improvement_v4 stream", "Not all providers proven live"),
    "M050": T(True, True, True, 80, "bandit reorder+update", "V6 M050", "bandit tests partial", "Not continuous-product UI"),
    "M061": T(True, True, True, 85, "promote_durable", "learning docs partial", "test_foundation_complete_must", "Product UX incomplete"),
    "M062": T(True, True, True, 85, "resolve_conflicts", "partial", "learning tests", "Conflict UI incomplete"),
    "M063": T(True, True, True, 85, "distill+deprecate", "partial", "learning tests", "Lifecycle product incomplete"),
    "M068": T(True, True, True, 85, "preferences.bias_candidates", "partial", "tests", "Deep routing bias not fully proven"),
    "M079": T(True, True, True, 85, "global --json", "CLI help", "partial tests", "Not all commands emit JSON by default"),
    "M080": T(True, True, True, 80, "exit_codes module", "partial", "test_foundation_complete_must", "Not all process exits wired"),
    "M081": T(True, False, False, 60, "Typer help exists", "Uneven examples; no help quality guide", "No dedicated help tests", "Thorough docs + tests missing"),
    "M082": T(True, False, False, 55, "add_completion=True", "Typer docs only", "No completion E2E tests", "Docs+tests incomplete"),
    "M090": T(True, True, True, 80, "TOP_30 + contract smoke", "V6 M090", "verify_top30 offline", "Not live invocation of all 30 CLIs"),
    "M093": T(True, True, True, 85, "mcp_safety wrap", "V6 M093", "mcp tests partial", "Full MCP tool matrix not exhaustive"),
    "M100": T(True, True, True, 80, "dashboard honesty labels", "partial", "tests partial", "Full dashboard product incomplete"),
    "M089": T(True, True, True, 90, "smoke harness code", "plans document host gate", "harness tests offline", "HOST: live keys required"),
    "MOS-N8": T(True, True, True, 90, "smoke harness", "MOSCOW N8 postponed", "test_n8 no false pass", "HOST live multi-vendor"),
    "V1-P99": T(True, True, True, 90, "smoke code", "IMPROVEMENT_PLAN Phase 99", "offline harness", "HOST live smoke"),
    "V1-N8": T(True, True, True, 50, "plugin_catalog browse", "PHASE8 N8", "test_phase8 partial", "Not marketplace product"),
    "W7": T(True, False, True, 45, "VS Code extension thin", "No thorough extension docs", "smoke-preflight related", "IDE depth incomplete"),
    "V4-M1": T(True, True, True, 85, "spend_guard major paths", "V4 plan", "test_improvement_v4", "Not every spend path"),
    "V4-M2": T(True, True, True, 85, "contracts major paths", "V4 plan", "test_improvement_v4", "Not everywhere public"),
    "V4-M4": T(True, True, True, 85, "call_stream", "V4 plan", "test stream", "Provider coverage incomplete"),
    "V4-S3": T(True, True, True, 80, "bandit feedback", "V4 plan", "partial", "Continuous bandit incomplete"),
    "V4-DOD-1": T(True, True, True, 85, "spend_guard sweep", "V4 DoD", "tests", "Residual thin wrappers"),
    "V5-M1": T(True, True, True, 85, "public_api.wrap key paths", "V5 plan", "test_improvement_v5", "Not all CLI cmds"),
    "V5-M2": T(True, True, True, 85, "MCP superai_run budget", "V5 plan", "mcp tests", "Full MCP parity matrix incomplete"),
    "V5-M3": T(True, True, True, 90, "CancelToken agent", "V5 plan", "tests", "All board workers edge cases"),
    "V5-M4": T(True, True, True, 90, "cost_accounting", "V5 plan", "tests", "Estimate fallbacks remain"),
    "V1-P1-1": T(True, True, True, 85, "result_contract", "IMPROVEMENT_PLAN P1", "test_result_contract", "Not all surfaces"),
    "V1-P1-3": T(True, True, True, 85, "budget foundation", "P1 plan", "tests", "Universal ceiling incomplete"),
    "V1-P1-4": T(True, True, True, 85, "cost fields", "P1 plan", "tests", "Accuracy gaps"),
    "V1-P5-2": T(True, True, True, 85, "progress + stream", "P5 plan", "tests", "True SSE all providers incomplete"),
    "V2-A4": T(True, True, True, 85, "contracts tool/agent", "V2 plan", "sprint tests", "Universal CLI incomplete"),
    "V2-B3": T(True, True, True, 90, "session_compact", "V2 plan", "tests", "Decision/todo edge cases"),
    "V2-C5": T(True, True, True, 80, "agent-graph SVG", "V2/V3 plan", "tests", "HTML graph legacy partial"),
    "V3-A4": T(True, True, True, 85, "board contracts", "V3 plan", "tests", "Not all APIs"),
    "V3-D1": T(True, True, True, 80, "bandit pin", "V3 plan", "tests", "Continuous product incomplete"),
    "MOS-S1": T(True, True, True, 85, "token_stream TUI", "MOSCOW S1", "test_moscow", "Real provider SSE incomplete"),
}


def parse_source_items() -> list[tuple[str, str, str]]:
    """Read-only parse of existing unified scorecard for ID + title inventory."""
    if not SOURCE.is_file():
        return []
    text = SOURCE.read_text(encoding="utf-8")
    items = []
    for m in re.finditer(r"^### ([^\n—]+) — ([^\n]+)\n", text, re.M):
        iid = m.group(1).strip()
        title = m.group(2).strip()
        # track from following lines
        chunk = text[m.end() : m.end() + 200]
        tm = re.search(r"\*\*Track:\*\* ([^\n]+)", chunk)
        track = tm.group(1).strip() if tm else "unknown"
        items.append((track, iid, title))
    return items


def assess(track: str, iid: str, title: str) -> tuple[str, Triple]:
    """
    Return (bucket, triple) where bucket is:
      complete | incomplete_code | incomplete_docs | incomplete_tests |
      incomplete_multi | host | refuse | stub | absent | foundation
    """
    if iid in STRICT_INCOMPLETE:
        t = STRICT_INCOMPLETE[iid]
        if iid in {"M089", "MOS-N8", "V1-P99"}:
            return "host", t
        if is_complete(t):
            return "complete", t
        # classify primary gap
        c, d, te, pct, *_ = t
        if not c and not d and not te:
            return "absent", t
        if pct <= 20:
            return "stub", t
        return "foundation", t

    if iid.startswith("P") and iid[1:].isdigit():
        n = int(iid[1:])
        if 386 <= n <= 400:
            return "refuse", T(
                True, True, True, 100,
                "Refuse-closed policy in parked_features",
                "V6 backlog P386–P400",
                "parked/refuse tests where present",
                "Must not implement as feature",
            )
        if n in (366, 368):
            return "foundation", T(
                True, True, False, 40,
                "Partial strategy/flag only",
                "Parked notes",
                "No full product tests",
                "Not production dual-stack / CLI reimplementation",
            )
        return "stub", T(
            False, True, False, 10,
            "Parked vanity/overbuild — not product code",
            "V6 parked catalog",
            "No feature tests",
            "Not scheduled",
        )

    if iid in COMPLETE_IDS:
        # docs evidence by track
        docs_note = {
            "V6": "IMPROVEMENT_V6_BACKLOG + module docstrings",
            "V1-V5": "IMPROVEMENT / MOSCOW / PHASE plans + module docstrings",
        }.get(track, "plan docs")
        if track == "V6" or iid.startswith("M") or iid.startswith("S") or iid.startswith("N"):
            docs_note = "IMPROVEMENT_V6_BACKLOG.md + code docs"
        if iid.startswith("MOS-") or iid.startswith("W"):
            docs_note = "MOSCOW_100_PLAN.md / NOT_IMPORTANT_PLAN.md"
        if iid.startswith("V4"):
            docs_note = "IMPROVEMENT_V4_PLAN.md"
        if iid.startswith("V5"):
            docs_note = "IMPROVEMENT_V5_PLAN.md"
        if iid.startswith("V1") or iid.startswith("V2") or iid.startswith("V3"):
            docs_note = "IMPROVEMENT_PLAN / V2 / V3 plan docs"
        tests_note = "unit tests in tests/ (moscow/v4/v5/sprint/foundation/voice as applicable)"
        return "complete", T(
            True, True, True, 100,
            f"Production-usable implementation for: {title}",
            docs_note,
            tests_note,
            "—",
        )

    # Heuristic from id prefix for remaining
    if iid.startswith("N"):
        return "stub", T(
            False, True, False, 15,
            "Nice item — stub or thin module only",
            "V6 backlog Nice section",
            "No thorough dedicated tests",
            "Production product + docs + tests",
        )
    if iid.startswith("S"):
        return "foundation", T(
            True, True, False, 45,
            "Partial Should implementation may exist",
            "V6 backlog Should section",
            "Insufficient dedicated tests for full bar",
            "Full production hardening + tests + docs",
        )
    if iid.startswith("M"):
        return "foundation", T(
            True, True, False, 50,
            "Partial Must code path",
            "V6 backlog Must",
            "Tests incomplete for strict bar",
            "Close gaps to production + full tests",
        )

    return "foundation", T(
        True, False, False, 40,
        f"Related code may exist for {title}",
        "Insufficient thorough documentation",
        "Insufficient tests",
        "Code + thorough docs + full tests required",
    )


def main() -> None:
    items = parse_source_items()
    if not items:
        raise SystemExit(f"Cannot read inventory from {SOURCE} (read-only source missing)")

    # Deduplicate by id (prefer first)
    seen = set()
    unique = []
    for track, iid, title in items:
        if iid in seen:
            continue
        seen.add(iid)
        unique.append((track, iid, title))

    assessed = []
    for track, iid, title in unique:
        bucket, triple = assess(track, iid, title)
        assessed.append((track, iid, title, bucket, triple))

    # Re-bucket complete vs incomplete
    complete = [a for a in assessed if a[3] == "complete" or (a[3] != "refuse" and is_complete(a[4]))]
    # fix: only is_complete
    complete = [a for a in assessed if is_complete(a[4]) and a[3] not in {"host", "refuse"}]
    # host/refuse separate
    host = [a for a in assessed if a[3] == "host" or a[1] in {"M089", "MOS-N8", "V1-P99"}]
    refuse = [a for a in assessed if a[3] == "refuse"]
    incomplete = [
        a
        for a in assessed
        if a not in complete and a not in host and a not in refuse
    ]

    # counts
    c_complete = len(complete)
    c_host = len(host)
    c_refuse = len(refuse)
    c_incomplete = len(incomplete)
    total = len(assessed)

    def pct_avg(rows):
        if not rows:
            return 0.0
        return sum(r[4][3] for r in rows) / len(rows)

    lines = [
        "# SuperAI V1–V6 Unified IMPROVED Scorecard (strict bar)",
        "",
        "**Generated:** 2026-07-16  ",
        f"**Total unique improvement IDs:** {total}  ",
        "**Source inventory (read-only):** `docs/V1_V6_UNIFIED_SCORECARD.md` — **not modified**  ",
        "**This file:** `docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md`  ",
        "",
        "## Strict completion rule (mandatory)",
        "",
        "An improvement is **COMPLETE** only if **all three** are true:",
        "",
        "1. **Production-ready code** (usable for the stated intent, not a stub)",
        "2. **Thorough documentation** (plan/backlog section and/or dedicated docs explaining behavior)",
        "3. **Fully tested** (unit/integration tests covering the intent offline)",
        "",
        "If any criterion fails → **INCOMPLETE** (regardless of prior scorecards).",
        "",
        "| Field | Meaning |",
        "|-------|---------|",
        "| **Complete?** | YES only when code+docs+tests all pass |",
        "| **Percent** | Overall readiness 0–100; **100 only if complete** |",
        "| **Code / Docs / Tests** | Evidence or gap for each pillar |",
        "",
        "## Summary",
        "",
        "| Bucket | Count |",
        "|--------|------:|",
        f"| **COMPLETE (production + docs + tests)** | **{c_complete}** |",
        f"| **INCOMPLETE** | **{c_incomplete}** |",
        f"| **HOST-GATED** (code/docs/tests offline; live proof missing) | **{c_host}** |",
        f"| **REFUSE-CLOSED** (policy; not a shipped feature) | **{c_refuse}** |",
        f"| **Total** | **{total}** |",
        "",
        f"- **Strict completion rate (complete / (total − refuse)):** "
        f"**{100 * c_complete / max(1, total - c_refuse):.1f}%**",
        f"- **Average percent (incomplete only):** **{pct_avg(incomplete):.1f}%**",
        f"- **Average percent (all non-refuse):** "
        f"**{pct_avg([a for a in assessed if a[3] != 'refuse']):.1f}%**",
        "",
        "### Note for validators",
        "",
        "- Do **not** treat the older `V1_V6_UNIFIED_SCORECARD.md` full@100% rows as complete under this bar.",
        "- MOS-N6 voice is complete under this bar: production `voice_io`, MOSCOW plan N6 docs, `tests/test_voice_mos_n6.py`.",
        "- M001/M008-style “everywhere” claims remain **incomplete** until exhaustive path coverage is proven.",
        "",
        "---",
        "",
        "## 1. COMPLETE (only these count as completed)",
        "",
        f"**Count:** {c_complete}",
        "",
    ]

    for track, iid, title, bucket, t in sorted(complete, key=lambda x: x[1]):
        c, d, te, pct, cn, dn, tn, gap = t
        lines += [
            f"### {iid} — {title}",
            "",
            f"- **Track:** {track}",
            f"- **Complete?** **YES**",
            f"- **Percent:** **{pct}%**",
            f"- **Code (production-ready):** YES — {cn}",
            f"- **Documentation (thorough):** YES — {dn}",
            f"- **Tests (full):** YES — {tn}",
            f"- **Still incomplete:** {gap}",
            "",
        ]

    lines += [
        "---",
        "",
        "## 2. INCOMPLETE (not production-complete under strict bar)",
        "",
        f"**Count:** {c_incomplete}",
        "",
        "Sub-order: foundation-like → stub → absent (heuristic).",
        "",
    ]

    def subkey(a):
        pct = a[4][3]
        return (-pct, a[1])

    for track, iid, title, bucket, t in sorted(incomplete, key=subkey):
        c, d, te, pct, cn, dn, tn, gap = t
        lines += [
            f"### {iid} — {title}",
            "",
            f"- **Track:** {track}",
            f"- **Complete?** **NO**",
            f"- **Percent:** **{pct}%**",
            f"- **Heuristic bucket:** `{bucket}`",
            f"- **Code production-ready?** {'YES' if c else 'NO'} — {cn}",
            f"- **Thorough documentation?** {'YES' if d else 'NO'} — {dn}",
            f"- **Fully tested?** {'YES' if te else 'NO'} — {tn}",
            f"- **Fully implemented:** {cn if c else '—'}",
            f"- **Partially implemented:** {(cn if c else '—') if not (c and d and te) else '—'}",
            f"- **Still incomplete:** {gap}",
            "",
        ]

    lines += [
        "---",
        "",
        "## 3. HOST-GATED (offline criteria may pass; live proof incomplete)",
        "",
        f"**Count:** {c_host}",
        "",
    ]
    for track, iid, title, bucket, t in sorted(host, key=lambda x: x[1]):
        c, d, te, pct, cn, dn, tn, gap = t
        lines += [
            f"### {iid} — {title}",
            "",
            f"- **Track:** {track}",
            f"- **Complete?** **NO** (host/live required)",
            f"- **Percent:** **{pct}%** (capped; live not proven)",
            f"- **Code:** {'YES' if c else 'NO'} — {cn}",
            f"- **Docs:** {'YES' if d else 'NO'} — {dn}",
            f"- **Tests (offline):** {'YES' if te else 'NO'} — {tn}",
            f"- **Still incomplete:** {gap}",
            "",
        ]

    lines += [
        "---",
        "",
        "## 4. REFUSE-CLOSED (not a feature; policy complete)",
        "",
        f"**Count:** {c_refuse}",
        "",
    ]
    for track, iid, title, bucket, t in sorted(refuse, key=lambda x: x[1]):
        lines += [
            f"### {iid} — {title}",
            "",
            f"- **Track:** {track}",
            f"- **Complete as shipped feature?** **NO**",
            f"- **Policy refuse closed?** **YES**",
            f"- **Percent (policy):** 100% refuse-closed",
            f"- **Still incomplete:** Must not implement",
            "",
        ]

    lines += [
        "---",
        "",
        "## How this file was produced",
        "",
        "```text",
        "python scripts/gen_v1_v6_unified_improved_scorecard.py",
        "```",
        "",
        "- Reads `docs/V1_V6_UNIFIED_SCORECARD.md` **read-only** for ID inventory.",
        "- Writes **only** `docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md`.",
        "- Does **not** modify the file under concurrent validation.",
        "",
    ]

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print("complete", c_complete, "incomplete", c_incomplete, "host", c_host, "refuse", c_refuse, "total", total)
    # verify source untouched mtime optional
    print("source", SOURCE, "exists", SOURCE.is_file())


if __name__ == "__main__":
    main()
