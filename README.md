# SuperAI (v1 codebase)

**SuperAI** is a multi-model AI orchestration platform under active development.  
This repository (`SuperAI_v1`) is the **canonical code tree**.

> **Honest status (2026-07-13):** Tracks A–E done (Phase 1 foundation + core of Phases 2–5 in mock/local mode).  
> Remaining plan features (live multi-provider, cloud backup, Phase 6–8) are **required** and sequenced as Tracks F–I — **not optional**.  
> Always resume from **[TASKBOARD.md](TASKBOARD.md)**.

## Docs for implementers

| Document | Purpose |
|----------|---------|
| [TASKBOARD.md](TASKBOARD.md) | **What is done / pending** (resume here) |
| [AGENTS.md](AGENTS.md) | Agent rules & environment |
| [implementation_plan_detailed.md](implementation_plan_detailed.md) | Full phase plan + DoD |
| [implementation_plan_v2.md](implementation_plan_v2.md) | Consolidated blueprint |
| [codes.md](codes.md) | Reusable code snippets |
| [docs/STABILIZATION_STATUS.md](docs/STABILIZATION_STATUS.md) | Stabilization notes |

## Features (current vs planned)

| Area | Status |
|------|--------|
| CLI (`init`, `run`, `history`, `config`, `status`) | Working (mock) |
| Config + logging + task history | Working |
| Orchestrator multi-step plans | Working (mock model calls) |
| Model registry (`config/models.json`) | Working |
| Intelligent routing + circuit breaker | Partial (Phase 2) |
| Memory Palace / LearningEngine | Partial (Phase 3) |
| Skills system | Draft (Phase 4) |
| Encrypted backup | Draft (Phase 5) |
| External CLI discovery | Required — pending Track H |
| Cloud backup (rclone) | Required — pending Track F5 |
| Phase 6 polish / CI / docs | Required — pending Track G |
| Phase 7–8 advanced features | Required — pending Tracks H–I |

## Installation

```powershell
cd C:\Users\burhan.husain\Documents\Personal\github\SuperAI_v1
pip install -e ".[dev]"
```

Requires Python 3.10+.

## Phase 1 quick verify (Windows)

```powershell
superai version
superai init --non-interactive
superai config show
superai list-models
superai run "Create a FastAPI hello world" -v --format json
superai history --limit 5
superai status
pytest -q
```

Expected: mock run returns `"success": true` and a `task_id`; history lists the run.

## Common commands

| Command | Description |
|---------|-------------|
| `superai init` | Create `~/.superai/` layout + default config |
| `superai run "<task>"` | Run orchestrated task (mock by default) |
| `superai run ... --format json` | Structured JSON result |
| `superai plan "<task>"` | Show plan only |
| `superai history` | Recent runs |
| `superai config show\|get\|set` | Configuration |
| `superai list-models [--refresh]` | Registry models |
| `superai set-supervisor <model>` | Persist default supervisor |
| `superai backup` / `backup-status` | Backup draft commands |

## Configuration

- File: `~/.superai/config.json`
- Env overrides: `SUPERAI_MOCK_MODE`, `SUPERAI_LOG_LEVEL`, `SUPERAI_DEFAULT_SUPERVISOR`, `SUPERAI_NON_INTERACTIVE`
- Models: `config/models.json` in this repo (loaded by `ModelRegistry`)

Default **`mock_mode: true`** — no API keys required for local smoke tests.  
Set keys (`XAI_API_KEY`, `OPENAI_API_KEY`, …) and `mock_mode: false` for live calls (Phase 2 maturity).

## Architecture (target)

See [docs/architecture.md](docs/architecture.md). Runtime path today:

```
CLI → SuperAIOrchestrator → TaskPlanner → ModelRouter → ModelCaller (mock/live)
                         ↘ History / MemoryPalace learn hook
```

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Read [AGENTS.md](AGENTS.md) and pick the next open item on [TASKBOARD.md](TASKBOARD.md).
