# AGENTS.md — SuperAI

Instructions for any AI agent working in this repository.

## Canonical path

```
C:\Users\burhan.husain\Documents\Personal\github\SuperAI
```

This is the **canonical SuperAI codebase** (renamed from `SuperAI_v1`).  
Siblings such as `SuperAI_Master` / `SuperAI_v2` are separate trees — **prefer this `SuperAI` repo for product code.**

## Always resume from the taskboard

1. Read **`TASKBOARD.md`** (index), then **your owner board**:
   - **Grok** → `TASKBOARD_GROK.md` (learning, routing, streaming honesty, dashboard, host smoke)
   - **AGY** → `TASKBOARD_AGY.md` (spend, contracts, JSON/MCP surfaces, cost, TOP_30)
2. Strict scorecard: **`docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md`**. Docs map: **`docs/README.md`**.
3. Do **not** re-open **archived** docs under `docs/archive/` unless tests fail / regression proven.
4. Pick the highest-priority incomplete item on **your** board (`[ ]` or `[~]`).
5. Work autonomously through the plan; **do not stop for approval** between planned items unless blocked externally (`[!]` — keys, network, cloud credentials, GitHub admin).
6. There is **no daily resume task**; continue in-session until blocked or plan complete.
7. After each item (or ~30–45 min): update **your** owner board Last session (and index if needed), then run:
   `powershell -File scripts/checkpoint.ps1 -Label "<item-id>"`
8. See **`docs/CHECKPOINT_PROTOCOL.md`**. New checkpoints still go under `docs/checkpoints/`; historical ones are in `docs/archive/2026-07-25-checkpoints/`.

## Scope (non-negotiable)

- `implementation_plan_detailed.md` and `implementation_plan_v2.md` define **required** product scope.
- Features may be **sequenced later** (Tracks G–I).
- Features are **never optional**. Do not label plan work as optional, nice-to-have, or cancelled.
- Only the project owner may amend the plan to drop scope.

## Implementation guides (in order)

1. `implementation_plan_detailed.md` — exhaustive DoD / algorithms  
2. `implementation_plan_v2.md` — consolidated blueprint  
3. `codes.md` — reuse existing snippets before rewriting  
4. Owner taskboard + strict scorecard (above) — current status  

## Environment

- OS: Windows · shell: PowerShell or Git Bash  
- Python: `python` (3.10+), not necessarily `python3`  
- Install: `pip install -e .` from repo root  
- CLI: `superai ...` after install  
- Runtime data: `~/.superai/` (config, logs, history, memory, skills, backups)  
- Default: **mock_mode=true** — no API keys required for Phase 1  

## Package layout

```
src/superai/
  cli/main.py          # Typer app entry
  core/                # config, logger, orchestrator, models, memory, ...
```

Entry point: `superai = "scli.main:app"` (folders `src/cli` + `src/core`; imports `scli` + `core`)

Resume from `TASKBOARD.md` → owner board (`TASKBOARD_GROK.md` / `TASKBOARD_AGY.md`). Security: `docs/SECURITY_REVIEW.md`. Closed plans/reviews: `docs/archive/`.

## Rules

- Prefer small, reversible commits of work per taskboard ID (B1, B2, …).
- Never log API keys.
- Do not claim Phase 2–5 complete without tests + smoke evidence.
- Keep marketing docs (`README`, `SUPERAI_FINAL_SUMMARY`) honest.
- When unsure, re-read your owner TASKBOARD + Phase DoD rather than inventing new architecture.
- Closed handoffs/plans/scorecards live under `docs/archive/` only (not under `docs/` root).
