"""
Agent session TUI (Phase 8 N1).

Patterns inspired by open-source coding agents (Aider/OpenCode-style):
  - visible tool/model steps
  - compact prior turns
  - plan vs act permission
Uses Rich (already a SuperAI dependency) — no heavy Textual dep required.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .ask_session import AskSessionStore
from .nl_intent import ask_superai, parse_intent
from .permission_mode import mode_from_config, normalize_mode
from .progress_events import get_progress_bus


console = Console()


def compact_turns(turns: List[Dict[str, Any]], max_chars: int = 1200) -> str:
    """Summarize prior turns for context window (OpenCode/Aider-like compact)."""
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

    store = AskSessionStore()
    sid = session_id or store.create()
    bus = get_progress_bus()
    traces: List[Dict[str, Any]] = []

    def _hook(ev: Dict[str, Any]) -> None:
        traces.append(ev)

    bus.on(_hook)

    console.print(
        Panel.fit(
            f"[bold]SuperAI Agent TUI[/bold]\n"
            f"session={sid}  permission={mode_from_config(cfg)}\n"
            f"Slash: /help /trace /compact /tool … /permission /profile /exit\n"
            f"Tools: /tool read path=… · grep pattern=… · write · diff_apply",
            border_style="cyan",
        )
    )

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
            if cmd in {"exit", "quit", "q"}:
                break
            if cmd == "help":
                console.print(
                    Markdown(
                        "- `/trace` show tool/step events\n"
                        "- `/compact` [smart] compact context\n"
                        "- `/tool read path=FILE` · `/tool grep pattern=X`\n"
                        "- `/tool write path=F content=…` (respects permission)\n"
                        "- `/tool diff_apply diff=…` (plan=dry-run)\n"
                        "- `/permission plan|ask|auto|yolo` · `/profile …`\n"
                        "- plain text → agent (`ask`)\n"
                    )
                )
                continue
            if cmd == "trace":
                render_trace(traces)
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
            if cmd == "permission":
                cfg.config["permission_mode"] = normalize_mode(arg or "ask")
                console.print(f"permission={cfg.config['permission_mode']}")
                continue
            if cmd == "profile":
                apply_profile_to_config(cfg, arg or "balanced")
                console.print(f"profile={cfg.config.get('run_profile')}")
                continue
            console.print(f"[yellow]Unknown slash: /{cmd}[/yellow]")
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
        # Display
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
        console.print(Panel(str(body), title=f"agent ({intent.action})", border_style="green"))
        console.print(
            f"[dim]mock={out.get('mock')} dry_run={out.get('dry_run')} "
            f"cost≈${float(out.get('estimated_cost_usd') or 0):.6f}[/dim]"
        )
        if traces:
            render_trace(traces, limit=6)
        store.append_turn(
            sid,
            line,
            str(body)[:500],
            meta={"action": intent.action, "ok": out.get("ok"), "tools": len(tool_results)},
        )

    console.print(f"[dim]session saved: {sid}[/dim]")
