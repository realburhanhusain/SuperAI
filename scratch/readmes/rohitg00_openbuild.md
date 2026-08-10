# openbuild

Model-agnostic agent shell. Single Rust binary. No vendor lock-in.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Rust](https://img.shields.io/badge/rust-1.80%2B-orange.svg)](#)

## Why

Every AI lab is shipping its own dev shell — and every shell speaks the same shape: prompt, tools, subagents, MCP, skills, hooks, plugins, marketplaces. The model is interchangeable. The harness is what people actually use.

openbuild is the universal harness:
- **Any model.** OpenAI, Anthropic, xAI, Ollama, OpenRouter, Bedrock, Vertex, llama.cpp — same CLI, same flags.
- **Any config.** Imports Claude Code, Cursor, Codex, OpenCode, Aider, Cline, and the generic `AGENTS.md`. Bring your existing setup.
- **No phone-home.** No proxy. No telemetry. No auto-update calls.
- **Reusable primitives.** Roles, personas, agents, skills — composable, forkable, CC0.

## Status

Pre-alpha. M0 scaffolded.

| Milestone | Scope | State |
|---|---|---|
| M0 | core loop + OpenAI-compatible provider + read_file + run_terminal_cmd + jsonl sessions | in progress |
| M1 | provider matrix (Anthropic, xAI, Ollama, OpenRouter) + reasoning_effort routing | pending |
| M2 | TUI + permission engine + universal config import + MCP stdio | pending |
| M3 | sandbox (macOS+Linux) + subagent + skills + worktree + best-of-N | pending |

## Quick start

```bash
cargo install --git https://github.com/rohitg00/openbuild openbuild-cli

# OpenAI
OPENBUILD_API_KEY=sk-... openbuild -p "explain this codebase"

# Anthropic via base_url override
OPENBUILD_BASE_URL=https://api.anthropic.com/v1 \
OPENBUILD_API_KEY=sk-ant-... \
openbuild -m claude-sonnet-4-6 -p "..."

# Ollama (no key needed)
OPENBUILD_BASE_URL=http://localhost:11434/v1 \
openbuild -m llama3 -p "..."

# xAI
OPENBUILD_BASE_URL=https://api.x.ai/v1 \
OPENBUILD_API_KEY=xai-... \
openbuild -m grok-4 -p "..."
```

## Architecture

```
openbuild-cli              # binary, clap wiring
openbuild-core             # Provider trait, Event stream, Message, ToolSchema
openbuild-providers        # OpenAI / Anthropic / Ollama / xAI / ... adapters
openbuild-tools            # read_file, write_file, edit_file, run_terminal_cmd, grep, glob
openbuild-config           # config + universal importers
openbuild-permissions      # Tool(arg) rule engine
openbuild-session          # JSONL session log, resume, share
openbuild-skills           # SKILL.md / AGENTS.md / .cursorrules loader
openbuild-mcp              # MCP client (stdio + http + sse)
openbuild-sandbox          # macOS seatbelt + Linux landlock+seccomp
openbuild-tui              # ratatui frontend
```

See [SPEC.md](SPEC.md) for full design rationale.

## License

Apache-2.0
