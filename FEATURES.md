# SuperAI — Features (aligned with code)

**Repo:** SuperAI_v1 · **Board:** `TASKBOARD.md` · **Tests:** 117 passed  
**Packages:** `core` · `scli` (folder `src/cli`)

## Core

| Feature | Status |
|---------|--------|
| Multi-step orchestration + parallel plans | **Implemented** |
| Mock-first + multi-provider ModelCaller | **Implemented** |
| Scoring router + bandit + failover chain + A/B | **Implemented** |
| Memory Palace (Chroma / FAISS / in-memory) | **Implemented** |
| Learning, skills, preferences, constitution | **Implemented** |
| Encrypted backup + key export + rclone hooks | **Implemented** |
| Council / hierarchy / agentic roles | **Implemented** |
| **Parallel multi-CLI pool + unified dashboard** | **Implemented** |
| Tool proposals + diff-first edits + workspace jail | **Implemented** |
| Doctor, chat, budget, audit, policy, schedule | **Implemented** |
| MCP server, PWA, VS Code extension scaffold | **Implemented** |
| Compliance mode, GDPR forget/TTL, i18n, telemetry | **Implemented** |
| TDD loop, PR review, notebook runner, browser tool | **Implemented** |
| Live multi-provider E2E | **Deferred smoke** |

## Parallel multi-CLI (agentic)

Run several external AI CLIs at once; every worker is visible in one place.

| Piece | Detail |
|-------|--------|
| Engine | `core.cli_pool.ParallelCLIManager` — ThreadPool + `~/.superai/cli_jobs.json` |
| Agentic | Role fan-out (architect / implementer / tester / reviewer) + supervisor merge |
| Terminal | `superai dashboard` — **Parallel CLI workers** panel |
| Web | `/cli-pool` page · `/api/cli-pool` JSON |
| CLI | `cli-parallel` · `cli-jobs list\|snapshot\|clear` |
| Safety | Dry-run default; auto dry-run if CLI not on PATH |

## Key commands

See `QUICK_REFERENCE.md` for the full list. Highlights:

`cli-parallel` · `cli-jobs` · `dashboard` · `doctor` · `run` · `chat` · `tdd` · `diff-edit` · `forecast` · `compliance` · `onboard` · `diagnose` · `secrets` · `workspace-index` · `pr-review` · `mcp-serve` · `web` (/pwa/, /cli-pool) · `memory-forget` · `lang`

## Deferred host

API keys · Telegram/Slack tokens · rclone remote · GitHub Pages enable
