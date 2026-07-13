# SuperAI — Features (aligned with code)

**Repo:** SuperAI_v1 · **Board:** `TASKBOARD.md` · **Tests:** 141 passed  
**Packages:** `core` · `scli` (folder `src/cli`)

## Core

| Feature | Status |
|---------|--------|
| Multi-step orchestration + parallel plans | **Implemented** |
| Mock-first + multi-provider ModelCaller | **Implemented** |
| Scoring router + bandit + failover chain + A/B | **Implemented** |
| Memory Palace (Chroma / FAISS / in-memory) | **Implemented** |
| **Central Memory Palace for all SuperAI-mediated AIs** | **Implemented** |
| Learning, skills, preferences, constitution | **Implemented** |
| Encrypted backup + key export + rclone hooks | **Implemented** |
| Council / hierarchy / agentic roles | **Implemented** |
| **Parallel multi-CLI pool + unified dashboard** | **Implemented** |
| **Parallel multi-terminal pool + unified dashboard** | **Implemented** |
| **Host tools checklist + optional auto-install** | **Implemented** |
| Tool proposals + diff-first edits + workspace jail | **Implemented** |
| Doctor, chat, budget, audit, policy, schedule | **Implemented** |
| MCP server, PWA, VS Code extension scaffold | **Implemented** |
| **Local MCP server for external AIs (shared Memory Palace)** | **Implemented** |
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

## Local MCP server (other AIs share SuperAI memory)

SuperAI runs its **own local MCP server**. Claude Code, Cursor, Codex, Gemini CLI, Grok, etc. connect as MCP clients and use the **same central Memory Palace**.

| Piece | Detail |
|-------|--------|
| Stdio | `superai mcp-serve` |
| Client config | `superai mcp-config` / `--write` → `~/.superai/mcp_client_config.json` |
| HTTP | `superai web` → `POST /mcp` · `GET /api/mcp/tools` · page `/mcp` |
| Memory tools | `superai_memory_search` · `store` · `context` · `learn` · `central_memory_status` |
| CLI tools | `superai_cli_discover` · `cli_run` · `cli_parallel` (through SuperAI → write-back) |
| Orchestration | `superai_run` · `superai_status` · `superai_host_tools` |

## Central Memory Palace (all SuperAI-mediated AIs)

One shared store (`MemoryPalace` at `~/.superai/memory`) for every AI SuperAI runs:

| Path | Inject memory | Write-back outcomes |
|------|---------------|---------------------|
| Orchestrator (`run`) | Yes | Yes |
| External CLI (`cli-run`) | **Default on** (`--no-context` to skip) | **Default on** (`--no-memory` to skip) |
| Multi-CLI (`cli-parallel`) | Yes | Per-job + workflow summary |
| Multi-terminal (`term-parallel`) | N/A (shell) | Workflow summary |
| Council / agentic debate | Yes | Yes |

Opt-out: `central_memory=false` · `SUPERAI_CENTRAL_MEMORY=0` · `SUPERAI_CENTRAL_MEMORY_WRITE=0`

## Host tools (not bundled)

External CLIs are **detected on PATH** and can be **installed via the host package manager** — they are never shipped inside the SuperAI Python package.

| Piece | Detail |
|-------|--------|
| Engine | `core.host_tools` — catalog + `checklist` + `install_tools` |
| Profiles | `core` · `agentic` · `cloud` · `full` |
| Managers | winget / choco / scoop / brew / apt / pip / npm (best available) |
| CLI | `superai host-tools check\|install\|matrix\|profiles` |
| Bootstrap | `scripts/bootstrap.ps1` · `scripts/bootstrap.sh` |
| Auto | `SUPERAI_AUTO_HOST_TOOLS=1` (dry-run on init/onboard) or `=install` (live core) |
| Manual-only | cursor, antigravity, grok (ambiguous), continue — hints/URLs only |

## Key commands

See `QUICK_REFERENCE.md` for the full list. Highlights:

`host-tools` · `cli-parallel` · `cli-jobs` · `term-parallel` · `term-jobs` · `dashboard` · `doctor` · `run` · `chat` · `tdd` · `diff-edit` · `forecast` · `compliance` · `onboard` · `diagnose` · `secrets` · `workspace-index` · `pr-review` · `mcp-serve` · `web` (/pwa/, /cli-pool, /terminals) · `memory-forget` · `lang`

## Deferred host

API keys · Telegram/Slack tokens · rclone remote · GitHub Pages enable
