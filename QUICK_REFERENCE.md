# SuperAI Quick Reference

**Repo:** `SuperAI_v1` · **Board:** `TASKBOARD.md` · **Progress:** `docs/PROGRESS.md`  
**Packages:** `core` · `scli` · **Tests:** `pytest -q` (114+)

## Install

```powershell
cd C:\Users\burhan.husain\Documents\Personal\github\SuperAI_v1
pip install -e ".[dev]"
# Optional: .[web] .[embeddings] .[vector] .[data]
superai --install-completion
```

## First-time

```powershell
superai init --non-interactive
# or
superai onboard
superai doctor
superai run "hello" --format json
```

## Everyday

| Command | Purpose |
|---------|---------|
| `cli-parallel "task" [--clis a,b] [--dry-run\|--live]` | Multi-CLI parallel agentic workers |
| `cli-jobs list\|snapshot\|clear` | Parallel CLI job registry |
| `term-parallel "task" [--commands a;b] [--dry-run\|--live]` | Multi-terminal parallel agentic shells |
| `term-jobs list\|snapshot\|clear` | Parallel terminal session registry |
| `dashboard` / `web` → `/cli-pool` · `/terminals` | Single dashboard for CLI + terminal workers |
| `run "<task>"` | Orchestrated multi-step run |
| `run … --resume ID` | Resume checkpoint |
| `run … --stream -m model` | Stream single-model output |
| `chat "msg" [--new\|-s ID]` | Multi-turn chat |
| `tdd "implement X"` | Code + test loop |
| `plan "…" --export mermaid\|json\|md` | Plan export |
| `doctor` / `diagnose` / `update` | Health, diagnostics zip, version |
| `forecast "task"` | Cost estimate |
| `diff-edit PATH CONTENT` | Diff-first file edit |
| `workspace-index [-q query]` | Code map |
| `secrets set\|get\|list\|inject` | Secure secrets |
| `budget show\|set` | Spend limits |
| `compliance enable` | Local-only strict mode |
| `feedback ID "…"` | Feedback → learning + bandit |
| `pr-review [--ref HEAD~1]` | Council review of git diff |
| `web` | Memory UI + `/pwa/` + `/ws/dashboard` |

## Memory & data

| Command | Purpose |
|---------|---------|
| `memory-chat` / `memory-clusters` / `memory-forget` / `memory-ttl` | Memory ops |
| `memory-sync export\|import -p` | Encrypted team sync pack |
| `data-ask` / `data-schema` | NL SQL analytics |
| `learnings` / `reflect` / `conflicts` / `evolve` | Learning |

## Ops & safety

| Command | Purpose |
|---------|---------|
| `audit` / `policy` / `constitution` | Audit + rules |
| `backup` / `backup-key` / `restore` | Encrypted backup |
| `rate-queue` / `ab-route` / `failover` | Resilience |
| `profile-bundle export\|import` | Move profile |
| `telemetry enable\|disable` / `lang en` | Telemetry + i18n |

## Advanced

| Command | Purpose |
|---------|---------|
| `council` / `delegate` / `roles` / `debate` | Multi-model |
| `mcp-serve` / `langgraph-export` | Interop |
| `browse URL` / `notebook` / `git-helper` | Tools |
| `plugins` / `plugin-catalog` / `skill-perms` | Plugins |
| `schedule` / `metrics` / `evals` / `benchmark --report` | Ops |
| `speak` / `listen` / `ticket` / `msg-inbound` | Extra surfaces |

## Env (selected)

| Variable | Purpose |
|----------|---------|
| `SUPERAI_MOCK_MODE` | true/false |
| `SUPERAI_WORKSPACE` | Path jail root |
| `SUPERAI_WEB_TOKEN` | Web API auth |
| `SUPERAI_MEMORY_BACKEND` | `faiss` for vector store |
| `SUPERAI_CONTAINER_SANDBOX` | Docker tool shell |
| `SUPERAI_LANG` | en/es/fr/de |
| `SUPERAI_VERSION_URL` | Update check JSON |
| `*_API_KEY` | Live providers |

## Paths

`~/.superai/` — config, history, memory, skills, backups, audit, chats, diagnostics
