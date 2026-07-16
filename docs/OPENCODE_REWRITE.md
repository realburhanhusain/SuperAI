# SuperAI OpenCode-style agent rewrite

**Updated:** 2026-07-16  
**Status:** Implemented (SuperAI-native; **not** a fork of OpenCode Go/JS)  
**Next:** Phase 99 live multi-vendor smoke  

## Why

Earlier MoSCoW marked “full OpenCode rewrite” as out of scope and shipped TUI polish (W1–W8).  
This sprint **implements a full OpenCode-inspired agent stack** inside SuperAI:

| OpenCode idea | SuperAI implementation |
|---------------|------------------------|
| Multi-agent roles | `build` / `plan` / `ask` in `opencode_agent/agents.py` |
| Tool loop | `AgentRuntime` + `tool_protocol` + `tools_bridge` |
| Full message sessions | `OpenCodeSessionStore` (`~/.superai/opencode_sessions`) |
| Native TUI | Multi-panel Rich TUI (`opencode_agent/tui.py`) |
| Model-agnostic | SuperAI `ModelCaller` + registry / failover |
| Client/server | HTTP `POST /api/opencode/run` + session list |
| Permissions | plan / ask / auto / yolo |

## Commands

```powershell
# Interactive OpenCode-style TUI (also default agent-tui)
superai opencode
superai agent-tui --agent build
superai agent-tui --legacy          # old simple TUI

# One-shot
superai opencode "summarize src/core/config.py" --agent ask
superai opencode-agents

# Web
# POST /api/opencode/run  {"prompt":"…","agent":"build","permission":"plan"}
# GET  /api/opencode/agents
# GET  /api/opencode/sessions
```

## TUI slash commands

`/agent` `/model` `/permission` `/new` `/sessions` `/resume` `/export` `/undo`  
`/cost` `/tools` `/trace` `/stream` `/layout` `/help` `/exit`

## Layout

```
┌ header: session · agent · model · permission ─────────────┐
│ messages (user/assistant + tool parts) │ tools / events   │
└ status: cost · tokens · msg count ────────────────────────┘
```

## Not remaining “not important” code work

| Item | Status |
|------|--------|
| W1–W8 polish | done prior |
| OpenCode rewrite | **done this sprint** |
| Voice file fallback | done |
| Notion local log list | done |
| Live multi-vendor smoke | **Phase 99 next** |

## Verify

```powershell
pytest tests/test_opencode_agent.py tests/test_not_important.py -q
```

## Honesty

This is a **full product rewrite of SuperAI’s coding-agent UX** using OpenCode’s architecture patterns.  
It is **not** a port of the OpenCode Go/Bun codebase or Bubble Tea TUI.
