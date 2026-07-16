# SuperAI Quick Reference

**Repo:** `SuperAI` · **Board:** `TASKBOARD.md` · **Progress:** `docs/PROGRESS.md`  
**Packages:** `core` · `scli` · **Tests:** `pytest -q` (114+)

## Install

```powershell
cd C:\Users\burhan.husain\Documents\Personal\github\SuperAI
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
| `install` | Guided install: host tools profile + optional Postgres/pgvector + DSN |
| `install-postgres [--setup-only] [--live]` | Detect/install Postgres, create DB + vector, write `memory_dsn` |
| `host-tools check\|install\|matrix [--profile core\|agentic\|cloud\|full]` | Host CLI checklist + optional install (not bundled) |
| `scripts/bootstrap.ps1` / `bootstrap.sh` | pip + optional `-Interactive` / `--with-postgres` |
| `cli-run NAME "…" [-M MODEL] · name@MODEL` | External CLI run; optional inner model (`--cli-model` / `@`) |
| `cli-run` … `--context/--no-context` · `--memory/--no-memory` | Central Memory Palace inject + write-back (default on) |
| `members [--available] [--with-models] [--live-probe] [--pick]` | API + CLIs + inner models; optional interactive pick |
| Config `central_memory` / env `SUPERAI_CENTRAL_MEMORY` | Master switch for shared Memory Palace |
| `providers [--ready]` | List cloud/local/gateway LLM providers + key env |
| `models-sync-ollama` | Import Ollama tags into user models.json |
| `models-register --name … --model-id … --base-url …` | Any OpenAI-compatible vendor/server |
| `list-models [--refresh]` | Registry models (DeepSeek, Kimi, GLM, NVIDIA, local, …) |
| `ask "…"` / `ask` (REPL) | **Universal NL agent** — any request (routes or orchestrates) |
| `ask "review auth with gpt-4o" --plan-only` | Show planned command only |
| `chat "…"` | Routes NL via `ask` (use `--no-intent` for pure chat) |
| `run "task" --critic off\|light\|council` | Critic mode (default light) |
| `run "task" --replan-approval` | HITL must approve recovery replan |
| `run "task" --with-clis claude,aider [--cli-live]` | After plan, multi-CLI fan-out (dry-run default) |
| `hitl answer <id> approve\|reject` | Answer replan / clarifications |
| `memory-palace layout\|browse\|search\|suggest\|promote\|snapshot` | Palace browser + room promotion |
| `memory-clusters --method auto\|embedding\|wing\|tag` | Memory clustering |
| `wings list\|stats\|browse\|assign\|sync` | Wings & rooms navigation |
| `web` → `/palace` | Interactive Memory Palace browser |
| `search-web "q" --provider duckduckgo` | Instant Answer API (no scrape) |
| `github status\|issues\|prs\|issue-create\|pr\|comment` | GitHub product API / gh CLI |
| `review "…" [-m gpt-4o,cli:gemini@MODEL] [--pick] [--prefer mixed\|cli\|api]` | Multi-member review (API + CLI) |
| `advise "…" [-m …] [--pick] [--prefer mixed\|cli\|api]` | Multi-member advisor board (API + CLI) |
| `council "…" [--models gpt-4o,cli:grok] [--pick] [--prefer mixed\|cli\|api]` | Council with API models and/or CLIs |
| `pr-review --use-clis` | Diff review with CLI board + council (default CLIs on) |
| Env `SUPERAI_MEMORY_BACKEND=pgvector` | Default Memory Palace backend (Postgres+pgvector or SQLite cosine) |
| Env `SUPERAI_MEMORY_DSN` | e.g. `postgresql+psycopg://user:pass@localhost/superai` |
| Env `SUPERAI_MEMORY_BACKEND=faiss` | Optional FAISS offline index |
| Env `SUPERAI_FAISS_INDEX=hnsw` | FAISS HNSW (when backend=faiss) |
| `run "…" --workers gpt-4o,cli:gemini@MODEL [--worker-prefer mixed]` | Worker pool (API + CLIs + failover) |
| `run "…" --pick-workers` | Interactive pick from detected API/CLI models |
| `config set worker_prefer mixed\|api\|cli\|router` | Default worker auto-pick (default mixed) |
| `config set worker_members gpt-4o,cli:claude` | Persistent worker pool |
| `config set cli_delegate_workers true` | Legacy: force CLI-first worker pool |
| `config set cli_delegate_reviewers true` | Orchestrator critic multi-member board (opt-in) |
| `run "…" --model cli:claude` | Force step execution via external CLI (integrated) |
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
| `council` / `delegate` / `roles` / `debate` | Multi-model / multi-CLI |
| Member syntax | `gpt-4o` · `cli:gemini` · `cli:gemini@MODEL` · `gemini@MODEL` |
| `mcp-serve` | Local MCP server (stdio) — other AIs share Memory Palace |
| `mcp-config [--write]` | Client config for Claude Desktop / Cursor / etc. |
| `web` → `POST /mcp` · `/api/mcp/tools` | HTTP MCP + tool listing |
| `langgraph-export` | Interop |
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
| `SUPERAI_MEMORY_BACKEND` | `pgvector` (default) · `faiss` · `memory` |
| `SUPERAI_MEMORY_DSN` | Postgres URL for true pgvector; else SQLite under `~/.superai/memory` |
| `SUPERAI_CONTAINER_SANDBOX` | Docker tool shell |
| `SUPERAI_LANG` | en/es/fr/de |
| `SUPERAI_VERSION_URL` | Update check JSON |
| `*_API_KEY` | Live providers |

## Paths

`~/.superai/` — config, history, memory, skills, backups, audit, chats, diagnostics
