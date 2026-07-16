"""
Agent session TUI (Phase 8 N1 / MoSCoW S1 N1 N6).

Simple SuperAI agent TUI (older loop; prefer `superai` / `core.superai_agent`).
  - visible tool/model steps
  - compact prior turns
  - plan vs act permission
  - token streaming display
  - /diff confirm, /listen /speak voice hooks
Uses Rich (already a SuperAI dependency).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .ask_session import AskSessionStore
from .nl_intent import ask_superai, parse_intent
from .permission_mode import mode_from_config, normalize_mode
from .progress_events import get_progress_bus


console = Console()


def compact_turns(turns: List[Dict[str, Any]], max_chars: int = 1200) -> str:
    """Summarize prior turns for context window."""
    if not turns:
        return ""
    chunks = []
    budget = max_chars
    for t in reversed(turns):
        u = str(t.get("user") or "")[:200]
        a = str(t.get("assistant") or "")[:200]
        block = f"U: {u}\nA: {a}\n"
        if len(block) > budget:
            break
        chunks.append(block)
        budget -= len(block)
    chunks.reverse()
    return "[Compacted session]\n" + "".join(chunks)


def render_trace(events: List[Dict[str, Any]], limit: int = 12) -> None:
    table = Table(title="Tool / step trace", show_header=True)
    table.add_column("kind")
    table.add_column("detail")
    for ev in events[-limit:]:
        kind = str(ev.get("kind") or "")
        detail = {k: v for k, v in ev.items() if k not in {"ts", "kind"}}
        table.add_row(kind, json.dumps(detail, default=str)[:120])
    console.print(table)


def run_agent_tui(
    *,
    session_id: Optional[str] = None,
    permission: Optional[str] = None,
    profile: Optional[str] = None,
) -> None:
    """
    Interactive agent loop with traces (Phase 8 N1).
    Commands: /help /trace /compact /exit /permission X /profile X
    """
    from .config import Config
    from .run_profiles import apply_profile_to_config

    cfg = Config()
    if profile:
        apply_profile_to_config(cfg, profile)
    if permission:
        cfg.config["permission_mode"] = normalize_mode(permission)

    from .tui_commands import command_palette, help_markdown, resolve_alias

    store = AskSessionStore()
    sid = session_id or store.create()
    bus = get_progress_bus()
    traces: List[Dict[str, Any]] = []
    session_cost = 0.0
    session_tokens = 0

    def _hook(ev: Dict[str, Any]) -> None:
        traces.append(ev)

    bus.on(_hook)

    def _footer() -> str:
        return (
            f"session={sid}  perm={mode_from_config(cfg)}  "
            f"cost≈${session_cost:.6f}  tokens={session_tokens}"
        )

    console.print(
        Panel.fit(
            f"[bold]SuperAI Agent TUI[/bold]\n"
            f"{_footer()}\n"
            f"Slash: /help /commands /export /sessions /resume /undo /paste /cost\n"
            f"       /tool /diff /listen /speak /voice /permission /profile /stream /exit",
            border_style="cyan",
            title="session",
            subtitle="W1–W6 polish · shared AskSessionStore",
        )
    )
    stream_enabled = True
    paste_buf: List[str] = []
    paste_mode = False

    while True:
        try:
            line = console.input("[bold green]you>[/bold green] ").rstrip("\n")
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        # W6: multi-line paste until /end
        if paste_mode:
            if line.strip().lower() in {"/end", "end"}:
                paste_mode = False
                line = "\n".join(paste_buf).strip()
                paste_buf = []
                if not line:
                    console.print("[dim]empty paste[/dim]")
                    continue
                # fall through as normal user message (not slash)
            else:
                paste_buf.append(line)
                console.print(f"[dim]… paste line {len(paste_buf)} (type /end)[/dim]")
                continue

        line = line.strip()
        if not line:
            continue
        if line.startswith("/"):
            raw_cmd, *rest = line[1:].split(maxsplit=1)
            cmd = resolve_alias(raw_cmd)
            arg = rest[0] if rest else ""
            if cmd in {"exit", "quit", "q"}:
                break
            if cmd in {"help", "?"}:
                console.print(Markdown(help_markdown()))
                continue
            if cmd in {"commands", "cmds"}:
                table = Table(title="Command palette", show_header=True)
                table.add_column("command")
                table.add_column("alias")
                table.add_column("desc")
                for row in command_palette():
                    table.add_row(row["cmd"], row.get("alias") or "", row["desc"])
                console.print(table)
                continue
            if cmd == "trace":
                render_trace(traces)
                continue
            if cmd == "stream":
                stream_enabled = (arg or "on").lower() not in {"off", "0", "false"}
                console.print(f"stream={stream_enabled}")
                continue
            if cmd in {"cost", "tokens"}:
                tot = store.session_totals(sid)
                session_cost = float(tot.get("estimated_cost_usd") or session_cost)
                session_tokens = int(tot.get("tokens") or session_tokens)
                console.print(
                    Panel(
                        f"turns={tot.get('turns')}  tokens={tot.get('tokens')}  "
                        f"cost≈${float(tot.get('estimated_cost_usd') or 0):.6f}\n"
                        f"{_footer()}",
                        title="session cost",
                        border_style="green",
                    )
                )
                continue
            if cmd == "export":
                from pathlib import Path

                dest = Path(arg) if arg else None
                console.print_json(data=store.export_markdown(sid, dest=dest))
                continue
            if cmd in {"sessions", "ls"}:
                rows = store.list_sessions(15)
                table = Table(title="Sessions", show_header=True)
                table.add_column("id")
                table.add_column("turns")
                table.add_column("created")
                for r in rows:
                    table.add_row(
                        str(r.get("id")),
                        str(r.get("turns")),
                        str(r.get("created_at") or "")[:19],
                    )
                console.print(table)
                continue
            if cmd == "resume":
                if not arg:
                    console.print("[yellow]usage: /resume ask-…[/yellow]")
                    continue
                try:
                    store.get(arg.strip())
                    sid = arg.strip()
                    tot = store.session_totals(sid)
                    session_cost = float(tot.get("estimated_cost_usd") or 0)
                    session_tokens = int(tot.get("tokens") or 0)
                    console.print(f"[green]resumed {sid}[/green]  {_footer()}")
                except KeyError:
                    console.print(f"[red]unknown session {arg}[/red]")
                continue
            if cmd == "undo":
                console.print_json(data=store.undo_turn(sid))
                tot = store.session_totals(sid)
                session_cost = float(tot.get("estimated_cost_usd") or 0)
                session_tokens = int(tot.get("tokens") or 0)
                continue
            if cmd == "paste":
                paste_mode = True
                paste_buf = []
                console.print(
                    "[cyan]Paste mode: enter lines, finish with /end[/cyan]"
                )
                continue
            if cmd == "panel":
                data = store._load(sid)
                turns = data.get("turns") or []
                table = Table(title=f"Session {sid}", show_header=True)
                table.add_column("#")
                table.add_column("user")
                table.add_column("assistant")
                for i, t in enumerate(turns[-8:], 1):
                    table.add_row(
                        str(i),
                        str(t.get("user") or "")[:40],
                        str(t.get("assistant") or "")[:40],
                    )
                console.print(table)
                console.print(
                    Panel(
                        f"{_footer()}  traces={len(traces)}",
                        title="status",
                        border_style="blue",
                    )
                )
                continue
            if cmd == "diff":
                # N1: /diff confirm — show git diff, ask before apply
                from .git_diff_apply import apply_unified_diff, check_unified_diff
                from .pr_review import get_git_diff

                ref = arg or "HEAD~1"
                try:
                    diff_text = get_git_diff(ref)
                except Exception as e:
                    console.print(f"[red]diff error: {e}[/red]")
                    continue
                if not (diff_text or "").strip():
                    import subprocess

                    proc = subprocess.run(
                        ["git", "diff", "HEAD"],
                        capture_output=True,
                        text=True,
                        shell=False,
                    )
                    diff_text = proc.stdout or ""
                console.print(
                    Panel(
                        (diff_text or "(empty diff)")[:3000],
                        title=f"git diff {ref}",
                        border_style="magenta",
                    )
                )
                try:
                    chk = check_unified_diff(diff_text)
                except Exception:
                    chk = {"ok": True, "note": "check_unavailable"}
                console.print_json(data=chk if isinstance(chk, dict) else {"check": str(chk)})
                if mode_from_config(cfg) == "plan":
                    console.print("[yellow]plan mode: not applying[/yellow]")
                    continue
                if not (diff_text or "").strip():
                    console.print("[dim]no diff to apply[/dim]")
                    continue
                ans = console.input("Apply this diff? [y/N] ").strip().lower()
                if ans in {"y", "yes"}:
                    try:
                        applied = apply_unified_diff(
                            diff_text,
                            dry_run=False,
                            check_first=True,
                        )
                        console.print_json(
                            data=applied if isinstance(applied, dict) else {"ok": True}
                        )
                    except Exception as e:
                        console.print(f"[red]apply failed: {e}[/red]")
                else:
                    console.print("[dim]skipped apply[/dim]")
                continue
            if cmd == "listen":
                from .voice_io import listen_once

                try:
                    to = float(arg.strip()) if (arg or "").strip() else 5.0
                except Exception:
                    to = 5.0
                r = listen_once(timeout=to)
                console.print_json(data=r)
                if r.get("ok") and r.get("text"):
                    line = str(r["text"])
                    console.print(f"[cyan]voice→[/cyan] {line[:200]}")
                    # fall through to agent with spoken text
                else:
                    continue
            elif cmd == "speak":
                from .voice_io import speak

                text = arg or "SuperAI agent ready."
                console.print_json(data=speak(text))
                continue
            elif cmd == "voice":
                from .voice_io import handle_voice_slash

                console.print_json(data=handle_voice_slash(arg or "status"))
                continue
            if cmd == "compact":
                data = store._load(sid)
                if arg == "smart":
                    from .session_compact import smart_compact

                    pref = smart_compact(data.get("turns") or [])
                else:
                    pref = compact_turns(data.get("turns") or [])
                console.print(Panel(pref or "(empty)", title="compacted"))
                continue
            if cmd == "tool" or line.startswith("/tool"):
                from .agent_tools import execute_directives

                # allow "/tool read path=x" as full line
                blob = line if line.startswith("/tool") else f"/tool {arg}"
                bus.emit("tool_batch", text=blob[:120])
                results = execute_directives(
                    blob, permission_mode=mode_from_config(cfg)
                )
                for r in results:
                    bus.emit("tool_result", tool=r["directive"].get("tool"), ok=r["result"].get("ok"))
                    console.print_json(data=r)
                continue
            if cmd in {"permission", "perm"}:
                cfg.config["permission_mode"] = normalize_mode(arg or "ask")
                console.print(f"permission={cfg.config['permission_mode']}")
                continue
            if cmd == "profile":
                apply_profile_to_config(cfg, arg or "balanced")
                console.print(f"profile={cfg.config.get('run_profile')}")
                continue
            if cmd not in {"listen"}:
                console.print(
                    f"[yellow]Unknown slash: /{cmd} — try /commands[/yellow]"
                )
                continue

        # Inline /tool lines mixed with message
        tool_results = []
        if "/tool" in line:
            from .agent_tools import execute_directives

            tool_results = execute_directives(
                line, permission_mode=mode_from_config(cfg)
            )
            for r in tool_results:
                bus.emit("tool_result", tool=r["directive"].get("tool"), ok=r["result"].get("ok"))
                console.print(
                    Panel(
                        json.dumps(r["result"], default=str)[:1500],
                        title=f"tool:{r['directive'].get('tool')}",
                        border_style="yellow",
                    )
                )

        # Build prompt with compacted history
        preface = ""
        try:
            data = store._load(sid)
            from .session_compact import smart_compact

            preface = smart_compact(data.get("turns") or [], max_chars=1500)
        except Exception:
            try:
                preface = compact_turns(store._load(sid).get("turns") or [], max_chars=1500)
            except Exception:
                preface = ""
        prompt = f"{preface}\n\n{line}" if preface else line
        if tool_results:
            prompt += "\n\n[Tool results]\n" + json.dumps(tool_results, default=str)[:2000]
        intent = parse_intent(line)
        console.print(f"[dim]→ {intent.action}: {intent.planned_command}[/dim]")
        bus.emit("user_message", text=line[:200])

        def _live(ev: Dict[str, Any]) -> None:
            if ev.get("kind") in {
                "board_member_start",
                "board_member_end",
                "worker_pool",
                "step",
                "tool_result",
            }:
                detail = {
                    k: v
                    for k, v in ev.items()
                    if k not in {"ts", "kind"}
                }
                console.print(
                    f"[dim]… {ev.get('kind')} "
                    f"{json.dumps(detail, default=str)[:80]}[/dim]"
                )

        bus.on(_live)
        out = ask_superai(prompt, execute=True, verbose=False)
        bus.emit(
            "agent_done",
            ok=out.get("ok"),
            action=intent.action,
            cost=out.get("estimated_cost_usd"),
        )
        # Display (+ S1 token streaming)
        res = out.get("result")
        if isinstance(res, dict):
            body = (
                res.get("message")
                or res.get("result")
                or res.get("board", {}).get("summary")
                or json.dumps(res, default=str)[:2000]
            )
        else:
            body = str(res or out.get("error") or "")[:2000]
        # MOS-N6: optional auto-speak of assistant reply
        try:
            from .voice_io import speak_reply

            speak_reply(str(body or "")[:500])
        except Exception:
            pass
        if stream_enabled and body:
            try:
                from .token_stream import stream_tokens

                buf: List[str] = []

                def _tok(ch: str) -> None:
                    buf.append(ch)

                with Live(console=console, refresh_per_second=12) as live:
                    for ch in stream_tokens(str(body), chunk_size=20, on_token=_tok):
                        live.update(
                            Panel(
                                "".join(buf)[:3000],
                                title=f"agent ({intent.action}) · streaming",
                                border_style="green",
                            )
                        )
                body = "".join(buf) or body
            except Exception:
                console.print(
                    Panel(str(body), title=f"agent ({intent.action})", border_style="green")
                )
        else:
            console.print(
                Panel(str(body), title=f"agent ({intent.action})", border_style="green")
            )
        turn_cost = float(out.get("estimated_cost_usd") or 0)
        turn_tok = int(out.get("tokens") or 0)
        session_cost += turn_cost
        session_tokens += turn_tok
        console.print(
            f"[dim]mock={out.get('mock')} dry_run={out.get('dry_run')} "
            f"turn≈${turn_cost:.6f}  {_footer()}[/dim]"
        )
        if traces:
            render_trace(traces, limit=6)
        store.append_turn(
            sid,
            line,
            str(body)[:500],
            meta={
                "action": intent.action,
                "ok": out.get("ok"),
                "tools": len(tool_results),
                "tokens": turn_tok,
                "estimated_cost_usd": turn_cost,
            },
        )

    console.print(f"[dim]session saved: {sid}  {_footer()}[/dim]")
