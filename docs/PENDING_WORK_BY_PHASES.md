# SuperAI — Pending Work by Phases

**Last Updated:** 2026-07-14  
**Status:** Code tracks A–J complete. Prefer **`TASKBOARD.md`**.

---

## How to Use

This file is a **phase-oriented backlog**. Almost all implementation items are done.  
Only **deferred smoke** remains.

---

## Next priorities

| # | Task | Type |
|---|------|------|
| 1 | Live multi-provider smoke | External keys |
| 2 | Live Telegram/Slack E2E | External tokens |
| 3 | rclone remote E2E | Host rclone config |
| 4 | Enable GitHub Pages | Repo admin |

---

## Phases 1–8 — implementation

| Phase | Implementation | Remaining |
|-------|----------------|-----------|
| 1 Core | Done (+ TaskResult Pydantic) | — |
| 2 Routing | Done (+ bandit blend) | Live key smoke |
| 3 Memory | Done | — |
| 4 Skills | Done | — |
| 5 Backup | Done (rclone hooks) | rclone E2E |
| 6 Polish | Done (docs/CI/completion) | Pages enable |
| 7 Advanced | Done (CLI, bandit, dual dash, proposals) | — |
| 8 Agentic | Done (debate, hierarchy, MCP, ecosystem) | Live messengers |

---

## Definition of “done” for deferred smoke

- `superai smoke-providers` succeeds with at least one real key  
- `superai msg-send -c telegram|slack` delivers with real tokens  
- `superai backup --cloud` + `restore --cloud` against a real remote  
- GitHub Actions Pages deployment URL works after admin enable  

Until then, full suite: `pytest -q` in mock mode.
