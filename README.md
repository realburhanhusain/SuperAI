# SuperAI

**SuperAI** is a multi-model AI orchestration platform: plan → route → execute → learn, with safety rails.

**Canonical tree:** this repo (`Documents\Personal\github\SuperAI`).  
**Resume:** [TASKBOARD.md](TASKBOARD.md) · **Backlog:** [docs/FEATURE_BACKLOG.md](docs/FEATURE_BACKLOG.md)

> **Status (2026-07-14):** Feature backlog (M/S/N waves 1–2) **implemented in code**.  
> Remaining: **host smoke** only (API keys, live bots, rclone, GitHub Pages).  
> **Tests:** `pytest -q` → **114 passed**.

## Layout

```
src/
  cli/     # Typer CLI + web/PWA  (import: scli)
  core/    # domain logic         (import: core)
extensions/vscode-superai/   # VS Code extension scaffold
```

Entry point: `superai` → `scli.main:app`

## Install

```powershell
cd C:\Users\burhan.husain\Documents\Personal\github\SuperAI
pip install -e ".[dev]"
# Optional: pip install -e ".[web]" ".[embeddings]" ".[vector]" ".[data]"
superai onboard
superai doctor
```

**Local MCP** (other AIs share SuperAI Memory Palace):

```powershell
superai mcp-config --write    # ~/.superai/mcp_client_config.json for Claude/Cursor
superai mcp-serve             # stdio MCP server
# HTTP: superai web  →  POST /mcp  ·  GET /api/mcp/tools
```

**Host tools** (git, gh, aws, claude, gemini, …) are **not** bundled in the SuperAI package. They are detected on PATH and can be installed via winget/brew/apt/pip/npm:

```powershell
superai host-tools check --profile full
superai host-tools install --profile core --dry-run   # preview
superai host-tools install --profile agentic --live   # install missing
# Or one-shot bootstrap (pip + host-tools dry-run):
powershell -File scripts\bootstrap.ps1
# Live host installs:
powershell -File scripts\bootstrap.ps1 -Profile agentic -LiveHostTools
# Optional auto on init/onboard:
$env:SUPERAI_AUTO_HOST_TOOLS = "1"        # dry-run core
$env:SUPERAI_AUTO_HOST_TOOLS = "install"  # live core
```

## Quick start

```powershell
superai run "Create a FastAPI hello world" -v --format json
superai chat "explain the last task" --new
superai tdd "add a unit test for X"
superai web   # http://127.0.0.1:8787  and  /pwa/
```

## Docs

| Doc | Purpose |
|-----|---------|
| [TASKBOARD.md](TASKBOARD.md) | Live status |
| [FEATURES.md](FEATURES.md) | Feature matrix |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Commands |
| [docs/PROGRESS.md](docs/PROGRESS.md) | Phase % |
| [docs/SECURITY_REVIEW.md](docs/SECURITY_REVIEW.md) | Security |
| [docs/architecture.md](docs/architecture.md) | Architecture |
| [CHANGELOG.md](CHANGELOG.md) | Release notes |
| [AGENTS.md](AGENTS.md) | Agent rules |

## Feature summary

Orchestration, multi-provider routing, bandit/A/B, memory (Chroma/FAISS), skills, encrypted backup, council/hierarchy, tool proposals, doctor/chat/TDD/diff-edit, compliance, GDPR forget, MCP, PWA, VS Code extension, and more — see FEATURES.md.

**Deferred (host):** live multi-provider E2E, live Telegram/Slack, rclone remote, Pages enable.

## License

MIT — see [LICENSE](LICENSE).
