# SuperAI feature backlog (M / S / N)

**Wired into:** `TASKBOARD.md`  
**Updated:** 2026-07-14  
**Status:** All implementable backlog items are **done** in code. Only external host smoke remains.

## Must have (M) — all done

| ID | Feature | Status |
|----|---------|--------|
| M1–M8 | doctor, secrets, jail, approval, RO data, resume, first-run, web auth | **done** |

## Should have (S) — all done

| ID | Feature | Status |
|----|---------|--------|
| S1–S12 | stream, chat, planner, budget, failover, tools, project config, audit, backup-key, plugins load, errors, evals | **done** |

## Nice to have (N) — all done in-repo

| ID | Feature | Status |
|----|---------|--------|
| N1 | MCP server | **done** |
| N2 | VS Code extension scaffold | **done** `extensions/vscode-superai/` |
| N3 | Profiles | **done** |
| N4 | Policy | **done** |
| N5 | FAISS / vector backend | **done** (`SUPERAI_MEMORY_BACKEND=faiss`, optional `faiss-cpu`) |
| N6 | Messenger inbound | **done** |
| N7 | Mermaid plan | **done** |
| N8 | Benchmark markdown report | **done** (`benchmark --report`) |
| N9 | Git helpers | **done** |
| N10 | Schedule | **done** |
| N11 | Metrics | **done** |
| N12 | Ticket stub | **done** |
| N13 | Mobile PWA | **done** (`superai web` → `/pwa/`) |
| N14 | Constitution | **done** |
| N15 | Container sandbox | **done** (Docker when enabled) |

## Not in backlog scope (host)

Live API keys, live bots, rclone remote, GitHub Pages admin toggle.
