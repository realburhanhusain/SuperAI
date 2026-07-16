# SuperAI agent (product name)

**Updated:** 2026-07-16  

SuperAI’s multi-agent coding UX is branded **SuperAI**, not a third-party product name.  
Architecture patterns (multi-agent, tool loop, sessions, TUI) were inspired by open-source
coding agents; SuperAI is **not a fork**.

## Entry points

| Command | What |
|---------|------|
| `superai` | **Default** — SuperAI agent TUI |
| `superai agent` | Same agent TUI / one-shot |
| `superai agent "task"` | One-shot JSON result |
| `superai --ask` | NL product-route REPL (`ask` routes) |
| `superai ask "…"` | One-shot NL product routes |
| `superai agent-roles` | List build / plan / ask |
| `superai opencode` | **Deprecated** hidden alias → agent |

## HTTP

| Path | Notes |
|------|--------|
| `GET /api/agent/roles` | Preferred |
| `GET /api/agent/sessions` | Preferred |
| `POST /api/agent/run` | Preferred |
| `/api/opencode/*` | Deprecated aliases |

## Package

- Preferred: `core.super_agent`
- Deprecated re-export: `core.opencode_agent`

Sessions: `~/.superai/agent_sessions` (legacy `opencode_sessions` still read if present).

## Verify

```powershell
pytest tests/test_super_agent.py -q
```
