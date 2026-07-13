# AGENTS.md — SuperAI_v1

Instructions for any AI agent working in this repository.

## Canonical path

```
C:\Users\burhan.husain\Documents\Personal\github\SuperAI_v1
```

There is also a thinner sibling at `...\github\SuperAI` (plans + skeleton). **Prefer SuperAI_v1 for code.** Plans live in both; v1 has the full modules.

## Always resume from the taskboard + checkpoints

1. Read **latest** `docs/checkpoints/CHECKPOINT_*.md` (if any) and **`TASKBOARD.md`**.
2. Read **`docs/PROGRESS.md`** for phase % snapshot.
3. Do **not** restart packaging or re-do completed tracks unless tests fail.
4. Pick the highest-priority incomplete item (`[ ]` or `[~]`).
5. Work autonomously through the plan; **do not stop for approval** between planned items unless blocked externally (`[!]` — keys, network, cloud credentials, GitHub admin).
6. There is **no daily resume task**; continue in-session until blocked or plan complete.
7. After each item (or ~30–45 min): update TASKBOARD Last session, then run:
   `powershell -File scripts/checkpoint.ps1 -Label "<item-id>"`
8. See **`docs/CHECKPOINT_PROTOCOL.md`**.

## Scope (non-negotiable)

- `implementation_plan_detailed.md` and `implementation_plan_v2.md` define **required** product scope.
- Features may be **sequenced later** (Tracks G–I).
- Features are **never optional**. Do not label plan work as optional, nice-to-have, or cancelled.
- Only the project owner may amend the plan to drop scope.

## Implementation guides (in order)

1. `implementation_plan_detailed.md` — exhaustive DoD / algorithms  
2. `implementation_plan_v2.md` — consolidated blueprint  
3. `codes.md` — reuse existing snippets before rewriting  
4. `docs/STABILIZATION_STATUS.md` — honest status after Track A  

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

Resume from `TASKBOARD.md`. Feature backlog: `docs/FEATURE_BACKLOG.md`. Security: `docs/SECURITY_REVIEW.md`.

## Rules

- Prefer small, reversible commits of work per taskboard ID (B1, B2, …).
- Never log API keys.
- Do not claim Phase 2–5 complete without tests + smoke evidence.
- Keep marketing docs (`README`, `SUPERAI_FINAL_SUMMARY`) honest.
- When unsure, re-read TASKBOARD + Phase DoD rather than inventing new architecture.
