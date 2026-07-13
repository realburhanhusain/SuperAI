# SuperAI (v1 codebase)

**SuperAI** is a multi-model AI orchestration platform.  
This repository (`SuperAI_v1`) is the **canonical code tree**.

> **Status (2026-07-14):** Tracks A–J **implemented** in code (mock-first).  
> Remaining work is **external host smoke** only (API keys, live bots, rclone remote, GitHub Pages toggle) — deferred as the last activity.  
> Always resume from **[TASKBOARD.md](TASKBOARD.md)**.

## Docs for implementers

| Document | Purpose |
|----------|---------|
| [TASKBOARD.md](TASKBOARD.md) | **What is done / pending** (resume here) |
| [AGENTS.md](AGENTS.md) | Agent rules & environment |
| [FEATURES.md](FEATURES.md) | Feature matrix vs code |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Command cheat sheet |
| [docs/architecture.md](docs/architecture.md) | Runtime architecture |
| [docs/PROGRESS.md](docs/PROGRESS.md) | Phase % complete |
| [docs/OTHER_TOOL_FEATURES.md](docs/OTHER_TOOL_FEATURES.md) | Other-tools checklist |
| [CHANGELOG.md](CHANGELOG.md) | Release notes |
| [implementation_plan_detailed.md](implementation_plan_detailed.md) | Full phase plan + DoD |

## Features (summary)

| Area | Status |
|------|--------|
| CLI orchestration (`run`, plan, history, config) | **Done** (mock default) |
| Scoring router + load balancer + circuit breaker | **Done** |
| Bandit-blended routing | **Done** |
| Memory Palace + learning + skills + backup | **Done** |
| Council / hierarchy / agentic debate | **Done** |
| External CLI delegation + MCP context packs | **Done** |
| Messengers (Telegram/Slack/webhook) | **Done** (tokens for live) |
| Databao NL data + interactive Vega charts | **Done** |
| Plugin marketplace registry | **Done** |
| Terminal + web dual dashboard | **Done** |
| Ecosystem webhooks / search stubs | **Done** |
| Parallel multi-step plan execution | **Done** |
| Live multi-provider / rclone / Pages E2E | **Deferred smoke** |

## Installation

```powershell
cd C:\Users\burhan.husain\Documents\Personal\github\SuperAI_v1
pip install -e ".[dev]"
# Optional:
# pip install -e ".[web]"         # FastAPI UI
# pip install -e ".[embeddings]"  # sentence-transformers
# pip install -e ".[data]"        # SQLAlchemy / databao-agent
```

Requires Python 3.10+.

## Quick verify (no API keys)

```powershell
superai version
superai init --non-interactive
superai run "Create a FastAPI hello world" -v --format json
superai status
pytest -q
```

Shell completion:

```powershell
superai --install-completion
```

## Common commands

| Command | Description |
|---------|-------------|
| `superai run "<task>"` | Orchestrated multi-step run |
| `superai plan "<task>"` | Show plan only |
| `superai council` / `delegate` / `debate` | Multi-model / hierarchical |
| `superai data-ask` / `--chart-html` | NL data analytics + Vega HTML |
| `superai web` / `dashboard` | Web UI / live terminal dashboard |
| `superai msg-send` / `plugins` / `bandit` | Messengers, plugins, bandit |
| `superai context-pack` / `cli-run --context` | MCP-style external handoff |
| `superai search-web` / `emit-event` / `ecosystem` | Ecosystem integrations |
| `superai backup` / `restore` | Encrypted backup (+ rclone when configured) |

See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for the full list.

## Configuration

- File: `~/.superai/config.json`
- Env: `SUPERAI_MOCK_MODE`, `SUPERAI_LOG_LEVEL`, `SUPERAI_USE_BANDIT`, messenger/token vars, provider `*_API_KEY`
- Models: `config/models.json`

Default **`mock_mode: true`** — no API keys required.

## Architecture

```
CLI / Web / Dashboard
        ↓
SuperAIOrchestrator → TaskPlanner (parallel-aware)
        ↓
ModelRouter (+ bandit) → ModelCaller → LoadBalancer
        ↓
History · MemoryPalace · Skills · Preferences · Backup
```

Details: [docs/architecture.md](docs/architecture.md).

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md), and pick the next open item on [TASKBOARD.md](TASKBOARD.md).
