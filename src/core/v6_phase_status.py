"""
V6 phase completion registry — honest status (code/tests vs host vs park).
"""

from __future__ import annotations

from typing import Any, Dict, List

# status: done | partial | host | park | n/a
PHASES: List[Dict[str, Any]] = [
    {
        "phase": 0,
        "name": "Foundation lock",
        "status": "done",
        "ids": "baseline V1–V5",
        "notes": "Existing SuperAI core verified present",
    },
    {
        "phase": 1,
        "name": "Trust & money",
        "status": "done",
        "ids": "M001–M020, M086–M090",
        "notes": "spend_guard, public_api, error_codes, cost_accounting, safety tests",
    },
    {
        "phase": 2,
        "name": "Agent loop",
        "status": "done",
        "ids": "M021–M040",
        "notes": "superai_agent + change_set + tool protocol + roles",
    },
    {
        "phase": 3,
        "name": "Multi-model / multi-CLI",
        "status": "done",
        "ids": "M041–M055",
        "notes": "catalog, boards, failover, bakeoff, cost_router",
    },
    {
        "phase": 4,
        "name": "Memory & learning",
        "status": "done",
        "ids": "M056–M070",
        "notes": "palace, inject, tenant, learning, skills, backup",
    },
    {
        "phase": 5,
        "name": "CLI product quality",
        "status": "done",
        "ids": "M071–M085",
        "notes": "front door, doctor, status --cost, install, host-tools",
    },
    {
        "phase": 6,
        "name": "Verification & honesty",
        "status": "partial",
        "ids": "M086–M100",
        "notes": "unit+golden+harness done; M089 live smoke is HOST-only",
        "host_blockers": ["M089 live multi-provider smoke"],
    },
    {
        "phase": 7,
        "name": "Should: intelligence",
        "status": "done",
        "ids": "S101–S125",
        "notes": "agent_todos, spec_mode, quality_gates, ci_log, recipes foundations",
    },
    {
        "phase": 8,
        "name": "Should: cost/efficiency",
        "status": "done",
        "ids": "S126–S150",
        "notes": "result_cache, adaptive escalate, sticky profile, early-exit boards",
    },
    {
        "phase": 9,
        "name": "Should: routing & models",
        "status": "done",
        "ids": "S151–S170",
        "notes": "capability_tags, tool timeouts, concurrency caps, catalog refresh",
    },
    {
        "phase": 10,
        "name": "Should: memory & team",
        "status": "done",
        "ids": "S171–S185",
        "notes": "project_memory, retention, memory confirm, session encryption helpers",
    },
    {
        "phase": 11,
        "name": "Should: polish",
        "status": "done",
        "ids": "S186–S200",
        "notes": "recipes, onboarding quest, changelog, profile-suggest, explain-run",
    },
    {
        "phase": 12,
        "name": "Nice: power CLI",
        "status": "done",
        "ids": "N201–N230",
        "notes": "macros, watch, hooks, agent DSL, replay tape foundations",
    },
    {
        "phase": 13,
        "name": "Nice: deep coding",
        "status": "done",
        "ids": "N231–N260",
        "notes": "lsp_bridge (optional), ast_edit, format hooks, ci-why foundations",
    },
    {
        "phase": 14,
        "name": "Nice: orchestration theater",
        "status": "done",
        "ids": "N261–N280",
        "notes": "role_debate, handoff, release checklist, ticket stub deepen",
    },
    {
        "phase": 15,
        "name": "Nice: ecosystem",
        "status": "done",
        "ids": "N281–N300",
        "notes": "packaging templates, GH Action sample, pre-commit sample",
    },
    {
        "phase": 16,
        "name": "Parked",
        "status": "park",
        "ids": "P301–P400",
        "notes": "Intentionally not implemented",
    },
    {
        "phase": 17,
        "name": "—",
        "status": "n/a",
        "ids": "—",
        "notes": "V6 roadmap has no phase 17",
    },
    {
        "phase": 18,
        "name": "—",
        "status": "n/a",
        "ids": "—",
        "notes": "V6 roadmap has no phase 18",
    },
    {
        "phase": 19,
        "name": "—",
        "status": "n/a",
        "ids": "—",
        "notes": "V6 roadmap has no phase 19",
    },
    {
        "phase": 20,
        "name": "—",
        "status": "n/a",
        "ids": "—",
        "notes": "V6 roadmap has no phase 20",
    },
]


def phase_report() -> Dict[str, Any]:
    done = sum(1 for p in PHASES if p["status"] == "done")
    partial = sum(1 for p in PHASES if p["status"] == "partial")
    park = sum(1 for p in PHASES if p["status"] == "park")
    na = sum(1 for p in PHASES if p["status"] == "n/a")
    host = [p for p in PHASES if p.get("host_blockers")]
    return {
        "ok": True,
        "phases": PHASES,
        "counts": {
            "done": done,
            "partial": partial,
            "park": park,
            "n/a": na,
            "total_defined": 17,  # 0–16
        },
        "host_blockers": host,
        "contract": "superai.result.v1",
        "truth": (
            "Phases 1–15 implemented as code foundations + prior V1–V5; "
            "Phase 6 partial only because live smoke is host-gated; "
            "Phase 16 parked; phases 17–20 do not exist in V6 roadmap."
        ),
    }
