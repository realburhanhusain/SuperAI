# TUI Advanced — N208 · N210 · N211 · N215

**Status:** Production-ready **with live TTY input**  
**Related:** [SPLIT_PANE_TUI.md](SPLIT_PANE_TUI.md) (N209)  
**Tests:** `tests/test_tui_advanced_n208_n215.py`, `tests/test_tui_live_input.py`  
**Agent integration:** `src/core/superai_agent/tui.py`  
**Live stack:** `tui_raw_input.py` · `tui_live_session.py`

| ID | Feature | Module | CLI |
|----|---------|--------|-----|
| **N208** | Multiplexed sessions (tmux-like) | `src/core/tui_mux.py` | `superai mux` |
| **N210** | Vim keys (**live** single-key) | `src/core/tui_vim.py` | `superai vim-keys` |
| **N211** | Optional mouse (**live** CSI) | `src/core/tui_mouse.py` | `superai mouse` |
| **N215** | Screen-reader mode (**live** announce file) | `src/core/tui_a11y.py` | `superai a11y` |
| — | Live TTY reader | `src/core/tui_raw_input.py` | `superai tui-live` |

---

## Architecture

```text
superai agent / split-tui
        │
        ├─ tui_live_session (default on TTY)
        │     ├─ RawTTY  msvcrt (Windows) / termios cbreak (Unix)
        │     ├─ CSI assembly (arrows, mouse SGR 1006)
        │     └─ LineEditor (INSERT)
        │
        ├─ SessionMux (N208)     windows → agent session ids · live status bar
        ├─ VimEngine (N210)      NORMAL / INSERT / COMMAND · single-key live
        ├─ MouseController (N211) SGR parse + hit-test → focus/scroll live
        ├─ A11yController (N215)  landmarks + live file + bell
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

### Live input (implemented)

On a real TTY, `superai agent` enables **raw/cbreak** input by default:

| Mode | Live behavior |
|------|----------------|
| NORMAL | Each keystroke → vim engine immediately (`j`/`k`/`gg`/…) |
| INSERT | Line editor (arrows, backspace, Ctrl-W word delete) until Enter |
| COMMAND | Live `:` buffer until Enter |

Force cooked line mode: `SUPERAI_TUI_LIVE=0`  
Force live when possible: `SUPERAI_TUI_LIVE=1` (default when TTY)

```powershell
superai tui-live status
superai tui-live demo-keys "jk"
```

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

### Live mouse (implemented)

When `/mouse on` and the agent TUI is on a TTY:

1. `RawTTY` emits DECSET `1000/1002/1006`  
2. SGR CSI sequences are assembled live  
3. Clicks → `focus_pane` (N209) + frame redraw  
4. Wheel → scroll actions + a11y announce  

```powershell
superai mouse on
superai tui-live demo-mouse sgr:0;10;5
superai agent   # live mouse while TTY
```

Non-TTY (CI/pipes) falls back to cooked input; `superai mouse hit` still simulates clicks.

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

### Live announcements (implemented)

| Channel | Behavior |
|---------|----------|
| In-frame | `ANNOUNCE:` prefix when `/a11y on` |
| Live file | Append-only `~/.superai/tui/a11y_live.txt` (tail-friendly) |
| Bell | ASCII BEL on each `announce()` |
| Voice | Optional: `SUPERAI_A11Y_VOICE=1` → `voice_io.speak` |

Mode changes, mux switches, scroll/focus, and agent completion call `announce(..., immediate=True)`.

```powershell
# Watch live announcements in another terminal
Get-Content $env:USERPROFILE\.superai\tui\a11y_live.txt -Wait -Tail 20
```

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

## Live mode + former “intentional” gaps (now implemented)

| Former boundary | Implementation |
|-----------------|----------------|
| Line-only vim sequences | **RawTTY** single-key NORMAL / live INSERT editor |
| Mouse parse without CSI delivery | **RawTTY** + DECSET 1006 → `MouseController` |
| A11y only in-frame text | Live file + BEL + voice |
| Session mux only (no processes) | **`ProcessMux`** — real subprocess panes (Unix PTY / Win pipes) |
| No native SR bridge | **`tui_a11y_native`** — SAPI / `say` / spd-say / UIA live region |

### N208 process mux (OS panes)

```powershell
superai process-mux status
superai process-mux shell
superai process-mux spawn "python -c print(1)"
superai process-mux read
superai process-mux write "echo hi"
superai process-mux next
superai process-mux kill
superai process-mux tmux superai   # if host tmux installed
```

In agent TUI: `/pmux shell` · `/pmux spawn …` · `/pmux read` · `/pmux link <session_id>`

| Backend | When |
|---------|------|
| Unix **PTY** | `pty.openpty` |
| Windows **ConPTY** | True pseudo-console via `CreatePseudoConsole` (`tui_conpty.py`) |
| Windows **pipes** | Fallback if ConPTY fails |
| External **tmux** | Optional helper when `tmux` on PATH |

**Restore after restart**

```powershell
superai process-mux restore          # respawn all saved panes
$env:SUPERAI_PMUX_RESTORE = "1"      # auto-restore on ProcessMux init
superai process-mux saved            # list metadata
```

Metadata: `~/.superai/tui/process_mux.json` (commands + titles; new PIDs on restore)  
Session link bridges process panes ↔ `SessionMux` agent sessions.

### N215 native screen-reader bridges

| OS | Backends |
|----|----------|
| Windows | SAPI.SpVoice / System.Speech (PowerShell) + UIA live region files |
| macOS | `say` + notification (VoiceOver users hear speech) |
| Linux | **AT-SPI2** (`org.a11y.Bus`) + FDO Notifications + `spd-say` / espeak + `atspi_live.txt` |

```powershell
superai a11y backends
superai a11y native
superai a11y native-say "Hello SuperAI"
superai a11y native prefer file
superai a11y atspi
superai a11y atspi "Hello AT-SPI"
```

Live region files (Narrator / watchers):

- `~/.superai/tui/uia_live_region.txt`
- `~/.superai/tui/uia_live_region.utf16.txt`
- `~/.superai/tui/atspi_live.txt` (Linux AT-SPI poll file)
- `~/.superai/tui/a11y_live.txt` (append log)

### Env

| Variable | Effect |
|----------|--------|
| `SUPERAI_TUI_LIVE=0` | Force cooked `input()` (CI-friendly) |
| `SUPERAI_TUI_LIVE=1` | Prefer live raw when TTY |
| `SUPERAI_A11Y_VOICE=1` | Also use `voice_io.speak` |
| `SUPERAI_A11Y_NATIVE=0` | Disable native TTS bridge (file/landmarks remain) |
| `SUPERAI_PMUX_RESTORE=1` | Auto-respawn process panes from metadata on init |

---

## Testing

```powershell
$env:PYTHONPATH = "src"
pytest tests/test_tui_advanced_n208_n215.py tests/test_tui_live_input.py tests/test_tui_process_native_n208_n215.py tests/test_tui_polish_conpty_atspi_restore.py -q
```

Coverage includes: session mux; **process mux spawn/read/write/kill**; vim; mouse; a11y landmarks; **native backends / UIA file**; live CSI/editor.

---

## Definition of done

| ID | Criterion | Evidence |
|----|-----------|----------|
| N208 | Session mux + **process mux (PTY/pipes)** + CLI + tests + docs | `tui_mux.py` + `tui_process_mux.py` |
| N210 | Vim + live keys | `tui_vim.py` + `tui_raw_input.py` |
| N211 | Mouse + live CSI | `tui_mouse.py` + RawTTY |
| N215 | SR landmarks + live file + **native OS bridges** | `tui_a11y.py` + `tui_a11y_native.py` |
| Live | Raw reader + session loop | `tui_live_session.py` |
| All | Agent TUI + thorough tests + docs | `TUI_ADVANCED.md` |

---

## Related

- N209 Split-pane: [SPLIT_PANE_TUI.md](SPLIT_PANE_TUI.md)  
- M077 Rich TUI / agent sessions  
- V6 backlog Nice N208, N210, N211, N215  
