# Changelog

All notable SuperAI_v1 releases / checkpoints.

## [0.1.0] — 2026-07-14

### Complete (code)

- **Tracks A–J**: foundation, routing, memory, skills, backup, polish, advanced, agentic, other-tools
- **Parallel plan execution** with `depends_on` / `can_run_parallel`
- **Pydantic** `TaskResult` / `StepResult` validation
- **MCP-style context packs** (`context-pack`, `cli-run --context`)
- **Dual dashboard** (terminal + web `/dashboard`, shared snapshot)
- **Ecosystem hub** (`search-web`, `emit-event`, n8n/Zapier/Make hooks)
- **Messengers** Telegram/Slack/webhook + dry-run
- **Vega-Lite** interactive HTML + `/charts`
- **Plugin marketplace** registry
- **Bandit** blended into ModelRouter + orchestrator rewards
- **Databao** NL data adapter
- Preferences, file time-travel, hierarchical `delegate`, council voting

### Deferred smoke (host)

- Live API keys, live messengers, rclone remote, GitHub Pages enablement

### Tests

- `pytest -q` — 60+ unit tests (mock-first)

### Checkpoints

See `docs/checkpoints/` and `scripts/checkpoint.ps1`.
