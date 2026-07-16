# N209 — Split-pane TUI

**Status:** Production-ready  
**Module:** `src/core/split_pane_tui.py`  
**Agent integration:** `src/core/superai_agent/tui.py`  
**CLI:** `superai split-tui` · slash commands inside `superai agent` / `superai agent-tui`  
**Tests:** `tests/test_split_pane_tui_n209.py`  
**Depends on:** Rich `Layout` (existing SuperAI dependency), M077 agent TUI  

---

## Purpose

N209 upgrades SuperAI’s agent UI from a **single fixed multi-panel frame** to a real **split-pane product**:

| Capability | Behavior |
|------------|----------|
| Layout presets | `classic`, `h-split`, `v-split`, `triple`, `quad`, `focus`, `agent`, `ide` |
| Focus | Highlight active pane; cycle with `/cycle` |
| Hide / show | Remove a pane and reflow remaining tree |
| Ratios | Override e.g. messages:tools `3:1` |
| Persistence | `~/.superai/tui/split_pane.json` |
| Non-interactive | CLI `status` / `layouts` / `demo` for CI and scripts |

This is **not** a full Textual/curses window manager and **not** tmux multiplexing (see N208). It is a SuperAI-native Rich split layout with durable preferences.

---

## Architecture

```text
superai split-tui run
        │
        ▼
  superai_agent.tui.run_superai_agent_tui()
        │
        ├─ slash: /split /layout /focus /cycle /hide /show /ratio …
        │         └─► split_pane_tui.handle_split_slash()
        │
        └─ render_frame(..., use_split=True)
                  └─► split_pane_tui.render_split_frame()
                            ├─ content_from_agent_state()
                            ├─ load_config() / PRESETS
                            ├─ filter_tree(hidden)
                            ├─ apply_ratio_overrides()
                            └─ build_layout() → rich.layout.Layout
```

### Files

| Path | Role |
|------|------|
| `src/core/split_pane_tui.py` | Engine: presets, config, render, slash API |
| `src/core/superai_agent/tui.py` | Interactive agent loop (uses engine) |
| `src/core/tui_commands.py` | Command palette entries for split cmds |
| `~/.superai/tui/split_pane.json` | Saved layout / focus / hidden / ratios |

### Pane catalog

| Pane id | Typical content |
|---------|-----------------|
| `header` | Session, agent, model, permission, stream |
| `messages` | Chat transcript + tool call/result chips |
| `tools` | Tool catalog table |
| `events` | Progress / tool event stream |
| `cost` | Tokens + estimated cost |
| `sessions` | Recent session list |
| `changeset` | Staged write summary |
| `help` | Split-pane help text |
| `status` | Footer status line |

---

## Layout presets

| Name | Description |
|------|-------------|
| `classic` | Messages \| tools (side-by-side, 3:1) |
| `v-split` | Equal side-by-side messages \| tools |
| `h-split` | Messages above tools |
| `triple` | Messages \| tools \| events |
| `quad` | 2×2: messages/tools × events/cost |
| `focus` | Single pane (focused content) |
| `agent` | **Default** — header + messages\|(tools/events) + status |
| `ide` | Header + messages\|(tools/changeset/cost) + status |

Aliases accepted by `/split` / `set_layout`:

| Alias | Resolves to |
|-------|-------------|
| `h`, `horizontal` | `h-split` |
| `v`, `vertical` | `v-split` |
| `side`, `side-by-side` | `classic` |
| `default` | `agent` |
| `2x2` | `quad` |
| `3` | `triple` |

---

## CLI

```powershell
# Interactive agent TUI with split-pane engine
superai split-tui
superai split-tui run --layout triple
superai split-tui run --agent plan --session <id>

# Also available via existing entry points (same engine)
superai agent
superai agent-tui

# Non-interactive
superai split-tui status
superai split-tui layouts
superai split-tui demo agent
superai split-tui demo quad

# Prefer / persist layout without opening TUI
superai split-tui set-layout ide
superai split-tui focus tools
superai split-tui ratio 3:1
superai split-tui reset

# Help text
superai split-tui help
```

### CLI options (`run`)

| Option | Default | Meaning |
|--------|---------|---------|
| `--layout / -l` | (saved) | Apply preset before launch |
| `--agent / -a` | `build` | Agent role |
| `--model / -m` | auto | Model override |
| `--session / -s` | new | Resume session id |
| `--permission` | config | plan\|ask\|auto\|yolo |
| `--mock / --live` | mock | Mock vs live models |

---

## Slash commands (inside agent TUI)

| Command | Action |
|---------|--------|
| `/layout [name]` | Show summary or set preset |
| `/split h\|v\|classic\|triple\|quad\|agent\|ide\|focus` | Layout shortcut |
| `/focus <pane>` | Focus pane (▸ title + bright border) |
| `/cycle` | Focus next visible pane |
| `/hide <pane>` | Hide + reflow |
| `/show <pane>` | Unhide pane |
| `/ratio 3:1` | Override `messages:tools` |
| `/ratio messages:tools=2:1` | Named override |
| `/ratio 3:1:1` | Triple column override |
| `/panes` | Visible / hidden / all |
| `/layouts` | Preset catalog JSON |
| `/split-status` | Full layout summary |
| `/split-reset` | Clear preferences |
| `/split-help` | This command table |

`/help` in the agent TUI also prints the split-pane section.

---

## Config schema

`~/.superai/tui/split_pane.json` example:

```json
{
  "layout": "agent",
  "focus": "messages",
  "hidden": ["sessions"],
  "ratio_overrides": {
    "messages:tools": [3.0, 1.0]
  },
  "border_focused": "bright_cyan",
  "border_normal": "white",
  "updated_at": "2026-07-17T00:00:00Z"
}
```

---

## Programmatic API

```python
from core.split_pane_tui import (
    SplitPaneConfig,
    build_layout,
    set_layout,
    set_focus,
    cycle_focus,
    hide_pane,
    show_pane,
    set_ratio,
    handle_split_slash,
    render_split_frame,
    layout_summary,
    demo_frame,
)

set_layout("triple")
set_focus("events")
set_ratio("3:1:1")
print(layout_summary())

# Pure render (tests / headless)
cfg = SplitPaneConfig(layout="quad", focus="messages")
layout = build_layout({"messages": "hi", "tools": "t"}, cfg=cfg)

# Agent-shaped frame
layout = render_split_frame(state=session_state, events=[], tools_info=[])
```

### Slash from code

```python
from core.split_pane_tui import handle_split_slash

r = handle_split_slash("split", "ide", persist=True)
assert r["handled"] and r["ok"]
```

---

## Safety / design notes

| Topic | Note |
|-------|------|
| No extra deps | Rich only; no Textual required for N209 |
| Headless tests | All layout ops work without a real TTY |
| Focus UX | Visual only (border/title); input still via prompt line |
| Hidden panes | Tree filter + collapse single-child branches |
| Invalid config | Unknown layout/focus fall back to defaults |
| Legacy mode | `render_frame(..., use_split=False)` keeps fixed classic frame |

---

## Testing

```powershell
$env:PYTHONPATH = "src"
pytest tests/test_split_pane_tui_n209.py -q
```

### Coverage

| Area | Cases |
|------|--------|
| Config | default, save/load, invalid fallback |
| Presets | list all, panes_in_tree, filter hide/collapse |
| Build | each preset, hidden reflow, focus wrap, demo |
| Mutations | set_layout (+aliases), focus, cycle, hide/show, ratio, reset |
| Slash | handled/not, layout, panes, help, focus/cycle/ratio |
| Content | agent state → panes, render_split_frame, status_public |
| Integration | `superai_agent.tui.render_frame` split + legacy |

---

## Definition of done (N209)

| Criterion | Evidence |
|-----------|----------|
| Production-ready code | `split_pane_tui.py` + agent TUI integration + CLI |
| Thorough documentation | This file |
| Fully tested | `tests/test_split_pane_tui_n209.py` |
| Multi-layout product | 8 presets, focus, hide, ratios, persistence |

### Out of scope (related IDs)

| ID | Topic |
|----|--------|
| N208 | Multiplexed sessions (tmux-like process mux) |
| N210 | Vim keys in TUI |
| N211 | Optional mouse support |
| N215 | Screen-reader friendly TUI |

---

## Related

- Agent TUI (M077 / MoSCoW N1): `superai_agent/tui.py`, `agent_tui.py`  
- Command palette (W5): `tui_commands.py`  
- Dashboard multi-panel (observability): `cli/dashboard.py`  
- V6 backlog: N209 · parent M077  
