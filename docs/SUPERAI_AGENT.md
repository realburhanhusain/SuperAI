# SuperAI agent (product name)

**Updated:** 2026-07-16  

SuperAI multi-agent coding UX — branded **SuperAI**, not a third-party product.

## Entry points

| Command | What |
|---------|------|
| `superai` | **Default** — SuperAI agent TUI |
| `superai agent` | Same agent TUI / one-shot |
| `superai agent "task"` | One-shot JSON result |
| `superai --ask` | NL product-route REPL |
| `superai ask "…"` | One-shot NL product routes |
| `superai agent-roles` | List build / plan / ask |

## HTTP

| Path | Notes |
|------|--------|
| `GET /api/superai/roles` | Preferred |
| `GET /api/superai/sessions` | Preferred |
| `POST /api/superai/run` | Preferred |
| `/api/agent/*` | Deprecated alias |
| `/api/opencode/*` | Deprecated alias |

## Package

- Preferred: `core.superai_agent`
- Deprecated: `core.super_agent`, `core.opencode_agent`

Sessions: `~/.superai/superai_sessions`  
Env: `SUPERAI_SESSIONS_ROOT` (legacy: `SUPERAI_AGENT_ROOT`, `SUPERAI_OPENCODE_ROOT`)

## Verify

```powershell
pytest tests/test_superai_agent.py -q
```
