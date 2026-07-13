# SuperAI Quick Reference

**Repo:** `SuperAI_v1` · **Resume:** `TASKBOARD.md` · **Progress:** `docs/PROGRESS.md` · **Checkpoints:** `scripts/checkpoint.ps1`

## Install

```powershell
cd C:\Users\burhan.husain\Documents\Personal\github\SuperAI_v1
pip install -e ".[dev]"
# Optional richer embeddings:
# pip install -e ".[embeddings]"
```

Shell completion (G3):

```powershell
superai --install-completion
# restart shell
```

## First-time setup

```powershell
superai init --non-interactive
```

Creates `~/.superai/` (config, logs, history, memory, skills, backups).

## Core commands

| Command | Description |
|---------|-------------|
| `superai version` / `status` | Version and system status |
| `superai run "<task>" [-v] [-m model] [--format json]` | Orchestrated run (mock by default) |
| `superai plan "<task>"` | Plan only |
| `superai history` | Recent task runs |
| `superai config show\|get\|set` | Configuration |
| `superai list-models [--refresh]` | Model registry |
| `superai set-supervisor <model>` | Default supervisor |
| `superai set-strategy <strategy>` | smart_fallback \| round_robin \| latency_based \| cost_based |
| `superai routing-stats [--explain "..."]` | Routing aggregates |
| `superai smoke-providers [--mock]` | Provider smoke tests |
| `superai provider-health` | Health + quota windows |
| `superai learnings` / `reflect` / `conflicts` / `evolve <topic>` | Learning |
| `superai feedback <task_id> "..."` | Human feedback |
| `superai list-skills` / `skill-promote` / `skill-rollback` | Skills |
| `superai backup [--full] [--cloud] [--keep N]` | Encrypted backup |
| `superai backup-status` / `backup-verify` | Backup ops |
| `superai restore <path>` or `restore --cloud` | Restore local or pull+restore |

## Paths

| Item | Location |
|------|----------|
| Config | `~/.superai/config.json` |
| History | `~/.superai/history/` |
| Memory | `~/.superai/memory/` |
| Skills | `~/.superai/skills/` |
| Backups | `~/.superai/backups/` |
| Encryption key | `~/.superai/.backup_key` (**back up securely**) |
| Provider health | `~/.superai/provider_health.json` |

## Environment

| Variable | Purpose |
|----------|---------|
| `SUPERAI_MOCK_MODE` | true/false |
| `SUPERAI_LOG_LEVEL` | INFO/DEBUG/... |
| `SUPERAI_NON_INTERACTIVE` | skip prompts |
| `SUPERAI_MODELS_URL` | remote models JSON for `--refresh` |
| `SUPERAI_EMBEDDING_MODEL` | HF/ST model id (`auto` default) |
| `SUPERAI_EMBEDDING_HASH` | `1` = offline hash embeddings |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`, `GOOGLE_API_KEY`, … | live providers |

## Strategies

`smart_fallback` (default), `round_robin`, `latency_based`, `cost_based`

## Checkpoint after work

```powershell
powershell -File scripts\checkpoint.ps1 -Label "G1-progress"
```

## Tests

```powershell
pytest -q
```
