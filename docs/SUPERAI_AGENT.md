# SuperAI agent

**Updated:** 2026-07-16  

Multi-agent coding UX for SuperAI (`core.superai_agent`).

## Entry points

| Command | What |
|---------|------|
| `superai` | Default SuperAI agent TUI |
| `superai agent` | Same agent TUI / one-shot |
| `superai agent "task"` | One-shot JSON result |
| `superai --ask` | NL product-route REPL |
| `superai ask "…"` | One-shot NL product routes |
| `superai agent-roles` | List build / plan / ask |

## HTTP

| Path | Purpose |
|------|---------|
| `GET /api/superai/roles` | Agent roles |
| `GET /api/superai/sessions` | Sessions |
| `POST /api/superai/run` | One-shot run |

## Package & storage

- Package: `core.superai_agent`
- Sessions: `~/.superai/superai_sessions`
- Env override: `SUPERAI_SESSIONS_ROOT`

## Verify

```powershell
pytest tests/test_superai_agent.py -q
```
