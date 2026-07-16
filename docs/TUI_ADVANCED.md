# TUI Advanced — N208 · N210 · N211 · N215

**Status:** Production-ready  
**Related:** [SPLIT_PANE_TUI.md](SPLIT_PANE_TUI.md) (N209)  
**Tests:** `tests/test_tui_advanced_n208_n215.py`  
**Agent integration:** `src/core/superai_agent/tui.py`

| ID | Feature | Module | CLI |
|----|---------|--------|-----|
| **N208** | Multiplexed sessions (tmux-like) | `src/core/tui_mux.py` | `superai mux` |
| **N210** | Vim keys | `src/core/tui_vim.py` | `superai vim-keys` |
| **N211** | Optional mouse | `src/core/tui_mouse.py` | `superai mouse` |
| **N215** | Screen-reader mode | `src/core/tui_a11y.py` | `superai a11y` |

---

## Architecture

```text
superai agent / split-tui
        │
        ├─ SessionMux (N208)     windows → agent session ids
        ├─ VimEngine (N210)      NORMAL / INSERT / COMMAND
        ├─ MouseController (N211) SGR parse + hit-test → focus/scroll
        ├─ A11yController (N215)  linear landmarks vs Rich layout
        └─ split_pane_tui (N209)  pane focus / layouts
```

Preferences live under `~/.superai/tui/`:

| File | Owner |
|------|--------|
| `mux.json` | N208 window list + active index |
| `vim.json` | N210 enabled + default mode |
| `mouse.json` | N211 enabled + scroll_lines |
| `a11y.json` | N215 enabled + verbosity |
| `split_pane.json` | N209 layout (existing) |

---

## N208 — Multiplexed sessions (tmux-like)

Application-level **window mux** over SuperAI agent sessions (not a process multiplexer like OS tmux).

### Concepts

| Term | Meaning |
|------|---------|
| **Mux** | Named container of windows (`default`, renamable) |
| **Window** | Slot pointing at a `session_id` (+ title, agent) |
| **Active window** | Selected index; agent TUI loads that session |

### CLI

```powershell
superai mux status
superai mux new "research"
superai mux list
superai mux select 0
superai mux next
superai mux prev
superai mux attach sa-abc123
superai mux rename "my-window"
superai mux name work
superai mux kill
superai mux help
```

### Slash (agent TUI)

```text
/mux status|new [title]|attach <sid>|select <n|id>|next|prev|kill|rename|list|name|help
/w          → next window
```

### Status bar

Example: `[work]  0:research | *1:coding |  2:review`

### API

```python
from core.tui_mux import SessionMux

m = SessionMux()
m.new_window(title="A", create_session=True)
m.next_window()
print(m.status_bar())
print(m.status())
```

### Limits (honest)

- Does **not** fork PTY processes or embed shell panes  
- Switching windows reloads the agent **session store** JSON  
- Safe for multi-topic agent work on one terminal  

---

## N210 — Vim keys

Modal key engine: **INSERT** (default for chat) · **NORMAL** · **COMMAND**.

### Modes

| Mode | Enter | Leave |
|------|-------|-------|
| INSERT | default / `i` | `Esc` → NORMAL |
| NORMAL | `Esc` | `i` → INSERT, `:` → COMMAND |
| COMMAND | `:` | Enter runs · Esc cancels |

### NORMAL map (summary)

| Keys | Action |
|------|--------|
| `j` `k` | Scroll messages |
| `Ctrl-d` `Ctrl-u` | Page |
| `gg` `G` | Top / bottom |
| `h` `l` / `Tab` | Pane focus |
| `Ctrl-w w` | Next pane |
| `Ctrl-w t/p` | Mux next/prev |
| `Ctrl-w n` | Mux new |
| `q` `ZZ` | Quit |
| `:` | Ex command |

**Commands:** `:q` `:help` `:tabnew` `:bn` `:bp` `:<n>` select window

### CLI / slash

```powershell
superai vim-keys status
superai vim-keys on
superai vim-keys off
superai vim-keys feed jk
superai vim-keys help
```

```text
/vim on|off|status|normal|insert|help|feed <keys>
```

### Line-oriented TUI note

The agent loop uses `input()` lines. In **NORMAL** mode, a typed line is interpreted as a **key sequence** (`j`, `gg`, `ZZ`, …). Full single-keystroke raw mode would need a raw terminal reader; the engine itself is complete and testable.

### API

```python
from core.tui_vim import VimEngine, create_engine

eng = create_engine()
eng.feed("Esc")
print(eng.feed("j").to_dict())
print(eng.parse_command("tabnew").to_dict())
```

---

## N211 — Optional mouse support

**Opt-in** (`enabled: false` by default).

### Features

| Input | Action |
|-------|--------|
| Click in pane region | Focus pane (N209) |
| Wheel up/down | Scroll messages (N× lines) |
| SGR / X10 CSI | Parsed to `MouseEvent` |

### ANSI enable (raw terminal attach)

```python
from core.tui_mouse import enable_mouse_ansi, disable_mouse_ansi
# write enable_mouse_ansi() to stdout when owning the TTY
```

DECSET: `1000` (click), `1002` (drag), `1006` (SGR).

### CLI / slash

```powershell
superai mouse status
superai mouse on
superai mouse off
superai mouse hit 5 10 classic
superai mouse parse sgr:0;12;8
superai mouse help
```

```text
/mouse on|off|status|hit <x> <y> [layout]|parse …|help
```

### Regions

Approximate rectangles for layouts (`agent`, `classic`, `triple`, `quad`, …). Used for hit-testing without a full layout compositor.

### API

```python
from core.tui_mouse import MouseController, parse_mouse_event

ctl = MouseController()
ctl.enable(True)
ctl.set_layout("agent", 80, 24)
ev = parse_mouse_event("\x1b[<0;10;5M")
print(ctl.handle_event(ev).to_dict())
```

### Limits (honest)

- Line `input()` cannot receive raw CSI mouse events without a raw reader  
- Parser + hit-test + config + slash **demo-click** are production-complete  
- Raw reader can call `handle_sequence()` when available  

---

## N215 — Screen-reader friendly TUI

**Opt-in** linear output with semantic landmarks.

### When `/a11y on`

Instead of Rich box panels, the frame is plain text:

```text
ANNOUNCE: New session sa-….

[banner: session]
SuperAI agent session sa-…. Agent build. …
[/banner: session]

[main: messages]
user: …
assistant: …
[/main: messages]

[complementary: tools]
- read: …
[/complementary: tools]

[contentinfo: status]
Cost approximately $0.00. …
[/contentinfo: status]
```

### Verbosity

| Level | Effect |
|-------|--------|
| `brief` | Header + messages + status only; truncated text |
| `normal` | + tools + events (default) |
| `verbose` | Longer message excerpts |

### Live announcements

Mode changes, mux switches, and agent completion can enqueue `ANNOUNCE:` lines.

### CLI / slash

```powershell
superai a11y status
superai a11y on
superai a11y brief
superai a11y render
superai a11y help
```

```text
/a11y on|off|status|brief|normal|verbose|announce <text>|help
```

### API

```python
from core.tui_a11y import A11yController, linearize_frame

ctl = A11yController()
ctl.enable(True)
print(ctl.render(state=session_state, events=[], tools_info=[]))
```

---

## Combined agent TUI workflow

```powershell
superai agent
# or
superai split-tui run --layout agent
```

Inside:

```text
/mux new research
/mux new coding
/mux select 0
/vim on
# Esc then j/k to scroll; i to type; :q to quit intent
/mouse on
/mouse hit 5 10 agent
/a11y on
/a11y verbose
```

---

## Testing

```powershell
$env:PYTHONPATH = "src"
pytest tests/test_tui_advanced_n208_n215.py -q
```

Coverage includes: mux CRUD/cycle/persist/slash; vim modes/counts/ctrl-w/commands; mouse SGR/X10/hit/wheel; a11y landmarks/announce/verbosity; help strings.

---

## Definition of done

| ID | Criterion | Evidence |
|----|-----------|----------|
| N208 | Production mux + CLI + slash + tests + docs | `tui_mux.py` + this doc |
| N210 | Production vim engine + CLI + slash + tests + docs | `tui_vim.py` |
| N211 | Production mouse parse/hit + CLI + slash + tests + docs | `tui_mouse.py` |
| N215 | Production SR linearization + CLI + slash + tests + docs | `tui_a11y.py` |
| All | Agent TUI integration | `superai_agent/tui.py` |
| All | Thorough tests | `test_tui_advanced_n208_n215.py` |

### Explicit non-goals

| Not claimed | Why |
|-------------|-----|
| Full OS tmux/zellij replacement | Process mux is N208 scope boundary |
| Raw tty single-keystroke loop | Engine ready; line mode works today |
| Full AT-SPI / VoiceOver bridge | Landmark plain text is the portable approach |

---

## Related

- N209 Split-pane: [SPLIT_PANE_TUI.md](SPLIT_PANE_TUI.md)  
- M077 Rich TUI / agent sessions  
- V6 backlog Nice N208, N210, N211, N215  
