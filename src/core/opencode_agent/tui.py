"""
OpenCode-style multi-panel agent TUI (Rich).

Panels: header (agent/model/perm) · messages · tools/events · footer (cost).
This is SuperAI's full rewrite of the interactive agent UX, inspired by OpenCode
patterns (multi-agent, tools, sessions) — not a Go/Bubble Tea fork.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .agents import list_agents
from .runtime import AgentRuntime
from .session import OpenCodeSessionStore
from .tools_bridge import catalog


console = Console()


HELP = """
### SuperAI OpenCode Agent

**Agents:** `/agent build|plan|ask`  
**Model:** `/model <name>`  
**Permission:** `/permission plan|ask|auto|yolo`  
**Sessions:** `/new` `/sessions` `/resume id` `/export` `/undo`  
**Tools:** `/tools` · inline tool loop automatic  
**Other:** `/cost` `/trace` `/help` `/exit`

Plain text → agent run (tool loop).
"""


def _header(state, stream_on: bool) -> Panel:
    txt = (
        f"[bold cyan]SuperAI OpenCode[/bold cyan]  "
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
                        f"  ⚙ {p.get('name')} {json.dumps(p.get('arguments') or {})[:80]}\n",
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
    body = Group(*blocks) if blocks else Text("(no messages yet — type a task)", style="dim")
    return Panel(body, title="messages", border_style="white")


def _tools_panel(events: List[Dict[str, Any]], tools_info: List[Dict[str, str]]) -> Panel:
    table = Table(show_header=True, expand=True)
    table.add_column("tool")
    table.add_column("desc")
    for t in tools_info[:8]:
        table.add_row(t["name"], t["desc"][:40])
    ev_lines = []
    for e in events[-6:]:
        ev_lines.append(f"{e.get('kind')}: {json.dumps({k:v for k,v in e.items() if k!='kind' and k!='ts'}, default=str)[:60]}")
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


def render_frame(state, events, stream_on: bool = True, status: str = "") -> Layout:
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


def run_opencode_tui(
    *,
    session_id: Optional[str] = None,
    agent: str = "build",
    model: Optional[str] = None,
    permission: Optional[str] = None,
    use_mock: Optional[bool] = None,
) -> None:
    """Interactive OpenCode-style agent TUI (full rewrite)."""
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

    console.print(
        Panel.fit(
            "[bold]SuperAI OpenCode Agent TUI[/bold]\n"
            "Multi-agent · tool loop · sessions · permission modes\n"
            "Type /help · plain text runs the agent",
            border_style="cyan",
        )
    )
    console.print(render_frame(state, events, stream_on))

    while True:
        try:
            line = console.input("[bold green]you>[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
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
                console.print(f"[green]new session {state.id}[/green]")
                console.print(render_frame(state, events, stream_on))
                continue
            if cmd == "sessions":
                table = Table(title="OpenCode sessions")
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
                    console.print(f"[green]resumed {state.id}[/green]")
                    console.print(render_frame(state, events, stream_on))
                except KeyError:
                    console.print(f"[red]unknown {arg}[/red]")
                continue
            if cmd == "export":
                path = store.export_markdown(state)
                console.print(f"[green]exported {path}[/green]")
                continue
            if cmd == "undo":
                state = store.undo_last_user_assistant(state)
                console.print(render_frame(state, events, stream_on, "undone"))
                continue
            if cmd == "cost":
                console.print(
                    f"tokens={state.tokens} cost≈${state.estimated_cost_usd:.6f}"
                )
                continue
            if cmd == "tools":
                console.print_json(data=catalog())
                continue
            if cmd == "trace":
                console.print_json(data=events[-20:])
                continue
            if cmd == "stream":
                stream_on = (arg or "on").lower() not in {"off", "0", "false"}
                console.print(f"stream={stream_on}")
                continue
            if cmd == "layout":
                console.print(render_frame(state, events, stream_on))
                continue
            console.print(f"[yellow]unknown /{cmd} — /help[/yellow]")
            continue

        # Approve callback for ask mode
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

        with console.status("[bold cyan]agent running…[/bold cyan]"):
            result = runtime.run(
                line,
                session=state,
                approve=_approve if state.permission == "ask" else None,
                on_token=_tok if stream_on else None,
            )
        # reload state
        state = store.load(result.session_id)
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
        console.print(render_frame(state, events, stream_on, "ok" if result.ok else "err"))

    console.print(f"[dim]session saved: {state.id}[/dim]")
