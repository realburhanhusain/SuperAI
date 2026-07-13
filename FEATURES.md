# SuperAI — Features (aligned with code)

**Repo:** SuperAI_v1 · **Board:** `TASKBOARD.md` · **Tests:** 123 passed  
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
| **Parallel multi-terminal pool + unified dashboard** | **Implemented** |
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

## Parallel multi-terminal (agentic)

Run several shell terminals at once; every session is visible in one place.

| Piece | Detail |
|-------|--------|
| Engine | `core.terminal_pool.ParallelTerminalManager` — ThreadPool + `~/.superai/terminal_sessions.json` |
| Agentic | Role terminals + supervisor merge of stdout |
| Dashboard | `superai dashboard` — **Parallel terminals** panel (side-by-side with CLI pool) |
| Web | `/terminals` page · `/api/terminals` JSON |
| CLI | `term-parallel` · `term-jobs list\|snapshot\|clear` |
| Safety | Dry-run default; argv only (`shell=False`); workspace jail for cwd; block shell meta unless `SUPERAI_ALLOW_SHELL_META=1` |

## Key commands

See `QUICK_REFERENCE.md` for the full list. Highlights:

`cli-parallel` · `cli-jobs` · `term-parallel` · `term-jobs` · `dashboard` · `doctor` · `run` · `chat` · `tdd` · `diff-edit` · `forecast` · `compliance` · `onboard` · `diagnose` · `secrets` · `workspace-index` · `pr-review` · `mcp-serve` · `web` (/pwa/, /cli-pool, /terminals) · `memory-forget` · `lang`

## Deferred host

API keys · Telegram/Slack tokens · rclone remote · GitHub Pages enable
