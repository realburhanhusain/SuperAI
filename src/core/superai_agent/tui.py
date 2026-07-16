"""
SuperAI multi-panel agent TUI (Rich) with N209 split-pane layouts.

Uses `core.split_pane_tui` for configurable layouts, focus, hide/show, ratios.
Legacy fixed layout remains available via layout preset `classic`.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from rich.console import Console, Group
from rich.layout import Layout
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .agents import list_agents
from .runtime import AgentRuntime
from .tools_bridge import catalog


console = Console()


HELP = """
### SuperAI agent

**Agents:** `/agent build|plan|ask`  
**Model:** `/model <name>`  
**Permission:** `/permission plan|ask|auto|yolo`  
**Sessions:** `/new` `/sessions` `/resume id` `/export` `/undo`  
**Mux (N208):** `/mux status|new|next|prev|select|kill|rename|attach|list`  
**Changes:** `/changeset` `/apply` `/reject` (staged writes)  
**Tools:** `/tools` · tool loop runs automatically  
**Split-pane (N209):** `/layout` `/split` `/focus` `/cycle` `/hide` `/show` `/ratio` `/panes` `/layouts` `/split-help`  
**Vim (N210):** `/vim on|off|status|help` · Esc=NORMAL in vim mode  
**Mouse (N211):** `/mouse on|off|status|help`  
**A11y (N215):** `/a11y on|off|brief|normal|verbose|status|help`  
**Voice:** `/listen [sec]` `/speak [text]` `/voice status|on|off|auto on|off|queue …`  
**Other:** `/cost` `/trace` `/help` `/exit`

Plain text → agent run (tool loop).

Also: `superai` · `superai agent` · `superai mux` · `superai split-tui` · `superai ask`
"""


def _header(state, stream_on: bool) -> Panel:
    txt = (
        f"[bold cyan]SuperAI[/bold cyan]  "
        f"session=[yellow]{state.id}[/yellow]  "
        f"agent=[green]{state.agent}[/green]  "
        f"model=[magenta]{state.model or 'auto'}[/magenta]  "
        f"perm=[blue]{state.permission}[/blue]  "
        f"stream={'on' if stream_on else 'off'}"
    )
    return Panel(txt, border_style="cyan", title="header")


def _messages_panel(messages: List[Dict[str, Any]], limit: int = 8) -> Panel:
    blocks = []
    for m in (messages or [])[-limit:]:
        role = str(m.get("role") or "")
        content = str(m.get("content") or "")[:600]
        style = "bold green" if role == "assistant" else "bold white"
        blocks.append(Text(f"{role}> ", style=style))
        blocks.append(Text(content + "\n", style="dim" if role == "user" else ""))
        for p in m.get("parts") or []:
            if p.get("type") == "tool_call":
                blocks.append(
                    Text(
                        f"  ⚙ {p.get('name')} "
                        f"{json.dumps(p.get('arguments') or {})[:80]}\n",
                        style="yellow",
                    )
                )
            if p.get("type") == "tool_result":
                blocks.append(
                    Text(
                        f"  → ok={p.get('ok')}\n",
                        style="green" if p.get("ok") else "red",
                    )
                )
    body = (
        Group(*blocks)
        if blocks
        else Text("(no messages yet — type a task)", style="dim")
    )
    return Panel(body, title="messages", border_style="white")


def _tools_panel(events: List[Dict[str, Any]], tools_info: List[Dict[str, str]]) -> Panel:
    table = Table(show_header=True, expand=True)
    table.add_column("tool")
    table.add_column("desc")
    for t in tools_info[:8]:
        table.add_row(t["name"], t["desc"][:40])
    ev_lines = []
    for e in events[-6:]:
        detail = {
            k: v for k, v in e.items() if k not in {"kind", "ts"}
        }
        ev_lines.append(f"{e.get('kind')}: {json.dumps(detail, default=str)[:60]}")
    footer = "\n".join(ev_lines) if ev_lines else "(events appear here)"
    return Panel(
        Group(table, Text("\n" + footer, style="dim")),
        title="tools / events",
        border_style="yellow",
    )


def _footer(state, extra: str = "") -> Panel:
    return Panel(
        f"cost≈${float(state.estimated_cost_usd):.6f}  tokens={state.tokens}  "
        f"msgs={len(state.messages)}  {extra}",
        title="status",
        border_style="blue",
    )


def render_frame(
    state,
    events,
    stream_on: bool = True,
    status: str = "",
    *,
    use_split: bool = True,
    changeset_summary: Optional[Dict[str, Any]] = None,
) -> Layout:
    """
    Render multi-pane frame.

    When use_split=True (default), uses N209 split_pane_tui presets/config.
    """
    if use_split:
        from core.split_pane_tui import render_split_frame

        return render_split_frame(
            state=state,
            events=events,
            tools_info=catalog(),
            stream_on=stream_on,
            status=status,
            changeset_summary=changeset_summary,
        )

    # Legacy fixed layout (classic messages | tools)
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=3),
    )
    layout["body"].split_row(
        Layout(name="messages", ratio=3),
        Layout(name="tools", ratio=1),
    )
    layout["header"].update(_header(state, stream_on))
    layout["messages"].update(_messages_panel(state.messages))
    layout["tools"].update(_tools_panel(events, catalog()))
    layout["footer"].update(_footer(state, status))
    return layout


def run_superai_agent_tui(
    *,
    session_id: Optional[str] = None,
    agent: str = "build",
    model: Optional[str] = None,
    permission: Optional[str] = None,
    use_mock: Optional[bool] = None,
) -> None:
    """Interactive SuperAI multi-agent TUI."""
    from ..config import Config
    from ..permission_mode import mode_from_config, normalize_mode
    from ..progress_events import get_progress_bus

    cfg = Config()
    perm = normalize_mode(permission or mode_from_config(cfg))
    runtime = AgentRuntime(use_mock=use_mock)
    store = runtime.store
    if session_id:
        try:
            state = store.load(session_id)
        except KeyError:
            state = runtime.new_session(agent=agent, model=model, permission=perm)
            console.print(f"[yellow]session not found; created {state.id}[/yellow]")
    else:
        state = runtime.new_session(agent=agent, model=model, permission=perm)

    bus = get_progress_bus()
    events: List[Dict[str, Any]] = []

    def _hook(ev: Dict[str, Any]) -> None:
        events.append(ev)

    bus.on(_hook)
    stream_on = True
    from ..change_set import ChangeSet

    changeset = ChangeSet()

    from core.split_pane_tui import (
        SPLIT_COMMANDS,
        SPLIT_HELP,
        handle_split_slash,
        layout_summary,
        set_focus,
    )
    from core.tui_a11y import A11Y_HELP, A11yController, handle_a11y_slash
    from core.tui_mouse import MOUSE_HELP, MouseController, handle_mouse_slash
    from core.tui_mux import MUX_HELP, SessionMux, handle_mux_slash
    from core.tui_vim import VIM_HELP, create_engine, handle_vim_slash

    mux = SessionMux(persist=True)
    mux.sync_active_session(
        state.id, title=getattr(state, "title", "") or state.id, agent=state.agent
    )
    vim_eng = create_engine()
    mouse_ctl = MouseController()
    a11y = A11yController()
    msg_scroll_offset = 0  # used by vim/mouse scroll actions

    def _print_frame(status: str = "") -> None:
        nonlocal msg_scroll_offset
        try:
            cs_sum = changeset.summary()
        except Exception:
            cs_sum = None
        if a11y.cfg.enabled:
            text = a11y.render(
                state=state,
                events=events,
                tools_info=catalog(),
                stream_on=stream_on,
                status=status,
                mux_bar=mux.status_bar(),
                vim_mode=vim_eng.mode_indicator() if vim_eng.enabled else "",
                mouse_on=mouse_ctl.cfg.enabled,
            )
            console.print(text)
            return
        # decorate header status with mux + vim indicator
        extra = status
        bar = mux.status_bar()
        ind = vim_eng.mode_indicator()
        if bar:
            extra = f"{extra} {bar}".strip()
        if ind:
            extra = f"{extra} [{ind}]".strip()
        console.print(
            render_frame(
                state,
                events,
                stream_on,
                extra,
                changeset_summary=cs_sum,
            )
        )

    def _apply_nav_action(name: str, *, count: int = 1, arg: str = "") -> bool:
        """Apply vim/mouse navigation actions. Returns True if consumed (not passthrough)."""
        nonlocal state, msg_scroll_offset
        if name in {"scroll_up", "page_up"}:
            step = count * (5 if name == "page_up" else 1)
            msg_scroll_offset = max(0, msg_scroll_offset + step)
            a11y.announce(f"Scroll up {step}.")
            return True
        if name in {"scroll_down", "page_down"}:
            step = count * (5 if name == "page_down" else 1)
            msg_scroll_offset = max(0, msg_scroll_offset - step)
            a11y.announce(f"Scroll down {step}.")
            return True
        if name == "scroll_top":
            msg_scroll_offset = 10**9
            return True
        if name == "scroll_bottom":
            msg_scroll_offset = 0
            return True
        if name in {"focus_next", "focus_right", "focus_down"}:
            from core.split_pane_tui import cycle_focus

            cycle_focus(persist=True)
            return True
        if name in {"focus_prev", "focus_left", "focus_up"}:
            from core.split_pane_tui import cycle_focus, layout_summary as _ls

            # cycle twice for 2-pane feels wrong; reverse by cycling n-1
            vis = _ls().get("visible_panes") or ["messages"]
            for _ in range(max(1, len(vis) - 1)):
                cycle_focus(persist=True)
            return True
        if name == "focus_pane" and arg:
            set_focus(arg, persist=True)
            return True
        if name == "mux_next":
            handle_mux_slash("next", mux=mux)
            w = mux.active_window()
            if w:
                try:
                    state = store.load(w.session_id)
                except Exception:
                    pass
            return True
        if name == "mux_prev":
            handle_mux_slash("prev", mux=mux)
            w = mux.active_window()
            if w:
                try:
                    state = store.load(w.session_id)
                except Exception:
                    pass
            return True
        if name == "mux_new":
            out = handle_mux_slash("new", mux=mux)
            if out.get("ok") and out.get("created"):
                sid = out["created"].get("session_id")
                try:
                    state = store.load(sid)
                    events.clear()
                except Exception:
                    pass
            return True
        if name == "mux_select" and arg.isdigit():
            handle_mux_slash(f"select {arg}", mux=mux)
            w = mux.active_window()
            if w:
                try:
                    state = store.load(w.session_id)
                except Exception:
                    pass
            return True
        if name == "redraw":
            return True
        if name == "help":
            console.print(Markdown(HELP))
            return True
        return False

    console.print(
        Panel.fit(
            "[bold]SuperAI agent[/bold]\n"
            "Multi-agent · mux · split-pane · vim/mouse/a11y (N208–N215)\n"
            "Type /help · /mux · /vim · /mouse · /a11y · plain text runs the agent",
            border_style="cyan",
        )
    )
    _print_frame()

    while True:
        prompt = "[bold green]you>[/bold green] "
        if vim_eng.enabled and vim_eng.mode == "normal":
            prompt = "[bold yellow]NORMAL>[/bold yellow] "
        elif vim_eng.enabled and vim_eng.mode == "command":
            prompt = f"[bold magenta]:{vim_eng.command_buf}[/bold magenta] "
        try:
            line = console.input(prompt).rstrip("\n")
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        # N210: when vim normal mode, treat short line as key sequence
        if vim_eng.enabled and vim_eng.mode == "normal" and line and not line.startswith("/"):
            # multi-char sequences like gg, ZZ or single keys
            if line == ":":
                act = vim_eng.feed(":")
                console.print(f"[dim]{vim_eng.mode_indicator()}[/dim]")
                continue
            actions = []
            i = 0
            while i < len(line):
                # handle gg / ZZ as digraphs
                if i + 1 < len(line) and line[i : i + 2] in {"gg", "ZZ", "ZQ"}:
                    # feed as pending-aware two keys
                    actions.append(vim_eng.feed(line[i]))
                    actions.append(vim_eng.feed(line[i + 1]))
                    i += 2
                else:
                    actions.append(vim_eng.feed(line[i]))
                    i += 1
            quit_req = False
            for act in actions:
                if act.name == "quit":
                    quit_req = True
                    break
                if act.name == "submit_command":
                    parsed = vim_eng.parse_command(act.arg)
                    if parsed.name == "quit":
                        quit_req = True
                        break
                    _apply_nav_action(parsed.name, count=parsed.count, arg=parsed.arg)
                elif act.name == "enter_insert":
                    pass
                elif act.name not in {"none", "passthrough", "unknown"}:
                    _apply_nav_action(act.name, count=act.count, arg=act.arg)
            if quit_req:
                break
            _print_frame(f"vim={vim_eng.mode_indicator()}")
            if vim_eng.mode == "insert":
                continue
            continue
        if vim_eng.enabled and vim_eng.mode == "command":
            # entire line is command body if user typed after :
            parsed = vim_eng.parse_command(line)
            vim_eng.set_mode("normal")
            if parsed.name == "quit":
                break
            _apply_nav_action(parsed.name, count=parsed.count, arg=parsed.arg)
            _print_frame()
            continue

        line = line.strip()
        if not line:
            continue

        if line.startswith("/"):
            cmd, *rest = line[1:].split(maxsplit=1)
            arg = rest[0] if rest else ""
            cmd = cmd.lower()
            if cmd in {"exit", "quit", "q"}:
                break
            if cmd == "help":
                console.print(Markdown(HELP))
                console.print(Markdown(SPLIT_HELP))
                console.print(Markdown(MUX_HELP))
                console.print(Markdown(VIM_HELP))
                console.print(Markdown(MOUSE_HELP))
                console.print(Markdown(A11Y_HELP))
                continue
            # N208 mux
            if cmd in {"mux", "window", "w"}:
                if cmd in {"w", "window"} and not arg:
                    arg = "next"
                out = handle_mux_slash(arg, mux=mux)
                if out.get("help"):
                    console.print(Markdown(str(out["help"])))
                else:
                    console.print_json(data=out)
                sub0 = (arg or "status").split()[0].lower() if arg else "status"
                if sub0 in {
                    "next",
                    "prev",
                    "select",
                    "new",
                    "attach",
                    "kill",
                    "n",
                    "p",
                    "s",
                    "a",
                    "c",
                    "+",
                    "-",
                    "goto",
                    "create",
                    "x",
                    "close",
                }:
                    w = mux.active_window()
                    if w:
                        try:
                            state = store.load(w.session_id)
                            if sub0 in {"new", "c", "create"}:
                                events.clear()
                        except Exception:
                            pass
                a11y.announce(mux.status_bar())
                _print_frame()
                continue
            # N210 vim
            if cmd in {"vim", "vim-keys", "vi"}:
                out = handle_vim_slash(arg, engine=vim_eng)
                if out.get("help"):
                    console.print(Markdown(str(out["help"])))
                else:
                    # re-sync engine flags from config when toggled
                    if (arg or "").split()[:1] in (["on"], ["off"], ["enable"], ["disable"]):
                        from core.tui_vim import create_engine as _ce

                        vim_eng = _ce()
                    console.print_json(data=out)
                _print_frame()
                continue
            # N211 mouse
            if cmd in {"mouse"}:
                out = handle_mouse_slash(arg, ctl=mouse_ctl)
                if out.get("help"):
                    console.print(Markdown(str(out["help"])))
                else:
                    console.print_json(data=out)
                if out.get("action") and out["action"].get("name") == "focus_pane":
                    pane = out["action"].get("pane")
                    if pane:
                        set_focus(pane, persist=True)
                _print_frame()
                continue
            # N215 a11y
            if cmd in {"a11y", "sr", "screenreader", "screen-reader"}:
                out = handle_a11y_slash(arg, ctl=a11y)
                if out.get("help"):
                    console.print(Markdown(str(out["help"])))
                else:
                    console.print_json(data=out)
                _print_frame()
                continue
            # N209 split-pane commands
            if cmd in SPLIT_COMMANDS:
                out = handle_split_slash(cmd, arg, persist=True)
                if out.get("help"):
                    console.print(Markdown(str(out["help"])))
                else:
                    console.print_json(data=out)
                try:
                    mouse_ctl.set_layout(str(layout_summary().get("layout") or "agent"))
                except Exception:
                    pass
                _print_frame(f"layout={layout_summary().get('layout')}")
                continue
            if cmd == "agents":
                console.print_json(data=list_agents())
                continue
            if cmd == "agent":
                state.agent = (arg or "build").lower()
                store.save(state)
                console.print(f"agent={state.agent}")
                continue
            if cmd == "model":
                state.model = arg or None
                store.save(state)
                console.print(f"model={state.model}")
                continue
            if cmd in {"permission", "perm"}:
                state.permission = normalize_mode(arg or "ask")
                store.save(state)
                console.print(f"permission={state.permission}")
                continue
            if cmd == "new":
                state = runtime.new_session(
                    agent=state.agent,
                    model=state.model,
                    permission=state.permission,
                )
                events.clear()
                mux.new_window(
                    session_id=state.id,
                    title=state.title or state.id,
                    agent=state.agent,
                    create_session=False,
                )
                console.print(f"[green]new session {state.id}[/green]")
                a11y.announce(f"New session {state.id}.")
                _print_frame()
                continue
            if cmd == "sessions":
                table = Table(title="SuperAI sessions")
                table.add_column("id")
                table.add_column("agent")
                table.add_column("msgs")
                table.add_column("title")
                for r in store.list_sessions(15):
                    table.add_row(
                        str(r.get("id")),
                        str(r.get("agent")),
                        str(r.get("messages")),
                        str(r.get("title") or "")[:40],
                    )
                console.print(table)
                continue
            if cmd == "resume":
                try:
                    state = store.load(arg.strip())
                    mux.attach(state.id, title=state.title or state.id)
                    console.print(f"[green]resumed {state.id}[/green]")
                    a11y.announce(f"Resumed session {state.id}.")
                    _print_frame()
                except KeyError:
                    console.print(f"[red]unknown {arg}[/red]")
                continue
            if cmd == "export":
                path = store.export_markdown(state)
                console.print(f"[green]exported {path}[/green]")
                continue
            if cmd == "undo":
                state = store.undo_last_user_assistant(state)
                _print_frame("undone")
                continue
            if cmd == "cost":
                console.print(
                    f"tokens={state.tokens} cost≈${state.estimated_cost_usd:.6f}"
                )
                continue
            if cmd == "tools":
                console.print_json(data=catalog())
                continue
            if cmd in {"changeset", "cs"}:
                console.print_json(data=changeset.summary())
                continue
            if cmd == "apply":
                dry = (arg or "").lower() in {"dry", "dry-run", "--dry-run"}
                console.print_json(
                    data=changeset.apply(dry_run=dry or state.permission == "plan")
                )
                continue
            if cmd == "reject":
                console.print_json(data=changeset.reject())
                continue
            if cmd == "trace":
                console.print_json(data=events[-20:])
                continue
            if cmd == "stream":
                stream_on = (arg or "on").lower() not in {"off", "0", "false"}
                console.print(f"stream={stream_on}")
                continue
            if cmd == "layout":
                # With arg: handled by SPLIT_COMMANDS; bare /layout re-renders
                if arg:
                    out = handle_split_slash("layout", arg, persist=True)
                    console.print_json(data=out)
                _print_frame()
                continue
            # MOS-N6 voice hooks
            if cmd == "listen":
                from core.voice_io import listen_once

                try:
                    to = float(arg.strip()) if (arg or "").strip() else 5.0
                except Exception:
                    to = 5.0
                r = listen_once(timeout=to)
                console.print_json(data=r)
                if r.get("ok") and r.get("text"):
                    line = str(r["text"])
                    console.print(f"[cyan]voice→[/cyan] {line[:200]}")
                    # fall through to agent run with spoken text as user line
                else:
                    continue
            elif cmd == "speak":
                from core.voice_io import speak

                console.print_json(data=speak(arg or "SuperAI agent ready."))
                continue
            elif cmd == "voice":
                from core.voice_io import handle_voice_slash

                console.print_json(data=handle_voice_slash(arg or "status"))
                continue
            else:
                console.print(f"[yellow]unknown /{cmd} — /help[/yellow]")
                continue

            # Only successful /listen reaches here (other voice cmds continue above)

        def _approve(name: str, args: Dict[str, Any]) -> bool:
            console.print(
                Panel(
                    f"tool={name}\nargs={json.dumps(args, default=str)[:500]}",
                    title="permission ask",
                    border_style="red",
                )
            )
            ans = console.input("Allow? [y/N] ").strip().lower()
            return ans in {"y", "yes"}

        buf: List[str] = []

        def _tok(ch: str) -> None:
            if stream_on:
                buf.append(ch)

        with console.status("[bold cyan]SuperAI running…[/bold cyan]"):
            result = runtime.run(
                line,
                session=state,
                approve=_approve if state.permission == "ask" else None,
                on_token=_tok if stream_on else None,
                change_set=changeset,
                stage_writes=state.permission in {"ask", "plan"},
            )
        state = store.load(result.session_id)
        mux.sync_active_session(
            state.id, title=state.title or state.id, agent=state.agent
        )
        reply_txt = "".join(buf) if (stream_on and buf) else (result.response or "")
        if a11y.cfg.enabled:
            a11y.announce(
                f"Agent reply. Tools {result.tool_rounds}. "
                f"{'OK' if result.ok else 'Error'}."
            )
            if reply_txt:
                console.print(
                    f"assistant: {str(reply_txt)[:4000]}\n"
                    f"(mock={result.mock} cost≈${result.estimated_cost_usd:.6f})"
                )
        else:
            if stream_on and buf:
                console.print(
                    Panel("".join(buf)[:4000], title="stream", border_style="green")
                )
            else:
                console.print(
                    Panel(
                        (result.response or "")[:4000],
                        title=f"agent:{result.agent} tools={result.tool_rounds}",
                        border_style="green",
                    )
                )
            console.print(
                f"[dim]mock={result.mock} cost≈${result.estimated_cost_usd:.6f} "
                f"session={state.id}[/dim]"
            )
        # MOS-N6: auto-speak reply when /voice auto on
        try:
            from core.voice_io import speak_reply

            speak_reply(str(reply_txt)[:500])
        except Exception:
            pass
        _print_frame("ok" if result.ok else "err")

    console.print(f"[dim]session saved: {state.id}[/dim]")


