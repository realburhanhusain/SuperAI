"""
SuperAI CLI (Phase 1 + stabilized higher-phase commands)

Entry point: superai = "scli.main:app"
"""

from __future__ import annotations

import atexit
import json
import re
import traceback
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core import __version__
from core.config import Config
from core.errors import SuperAIError
from core.history import TaskHistory
from core.logger import get_logger
from core.orchestrator import SuperAIOrchestrator
from core.task_planner import TaskPlanner

app = typer.Typer(
    name="superai",
    help="SuperAI - Intelligent Multi-Model AI Orchestration Platform",
    add_completion=True,  # G3: enable `superai --install-completion`
    # Default entry: NL agent when no subcommand (Improvement Phase 2)
    no_args_is_help=False,
    invoke_without_command=True,
)

console = Console()
logger = get_logger("superai.cli")

_AUTO_BACKUP_REGISTERED = False


def _register_auto_backup_if_enabled() -> None:
    """E5: on clean exit, encrypted backup when backup_enabled is true."""
    global _AUTO_BACKUP_REGISTERED
    if _AUTO_BACKUP_REGISTERED:
        return
    try:
        cfg = Config()
        if not cfg.get("backup_enabled", True):
            return

        def _on_exit() -> None:
            try:
                # Skip no-op noise if nothing changed
                from core.backup_manager import BackupManager

                bm = BackupManager()
                path = bm.create_backup(incremental=True, quiet=True)
                if path:
                    logger.info("Auto-backup on exit: %s", path)
            except Exception as e:  # noqa: BLE001
                logger.debug("Auto-backup on exit skipped/failed: %s", e)

        atexit.register(_on_exit)
        _AUTO_BACKUP_REGISTERED = True
    except Exception:  # noqa: BLE001
        pass


@app.callback()
def _main_callback(
    ctx: typer.Context,
    no_auto_backup: bool = typer.Option(
        False,
        "--no-auto-backup",
        help="Disable atexit auto-backup for this process",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="JSON automation mode for public results (V6 M079)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Prefer dry-run / no side effects where supported",
    ),
    ask_mode: bool = typer.Option(
        False,
        "--ask",
        help="Use NL product-route REPL instead of SuperAI agent TUI",
    ),
    agent: str = typer.Option(
        "build",
        "--agent",
        "-a",
        help="Default agent role when launching SuperAI TUI: build|plan|ask",
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Model for default SuperAI agent session"
    ),
    permission: Optional[str] = typer.Option(
        None, "--permission", help="plan|ask|auto|yolo for default agent session"
    ),
    session: Optional[str] = typer.Option(
        None, "--session", "-s", help="Resume SuperAI agent session id"
    ),
) -> None:
    # Global automation surface (M079/M080)
    try:
        from core.public_surface import set_dry_run, set_json_mode

        set_json_mode(bool(json_out))
        set_dry_run(bool(dry_run))
        ctx.ensure_object(dict)
        ctx.obj["json"] = bool(json_out)
        ctx.obj["dry_run"] = bool(dry_run)
    except Exception:
        pass
    if not no_auto_backup:
        _register_auto_backup_if_enabled()
    # No subcommand → front-door interactive (DoD-strict) or TUI
    if ctx.invoked_subcommand is None:
        if ask_mode:
            from core.nl_intent import interactive_repl

            console.print(
                Panel.fit(
                    "[bold]SuperAI[/bold] — natural language routes\n"
                    "Type a request, or 'help' / 'exit'. "
                    "Agent TUI: `superai agent` · one-shot: `superai do \"…\"`",
                    border_style="cyan",
                )
            )
            interactive_repl(execute=True, verbose=False)
            raise typer.Exit(0)
        # Interactive front door: empty / /tui → full agent TUI; else route task
        try:
            from core.parked_features import splash_banner

            banner = splash_banner()
        except Exception:
            banner = "SuperAI"
        console.print(
            Panel.fit(
                f"[bold]{banner.splitlines()[0] if banner else 'SuperAI'}[/bold]\n"
                "Type a task (front-door routes agent/board/run)\n"
                "Empty or `/tui` opens multi-panel agent · `/ask` NL REPL · `exit` quits",
                border_style="cyan",
            )
        )
        try:
            line = console.input("[bold green]superai>[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            raise typer.Exit(0)
        if not line or line.lower() in {"/tui", "tui", "/agent"}:
            from core.superai_agent.tui import run_superai_agent_tui

            run_superai_agent_tui(
                session_id=session,
                agent=agent,
                model=model,
                permission=permission,
            )
            raise typer.Exit(0)
        if line.lower() in {"/ask", "ask"}:
            from core.nl_intent import interactive_repl

            interactive_repl(execute=True, verbose=False)
            raise typer.Exit(0)
        if line.lower() in {"exit", "quit", "/exit", "/quit"}:
            raise typer.Exit(0)
        # Route one-shot via front door + NL execute
        from core.front_door import choose_path
        from core.nl_intent import ask_superai

        route = choose_path(line)
        console.print(
            f"[dim]→ front_door path={route.get('path')} "
            f"reason={route.get('reason')}[/dim]"
        )
        out = ask_superai(line, execute=True, verbose=False)
        console.print_json(data=out if isinstance(out, dict) else {"result": out})
        raise typer.Exit(0)


def _suggest_fix(exc: Exception) -> Optional[str]:
    """G2: suggested fixes for common failures."""
    msg = str(exc).lower()
    if "api key" in msg or "authentication" in msg or "401" in msg:
        return (
            "Set the provider API key env var and `superai config set mock_mode false`. "
            "Check `superai smoke-providers`."
        )
    if "rclone" in msg or "not found on path" in msg:
        return "Install/configure rclone, or use local `superai backup` / `superai restore <file>`."
    if "empty" in msg and "task" in msg:
        return 'Provide a non-empty task string, e.g. superai run "Create a FastAPI app"'
    if "pgvector" in msg or "chromadb" in msg or "embedding" in msg:
        return (
            "Set SUPERAI_EMBEDDING_HASH=1 for offline hash embeddings, "
            "or pip install -e \".[embeddings]\"."
        )
    if "connection" in msg or "timeout" in msg or "network" in msg:
        return "Check network/VPN; retry; or use mock_mode true for offline work."
    if isinstance(exc, SuperAIError) and exc.hint:
        return None  # already in user_message
    return "Run with --debug for traceback; see TASKBOARD.md and docs/PROGRESS.md."


def _print_error(exc: Exception, debug: bool = False) -> None:
    if isinstance(exc, SuperAIError):
        console.print(f"[red]Error:[/red] {exc.user_message()}")
    else:
        console.print(f"[red]Error:[/red] {exc}")
    suggestion = _suggest_fix(exc)
    if suggestion:
        console.print(f"[yellow]Suggested fix:[/yellow] {suggestion}")
    if debug:
        console.print(traceback.format_exc())


@app.command()
def version():
    """Show SuperAI version"""
    console.print(
        f"[bold green]SuperAI v{__version__}[/bold green] "
        "- Core Foundation (stabilized SuperAI)"
    )


@app.command("init")
def init_cmd(
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Skip prompts (also set SUPERAI_NON_INTERACTIVE=1)",
    ),
    full_install: bool = typer.Option(
        False,
        "--full-install",
        help="Run interactive install wizard (host tools + optional Postgres)",
    ),
):
    """Initialize SuperAI home directory, config, and discover environment"""
    config = Config()
    if non_interactive:
        config.set("non_interactive", True, persist=True)

    # Optional guided install (host tools + Postgres opt-in)
    if full_install and not non_interactive:
        from core.install_wizard import run_install_wizard

        wiz = run_install_wizard(interactive=True)
        console.print_json(data=wiz)
        console.print(
            "[dim]Next: superai doctor && superai run \"hello\"[/dim]"
        )
        return

    dirs = config.initialize()

    from core.discovery import discover_environment
    from core.constitution import ensure_default_constitution

    env = discover_environment()
    if env.get("mock_recommended"):
        config.set("mock_mode", True, persist=True)
    config.set("discovered_clis", env.get("clis_available") or [], persist=True)
    const_path = ensure_default_constitution()

    # Host tools checklist (not bundled). Optional auto via SUPERAI_AUTO_HOST_TOOLS.
    ht_line = ""
    try:
        from core.host_tools import (
            checklist as host_checklist,
            maybe_auto_install_on_setup,
            save_checklist_report,
        )

        ht = host_checklist(profile="core")
        save_checklist_report(ht)
        missing_ids = [m["id"] for m in (ht.get("missing") or [])]
        ht_line = (
            f"Host tools (core): {ht['totals']['present']}/{ht['totals']['checked']} present"
            f" · missing={missing_ids}\n"
        )
        auto = maybe_auto_install_on_setup()
        if auto is not None:
            ht_line += (
                f"Host tools auto ({'dry-run' if auto.get('dry_run') else 'live'}): "
                f"{auto.get('totals')}\n"
            )
    except Exception:
        pass

    console.print(
        Panel.fit(
            "[bold green]SuperAI initialized successfully![/bold green]\n\n"
            f"Home: {dirs['home']}\n"
            f"Config: {config.config_path}\n"
            f"Logs: {dirs['logs']}\n"
            f"History: {dirs['history']}\n"
            f"Memory: {dirs['memory']}\n"
            f"Skills: {dirs['skills']}\n"
            f"Backups: {dirs['backups']}\n"
            f"Constitution: {const_path}\n"
            f"mock_mode: {config.use_mock}\n"
            f"CLIs found: {', '.join(env.get('clis_available') or []) or '(none)'}\n"
            f"Models registered: {env.get('models_registered')}\n"
            f"rclone: {env.get('rclone_on_path')} | ollama: {env.get('ollama_on_path')}\n"
            f"{ht_line}\n"
            f"Next: superai install   # guided host tools + optional Postgres\n"
            f"      superai doctor && superai run \"hello\"",
            border_style="green",
        )
    )


@app.command()
def run(
    task: str = typer.Argument(..., help="The task to execute"),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Force primary worker: gpt-4o | cli:gemini | cli:gemini@MODEL",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Save result JSON to file path"
    ),
    output_format: str = typer.Option(
        "text",
        "--format",
        "-f",
        help="Output format: text or json",
    ),
    plan_only: bool = typer.Option(False, "--plan", help="Only show execution plan"),
    debug: bool = typer.Option(False, "--debug", help="Show full tracebacks"),
    resume: Optional[str] = typer.Option(
        None, "--resume", help="Resume task_id from step cache checkpoint"
    ),
    stream: bool = typer.Option(
        False, "--stream", help="S1: stream model tokens when available"
    ),
    workers: Optional[str] = typer.Option(
        None,
        "--workers",
        help="Worker pool: gpt-4o,cli:gemini@MODEL,cli:claude (see superai members)",
    ),
    worker_prefer: Optional[str] = typer.Option(
        None,
        "--worker-prefer",
        help="Worker auto-pick: mixed | api | cli | router (default: config worker_prefer)",
    ),
    pick_workers: bool = typer.Option(
        False,
        "--pick-workers",
        help="Interactively pick workers from detected API models + CLIs/models",
    ),
    profile: Optional[str] = typer.Option(
        None, "--profile", help="cheap | balanced | quality | local-only"
    ),
    permission: Optional[str] = typer.Option(
        None, "--permission", help="plan | ask | auto | yolo"
    ),
    with_clis: Optional[str] = typer.Option(
        None,
        "--with-clis",
        help="Comma-separated external CLIs after plan (e.g. claude,aider)",
    ),
    cli_live: bool = typer.Option(
        False,
        "--cli-live",
        help="With --with-clis: execute CLIs live (default dry-run)",
    ),
    cli_approve: bool = typer.Option(
        False,
        "--cli-approve",
        help="With --with-clis: approve file-modifying CLIs for live runs",
    ),
    critic: Optional[str] = typer.Option(
        None,
        "--critic",
        help="Critic mode for this run: off | light | council (default: config)",
    ),
    replan_approval: Optional[bool] = typer.Option(
        None,
        "--replan-approval/--no-replan-approval",
        help="Require HITL approval before recovery replan",
    ),
):
    """Run a task using SuperAI orchestration (mock by default)"""
    try:
        orchestrator = SuperAIOrchestrator()
        if profile:
            from core.run_profiles import apply_profile_to_config

            apply_profile_to_config(orchestrator.config, profile)
        if permission:
            from core.permission_mode import normalize_mode

            orchestrator.config.config["permission_mode"] = normalize_mode(permission)
            if normalize_mode(permission) == "plan":
                # plan mode forces dry-run style CLI fanout
                pass

        if plan_only:
            planner = TaskPlanner(
                orchestrator.model_router, model_caller=orchestrator.model_caller
            )
            steps = planner.create_plan(task)
            planner.print_plan(steps)
            return

        console.print(Panel.fit(f"[bold]Task:[/bold] {task}", border_style="blue"))

        # M6: hint incomplete runs
        if not resume:
            try:
                from core.step_cache import StepResultCache

                open_runs = [
                    r
                    for r in StepResultCache().list_runs()[:5]
                    if r.get("remaining_step_ids")
                ]
                if open_runs:
                    console.print(
                        f"[yellow]Incomplete runs available "
                        f"({len(open_runs)}). Resume: superai runs resume <id>[/yellow]"
                    )
            except Exception:  # noqa: BLE001
                pass

        cli_list = (
            [c.strip() for c in with_clis.split(",") if c.strip()]
            if with_clis
            else None
        )
        worker_list = (
            [c.strip() for c in workers.split(",") if c.strip()] if workers else None
        )
        if pick_workers and not worker_list:
            from core.approval_tui import prompt_pick_from_catalog

            worker_list = prompt_pick_from_catalog(
                title="Pick workers (API models + CLIs)",
                max_n=5,
                prefer=(worker_prefer or "mixed"),
            )
            console.print(f"[dim]Workers: {', '.join(worker_list)}[/dim]")
        if worker_prefer and worker_prefer.lower() not in {
            "mixed",
            "api",
            "cli",
            "router",
            "off",
        }:
            console.print(
                "[red]--worker-prefer must be mixed | api | cli | router | off[/red]"
            )
            raise typer.Exit(code=1)

        if stream and model:
            # S1: simple stream of a single model response (bypass multi-step for demo)
            console.print(f"[dim]Streaming {model}…[/dim]")
            chunks = []
            for ch in orchestrator.model_caller.stream(model=model, prompt=task):
                console.print(ch, end="")
                chunks.append(ch)
            console.print()
            result = {
                "success": True,
                "status": "success",
                "model_used": model,
                "result": "".join(chunks),
                "streamed": True,
            }
        else:
            from core.permission_mode import force_dry_run, mode_from_config

            pmode = permission or mode_from_config(orchestrator.config)
            cli_dry = not cli_live
            if force_dry_run(pmode):
                cli_dry = True
            result = orchestrator.run_task(
                task=task,
                forced_model=model,
                verbose=verbose,
                resume_task_id=resume,
                with_clis=cli_list,
                cli_dry_run=cli_dry,
                cli_approve=cli_approve or (not cli_live),
                workers=worker_list,
                worker_prefer=worker_prefer.lower() if worker_prefer else None,
                critic_mode=critic,
                replan_requires_approval=replan_approval,
            )

        if output:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str)
            console.print(f"[green]Result saved to {output}[/green]")

        if result.get("status") == "waiting_human":
            clars = result.get("clarifications") or []
            cid = (clars[0] or {}).get("id") if clars else None
            console.print(
                Panel(
                    f"[bold yellow]Waiting for human[/bold yellow]\n"
                    f"Task ID: {result.get('task_id')}\n"
                    f"{result.get('message')}\n"
                    + (
                        f"Answer: superai hitl answer {cid} approve\n"
                        f"Resume: superai run \"{task}\" --resume {result.get('task_id')}"
                        if cid
                        else ""
                    ),
                    title="HITL",
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=2)

        # Cost / contract footer (Improvement Phase 1/3)
        console.print(
            f"[dim]cost≈${float(result.get('estimated_cost_usd') or 0):.6f}  "
            f"tokens={result.get('tokens') or result.get('total_tokens') or 0}  "
            f"mock={result.get('mock')} dry_run={result.get('dry_run')}  "
            f"profile={orchestrator.config.get('run_profile')}  "
            f"permission={orchestrator.config.get('permission_mode')}[/dim]"
        )

        if output_format.lower() == "json":
            console.print_json(data=result)
        else:
            summary = result.get("result") or result.get("message") or ""
            status = result.get("status", "unknown")
            color = "green" if result.get("success") else "yellow"
            meta = result.get("metadata") or {}
            extra = ""
            if meta.get("cli_parallel"):
                extra += f"\n[bold]CLIs:[/bold] {meta.get('cli_parallel')}"
            if meta.get("adaptation_events"):
                extra += (
                    f"\n[dim]adaptation events: "
                    f"{len(meta.get('adaptation_events') or [])}[/dim]"
                )
            console.print(
                Panel(
                    f"[bold]Status:[/bold] {status}\n"
                    f"[bold]Task ID:[/bold] {result.get('task_id')}\n"
                    f"[bold]Model:[/bold] {result.get('model_used')}\n"
                    f"[bold]Duration:[/bold] {result.get('duration')}s\n"
                    f"[bold]Mode:[/bold] {result.get('mode')}\n"
                    f"{extra}\n\n"
                    f"{summary}",
                    title="Result",
                    border_style=color,
                )
            )
    except typer.Exit:
        raise
    except Exception as e:  # noqa: BLE001
        _print_error(e, debug=debug)
        raise typer.Exit(code=1) from e


@app.command()
def plan(
    task: str = typer.Argument(..., help="Task to create execution plan for"),
    export: Optional[str] = typer.Option(
        None, "--export", help="Export format: json | markdown | md | mermaid"
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Write export to file"
    ),
):
    """Show execution plan without running the task (optional --export)"""
    orchestrator = SuperAIOrchestrator()
    planner = TaskPlanner(orchestrator.model_router)
    steps = planner.create_plan(task)
    if export:
        fmt = export.lower().strip()
        if fmt in {"md", "markdown"}:
            text = planner.export_plan_markdown(task, steps)
            if output:
                Path = __import__("pathlib").Path
                Path(output).write_text(text, encoding="utf-8")
                console.print(f"[green]Wrote[/green] {output}")
            else:
                console.print(text)
        elif fmt in {"mermaid", "mmd"}:
            text = planner.export_plan_mermaid(task, steps)
            if output:
                from pathlib import Path as P

                P(output).write_text(text, encoding="utf-8")
                console.print(f"[green]Wrote[/green] {output}")
            else:
                console.print(text)
        else:
            data = planner.export_plan(task, steps)
            if output:
                with open(output, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                console.print(f"[green]Wrote[/green] {output}")
            else:
                console.print_json(data=data)
        return
    planner.print_plan(steps)


@app.command()
def status(
    cost: bool = typer.Option(
        False, "--cost", help="V4 S9: budget spend, circuits, cache stats"
    ),
):
    """Show current SuperAI system status"""
    config = Config()
    history = TaskHistory()
    emb = "n/a"
    mem_count = "n/a"
    try:
        from core.memory_palace import MemoryPalace

        mp = MemoryPalace()
        st = mp.get_memory_stats()
        emb = st.get("embedding", "n/a")
        mem_count = st.get("total_memories", "n/a")
    except Exception:  # noqa: BLE001
        pass
    if cost:
        from core.budget import BudgetGuard

        payload: dict = {
            "budget": BudgetGuard().snapshot(),
            "enforce_budget": config.get("enforce_budget", True),
            "run_profile": config.get("run_profile"),
            "permission_mode": config.get("permission_mode"),
            "mock_mode": config.use_mock,
        }
        try:
            from core.provider_health import ProviderHealthStore

            payload["provider_health"] = ProviderHealthStore().summary() if hasattr(
                ProviderHealthStore(), "summary"
            ) else ProviderHealthStore().snapshot() if hasattr(
                ProviderHealthStore(), "snapshot"
            ) else {}
        except Exception as e:
            payload["provider_health_error"] = str(e)[:200]
        try:
            from pathlib import Path

            cache_dir = Path.home() / ".superai" / "cache" / "boards"
            payload["board_cache_files"] = (
                len(list(cache_dir.glob("*.json"))) if cache_dir.is_dir() else 0
            )
        except Exception:
            payload["board_cache_files"] = 0
        try:
            from core.step_cache import StepResultCache

            sc = StepResultCache()
            payload["step_cache_entries"] = len((sc._data.get("entries") or {}))
        except Exception:
            payload["step_cache_entries"] = 0
        try:
            from core.spend_report import spend_report

            rep = spend_report(days=7)
            payload["cache_hit_rate"] = rep.get("cache_hit_rate")
            payload["spend_total_estimated_usd"] = rep.get("total_estimated_usd")
            payload["mock_vs_live"] = {
                "mock": bool(config.use_mock),
                "label": "MOCK" if config.use_mock else "LIVE",
            }
        except Exception:
            pass
        console.print_json(data=payload)
        return
    console.print(
        Panel.fit(
            f"[bold]SuperAI Status[/bold]\n\n"
            f"Version: {__version__}\n"
            f"Config: {config.config_path}\n"
            f"Home: {config.home_dir}\n"
            f"mock_mode: {config.use_mock}\n"
            f"log_level: {config.get('log_level')}\n"
            f"default_supervisor: {config.default_supervisor}\n"
            f"history_entries: {history.count()}\n"
            f"memory_count: {mem_count}\n"
            f"embedding: {emb}\n"
            f"Tracks: A–E done; F nearly done; G–I pending (see TASKBOARD.md)",
            border_style="cyan",
        )
    )


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of recent runs"),
    task_id: Optional[str] = typer.Option(None, "--task-id", help="Show one task"),
):
    """Show recent task history"""
    store = TaskHistory()
    if task_id:
        record = store.get(task_id)
        if not record:
            console.print(f"[yellow]No history for task_id={task_id}[/yellow]")
            raise typer.Exit(code=1)
        console.print_json(data=record)
        return

    records = store.list(limit=limit)
    if not records:
        console.print("[yellow]No task history yet. Run a task first.[/yellow]")
        return

    table = Table(title=f"Recent tasks (last {len(records)})")
    table.add_column("Task ID")
    table.add_column("Status")
    table.add_column("Model")
    table.add_column("Duration")
    table.add_column("Task")
    for r in records:
        table.add_row(
            str(r.get("task_id", "")),
            str(r.get("status", "")),
            str(r.get("model_used", "")),
            str(r.get("duration", "")),
            str(r.get("task", ""))[:60],
        )
    console.print(table)


config_app = typer.Typer(help="View and modify configuration")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show():
    """Show full configuration"""
    cfg = Config()
    console.print_json(data=cfg.show())


@config_app.command("get")
def config_get(key: str = typer.Argument(..., help="Config key")):
    """Get a configuration value"""
    cfg = Config()
    console.print(cfg.get(key))


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key"),
    value: str = typer.Argument(..., help="Value (bool/number auto-parsed)"),
):
    """Set a configuration value"""
    cfg = Config()
    parsed: object = value
    lower = value.lower()
    if lower in {"true", "false"}:
        parsed = lower == "true"
    else:
        try:
            parsed = int(value)
        except ValueError:
            try:
                parsed = float(value)
            except ValueError:
                parsed = value
    cfg.set(key, parsed, persist=True)
    console.print(f"[green]Set {key} = {parsed}[/green]")


@app.command()
def reflect(
    distill: bool = typer.Option(
        False, "--distill", help="Also run knowledge distillation after reflection"
    ),
):
    """Trigger reflection on recent learnings"""
    from core.learning_engine import LearningEngine
    from core.memory_palace import MemoryPalace

    memory = MemoryPalace()
    engine = LearningEngine(memory)
    result = engine.reflect()

    patterns = result.get("patterns_identified") or result.get("insights") or []
    pattern_text = "\n".join(f"• {p}" for p in patterns) if patterns else "• (none yet)"

    console.print(
        Panel.fit(
            f"[bold]Reflection Report[/bold]\n\n"
            f"Total Learnings: {result.get('total_learnings', 0)}\n"
            f"Successes: {result.get('success_count', 0)} | "
            f"Failures: {result.get('failure_count', 0)}\n"
            f"Success Rate: {result.get('success_rate', 0)}%\n"
            f"Conflicts: {result.get('conflicts_detected', 0)}\n"
            f"Memories decayed: {result.get('memories_decayed', 0)}\n\n"
            f"[bold]Patterns[/bold]\n{pattern_text}\n\n"
            f"[green]{result.get('message', '')}[/green]\n"
            f"[dim]{result.get('recommendation', '')}[/dim]",
            border_style="cyan",
        )
    )

    if distill:
        d = engine.distill_knowledge()
        console.print(
            Panel.fit(
                f"[bold]Distillation[/bold]\n{d.get('message')}",
                border_style="blue",
            )
        )


@app.command()
def learnings(
    query: Optional[str] = typer.Argument(
        None, help="Natural language query about what was learned"
    ),
    task_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter summary by task type"
    ),
    limit: int = typer.Option(8, "--limit", "-n", help="Max semantic results"),
):
    """View or search what the system has learned"""
    from core.learning_engine import LearningEngine
    from core.memory_palace import MemoryPalace

    memory = MemoryPalace()
    engine = LearningEngine(memory)

    if query:
        results = memory.query_semantic(query, top_k=limit)
        if results:
            console.print(f"[bold]Results for:[/bold] {query}\n")
            for r in results:
                content = r.get("content", "")
                meta = r.get("metadata") or {}
                badge = "ok" if meta.get("success") is True else (
                    "fail" if meta.get("success") is False else "?"
                )
                console.print(
                    f"• [{badge}] {meta.get('model', '?')} / "
                    f"{meta.get('task_type', '?')}: {content[:280]}...\n"
                )
        else:
            console.print("[yellow]No relevant learnings found.[/yellow]")
    else:
        summary = engine.get_learnings_summary(task_type=task_type)
        stats = memory.get_memory_stats()
        console.print(
            Panel.fit(
                f"[bold]Learning Summary[/bold]\n\n"
                f"Total Learnings: {summary['total_learnings']}\n"
                f"Success Rate: {summary['success_rate']}%\n"
                f"Successes: {summary['success_count']} | "
                f"Failures: {summary['failure_count']}\n"
                f"Memory store: {stats.get('total_memories')} "
                f"(pgvector={stats.get('using_pgvector')} backend={stats.get('backend')})",
                border_style="green",
            )
        )


@app.command()
def conflicts(
    resolve: bool = typer.Option(
        False, "--resolve", help="Auto-resolve by deprecating weaker memories"
    ),
    task_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by task type"
    ),
):
    """Show detected conflicting learnings"""
    from core.learning_engine import LearningEngine
    from core.memory_palace import MemoryPalace

    memory = MemoryPalace()
    engine = LearningEngine(memory)
    found = engine.detect_conflicts(task_type=task_type)

    if found:
        console.print(f"[bold red]Found {len(found)} conflicting learning group(s):[/bold red]\n")
        for c in found:
            console.print(
                f"• [{c.get('severity', '?')}] "
                f"Task Type: {c.get('task_type')} | Model: {c.get('model')}"
            )
            console.print(f"  {c.get('description')}\n")
    else:
        console.print("[green]No conflicts detected.[/green]")

    if resolve:
        result = engine.resolve_conflicts(auto_resolve=True)
        console.print(
            Panel.fit(
                f"[bold]Resolve[/bold]\n{result.get('message')}\n"
                f"Deprecated: {result.get('conflicts_resolved', 0)}",
                border_style="yellow",
            )
        )


@app.command()
def backup(
    full: bool = typer.Option(False, "--full", help="Force full backup (ignore incremental)"),
    cloud: bool = typer.Option(
        False, "--cloud", help="After local backup, sync latest to rclone remote"
    ),
    remote: str = typer.Option(
        "superai", "--remote", help="rclone remote name (used with --cloud)"
    ),
    remote_path: str = typer.Option(
        "superai-backups", "--remote-path", help="Path on remote (used with --cloud)"
    ),
    keep: Optional[int] = typer.Option(
        None, "--keep", help="Retention: keep newest N backups after create"
    ),
    scope: Optional[str] = typer.Option(
        None,
        "--scope",
        help="Selective scopes comma-list: memory,skills,config,history,logs,plugins,full",
    ),
):
    """Create an encrypted incremental backup of SuperAI home data"""
    from core.backup_manager import BackupManager

    bm = BackupManager()
    if not bm.key_file.exists():
        console.print(
            "[yellow]Warning: encryption key will be created. "
            f"Back up {bm.key_file} securely.[/yellow]"
        )
    scopes = [s.strip() for s in scope.split(",")] if scope else None
    path = bm.create_backup(
        force_full=full, incremental=not full, scopes=scopes
    )
    if path:
        console.print(f"[green]Encrypted backup created:[/green] {path}")
    else:
        console.print(
            "[yellow]No new/changed files to backup (or sources empty). "
            "Try --full after creating data.[/yellow]"
        )
    if keep is not None:
        ret = bm.apply_retention(keep=keep)
        console.print(
            f"[dim]Retention: kept {ret['kept']}, removed {ret['removed_count']}[/dim]"
        )
    if cloud:
        ok = bm.sync_to_cloud(remote=remote, remote_path=remote_path)
        if ok:
            console.print(f"[green]Synced to {remote}:{remote_path}[/green]")
        else:
            console.print(
                f"[red]Cloud sync failed[/red] (is rclone configured for remote '{remote}'?)"
            )
            raise typer.Exit(code=1)


@app.command("backup-status")
def backup_status():
    """Show backup system status"""
    from core.backup_manager import BackupManager

    bm = BackupManager()
    status_data = bm.get_backup_status()
    console.print(Panel.fit(str(status_data), title="Backup Status", border_style="blue"))
    if not status_data.get("key_present"):
        console.print(
            "[yellow]Warning: encryption key missing — create a backup to generate one.[/yellow]"
        )


@app.command("backup-verify")
def backup_verify(
    path: Optional[str] = typer.Option(
        None, "--path", "-p", help="Backup file (default: latest)"
    ),
):
    """Verify integrity of a backup (decrypt + list members)"""
    from core.backup_manager import BackupManager

    bm = BackupManager()
    result = bm.verify_backup(path)
    if result.get("ok"):
        console.print(
            Panel.fit(
                f"[bold green]OK[/bold green]\n{result.get('message')}\n"
                f"Path: {result.get('path')}\n"
                f"SHA256: {result.get('sha256')}\n"
                f"Members: {result.get('member_count')}",
                title="Backup Verify",
                border_style="green",
            )
        )
    else:
        console.print(f"[red]Verify failed:[/red] {result.get('error')}")
        raise typer.Exit(code=1)


@app.command()
def restore(
    path: Optional[str] = typer.Argument(
        None, help="Path to .tar.zst.enc backup file (omit with --cloud)"
    ),
    dest: Optional[str] = typer.Option(
        None, "--dest", "-d", help="Restore directory (default: ~/.superai/restore)"
    ),
    cloud: bool = typer.Option(
        False, "--cloud", help="Pull from rclone remote then restore (F5.2)"
    ),
    remote: str = typer.Option("superai", "--remote", help="rclone remote name"),
    remote_path: str = typer.Option(
        "superai-backups", "--remote-path", help="Path on remote"
    ),
    filename: Optional[str] = typer.Option(
        None, "--filename", help="Remote backup filename (default: all then latest)"
    ),
):
    """Restore files from an encrypted backup (local path or --cloud pull)"""
    from core.backup_manager import BackupManager

    bm = BackupManager()
    if cloud:
        result = bm.restore_from_cloud(
            remote=remote,
            remote_path=remote_path,
            filename=filename or path,
            restore_dir=dest,
        )
    else:
        if not path:
            console.print("[red]Provide a local backup path or use --cloud[/red]")
            raise typer.Exit(code=1)
        result = bm.restore_backup(path, restore_dir=dest)

    if result.get("ok"):
        console.print(
            Panel.fit(
                f"[bold green]Restored[/bold green]\n{result.get('message')}\n"
                f"Files: {result.get('member_count')}\n"
                f"Local: {result.get('local_backup', path)}",
                title="Restore",
                border_style="green",
            )
        )
    else:
        console.print(f"[red]Restore failed:[/red] {result.get('error')}")
        raise typer.Exit(code=1)


@app.command("list-skills")
def list_skills():
    """List skills in the SuperAI skill library"""
    from core.skills import SkillsManager

    sm = SkillsManager()
    skills = sm.list_skills()
    if not skills:
        console.print("[yellow]No skills yet. Successful tasks can auto-create them.[/yellow]")
        return
    table = Table(title="Skills")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Tags")
    table.add_column("Uses")
    table.add_column("Success rate")
    table.add_column("Description")
    for s in skills:
        table.add_row(
            str(s.get("name")),
            str(s.get("status", "active")),
            ",".join(s.get("tags") or []),
            str(s.get("usage_count", 0)),
            str(s.get("success_rate", "")),
            str(s.get("description", ""))[:50],
        )
    console.print(table)


@app.command("skill-promote")
def skill_promote(name: str = typer.Argument(..., help="Skill name to promote from sandbox")):
    """Promote a sandboxed skill to active (injectable)"""
    from core.skills import SkillsManager

    sm = SkillsManager()
    if sm.promote_skill(name):
        console.print(f"[green]Promoted skill:[/green] {name}")
    else:
        console.print(f"[red]Skill not found:[/red] {name}")
        raise typer.Exit(code=1)


@app.command("skill-rollback")
def skill_rollback(name: str = typer.Argument(..., help="Skill name to rollback last improvement")):
    """Rollback last improvement section on a skill"""
    from core.skills import SkillsManager

    sm = SkillsManager()
    if sm.rollback_skill(name):
        console.print(f"[green]Rolled back skill:[/green] {name}")
    else:
        console.print(f"[yellow]Nothing to rollback or skill missing:[/yellow] {name}")
        raise typer.Exit(code=1)


@app.command("skill")
def skill_cmd(
    action: str = typer.Argument(
        ..., help="create | delete | improve | deps | test | validate"
    ),
    name: str = typer.Argument(..., help="Skill name"),
    content: Optional[str] = typer.Argument(
        None, help="Content for create/improve, or comma deps for deps"
    ),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma tags for create"),
    description: str = typer.Option("", "--description", "-d"),
):
    """Skill CRUD: create / delete / improve / deps / test"""
    from core.skills import SkillsManager

    sm = SkillsManager()
    act = action.lower()
    if act == "create":
        if not content:
            console.print("[red]Provide skill body content[/red]")
            raise typer.Exit(1)
        tag_list = [t.strip() for t in tags.split(",")] if tags else []
        path = sm.create_skill(
            name, content, tags=tag_list, description=description or name
        )
        console.print(f"[green]Created[/green] {path}")
        return
    if act == "delete":
        ok = sm.delete_skill(name)
        console.print("[green]Deleted[/green]" if ok else f"[red]Not found:[/red] {name}")
        if not ok:
            raise typer.Exit(1)
        return
    if act == "improve":
        if not content:
            console.print("[red]Provide improvement text[/red]")
            raise typer.Exit(1)
        ok = sm.improve_skill(name, content, reason="cli improve")
        if not ok:
            console.print(f"[red]Not found:[/red] {name}")
            raise typer.Exit(1)
        console.print(f"[green]Improved[/green] {name}")
        return
    if act == "deps":
        deps = [d.strip() for d in (content or "").split(",") if d.strip()]
        ok = sm.set_dependencies(name, deps)
        if not ok:
            console.print(f"[red]Not found:[/red] {name}")
            raise typer.Exit(1)
        console.print_json(data={"name": name, "depends_on": deps})
        return
    if act in {"test", "validate"}:
        console.print_json(data=sm.validate_skill(name))
        return
    console.print(f"[red]Unknown action: {action}[/red]")
    raise typer.Exit(1)


@app.command("host-tools")
def host_tools_cmd(
    action: str = typer.Argument(
        "check",
        help="check | install | matrix | profiles",
    ),
    profile: str = typer.Option(
        "full",
        "--profile",
        "-p",
        help="core | agentic | cloud | full",
    ),
    tools: Optional[str] = typer.Option(
        None,
        "--tools",
        "-t",
        help="Comma-separated tool ids (install only), e.g. git,gh,aider",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--live",
        help="Install: dry-run by default; --live runs package managers",
    ),
    category: Optional[str] = typer.Option(
        None,
        "--category",
        "-c",
        help="Filter: shell | vcs | cloud | ai_cli | container | utility",
    ),
    json_out: bool = typer.Option(False, "--json", help="JSON output"),
):
    """
    Host tools checklist + optional auto-install (NOT bundled in SuperAI).

    Detects git, gh, cloud CLIs, AI agent CLIs, etc. on PATH and can install
    missing ones via winget/choco/brew/apt/pip/npm when recipes exist.

    Auto on init/onboard: set SUPERAI_AUTO_HOST_TOOLS=1 (dry-run) or
    SUPERAI_AUTO_HOST_TOOLS=install (live core profile).
    """
    from core.host_tools import (
        PROFILES,
        checklist,
        install_tools,
        list_catalog,
        save_checklist_report,
    )

    if action == "profiles":
        data = {"profiles": PROFILES}
        if json_out:
            console.print_json(data=data)
        else:
            for k, v in PROFILES.items():
                console.print(f"[cyan]{k}[/cyan]: {v}")
        return

    if action == "matrix":
        rows = []
        for t in list_catalog(profile=profile, category=category):
            rows.append(
                {
                    "id": t.id,
                    "name": t.name,
                    "category": t.category,
                    "auto": t.auto_installable,
                    "winget": t.winget,
                    "brew": t.brew,
                    "apt": t.apt,
                    "pip": t.pip,
                    "npm": t.npm,
                    "url": t.url,
                    "profiles": t.profiles,
                }
            )
        if json_out:
            console.print_json(data={"tools": rows, "bundled": False})
            return
        table = Table(title="Host tools install matrix (not bundled)")
        table.add_column("id")
        table.add_column("category")
        table.add_column("auto")
        table.add_column("winget / brew / pip / npm")
        for r in rows:
            recipe = " · ".join(
                x
                for x in [
                    f"winget:{r['winget']}" if r.get("winget") else "",
                    f"brew:{r['brew']}" if r.get("brew") else "",
                    f"pip:{r['pip']}" if r.get("pip") else "",
                    f"npm:{r['npm']}" if r.get("npm") else "",
                ]
                if x
            ) or (r.get("url") or "manual")
            table.add_row(
                r["id"],
                r["category"],
                "yes" if r["auto"] else "no",
                recipe[:60],
            )
        console.print(table)
        console.print(
            "[dim]These are host installs — not part of the SuperAI Python package.[/dim]"
        )
        return

    if action == "install":
        ids = [x.strip() for x in tools.split(",")] if tools else None
        report = install_tools(
            ids,
            profile=profile,
            dry_run=dry_run,
            only_missing=True,
        )
        if json_out:
            console.print_json(data=report)
            return
        table = Table(
            title=f"Host tools install ({'dry-run' if dry_run else 'LIVE'}) · {profile}"
        )
        table.add_column("id")
        table.add_column("status")
        table.add_column("detail", max_width=70)
        for r in report.get("results") or []:
            detail = (
                r.get("command_str")
                or r.get("hint")
                or r.get("error")
                or r.get("path")
                or r.get("notes")
                or ""
            )
            table.add_row(str(r.get("id")), str(r.get("status")), str(detail)[:70])
        console.print(table)
        console.print_json(data={"totals": report.get("totals"), "next": report.get("next")})
        if not dry_run and not report.get("ok"):
            raise typer.Exit(1)
        return

    # check (default)
    report = checklist(profile=profile, category=category)
    save_checklist_report(report)
    if json_out:
        console.print_json(data=report)
        return
    table = Table(title=f"Host tools checklist · profile={profile}")
    table.add_column("id")
    table.add_column("status")
    table.add_column("path / hint", max_width=70)
    for t in report.get("tools") or []:
        if t.get("available"):
            table.add_row(
                t["id"],
                "[green]present[/green]",
                str(t.get("path") or "")[:70],
            )
        else:
            table.add_row(
                t["id"],
                "[yellow]missing[/yellow]",
                str(t.get("install_hint") or "")[:70],
            )
    console.print(table)
    totals = report.get("totals") or {}
    console.print(
        f"[dim]present={totals.get('present')}/{totals.get('checked')} · "
        f"missing_auto={totals.get('missing_auto_installable')} · "
        f"NOT bundled in SuperAI package[/dim]"
    )
    console.print(
        "[dim]Install dry-run: superai host-tools install --profile core --dry-run\n"
        "Install live:     superai host-tools install --profile core --live[/dim]"
    )


@app.command()
def discover():
    """Discover installed AI CLIs, API keys, and environment"""
    from core.discovery import discover_environment

    env = discover_environment()
    table = Table(title="External CLIs")
    table.add_column("Name")
    table.add_column("Available")
    table.add_column("Path")
    table.add_column("Modifies files")
    for c in env.get("clis") or []:
        table.add_row(
            str(c.get("name")),
            str(c.get("available")),
            str(c.get("path") or ""),
            str(c.get("modifies_files")),
        )
    console.print(table)
    console.print(
        Panel.fit(
            f"Models registered: {env.get('models_registered')} ({env.get('model_source')})\n"
            f"API keys: {env.get('api_keys_present')}\n"
            f"ollama: {env.get('ollama_on_path')} | rclone: {env.get('rclone_on_path')}\n"
            f"mock_recommended: {env.get('mock_recommended')}",
            title="Environment",
            border_style="cyan",
        )
    )


@app.command("cli-parallel")
def cli_parallel(
    task: str = typer.Argument(..., help="Task for all CLIs / agentic fan-out"),
    clis: Optional[str] = typer.Option(
        None,
        "--clis",
        help="Comma-separated CLI names (default: discovered or claude,aider,cursor,gemini)",
    ),
    workers: int = typer.Option(4, "--workers", "-w", help="Max parallel workers"),
    dry_run: bool = typer.Option(
        True, "--dry-run/--live", help="Dry-run by default (safe); --live executes"
    ),
    approve: bool = typer.Option(
        False, "--approve", help="Approve file-modifying CLIs for live runs"
    ),
    agentic: bool = typer.Option(
        True,
        "--agentic/--raw",
        help="Agentic roles + supervisor merge (default) or raw same-prompt fan-out",
    ),
):
    """
    Run multiple external CLIs in parallel; track all on one dashboard.

    Watch live: superai dashboard  |  superai web → /cli-pool
    """
    from core.cli_pool import ParallelCLIManager
    from core.audit_log import AuditLog

    mgr = ParallelCLIManager()
    cli_list = [c.strip() for c in clis.split(",")] if clis else None
    if agentic:
        result = mgr.run_agentic_parallel(
            task,
            clis=cli_list,
            max_workers=workers,
            dry_run=dry_run,
            auto_approve=approve or dry_run,
        )
    else:
        work = [
            {"cli": c, "prompt": task, "role": "worker"}
            for c in (cli_list or ["claude", "aider", "cursor"])
        ]
        result = mgr.run_parallel(
            work,
            max_workers=workers,
            dry_run=dry_run,
            auto_approve=approve or dry_run,
            workflow_label="raw-parallel",
        )
    AuditLog().record(
        "cli_parallel",
        {
            "workflow_id": result.get("workflow_id"),
            "total": result.get("total"),
            "succeeded": result.get("succeeded"),
            "dry_run": dry_run,
        },
    )
    # Compact table
    table = Table(title=f"Parallel CLI — {result.get('workflow_id')}")
    table.add_column("CLI")
    table.add_column("Role")
    table.add_column("Status")
    table.add_column("Sec")
    table.add_column("Output")
    for j in result.get("jobs") or []:
        table.add_row(
            str(j.get("cli")),
            str(j.get("role")),
            str(j.get("status")),
            str(j.get("duration_sec")),
            str(j.get("stdout_tail") or j.get("error") or "")[:60].replace("\n", " "),
        )
    console.print(table)
    if result.get("synthesis"):
        console.print(
            Panel(
                str((result.get("synthesis") or {}).get("text") or result.get("synthesis"))[
                    :2000
                ],
                title="Supervisor synthesis",
                border_style="green",
            )
        )
    console.print(
        f"[dim]Dashboard: superai dashboard · web /cli-pool · "
        f"ok={result.get('succeeded')}/{result.get('total')}[/dim]"
    )
    if not result.get("ok") and not dry_run:
        raise typer.Exit(1)


@app.command("cli-jobs")
def cli_jobs_cmd(
    action: str = typer.Argument("list", help="list | snapshot | clear"),
    workflow_id: Optional[str] = typer.Option(None, "--workflow", "-w"),
    status: Optional[str] = typer.Option(None, "--status"),
):
    """List / snapshot / clear parallel CLI job registry (dashboard feed)"""
    from core.cli_pool import ParallelCLIManager

    mgr = ParallelCLIManager()
    if action == "snapshot":
        console.print_json(data=mgr.snapshot_for_dashboard())
        return
    if action == "clear":
        n = mgr.clear_finished()
        console.print(f"[green]Cleared {n} finished jobs[/green]")
        return
    console.print_json(
        data=mgr.list_jobs(status=status, workflow_id=workflow_id, limit=50)
    )


@app.command("term-parallel")
def term_parallel(
    task: str = typer.Argument(
        ..., help="Task label for agentic multi-terminal fan-out"
    ),
    commands: Optional[str] = typer.Option(
        None,
        "--commands",
        "-c",
        help="Semicolon-separated commands (raw mode). Example: 'python -V;python -c print(1)'",
    ),
    workers: int = typer.Option(4, "--workers", "-w", help="Max parallel terminals"),
    dry_run: bool = typer.Option(
        True, "--dry-run/--live", help="Dry-run by default; --live executes"
    ),
    approve: bool = typer.Option(
        False, "--approve", help="Approve live terminal execution"
    ),
    agentic: bool = typer.Option(
        True,
        "--agentic/--raw",
        help="Agentic roles + supervisor merge (default) or raw command fan-out",
    ),
    cwd: Optional[str] = typer.Option(
        None, "--cwd", help="Working directory (must be under workspace)"
    ),
):
    """
    Run multiple shell terminals in parallel; track all on one dashboard.

    Watch live: superai dashboard  |  superai web → /terminals
    """
    from core.terminal_pool import ParallelTerminalManager
    from core.audit_log import AuditLog

    mgr = ParallelTerminalManager()
    if agentic and not commands:
        result = mgr.run_agentic_parallel(
            task,
            max_workers=workers,
            dry_run=dry_run,
            auto_approve=approve or dry_run,
            cwd=cwd,
        )
    else:
        # Parse semicolon-separated commands into work items
        if commands:
            parts = [p.strip() for p in commands.split(";") if p.strip()]
        else:
            parts = []
        if not parts:
            # Raw mode without commands: still use default agentic terminals as raw
            work = mgr._default_agentic_terminals(task)
            for w in work:
                w["role"] = "worker"
        else:
            work = [
                {
                    "title": f"term-{i + 1}",
                    "role": "worker",
                    "command": p,
                }
                for i, p in enumerate(parts)
            ]
        result = mgr.run_parallel(
            work,
            max_workers=workers,
            dry_run=dry_run,
            auto_approve=approve or dry_run,
            workflow_label="raw-terminals" if commands else "agentic-as-raw",
            cwd=cwd,
        )

    AuditLog().record(
        "term_parallel",
        {
            "workflow_id": result.get("workflow_id"),
            "total": result.get("total"),
            "succeeded": result.get("succeeded"),
            "dry_run": dry_run,
        },
    )
    table = Table(title=f"Parallel terminals — {result.get('workflow_id')}")
    table.add_column("Title")
    table.add_column("Role")
    table.add_column("Status")
    table.add_column("Sec")
    table.add_column("Command")
    table.add_column("Output")
    for s in result.get("sessions") or []:
        cmd = s.get("command") or []
        cmd_s = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        table.add_row(
            str(s.get("title")),
            str(s.get("role")),
            str(s.get("status")),
            str(s.get("duration_sec")),
            cmd_s[:40],
            str(s.get("stdout_tail") or s.get("error") or "")[:50].replace("\n", " "),
        )
    console.print(table)
    if result.get("synthesis"):
        console.print(
            Panel(
                str(
                    (result.get("synthesis") or {}).get("text")
                    or result.get("synthesis")
                )[:2000],
                title="Supervisor synthesis",
                border_style="cyan",
            )
        )
    console.print(
        f"[dim]Dashboard: superai dashboard · web /terminals · "
        f"ok={result.get('succeeded')}/{result.get('total')}[/dim]"
    )
    if not result.get("ok") and not dry_run:
        raise typer.Exit(1)


@app.command("term-jobs")
def term_jobs_cmd(
    action: str = typer.Argument("list", help="list | snapshot | clear"),
    workflow_id: Optional[str] = typer.Option(None, "--workflow", "-w"),
    status: Optional[str] = typer.Option(None, "--status"),
):
    """List / snapshot / clear parallel terminal session registry (dashboard feed)"""
    from core.terminal_pool import ParallelTerminalManager

    mgr = ParallelTerminalManager()
    if action == "snapshot":
        console.print_json(data=mgr.snapshot_for_dashboard())
        return
    if action == "clear":
        n = mgr.clear_finished()
        console.print(f"[green]Cleared {n} finished terminal sessions[/green]")
        return
    console.print_json(
        data=mgr.list_sessions(status=status, workflow_id=workflow_id, limit=50)
    )


@app.command("cli-run")
def cli_run(
    name: str = typer.Argument(
        ..., help="External CLI name (gemini, grok, …) or cli:name@MODEL"
    ),
    prompt: str = typer.Argument(..., help="Prompt/task for the CLI"),
    approve: bool = typer.Option(
        False, "--approve", help="Approve file-modifying actions this run"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show command only"),
    cli_model: Optional[str] = typer.Option(
        None,
        "--cli-model",
        "-M",
        help="Inner model for the CLI (e.g. gemini-2.5-pro). Also: name@model",
    ),
    with_context: bool = typer.Option(
        True,
        "--context/--no-context",
        help="Inject central Memory Palace context (default: on)",
    ),
    use_memory: bool = typer.Option(
        True,
        "--memory/--no-memory",
        help="Write result back to central Memory Palace (default: on)",
    ),
):
    """Run an external AI CLI with central Memory Palace (inject + write-back)."""
    from core.central_memory import inject_context, write_back
    from core.external_cli import ExternalCLITool

    cfg = Config()
    orig_prompt = prompt
    ctx_id = None
    # Parse name@model / cli:name@model shorthand
    run_name = name
    run_model = cli_model
    if run_name.startswith("cli:"):
        run_name = run_name[4:]
    if "@" in run_name and not run_model:
        run_name, run_model = run_name.split("@", 1)
    elif "/" in run_name and not run_model:
        # gemini/MODEL only when left side is a known CLI (avoid eating paths)
        left, right = run_name.split("/", 1)
        try:
            from core.external_cli import ExternalCLIRegistry

            if ExternalCLIRegistry().get(left):
                run_name, run_model = left, right
        except Exception:
            pass
    if with_context:
        ctx = inject_context(orig_prompt, prompt=orig_prompt, use_memory=True)
        prompt = ctx.get("prompt") or prompt
        ctx_id = ctx.get("context_id")
        if ctx_id:
            console.print(
                f"[dim]Memory Palace context {ctx_id} "
                f"(memories={ctx.get('memory_count', 0)})[/dim]"
            )
    # Permission mode + require_human_approval
    from core.permission_mode import apply_to_cli_tool_kwargs, mode_from_config

    pmode = mode_from_config(cfg)
    kw = apply_to_cli_tool_kwargs(
        pmode,
        dry_run=dry_run,
        auto_approve=(not cfg.require_human_approval) or approve,
    )
    auto = bool(kw.get("auto_approve"))
    dry_eff = bool(kw.get("dry_run"))
    tool = ExternalCLITool(dry_run=dry_eff, auto_approve=auto)
    result = tool.run(
        run_name,
        prompt,
        approve=True if auto else approve,
        cli_model=run_model,
    )
    data = result.to_dict()
    # Always write back into central Memory Palace (unless --no-memory)
    try:
        mem = write_back(
            task=orig_prompt,
            source="cli_run",
            model_or_cli=f"cli:{name}",
            success=result.ok,
            latency=result.duration_sec,
            output=result.stdout or "",
            error=result.error or result.stderr,
            context_id=ctx_id,
            task_type="coding" if result.modifies_files else "general",
            tags=["cli_run", name],
            use_memory=use_memory,
        )
        data["memory_write"] = mem
    except Exception:  # noqa: BLE001
        pass

    # M6: stable public result envelope on cli-run
    try:
        from core.result_contract import apply_contract

        data = apply_contract(
            data,
            mock=bool(cfg.use_mock),
            dry_run=bool(dry_eff),
            members=[f"cli:{run_name}"],
            ok=bool(result.ok),
        )
        data["model_chain"] = data.get("model_chain") or [f"cli:{run_name}"]
        if run_model:
            data["model_chain"] = [f"cli:{run_name}@{run_model}"]
    except Exception:
        pass

    if result.ok:
        console.print(Panel(result.stdout or "(no stdout)", title=f"{name} OK", border_style="green"))
    else:
        console.print(f"[red]Failed:[/red] {result.error or result.stderr}")
        console.print_json(data=data)
        raise typer.Exit(code=1)


@app.command("propose")
def propose(
    action: str = typer.Argument(..., help="edit_file | run_shell | web_search"),
    payload: str = typer.Argument(..., help="JSON object of args"),
    rationale: str = typer.Option("", "--why", help="Rationale"),
):
    """Create a tool proposal requiring approval before execute"""
    import json as _json

    from core.tool_proposals import ToolProposalManager

    args = _json.loads(payload)
    mgr = ToolProposalManager()
    p = mgr.propose(action=action, args=args, rationale=rationale)
    console.print(f"[green]Proposed[/green] id={p.id} action={p.action} status={p.status}")


@app.command("proposal")
def proposal_cmd(
    proposal_id: str = typer.Argument(..., help="Proposal id"),
    action: str = typer.Option(
        "show", "--action", help="show | approve | reject | execute"
    ),
):
    """Manage a tool proposal"""
    from core.tool_proposals import ToolProposalManager

    mgr = ToolProposalManager()
    if action == "show":
        p = mgr._get(proposal_id)
        console.print_json(data=p.to_dict())
        return
    if action == "approve":
        p = mgr.approve(proposal_id)
    elif action == "reject":
        p = mgr.reject(proposal_id)
    elif action == "execute":
        p = mgr.execute(proposal_id)
    else:
        console.print(f"[red]Unknown action {action}[/red]")
        raise typer.Exit(code=1)
    console.print_json(data=p.to_dict())


@app.command("proposals")
def proposals_list(
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status"),
):
    """List tool proposals"""
    from core.tool_proposals import ToolProposalManager

    mgr = ToolProposalManager()
    items = mgr.list(status=status)
    table = Table(title="Tool proposals")
    table.add_column("ID")
    table.add_column("Action")
    table.add_column("Status")
    table.add_column("Rationale")
    for p in items[:50]:
        table.add_row(p.id, p.action, p.status, (p.rationale or "")[:40])
    console.print(table)


@app.command()
def debate(
    topic: str = typer.Argument(..., help="Debate topic"),
    models: Optional[str] = typer.Option(
        None, "--models", help="Comma-separated model names"
    ),
    rounds: int = typer.Option(1, "--rounds", min=1, max=2),
):
    """Run a multi-model debate / critique pattern (I2)"""
    from core.agentic import AgenticWorkflows

    wf = AgenticWorkflows()
    model_list = [m.strip() for m in models.split(",")] if models else None
    result = wf.debate(topic, models=model_list, rounds=rounds)
    for p in result.get("proposals") or []:
        console.print(Panel(str(p.get("text")), title=f"Debater {p.get('model')}", border_style="blue"))
    for c in result.get("critiques") or []:
        console.print(Panel(str(c.get("text")), title=f"Critique {c.get('model')}", border_style="yellow"))


@app.command()
def council(
    topic: str = typer.Argument(..., help="Council topic / question"),
    voting: Optional[str] = typer.Option(
        None,
        "--voting",
        "-v",
        help="majority | supervisor | weighted (default from config)",
    ),
    models: Optional[str] = typer.Option(
        None,
        "--models",
        help="Comma-separated members: gpt-4o,cli:gemini@MODEL,cli:grok (see superai members)",
    ),
    supervisor: Optional[str] = typer.Option(
        None, "--supervisor", help="Supervisor model (for supervisor voting)"
    ),
    critique: bool = typer.Option(False, "--critique", help="Add critique refinement round"),
    document: Optional[List[str]] = typer.Option(
        None, "--document", "-d", help="Path to document to inject (repeatable)"
    ),
    prefer: str = typer.Option(
        "mixed",
        "--prefer",
        help="When --models omitted: mixed | cli | api",
    ),
    pick: bool = typer.Option(
        False, "--pick", help="Interactively pick council members"
    ),
):
    """Multi-model/CLI council with selectable voting (LLM Council inspired)"""
    from core.council import Council, VOTING_MODES

    cfg = Config()
    mode = voting or cfg.council_voting_mode
    if mode not in VOTING_MODES:
        console.print(f"[red]Invalid voting mode. Use one of: {VOTING_MODES}[/red]")
        raise typer.Exit(code=1)
    model_list = [m.strip() for m in models.split(",")] if models else None
    if pick and not model_list:
        from core.approval_tui import prompt_pick_from_catalog

        model_list = prompt_pick_from_catalog(
            title="Pick council members",
            max_n=3,
            prefer=prefer if prefer in {"mixed", "cli", "api"} else "mixed",
        )
    # Default: mixed available API models + external CLIs
    if model_list is None:
        try:
            from core.member_selection import resolve_members

            specs = resolve_members(
                None,
                max_members=3,
                prefer=prefer
                if prefer in {"mixed", "cli", "api"}
                else (
                    "cli"
                    if bool(cfg.get("council_prefer_clis", True))
                    else "mixed"
                ),
                role="advisor",
            )
            # Full selectors (cli:name@MODEL preserved — ModelCaller passes cli_model)
            model_list = [s.id for s in specs] if specs else None
        except Exception:
            model_list = None
    sup = supervisor or cfg.default_supervisor
    c = Council(voting_mode=mode, supervisor_model=sup)
    result = c.run(
        topic,
        models=model_list,
        voting_mode=mode,
        supervisor_model=sup,
        with_critique=critique,
        document_paths=document,
    )
    console.print(
        Panel.fit(
            f"[bold]Council[/bold]\nMode: {result.get('voting_mode')}\n"
            f"Members: {', '.join(result.get('members') or [])}",
            border_style="magenta",
        )
    )
    for p in result.get("proposals") or []:
        console.print(
            f"• {p.get('model')}: key={p.get('vote_key')} "
            f"conf={p.get('confidence')} — {str(p.get('summary'))[:120]}"
        )
    console.print(Panel.fit(str(result.get("decision")), title="Decision", border_style="green"))


@app.command("data-ask")
def data_ask(
    question: str = typer.Argument(..., help="Natural language question about your data"),
    dsn: Optional[str] = typer.Option(
        None, "--dsn", help="SQLAlchemy DSN (default: config data_dsn or demo SQLite)"
    ),
    thread_id: Optional[str] = typer.Option(
        None, "--thread", "-t", help="Conversation thread id for follow-ups"
    ),
    show_sql: bool = typer.Option(True, "--sql/--no-sql", help="Show generated SQL"),
    show_chart: bool = typer.Option(False, "--chart", help="Print chart JSON if any"),
    chart_html: bool = typer.Option(
        False, "--chart-html", help="Write interactive Vega HTML and print path"
    ),
    mock: bool = typer.Option(False, "--mock", help="Force mock/heuristic backend"),
):
    """Ask natural-language questions over SQL data (Databao-inspired)"""
    from core.databao_adapter import DatabaoAdapter
    from core.learning_engine import LearningEngine
    from core.memory_palace import MemoryPalace
    from rich.table import Table as RichTable

    cfg = Config()
    use_mock = mock or cfg.use_mock
    adapter = DatabaoAdapter(
        dsn=dsn or cfg.get("data_dsn"),
        use_databao=bool(cfg.get("use_databao_package", True)) and not mock,
        use_mock=use_mock,
        llm_name=cfg.get("databao_llm") or "gpt-4o-mini",
    )
    th = adapter.thread(thread_id)
    answer = th.ask(question)

    # Learn from analytics interaction
    try:
        LearningEngine(MemoryPalace()).learn_from_task(
            task_description=f"data-ask: {question}",
            task_type="research",
            model_used=f"databao:{answer.backend}",
            success=answer.error is None,
            latency=0.0,
            steps_completed=1 if answer.error is None else 0,
            error_message=answer.error,
        )
    except Exception:  # noqa: BLE001
        pass

    console.print(
        Panel.fit(
            f"[bold]Data answer[/bold]\n"
            f"Backend: {answer.backend} | thread: {answer.thread_id}\n"
            f"{answer.text}",
            border_style="cyan",
        )
    )
    if show_sql and answer.sql:
        console.print(f"[dim]SQL: {answer.sql}[/dim]")
    if answer.columns:
        table = RichTable(title=f"Results ({answer.row_count} rows)")
        for c in answer.columns:
            table.add_column(str(c))
        for row in answer.rows[:30]:
            table.add_row(*[str(x) for x in row])
        console.print(table)
    if show_chart and answer.chart:
        console.print_json(data=answer.chart)
    if chart_html and answer.chart:
        from core.vega_charts import write_chart_html

        path = write_chart_html(answer.chart, title=question[:80])
        console.print(f"[green]Interactive chart:[/green] {path}")
    if answer.error:
        raise typer.Exit(code=1)


@app.command("data-schema")
def data_schema(
    dsn: Optional[str] = typer.Option(None, "--dsn", help="SQLAlchemy DSN"),
):
    """Show registered/demo data schema summary"""
    from core.databao_adapter import DatabaoAdapter

    cfg = Config()
    adapter = DatabaoAdapter(
        dsn=dsn or cfg.get("data_dsn"),
        use_mock=cfg.use_mock,
    )
    console.print(Panel.fit(adapter.schema_summary(), title="Schema", border_style="blue"))
    console.print_json(data=adapter.capabilities())


@app.command("pref")
def pref_cmd(
    action: str = typer.Argument("show", help="show | set | get | delete"),
    key: Optional[str] = typer.Argument(None, help="Preference key"),
    value: Optional[str] = typer.Argument(None, help="Value for set"),
):
    """User preferences / learned profile"""
    from core.preferences import UserPreferenceModel

    pm = UserPreferenceModel()
    if action == "show":
        console.print_json(data=pm.profile_summary())
        return
    if action == "get":
        if not key:
            console.print("[red]key required[/red]")
            raise typer.Exit(1)
        console.print(pm.get(key))
        return
    if action == "set":
        if not key:
            console.print("[red]key required[/red]")
            raise typer.Exit(1)
        parsed: object = value
        if value is not None and value.lower() in {"true", "false"}:
            parsed = value.lower() == "true"
        pm.set(key, parsed)
        console.print(f"[green]Set preference[/green] {key}={parsed}")
        return
    if action == "delete":
        if not key or not pm.delete(key):
            console.print("[yellow]Not found[/yellow]")
            raise typer.Exit(1)
        console.print(f"[green]Deleted[/green] {key}")
        return
    console.print("[red]Unknown action[/red]")
    raise typer.Exit(1)


@app.command("tt-snapshot")
def tt_snapshot(
    path: str = typer.Argument(..., help="File path to snapshot"),
    note: str = typer.Option("", "--note"),
):
    """Snapshot a file for time-travel restore"""
    from core.time_travel import FileTimeTravel

    info = FileTimeTravel().snapshot(path, note=note)
    console.print_json(data=info)


@app.command("tt-list")
def tt_list(path: str = typer.Argument(..., help="File path")):
    """List time-travel versions for a file"""
    from core.time_travel import FileTimeTravel

    versions = FileTimeTravel().list_versions(path)
    if not versions:
        console.print("[yellow]No versions[/yellow]")
        return
    table = Table(title=f"Versions for {path}")
    table.add_column("Ver")
    table.add_column("When")
    table.add_column("Size")
    table.add_column("Note")
    for v in versions:
        table.add_row(
            str(v.get("version")),
            str(v.get("created_at")),
            str(v.get("size")),
            str(v.get("note") or ""),
        )
    console.print(table)


@app.command("tt-restore")
def tt_restore(
    path: str = typer.Argument(..., help="File path"),
    version: int = typer.Argument(..., help="Version number"),
):
    """Restore a file from a time-travel snapshot"""
    from core.time_travel import FileTimeTravel

    try:
        info = FileTimeTravel().restore(path, version)
        console.print(f"[green]Restored[/green] {info}")
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from e


@app.command("msg-send")
def msg_send(
    message: str = typer.Argument(..., help="Message text"),
    channel: str = typer.Option("cli", "--channel", "-c"),
):
    """Send via messenger bus (cli/file/webhook/telegram/slack)"""
    from core.messengers import MessengerBus

    result = MessengerBus().send(message, channel=channel)
    console.print_json(data=result)
    if not result.get("ok"):
        raise typer.Exit(1)


@app.command("msg-channels")
def msg_channels():
    """List messenger channels and configuration status"""
    from core.messengers import MessengerBus

    console.print_json(data=MessengerBus().list_channels())


@app.command("msg-broadcast")
def msg_broadcast(
    message: str = typer.Argument(..., help="Message text"),
    channels: Optional[str] = typer.Option(
        None, "--channels", help="Comma-separated channels (default: all enabled)"
    ),
):
    """Broadcast a message to multiple messenger channels"""
    from core.messengers import MessengerBus

    ch_list = [c.strip() for c in channels.split(",")] if channels else None
    result = MessengerBus().broadcast(message, channels=ch_list)
    console.print_json(data=result)
    if not result.get("ok"):
        raise typer.Exit(1)


@app.command("plugins")
def plugins_cmd(
    action: str = typer.Argument(
        "list", help="list | search | enable | disable | install | load | summary"
    ),
    arg: Optional[str] = typer.Argument(
        None, help="plugin id / query / path depending on action"
    ),
    category: Optional[str] = typer.Option(None, "--category", "-c"),
):
    """Plugin marketplace registry (list/search/enable/install)"""
    from core.plugin_registry import PluginRegistry

    reg = PluginRegistry()
    if action == "list":
        console.print_json(data=reg.list_plugins(category=category))
        return
    if action == "summary":
        console.print_json(data=reg.marketplace_summary())
        return
    if action == "search":
        console.print_json(data=reg.search(arg or ""))
        return
    if action == "enable":
        if not arg:
            console.print("[red]Need plugin id[/red]")
            raise typer.Exit(1)
        console.print_json(data=reg.enable(arg))
        return
    if action == "disable":
        if not arg:
            console.print("[red]Need plugin id[/red]")
            raise typer.Exit(1)
        console.print_json(data=reg.disable(arg))
        return
    if action == "install":
        if not arg:
            console.print("[red]Need path to plugin.json or directory[/red]")
            raise typer.Exit(1)
        from pathlib import Path as P

        console.print_json(data=reg.install_from_path(P(arg)))
        return
    if action == "load":
        if not arg:
            console.print("[red]Need plugin id[/red]")
            raise typer.Exit(1)
        console.print_json(data=reg.load_plugin(arg))
        return
    console.print(f"[red]Unknown action: {action}[/red]")
    raise typer.Exit(1)


@app.command("bandit")
def bandit_cmd(
    action: str = typer.Argument("status", help="status | reset"),
):
    """Show or reset contextual bandit routing state"""
    from core.bandit_router import EpsilonGreedyBandit

    b = EpsilonGreedyBandit()
    if action == "reset":
        b.state = {}
        b.save()
        console.print("[green]Bandit state cleared[/green]")
        return
    console.print_json(
        data={
            "epsilon": b.epsilon,
            "arms": b.state,
            "path": str(b.path),
        }
    )


@app.command("dashboard")
def dashboard_cmd(
    once: bool = typer.Option(False, "--once", help="Print one snapshot and exit"),
    refresh: float = typer.Option(3.0, "--refresh", help="Refresh interval seconds"),
):
    """Live terminal dashboard (shared snapshot with web UI)"""
    from scli.dashboard import SuperAIDashboard

    SuperAIDashboard().run_terminal_dashboard(refresh_sec=refresh, once=once)


@app.command("context-pack")
def context_pack_cmd(
    task: str = typer.Argument(..., help="Task / goal for the context pack"),
    save: bool = typer.Option(True, "--save/--no-save"),
    show_prompt: bool = typer.Option(False, "--prompt", help="Print prompt text form"),
):
    """Build MCP-style context pack for external CLI handoff"""
    from core.mcp_context import MCPContextPack

    mcp = MCPContextPack()
    pack = mcp.build(task=task)
    path = None
    if save:
        path = mcp.save(pack)
    console.print_json(data=pack)
    if path:
        console.print(f"[green]Saved[/green] {path}")
    if show_prompt:
        console.print(Panel(mcp.format_for_prompt(pack), title="Prompt form"))


@app.command("search-web")
def search_web_cmd(
    query: str = typer.Argument(..., help="Search query"),
    provider: str = typer.Option(
        "auto",
        "--provider",
        help="auto|tavily|brave|duckduckgo|stub",
    ),
):
    """Web search: Tavily/Brave keys, DuckDuckGo Instant Answer (no scrape), or stub"""
    from core.ecosystem import EcosystemHub

    console.print_json(data=EcosystemHub().search(query, provider=provider))


@app.command("github")
def github_cmd(
    action: str = typer.Argument(
        "status",
        help="status | issues | prs | issue-create | pr | comment",
    ),
    repo: Optional[str] = typer.Option(
        None, "--repo", "-R", help="owner/name (or SUPERAI_GITHUB_REPO)"
    ),
    state: str = typer.Option("open", "--state"),
    limit: int = typer.Option(20, "--limit", "-n"),
    number: Optional[int] = typer.Option(None, "--number", "-N"),
    title: Optional[str] = typer.Option(None, "--title"),
    body: Optional[str] = typer.Option(None, "--body"),
    labels: Optional[str] = typer.Option(None, "--labels", help="comma labels"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Do not call API even if token present"
    ),
):
    """GitHub issues/PRs (G15) — GITHUB_TOKEN or gh CLI; dry-run without either"""
    from core.github_api import GitHubClient

    client = GitHubClient(repo=repo, dry_run=dry_run)
    if action == "status":
        console.print_json(data=client.status())
        return
    if action == "issues":
        console.print_json(data=client.list_issues(state=state, limit=limit))
        return
    if action == "prs":
        console.print_json(data=client.list_prs(state=state, limit=limit))
        return
    if action == "issue-create":
        if not title:
            console.print("[red]--title required[/red]")
            raise typer.Exit(1)
        lbs = [x.strip() for x in (labels or "").split(",") if x.strip()] or None
        console.print_json(
            data=client.create_issue(title, body=body or "", labels=lbs)
        )
        return
    if action == "pr":
        if number is None:
            console.print("[red]--number required[/red]")
            raise typer.Exit(1)
        console.print_json(data=client.get_pr(number))
        return
    if action == "comment":
        if number is None or not body:
            console.print("[red]--number and --body required[/red]")
            raise typer.Exit(1)
        console.print_json(data=client.comment_on_issue(number, body))
        return
    console.print("[red]action: status|issues|prs|issue-create|pr|comment[/red]")
    raise typer.Exit(1)


@app.command("emit-event")
def emit_event_cmd(
    event: str = typer.Argument(..., help="Event name for n8n/Zapier/Make"),
    payload: Optional[str] = typer.Option(
        None, "--payload", help="JSON payload string"
    ),
):
    """Emit ecosystem webhook event (n8n / Zapier / Make)"""
    from core.ecosystem import EcosystemHub

    body = {}
    if payload:
        try:
            body = json.loads(payload)
        except json.JSONDecodeError:
            body = {"text": payload}
    result = EcosystemHub().emit_event(event, body)
    console.print_json(data=result)
    if not result.get("ok"):
        raise typer.Exit(1)


@app.command("ecosystem")
def ecosystem_cmd():
    """Show ecosystem integration capabilities"""
    from core.ecosystem import EcosystemHub

    console.print_json(data=EcosystemHub().capabilities())


@app.command("surface-feedback")
def surface_feedback_cmd(
    message: str = typer.Argument(..., help="Feedback visible on all surfaces"),
    surface: str = typer.Option("cli", "--surface"),
):
    """Post cross-surface feedback (CLI ↔ web dashboard)"""
    from core.observability import write_feedback, recent_feedback

    entry = write_feedback(message, surface=surface)
    console.print_json(data={"written": entry, "recent": recent_feedback(5)})


@app.command("compare")
def compare_cmd(
    prompt: str = typer.Argument(..., help="Prompt to run on multiple models"),
    models: Optional[str] = typer.Option(
        None, "--models", help="Comma-separated model names"
    ),
    mock: bool = typer.Option(True, "--mock/--live", help="Mock vs live APIs"),
    top: int = typer.Option(4, "--top", help="How many routed models if --models omitted"),
):
    """Compare models on the same prompt (winner by success+latency)"""
    from core.model_compare import compare_models

    model_list = [m.strip() for m in models.split(",")] if models else None
    data = compare_models(prompt, models=model_list, use_mock=mock, top_n=top)
    console.print_json(data=data)


@app.command("benchmark")
def benchmark_cmd(
    mock: bool = typer.Option(True, "--mock/--live"),
    models: Optional[str] = typer.Option(None, "--models"),
    report: Optional[str] = typer.Option(
        None, "--report", "-o", help="Write Markdown report path (N8)"
    ),
):
    """Run a small multi-prompt benchmark suite across models"""
    from core.model_compare import benchmark_models, benchmark_report_markdown

    model_list = [m.strip() for m in models.split(",")] if models else None
    data = benchmark_models(models=model_list, use_mock=mock)
    if report:
        from pathlib import Path as P

        md = benchmark_report_markdown(data)
        P(report).write_text(md, encoding="utf-8")
        console.print(f"[green]Wrote report[/green] {report}")
    console.print_json(data=data)


@app.command("pin-model")
def pin_model_cmd(
    name: str = typer.Argument(..., help="Logical model name"),
    model_id: Optional[str] = typer.Option(None, "--model-id"),
    provider: Optional[str] = typer.Option(None, "--provider"),
    note: str = typer.Option("", "--note"),
    unpin: bool = typer.Option(False, "--unpin"),
    list_all: bool = typer.Option(False, "--list"),
):
    """Pin/unpin concrete model_id for a registry name"""
    from core.model_pinning import ModelPinStore

    store = ModelPinStore()
    if list_all:
        console.print_json(data=store.list_pins())
        return
    if unpin:
        ok = store.unpin(name)
        console.print("[green]Unpinned[/green]" if ok else "[yellow]Not pinned[/yellow]")
        return
    console.print_json(data=store.pin(name, model_id=model_id, provider=provider, note=note))


@app.command("blacklist")
def blacklist_cmd(
    action: str = typer.Argument("list", help="list | block | unblock"),
    name: Optional[str] = typer.Argument(None, help="Model name"),
    reason: str = typer.Option("", "--reason"),
    hours: Optional[float] = typer.Option(None, "--hours"),
):
    """Model blacklist management (auto-threshold after repeated failures)"""
    from core.model_blacklist import ModelBlacklist

    bl = ModelBlacklist()
    if action == "list":
        console.print_json(data=bl.list_blocked())
        return
    if action == "block":
        if not name:
            raise typer.Exit(1)
        bl.block_model(name, reason=reason, hours=hours)
        console.print(f"[green]Blocked[/green] {name}")
        return
    if action == "unblock":
        if not name:
            raise typer.Exit(1)
        bl.unblock_model(name)
        console.print(f"[green]Unblocked[/green] {name}")
        return
    console.print(f"[red]Unknown action {action}[/red]")
    raise typer.Exit(1)


@app.command("memory-chat")
def memory_chat_cmd(
    query: str = typer.Argument(..., help="Memory question"),
    conversation: Optional[str] = typer.Option(
        None, "--conversation", "-c", help="Continue conversation id"
    ),
    new: bool = typer.Option(False, "--new", help="Force new conversation"),
):
    """Multi-turn conversational memory search"""
    from core.memory_chat import MemoryConversation

    mc = MemoryConversation()
    if new or not conversation:
        cid = mc.start()
    else:
        cid = conversation
    result = mc.ask(cid, query)
    console.print_json(data=result)


@app.command("notion")
def notion_cmd(
    action: str = typer.Argument("status", help="status | write | search"),
    title_or_query: Optional[str] = typer.Argument(None),
    content: Optional[str] = typer.Argument(None),
):
    """Notion integration (dry-run without NOTION_API_KEY)"""
    from core.notion_stub import NotionClient

    client = NotionClient()
    if action == "status":
        console.print_json(data=client.capabilities())
        return
    if action == "write":
        if not title_or_query:
            raise typer.Exit(1)
        console.print_json(
            data=client.write_page(title_or_query, content or "")
        )
        return
    if action == "search":
        console.print_json(data=client.search(title_or_query or ""))
        return
    raise typer.Exit(1)


@app.command("hitl")
def hitl_cmd(
    action: str = typer.Argument(
        "list", help="list | clarify | answer | veto"
    ),
    task_id: Optional[str] = typer.Argument(None),
    text: Optional[str] = typer.Argument(None, help="Question / answer / reason"),
):
    """Human-in-the-loop: clarification requests and veto"""
    from core.hitl import HITLStore

    store = HITLStore()
    if action == "list":
        console.print_json(data=store.list_all())
        return
    if action == "clarify":
        if not task_id or not text:
            console.print("[red]Need task_id and question[/red]")
            raise typer.Exit(1)
        console.print_json(data=store.request_clarification(task_id, text))
        return
    if action == "answer":
        if not task_id or not text:
            console.print("[red]Need clarification id and answer[/red]")
            raise typer.Exit(1)
        r = store.answer_clarification(task_id, text)
        if not r:
            raise typer.Exit(1)
        console.print_json(data=r)
        if (r.get("kind") or "") == "replan_approval":
            console.print(
                f"[dim]Replan decision={r.get('decision')}. "
                f"Resume: superai run \"…\" --resume {r.get('task_id')}[/dim]"
            )
        return
    if action == "veto":
        if not task_id:
            raise typer.Exit(1)
        console.print_json(data=store.veto(task_id, reason=text or ""))
        return
    raise typer.Exit(1)


@app.command("runs")
def runs_cmd(
    action: str = typer.Argument("list", help="list | show | clear | resume"),
    task_id: Optional[str] = typer.Argument(None),
):
    """List step-cache / resume run checkpoints"""
    from core.step_cache import StepResultCache

    cache = StepResultCache()
    if action == "list":
        console.print_json(data=cache.list_runs())
        return
    if action == "show" and task_id:
        console.print_json(data=cache.get_run(task_id) or {})
        return
    if action == "clear" and task_id:
        console.print_json(data={"cleared": cache.clear_run(task_id)})
        return
    if action == "resume" and task_id:
        orch = SuperAIOrchestrator()
        ck = cache.get_run(task_id) or {}
        result = orch.run_task(
            task=ck.get("task") or "resumed task",
            resume_task_id=task_id,
            verbose=True,
        )
        console.print_json(data=result)
        return
    console.print_json(data={"entries": len(cache._data.get("entries") or {})})


@app.command("patterns")
def patterns_cmd(
    apply: bool = typer.Option(False, "--apply", help="Create skills from patterns"),
    min_support: int = typer.Option(2, "--min-support"),
):
    """Extract generalized patterns from learning history"""
    from core.pattern_extract import PatternExtractor

    pe = PatternExtractor()
    data = pe.extract(min_support=min_support)
    if apply:
        created = pe.apply_to_skills(min_support=max(3, min_support))
        data["skills_created"] = created
    console.print_json(data=data)


@app.command("memory-clusters")
def memory_clusters_cmd(
    limit: int = typer.Option(200, "--limit"),
    method: str = typer.Option(
        "auto",
        "--method",
        "-m",
        help="auto | embedding | wing | tag",
    ),
    max_clusters: int = typer.Option(8, "--max", help="Max clusters"),
):
    """Cluster memories (embedding k-means / wing-room / tags)"""
    from core.memory_palace import MemoryPalace

    console.print_json(
        data=MemoryPalace().cluster_memories(
            limit=limit, max_clusters=max_clusters, method=method
        )
    )


@app.command("memory-palace")
def memory_palace_cmd(
    action: str = typer.Argument(
        "layout",
        help="layout | browse | search | suggest | promote | snapshot",
    ),
    wing: Optional[str] = typer.Option(None, "--wing", "-w"),
    room: Optional[str] = typer.Option(None, "--room", "-r"),
    query: Optional[str] = typer.Option(None, "--query", "-q"),
    limit: int = typer.Option(20, "--limit", "-n"),
    apply: bool = typer.Option(
        False, "--apply", help="promote: write rooms into wings catalog"
    ),
    reassign: bool = typer.Option(
        False, "--reassign", help="promote: also re-tag memory metadata"
    ),
    min_size: int = typer.Option(3, "--min-size", help="Min cluster size to promote"),
    method: str = typer.Option("auto", "--method", help="Cluster method"),
):
    """Browse Memory Palace by wings/rooms; suggest/promote rooms from clusters"""
    from core.memory_palace import MemoryPalace
    from rich.table import Table

    mp = MemoryPalace()
    if action == "layout":
        console.print_json(data=mp.palace_layout())
        return
    if action == "snapshot":
        console.print_json(data=mp.browser_snapshot(wing=wing, room=room, limit=limit))
        return
    if action == "browse":
        items = mp.query_by_location(wing=wing, room=room, limit=limit)
        table = Table(title=f"Palace browse wing={wing or '*'} room={room or '*'}")
        table.add_column("id", max_width=14)
        table.add_column("wing")
        table.add_column("room")
        table.add_column("content", max_width=50)
        for m in items:
            meta = m.get("metadata") or {}
            table.add_row(
                str(m.get("id") or "")[:14],
                str(m.get("wing") or meta.get("wing") or ""),
                str(m.get("room") or meta.get("room") or ""),
                (m.get("content") or "")[:50].replace("\n", " "),
            )
        console.print(table)
        console.print(f"[dim]{len(items)} item(s) · also: superai memory-palace snapshot[/dim]")
        return
    if action == "search":
        if not query:
            console.print("[red]Provide --query[/red]")
            raise typer.Exit(1)
        hits = mp.query_semantic(
            query, top_k=limit, wing=wing, room=room
        )
        console.print_json(data={"query": query, "wing": wing, "room": room, "hits": hits})
        return
    if action == "suggest":
        console.print_json(
            data=mp.suggest_rooms_from_clusters(
                limit=max(limit, 50), min_size=min_size, method=method
            )
        )
        return
    if action == "promote":
        report = mp.auto_promote_rooms(
            apply=apply,
            reassign=reassign,
            limit=max(limit, 100),
            min_size=min_size,
            method=method,
        )
        console.print_json(data=report)
        if not apply:
            console.print(
                "[dim]Dry-run. Apply: superai memory-palace promote --apply "
                "[--reassign][/dim]"
            )
        return
    console.print(
        "[red]action: layout | browse | search | suggest | promote | snapshot[/red]"
    )
    raise typer.Exit(1)


@app.command("roles")
def roles_cmd(
    task: str = typer.Argument(..., help="Task for dynamic role cycle"),
):
    """Run supervisor→workers→critic dynamic role switching"""
    from core.agentic import AgenticWorkflows

    console.print_json(data=AgenticWorkflows().dynamic_roles(task))


@app.command()
def doctor(
    quick: bool = typer.Option(False, "--quick", help="Skip smoke calls"),
):
    """M1/M7: Health pack — env, config, smoke, next steps"""
    from core.doctor import run_doctor

    report = run_doctor(quick=quick)
    for c in report.get("checks") or []:
        mark = "[green]OK[/green]" if c.get("ok") else "[red]FAIL[/red]"
        console.print(f"{mark} {c.get('name')}: {c.get('detail')}")
    console.print(Panel.fit(
        "\n".join(f"• {s}" for s in (report.get("next_steps") or [])),
        title="Next steps",
        border_style="cyan",
    ))
    if not report.get("ok"):
        raise typer.Exit(1)


@app.command("ask")
def ask_cmd(
    text: Optional[str] = typer.Argument(
        None,
        help='Natural language (omit for interactive agent REPL like Claude Code / Gemini)',
    ),
    plan_only: bool = typer.Option(
        False,
        "--plan-only",
        "--preview",
        help="N202: only parse intent and show planned SuperAI command (no execute)",
    ),
    execute: bool = typer.Option(
        True,
        "--execute/--no-execute",
        help="Execute the mapped command (default: yes unless --plan-only)",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    json_out: bool = typer.Option(True, "--json/--text", help="JSON result (default)"),
    repl: bool = typer.Option(
        False,
        "--repl",
        help="Force interactive natural-language REPL",
    ),
    session: Optional[str] = typer.Option(
        None, "--session", "-s", help="Continue ask session id"
    ),
    new_session: bool = typer.Option(False, "--new-session", help="Start new ask session"),
    permission: Optional[str] = typer.Option(
        None, "--permission", help="plan | ask | auto | yolo"
    ),
    profile: Optional[str] = typer.Option(
        None, "--profile", help="cheap | balanced | quality | local-only"
    ),
    image: Optional[List[str]] = typer.Option(
        None,
        "--image",
        "-i",
        help="Attach image path(s) for multimodal context (repeatable)",
    ),
):
    """Universal NL front door — any request (specialized routes or agentic run)."""
    from core.nl_intent import ask_superai, interactive_repl, parse_intent

    if profile:
        from core.config import Config
        from core.run_profiles import apply_profile_to_config

        apply_profile_to_config(Config(), profile)
    if permission:
        from core.config import Config
        from core.permission_mode import normalize_mode

        Config().config["permission_mode"] = normalize_mode(permission)

    if repl or not (text or "").strip():
        console.print(
            Panel.fit(
                "[bold]SuperAI agent[/bold] — natural language for everything\n"
                "Specialized: review · advise · council · doctor · memory · plan · tdd · …\n"
                "Anything else → orchestrated agent task (Claude Code style)",
                border_style="cyan",
            )
        )
        interactive_repl(execute=execute and not plan_only, verbose=verbose)
        return

    # Multi-turn session context
    ask_sid = session
    preface = ""
    if new_session or ask_sid:
        from core.ask_session import AskSessionStore

        store = AskSessionStore()
        if new_session or not ask_sid:
            ask_sid = store.create()
            console.print(f"[dim]ask_session={ask_sid}[/dim]")
        preface = store.context_preface(ask_sid)
    text_eff = f"{preface}\n\n{text}" if preface else text
    if image:
        from core.multimodal import prompt_with_images

        mm = prompt_with_images(text_eff or "", list(image))
        text_eff = mm.get("prompt") or text_eff
        console.print(
            f"[dim]attachments={len(mm.get('attachment_meta') or [])}[/dim]"
        )

    intent = parse_intent(text)
    agent_note = ""
    if intent.action == "run" and (
        "universal_agent" in intent.notes or "agent_default" in intent.notes
    ):
        agent_note = "  [agent]"
    console.print(
        Panel.fit(
            f"[bold]Intent:[/bold] {intent.action}{agent_note}  "
            f"(conf={intent.confidence:.2f})\n"
            f"[bold]Planned:[/bold] {intent.planned_command}",
            border_style="cyan",
        )
    )
    out = ask_superai(
        text_eff,
        execute=execute and not plan_only,
        plan_only=plan_only,
        verbose=verbose,
    )
    # Cost report footer
    if out.get("executed"):
        console.print(
            f"[dim]cost≈${float(out.get('estimated_cost_usd') or 0):.6f}  "
            f"tokens={out.get('tokens') or 0}  "
            f"mock={out.get('mock')} dry_run={out.get('dry_run')}  "
            f"models={','.join(out.get('model_chain') or [])[:80]}[/dim]"
        )
    if ask_sid and out.get("executed"):
        try:
            from core.ask_session import AskSessionStore

            summary = str(
                (out.get("result") or {}).get("message")
                or (out.get("result") or {}).get("status")
                or out.get("planned_command")
                or ""
            )[:500]
            AskSessionStore().append_turn(
                ask_sid, text or "", summary, meta={"action": intent.action}
            )
            out["ask_session"] = ask_sid
        except Exception:
            pass
    if json_out:
        console.print_json(data=out)
    else:
        if out.get("error"):
            console.print(f"[red]{out['error']}[/red]")
        elif out.get("result") is not None:
            console.print(str(out.get("result"))[:4000])
    if not out.get("ok"):
        raise typer.Exit(code=1)


@app.command()
def chat(
    message: Optional[str] = typer.Argument(None, help="Message (omit for new session id only)"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Continue chat id"),
    new: bool = typer.Option(False, "--new", help="Start new session"),
    list_chats: bool = typer.Option(False, "--list", help="List recent chats"),
    no_intent: bool = typer.Option(
        False,
        "--no-intent",
        help="Skip natural-language command routing (chat only)",
    ),
):
    """S2: Multi-turn chat; high-confidence product intents route via ask"""
    from core.chat_session import ChatSession

    cs = ChatSession()
    if list_chats:
        console.print_json(data=cs.list_chats())
        return
    sid = session
    if new or not sid:
        sid = cs.start()
        console.print(f"[dim]chat_id={sid}[/dim]")
    if not message:
        console.print("Send a message: superai chat \"hello\" -s " + sid)
        return

    # Route NL through universal ask (product intents + agentic run)
    if not no_intent:
        try:
            from core.nl_intent import parse_intent, ask_superai

            intent = parse_intent(message)
            # Pure chitchat stays in chat; everything product/agent goes to ask
            chitchat = re.search(
                r"^(hi|hello|hey|thanks|thank you|good (morning|evening))\b",
                message.strip(),
                flags=re.I,
            )
            if not chitchat:
                console.print(
                    f"[dim]→ intent {intent.action}: {intent.planned_command}[/dim]"
                )
                out = ask_superai(message, execute=True, verbose=False)
                console.print_json(data=out)
                return
        except Exception:
            pass

    out = cs.ask(sid, message)
    console.print(Panel(out.get("reply") or "", title=f"Assistant ({out.get('model')})", border_style="green"))
    console.print(f"[dim]session={sid} turns={out.get('turns')}[/dim]")


@app.command()
def budget(
    action: str = typer.Argument("show", help="show | set"),
    daily: Optional[float] = typer.Option(None, "--daily", help="Daily USD limit"),
    per_run: Optional[float] = typer.Option(None, "--run", help="Per-run USD limit"),
    tokens: Optional[int] = typer.Option(None, "--tokens", help="Daily token limit"),
):
    """S4: Cost/token budget guards"""
    from core.budget import BudgetGuard

    g = BudgetGuard()
    if action == "set":
        console.print_json(data=g.configure(daily_usd=daily, run_usd=per_run, daily_tokens=tokens))
        return
    console.print_json(data=g.snapshot())


@app.command()
def audit(
    limit: int = typer.Option(30, "--limit", "-n"),
):
    """S8: Show recent audit log entries"""
    from core.audit_log import AuditLog

    console.print_json(data=AuditLog().recent(limit=limit))


@app.command("backup-key")
def backup_key_cmd(
    action: str = typer.Argument(..., help="export | import"),
    path: str = typer.Argument(..., help="Destination or source key file path"),
):
    """S9: Export/import encryption key for backup recovery"""
    from core.backup_manager import BackupManager
    from core.audit_log import AuditLog

    bm = BackupManager()
    if action == "export":
        dest = bm.export_key(path)
        AuditLog().record("backup_key_export", {"dest": str(dest)})
        console.print(f"[green]Exported key to[/green] {dest}")
        return
    if action == "import":
        dest = bm.import_key(path)
        AuditLog().record("backup_key_import", {"src": path})
        console.print(f"[green]Imported key to[/green] {dest}")
        return
    raise typer.Exit(1)


@app.command()
def policy(
    action: str = typer.Argument("list", help="list | enable | disable"),
    rule_id: Optional[str] = typer.Argument(None),
):
    """N4: Policy engine rules"""
    from core.policy import PolicyEngine

    pe = PolicyEngine()
    if action == "list":
        console.print_json(data=pe.list_rules())
        return
    if action in {"enable", "disable"} and rule_id:
        ok = pe.set_enabled(rule_id, action == "enable")
        if not ok:
            raise typer.Exit(1)
        console.print_json(data=pe.list_rules())
        return
    raise typer.Exit(1)


@app.command()
def schedule(
    action: str = typer.Argument("list", help="list | add | run-due"),
    name: Optional[str] = typer.Argument(None),
    command: Optional[str] = typer.Argument(None, help="backup | doctor | run:<task>"),
    every_hours: float = typer.Option(24.0, "--every-hours"),
):
    """N10: Local scheduled jobs (run via schedule run-due or external cron)"""
    from core.schedule_store import ScheduleStore

    store = ScheduleStore()
    if action == "list":
        console.print_json(data=store.list_jobs())
        return
    if action == "add":
        if not name or not command:
            console.print("[red]Need name and command[/red]")
            raise typer.Exit(1)
        console.print_json(data=store.add(name, command, every_hours=every_hours))
        return
    if action == "run-due":
        console.print_json(data=store.run_due())
        return
    raise typer.Exit(1)


@app.command("mcp-serve")
def mcp_serve(
    transport: str = typer.Option(
        "stdio",
        "--transport",
        "-t",
        help="stdio (default, for Claude/Cursor) | note: HTTP is via superai web /mcp",
    ),
):
    """
    SuperAI local MCP server — other AIs/CLIs connect here to use central Memory Palace
    and SuperAI-mediated tools (memory search/store, cli-run, orchestrate).

    Claude Desktop / Cursor: superai mcp-config
    Then point their MCP settings at `superai mcp-serve`.
    """
    if transport not in {"stdio", "http"}:
        console.print("[red]transport must be stdio (or use superai web for HTTP /mcp)[/red]")
        raise typer.Exit(1)
    if transport == "http":
        console.print(
            "[yellow]HTTP MCP is served by:[/yellow] superai web  →  POST /mcp\n"
            "For stdio clients (Claude, Cursor), use default: superai mcp-serve"
        )
        raise typer.Exit(0)
    from core.mcp_server import serve_stdio

    serve_stdio()


@app.command("mcp-config")
def mcp_config_cmd(
    write: bool = typer.Option(
        False, "--write", help=f"Write to ~/.superai/mcp_client_config.json"
    ),
    cwd: Optional[str] = typer.Option(
        None, "--cwd", help="Working directory for the MCP server process"
    ),
    transport: str = typer.Option("stdio", "--transport", help="stdio | http"),
):
    """Print / write MCP client config so Claude, Cursor, etc. can use SuperAI memory."""
    from core.mcp_server import client_config_snippet, write_client_config, list_tools

    if write:
        path = write_client_config(cwd=cwd)
        console.print(f"[green]Wrote[/green] {path}")
    data = client_config_snippet(cwd=cwd, transport=transport)
    console.print_json(data=data)
    console.print(
        f"[dim]Tools ({len(list_tools())}): "
        f"{', '.join(t['name'] for t in list_tools())}[/dim]"
    )
    console.print(
        "[dim]Merge mcpServers.superai into Claude Desktop / Cursor MCP settings.[/dim]"
    )


@app.command()
def constitution(
    action: str = typer.Argument("show", help="show | init | path"),
):
    """N14: Show or initialize constitution/rules file"""
    from core.constitution import (
        ensure_default_constitution,
        load_constitution,
        constitution_paths,
    )

    if action == "init":
        p = ensure_default_constitution()
        console.print(f"[green]Wrote[/green] {p}")
        return
    if action == "path":
        console.print_json(data=[str(p) for p in constitution_paths()])
        return
    console.print(load_constitution())


@app.command()
def profile(
    action: str = typer.Argument("show", help="show | set"),
    name: Optional[str] = typer.Argument(None),
):
    """N3: Active profile name (config key)"""
    cfg = Config()
    if action == "set" and name:
        cfg.set("profile", name)
        console.print(f"[green]profile={name}[/green]")
        return
    console.print_json(data={"profile": cfg.get("profile"), "config": str(cfg.config_path)})


@app.command("failover")
def failover_cmd(
    action: str = typer.Argument("show", help="show | set"),
    chain: Optional[str] = typer.Option(
        None, "--chain", help="Comma-separated model names"
    ),
):
    """S5: Provider/model failover chain preference"""
    cfg = Config()
    if action == "set":
        models = [c.strip() for c in (chain or "").split(",") if c.strip()]
        cfg.set("failover_chain", models)
        console.print_json(data={"failover_chain": models})
        return
    console.print_json(data={"failover_chain": cfg.get("failover_chain") or []})


@app.command()
def metrics():
    """N11: Export simple metrics snapshot as JSON"""
    from core.budget import BudgetGuard
    from core.history import TaskHistory
    from core.observability import build_dashboard_snapshot

    snap = build_dashboard_snapshot()
    console.print_json(
        data={
            "history_count": TaskHistory().count(),
            "budget": BudgetGuard().snapshot(),
            "bandit_arms": snap.get("bandit_arms"),
            "memory": snap.get("memory"),
            "ts": snap.get("ts"),
        }
    )


@app.command()
def evals(
    offline: bool = typer.Option(True, "--offline/--live"),
):
    """S12: Offline regression eval harness (golden tasks)"""
    from core.orchestrator import SuperAIOrchestrator
    from core.task_planner import TaskPlanner
    from core.config import Config

    cfg = Config()
    if offline:
        cfg.set("mock_mode", True, persist=False)
    orch = SuperAIOrchestrator(config=cfg)
    planner = TaskPlanner(orch.model_router, model_caller=orch.model_caller)
    cases = [
        "build a FastAPI hello world",
        "research and compare databases",
        "fix a flaky test",
    ]
    results = []
    for task in cases:
        plan = planner.create_plan(task, use_llm=False)
        run = orch.run_task(task, verbose=False)
        results.append(
            {
                "task": task,
                "plan_steps": len(plan),
                "has_parallel": any(s.can_run_parallel for s in plan),
                "run_status": run.get("status"),
                "success": run.get("success"),
            }
        )
    passed = sum(1 for r in results if r.get("plan_steps", 0) >= 1)
    console.print_json(data={"passed": passed, "total": len(cases), "results": results})


@app.command("git-helper")
def git_helper(
    action: str = typer.Argument(..., help="status | branch-hint | commit-msg"),
    task: Optional[str] = typer.Option(None, "--task"),
):
    """N9: Gated git helpers (read-only except explicit branch-hint text)"""
    import subprocess
    from core.workspace import workspace_root
    from core.audit_log import AuditLog

    cwd = str(workspace_root())
    if action == "status":
        r = subprocess.run(
            ["git", "status", "-sb"],
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=False,
        )
        console.print(r.stdout or r.stderr)
        AuditLog().record("git_status", {"cwd": cwd})
        return
    if action == "branch-hint":
        name = (task or "feature-work")[:40].lower().replace(" ", "-")
        console.print(f"Suggested: git checkout -b superai/{name}")
        return
    if action == "commit-msg":
        console.print(
            f"Suggested message:\n\nfeat: {task or 'superai task'}\n\nGenerated by SuperAI (review before commit)."
        )
        return
    raise typer.Exit(1)


@app.command("msg-inbound")
def msg_inbound(
    channel: str = typer.Argument(..., help="telegram | slack | file"),
    text: str = typer.Argument(..., help="Inbound message text"),
):
    """N6: Inbound messenger stub — parse simple commands"""
    from core.messengers import MessengerBus
    from core.audit_log import AuditLog

    low = text.strip().lower()
    reply = "unknown command. try: /status /doctor /help"
    if low in {"/help", "help"}:
        reply = "Commands: /status /doctor /help"
    elif low in {"/status", "status"}:
        from core.history import TaskHistory

        reply = f"history={TaskHistory().count()} mock={Config().use_mock}"
    elif low in {"/doctor", "doctor"}:
        from core.doctor import run_doctor

        reply = f"doctor_ok={run_doctor(quick=True).get('ok')}"
    bus = MessengerBus()
    # Log inbound then reply on same channel if possible
    bus.send(f"[inbound:{channel}] {text}", channel="file")
    out = bus.send(reply, channel=channel if channel in bus.list_channels() else "file")
    AuditLog().record("msg_inbound", {"channel": channel, "text": text[:200]})
    console.print_json(data={"reply": reply, "send": out})


@app.command("ticket")
def ticket_cmd(
    action: str = typer.Argument("status", help="status | create"),
    title: Optional[str] = typer.Argument(None),
    body: Optional[str] = typer.Option(None, "--body"),
):
    """N12: Ticket sync stub (Linear/Jira) — local log until API keys"""
    from pathlib import Path
    import time
    import json as _json

    path = Path.home() / ".superai" / "tickets.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    if action == "create" and title:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "title": title,
            "body": body or "",
            "provider": "local-stub",
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(_json.dumps(entry) + "\n")
        console.print_json(data={"ok": True, "entry": entry})
        return
    if path.exists():
        lines = path.read_text(encoding="utf-8").strip().splitlines()[-10:]
        console.print_json(data=[__import__("json").loads(x) for x in lines if x])
    else:
        console.print_json(data=[])


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8787, "--port"),
):
    """Start web memory/status UI (requires pip install -e \".[web]\")"""
    import os

    try:
        import uvicorn
        from scli.web_app import create_app
    except ImportError as e:
        console.print(
            "[red]Web extras missing.[/red] Install: pip install -e \".[web]\""
        )
        raise typer.Exit(1) from e
    # Refuse non-loopback bind without auth token
    loopback = host in {"127.0.0.1", "localhost", "::1"}
    if not loopback and not (os.getenv("SUPERAI_WEB_TOKEN") or "").strip():
        console.print(
            "[red]Refusing to bind non-loopback without SUPERAI_WEB_TOKEN.[/red]\n"
            "Set SUPERAI_WEB_TOKEN or use --host 127.0.0.1"
        )
        raise typer.Exit(1)
    if (os.getenv("SUPERAI_WEB_TOKEN") or "").strip():
        console.print("[dim]API auth enabled (SUPERAI_WEB_TOKEN)[/dim]")
    console.print(f"[green]Starting SuperAI web on http://{host}:{port}[/green]")
    uvicorn.run(create_app(), host=host, port=port, log_level="info")


@app.command("delegate")
def delegate(
    goal: str = typer.Argument(..., help="High-level goal to decompose and run"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Hierarchical delegation of a goal into subtasks"""
    from core.hierarchy import HierarchicalDelegator

    tree = HierarchicalDelegator().run(goal, verbose=verbose)
    console.print_json(data=_json_safe(tree))


def _json_safe(obj):
    """Best-effort JSON-serializable copy for nested results."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


@app.command()
def wings(
    action: str = typer.Argument(
        "list",
        help="list | stats | browse | assign | rooms | sync",
    ),
    memory_id: Optional[str] = typer.Option(None, "--memory-id"),
    wing: Optional[str] = typer.Option(None, "--wing", "-w"),
    room: Optional[str] = typer.Option(None, "--room", "-r"),
    note: str = typer.Option("", "--note"),
    limit: int = typer.Option(40, "--limit", "-n"),
    list_all: bool = typer.Option(False, "--list", help="Alias for list"),
):
    """Memory wings & rooms organization (I4) — palace navigation"""
    from core.wings import WingsManager
    from core.memory_palace import MemoryPalace

    wm = WingsManager()
    act = "list" if list_all else action
    if act == "list":
        console.print_json(data=wm.list_wings())
        return
    if act == "stats":
        console.print_json(data={"wings": wm.stats(), "palace": MemoryPalace().palace_layout()})
        return
    if act == "rooms":
        if not wing:
            console.print("[red]--wing required[/red]")
            raise typer.Exit(1)
        console.print_json(data={"wing": wing, "rooms": wm.list_rooms(wing)})
        return
    if act == "browse":
        console.print_json(data=wm.browse(wing=wing, room=room, limit=limit))
        return
    if act == "sync":
        n = wm.sync_assignments_from_memories(MemoryPalace().get_all_memories())
        console.print(f"[green]Synced {n} assignments from memory metadata[/green]")
        return
    if act == "assign":
        if not (memory_id and wing and room):
            console.print("[red]Need --memory-id --wing --room[/red]")
            raise typer.Exit(1)
        entry = wm.assign(memory_id, wing, room, note=note)
        # Mirror onto memory metadata when possible
        try:
            MemoryPalace().update_metadata(
                memory_id, {"wing": wing, "room": room}
            )
        except Exception:
            pass
        console.print(f"[green]Assigned[/green] {entry}")
        return
    console.print("[red]action: list | stats | browse | assign | rooms | sync[/red]")
    raise typer.Exit(1)


@app.command("list-models")
def list_models(
    refresh: bool = typer.Option(
        False,
        "--refresh",
        help="Refresh catalog (project + SUPERAI_MODELS_URL) into ~/.superai/config/models.json",
    ),
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter provider"),
    open_weight: bool = typer.Option(False, "--open-weight", help="Open-weight family only"),
    local_only: bool = typer.Option(False, "--local", help="Local endpoints only"),
):
    """List models known to the registry"""
    from core.model_registry import ModelRegistry

    if refresh:
        from core.model_refresh import refresh_models

        try:
            models, meta = refresh_models(write_user_copy=True)
            console.print(
                f"[green]Refreshed {meta.get('count')} models[/green] "
                f"from {meta.get('sources')}"
            )
            if meta.get("errors"):
                console.print(f"[yellow]Warnings: {meta['errors']}[/yellow]")
            if meta.get("written_to"):
                console.print(f"[dim]Wrote {meta['written_to']}[/dim]")
        except Exception as e:  # noqa: BLE001
            console.print(f"[red]Refresh failed:[/red] {e}")
            raise typer.Exit(code=1) from e

    registry = ModelRegistry()
    if refresh:
        registry.refresh()

    table = Table(title=f"Registered models (source: {registry.source})")
    table.add_column("Name")
    table.add_column("Provider")
    table.add_column("Model ID")
    table.add_column("OW")
    table.add_column("Local")
    table.add_column("Latest")
    local_provs = {"ollama", "ollama_openai", "lmstudio", "vllm"}
    for name in registry.list_all_models():
        m = registry.get_model(name)
        if not m:
            continue
        if provider and str(m.provider).lower() != provider.lower():
            continue
        extra = m.extra or {}
        is_local = bool(
            extra.get("local")
            or m.provider in local_provs
            or (m.base_url or "").startswith("http://localhost")
            or (m.base_url or "").startswith("http://127.0.0.1")
        )
        is_ow = bool(extra.get("open_weight") or is_local or m.provider in {
            "deepseek", "qwen", "moonshot", "zhipu", "minimax", "nvidia",
            "openrouter", "fireworks", "siliconflow", "groq", "together", "mistral",
        })
        if open_weight and not is_ow:
            continue
        if local_only and not is_local:
            continue
        table.add_row(
            m.name,
            m.provider,
            m.model_id,
            "y" if is_ow else "",
            "y" if is_local else "",
            "yes" if m.is_latest else "",
        )
    console.print(table)


@app.command("providers")
def providers_cmd(
    only_ready: bool = typer.Option(
        False, "--ready", help="Only providers with keys / local"
    ),
):
    """List LLM providers (cloud, local open-weight, gateways, CLIs)."""
    from core.model_discovery import provider_status

    data = provider_status()
    rows = data.get("providers") or []
    if only_ready:
        rows = [r for r in rows if r.get("key_configured")]
    table = Table(title="SuperAI providers")
    table.add_column("ID")
    table.add_column("Label")
    table.add_column("Kind")
    table.add_column("Protocol")
    table.add_column("Key env")
    table.add_column("Ready")
    table.add_column("Circuit")
    for r in rows:
        table.add_row(
            str(r.get("id")),
            str(r.get("label") or ""),
            str(r.get("kind") or ""),
            str(r.get("protocol") or ""),
            str(r.get("api_key_env") or "—"),
            "yes" if r.get("key_configured") else "",
            "OPEN" if r.get("circuit_open") else "",
        )
    console.print(table)
    # Registry validation warnings
    try:
        from core.registry_validate import validate_registry

        val = validate_registry()
        if val.get("issue_count"):
            console.print(
                f"[yellow]Registry issues: {val['issue_count']}/{val['total']} "
                f"(sample {val['issues'][:3]})[/yellow]"
            )
    except Exception:
        pass
    console.print_json(data={"counts": data.get("counts")})


@app.command("profile")
def profile_cmd(
    name: Optional[str] = typer.Argument(
        None, help="cheap | balanced | quality | local-only (omit to list)"
    ),
    persist: bool = typer.Option(
        False, "--persist", help="Write profile defaults into config.json"
    ),
):
    """Apply or list cost/quality run profiles."""
    from core.config import Config
    from core.run_profiles import apply_profile_to_config, list_profiles

    if not name:
        console.print_json(data=list_profiles())
        return
    cfg = Config()
    applied = apply_profile_to_config(cfg, name)
    if persist:
        for k, v in applied.items():
            cfg.set(k, v, persist=True)
    console.print_json(data={"ok": True, "applied": applied, "persisted": persist})


@app.command("models-sync-ollama")
def models_sync_ollama_cmd(
    dry_run: bool = typer.Option(False, "--dry-run", help="Discover only, do not write"),
    native: bool = typer.Option(
        False,
        "--native",
        help="Use native Ollama generate API provider instead of OpenAI /v1",
    ),
):
    """Import local Ollama tags into ~/.superai/config/models.json."""
    from core.model_discovery import sync_ollama_to_user_registry

    meta = sync_ollama_to_user_registry(
        write=not dry_run, use_openai_compat=not native
    )
    console.print_json(data=meta)
    if not meta.get("ok") and not dry_run:
        raise typer.Exit(code=1)


@app.command("models-register")
def models_register_cmd(
    name: str = typer.Option(..., "--name", help="SuperAI registry name"),
    model_id: str = typer.Option(..., "--model-id", help="Upstream model id"),
    base_url: str = typer.Option(
        ..., "--base-url", help="OpenAI-compatible base URL ending in /v1"
    ),
    provider: str = typer.Option(
        "custom",
        "--provider",
        help="Provider id (openrouter, lmstudio, vllm, nvidia, custom, …)",
    ),
    api_key_env: Optional[str] = typer.Option(
        None, "--api-key-env", help="Env var for API key (optional for local)"
    ),
    strengths: str = typer.Option(
        "User-registered OpenAI-compatible model", "--strengths"
    ),
):
    """Register any OpenAI-compatible endpoint (any vendor / open-weight server)."""
    from core.model_discovery import register_openai_compatible_model

    out = register_openai_compatible_model(
        name,
        model_id,
        provider=provider,
        base_url=base_url,
        api_key_env=api_key_env,
        strengths=strengths,
        write=True,
    )
    console.print_json(data=out)
    console.print(
        f"[green]Registered[/green] {name}. Use: superai run \"…\" -m {name}"
    )


@app.command("smoke-providers")
def smoke_providers(
    mock: bool = typer.Option(
        False, "--mock", help="Force mock mode (always runs without keys)"
    ),
):
    """Live multi-provider smoke test (skips providers without credentials)"""
    from core.provider_smoke import run_provider_smoke

    summary = run_provider_smoke(use_mock=mock)
    console.print(
        Panel.fit(
            f"[bold]Provider Smoke[/bold]\n\n{summary.get('message')}\n"
            f"Available targets: {summary.get('targets_available')}",
            border_style="cyan",
        )
    )
    table = Table(title="Results")
    table.add_column("Provider")
    table.add_column("Model")
    table.add_column("Status")
    table.add_column("Latency")
    table.add_column("Detail")
    for r in summary.get("results") or []:
        detail = r.get("error") or r.get("response_preview") or ""
        table.add_row(
            str(r.get("provider")),
            str(r.get("model")),
            str(r.get("status")),
            str(r.get("latency", "")),
            str(detail)[:50],
        )
    console.print(table)
    if not summary.get("ok") and summary.get("failed", 0) > 0:
        raise typer.Exit(code=1)


@app.command("provider-health")
def provider_health_cmd():
    """Show persisted provider health and quota windows"""
    from core.provider_health import ProviderHealthStore

    store = ProviderHealthStore()
    snap = store.snapshot()
    if not snap:
        console.print("[yellow]No provider health data yet. Run tasks or smoke-providers.[/yellow]")
        return
    table = Table(title="Provider Health")
    table.add_column("Provider")
    table.add_column("Health")
    table.add_column("Success rate")
    table.add_column("Calls")
    table.add_column("Can call")
    table.add_column("Circuit")
    table.add_column("Quota throttled")
    for name, p in sorted(snap.items()):
        q = p.get("quota") or {}
        table.add_row(
            name,
            str(p.get("health")),
            str(p.get("success_rate")),
            str(p.get("calls")),
            str(p.get("can_call")),
            str(p.get("circuit_open")),
            str(q.get("throttled")),
        )
    console.print(table)


@app.command()
def evolve(
    topic: str = typer.Argument(..., help="Topic to track knowledge evolution for"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max timeline entries"),
):
    """Show how learnings about a topic evolved over time (F3.5)"""
    from core.learning_engine import LearningEngine
    from core.memory_palace import MemoryPalace

    engine = LearningEngine(MemoryPalace())
    result = engine.track_knowledge_evolution(topic, limit=limit)
    console.print(
        Panel.fit(
            f"[bold]Knowledge Evolution[/bold]\n\n"
            f"Topic: {result.get('topic')}\n"
            f"Detected: {result.get('evolution_detected')}\n"
            f"Memories: {result.get('total_memories')}\n"
            f"{result.get('message')}",
            border_style="magenta",
        )
    )
    timeline = result.get("timeline") or []
    if timeline:
        table = Table(title="Timeline")
        table.add_column("When")
        table.add_column("Model")
        table.add_column("OK")
        table.add_column("Insight")
        for row in timeline:
            table.add_row(
                str(row.get("timestamp") or "")[:19],
                str(row.get("model") or ""),
                str(row.get("success")),
                str(row.get("key_insight") or "")[:70],
            )
        console.print(table)


@app.command()
def feedback(
    task_id: str = typer.Argument(..., help="Task id from superai history"),
    text: str = typer.Argument(..., help="Human feedback text"),
    success: Optional[bool] = typer.Option(
        None, "--success/--failure", help="Mark outcome if known"
    ),
):
    """Record human feedback for a past task (high-importance learning)"""
    from core.history import TaskHistory
    from core.learning_engine import LearningEngine
    from core.memory_palace import MemoryPalace

    rec = TaskHistory().get(task_id)
    desc = (rec or {}).get("task") or f"task {task_id}"
    model = (rec or {}).get("model_used") or "unknown"
    task_type = ((rec or {}).get("metadata") or {}).get("task_type") or "general"
    if success is None and rec is not None:
        success = bool(rec.get("success"))

    engine = LearningEngine(MemoryPalace())
    mid = engine.record_human_feedback(
        task_id=task_id,
        feedback=text,
        success=success,
        task_description=desc,
        task_type=task_type,
        model_used=str(model),
    )
    # S20: feed thumbs into bandit + preferences
    try:
        from core.bandit_router import EpsilonGreedyBandit

        reward = 0.9 if success else 0.1
        if success is None:
            reward = 0.5
        EpsilonGreedyBandit().update(str(model), reward)
    except Exception:  # noqa: BLE001
        pass
    try:
        from core.preferences import UserPreferenceModel

        UserPreferenceModel().observe_task(
            task_type=str(task_type),
            model=str(model),
            success=bool(success) if success is not None else False,
            duration=float((rec or {}).get("duration") or 1.0),
        )
    except Exception:  # noqa: BLE001
        pass
    console.print(f"[green]Feedback stored[/green] memory_id={mid} task_id={task_id}")


@app.command("set-supervisor")
def set_supervisor(model: str = typer.Argument(..., help="Default supervisor model name")):
    """Persist default supervisor model"""
    cfg = Config()
    cfg.set("default_supervisor", model, persist=True)
    console.print(f"[green]Default supervisor set to:[/green] {model}")


@app.command("set-strategy")
def set_strategy(strategy: str = typer.Argument(..., help="Load balancing strategy")):
    """Persist strategy: smart_fallback | round_robin | latency_based | cost_based"""
    from core.load_balancer import parse_strategy

    parsed = parse_strategy(strategy)
    cfg = Config()
    cfg.set("load_balancing_strategy", parsed.value, persist=True)
    console.print(f"[green]Strategy set to:[/green] {parsed.value}")


@app.command("routing-stats")
def routing_stats(
    limit: int = typer.Option(50, "--limit", "-n", help="History window"),
    explain: Optional[str] = typer.Option(
        None, "--explain", help="Show scoring breakdown for a sample task"
    ),
):
    """Show model routing statistics from history; use --explain for score breakdown"""
    from core.load_balancer import LoadBalancer, parse_strategy
    from core.model_registry import ModelRegistry
    from core.model_router import ModelRouter
    from core.routing_stats import summarize_routing

    cfg = Config()
    summary = summarize_routing(limit=limit)
    console.print(
        Panel.fit(
            f"[bold]Routing Stats[/bold]\n\n"
            f"Strategy: {cfg.get('load_balancing_strategy')}\n"
            f"Runs sampled: {summary.get('total_runs_sampled')}\n"
            f"Models seen: {summary.get('total_models_seen')}\n"
            f"{summary.get('message')}",
            border_style="cyan",
        )
    )

    top = summary.get("top_models") or []
    if top:
        table = Table(title="Top models by success rate")
        table.add_column("Model")
        table.add_column("Success rate")
        table.add_column("Runs")
        table.add_column("Avg duration")
        for row in top:
            table.add_row(
                str(row["model"]),
                str(row["success_rate"]),
                str(row["total"]),
                str(row["avg_duration"]),
            )
        console.print(table)

    if explain:
        registry = ModelRegistry()
        lb = LoadBalancer(strategy=parse_strategy(cfg.get("load_balancing_strategy")))
        router = ModelRouter(registry, lb)
        router.refresh_history_stats()
        ranked = router.explain_selection(explain, top_k=8)
        table = Table(title=f"Score breakdown for: {explain[:50]}")
        table.add_column("Model")
        table.add_column("Provider")
        table.add_column("Score")
        table.add_column("Task match")
        table.add_column("History")
        table.add_column("Cost")
        table.add_column("Latency")
        table.add_column("Health")
        for row in ranked:
            c = row["components"]
            table.add_row(
                row["model"],
                row["provider"],
                str(row["score"]),
                str(c.get("task_type_match")),
                str(c.get("historical_success_rate")),
                str(c.get("cost_efficiency")),
                str(c.get("latency_score")),
                str(c.get("provider_health")),
            )
        console.print(table)


if __name__ == "__main__":
    app()


@app.command()
def secrets(
    action: str = typer.Argument("list", help="list | set | get | delete | inject"),
    name: Optional[str] = typer.Argument(None),
    value: Optional[str] = typer.Argument(None),
):
    """M10: Secure secret store (keyring or locked file)"""
    from core.keyring_store import SecretStore

    store = SecretStore()
    if action == "list":
        console.print_json(data=store.list_names())
        return
    if action == "set" and name and value:
        console.print_json(data=store.set(name, value))
        return
    if action == "get" and name:
        v = store.get(name)
        console.print("(set)" if v else "(missing)")
        return
    if action == "delete" and name:
        console.print_json(data={"deleted": store.delete(name)})
        return
    if action == "inject":
        n = store.inject_env()
        console.print(f"[green]Injected {n} secrets into env[/green]")
        return
    raise typer.Exit(1)


@app.command()
def update():
    """M11: Check for SuperAI updates"""
    from core.version_check import check_update

    console.print_json(data=check_update())


@app.command()
def diagnose(
    output: Optional[str] = typer.Option(None, "--output", "-o"),
):
    """M12: Build redacted diagnostics zip"""
    from core.diagnostics import build_diagnostics_bundle
    from pathlib import Path as P

    path = build_diagnostics_bundle(P(output) if output else None)
    console.print(f"[green]Diagnostics bundle:[/green] {path}")


@app.command("rate-queue")
def rate_queue_cmd(
    action: str = typer.Argument("list", help="list | clear"),
    item_id: Optional[str] = typer.Argument(None),
):
    """M13: Rate-limit queue status"""
    from core.rate_queue import RateLimitQueue

    q = RateLimitQueue()
    if action == "list":
        console.print_json(data=q.list_items())
        return
    if action == "clear" and item_id:
        console.print_json(data={"removed": q.remove(item_id)})
        return
    if action == "clear":
        q.data["items"] = []
        q.save()
        console.print("[green]Queue cleared[/green]")
        return
    raise typer.Exit(1)


@app.command("diff-edit")
def diff_edit_cmd(
    path: str = typer.Argument(..., help="File path under workspace"),
    content: str = typer.Argument(..., help="New file content"),
    yes: bool = typer.Option(False, "--yes", help="Skip approval prompt"),
):
    """S13: Diff-first file edit with approval"""
    from core.diff_edit import apply_edit_with_diff

    console.print_json(data=apply_edit_with_diff(path, content, auto_approve=yes, show=True))


@app.command()
def tdd(
    task: str = typer.Argument(..., help="Coding task"),
    rounds: int = typer.Option(2, "--rounds"),
):
    """S14: Test-driven loop — run task then tests, retry on failure"""
    from core.tdd_loop import tdd_cycle

    console.print_json(data=tdd_cycle(task, max_rounds=rounds))


@app.command("workspace-index")
def workspace_index_cmd(
    query: Optional[str] = typer.Option(None, "--query", "-q"),
):
    """S19: Build or search workspace code map"""
    from core.workspace_index import build_index, search_index

    idx = build_index()
    if query:
        console.print_json(data=search_index(query, idx))
        return
    console.print_json(
        data={"root": idx["root"], "file_count": idx["file_count"], "symbols": len(idx.get("symbols") or [])}
    )


@app.command("profile-bundle")
def profile_bundle_cmd(
    action: str = typer.Argument(..., help="export | import"),
    path: str = typer.Argument(..., help="Zip path"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """S21: Export/import profile bundle (config, skills, constitution)"""
    from core.profile_bundle import export_profile, import_profile
    from pathlib import Path as P

    if action == "export":
        console.print(f"[green]{export_profile(P(path))}[/green]")
        return
    if action == "import":
        console.print_json(data=import_profile(P(path), dry_run=dry_run))
        return
    raise typer.Exit(1)


@app.command()
def onboard(
    non_interactive: bool = typer.Option(
        True,
        "--non-interactive/--interactive",
        help="Interactive prompts for host tools + optional Postgres (default: non-interactive)",
    ),
    with_postgres: bool = typer.Option(
        False,
        "--with-postgres",
        help="Configure Postgres Memory Palace (opt-in)",
    ),
    live: bool = typer.Option(
        False,
        "--live",
        help="Allow live package/DB installs (default dry-run)",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Assume yes for recommended opts + live installs",
    ),
    host_tools_profile: str = typer.Option(
        "core",
        "--host-tools-profile",
        help="core | agentic | cloud | full",
    ),
):
    """N28: First-run onboarding (use --interactive for guided install)"""
    from core.onboarding import run_onboarding

    console.print_json(
        data=run_onboarding(
            non_interactive=non_interactive,
            with_postgres=with_postgres or None,
            live=live,
            yes=yes,
            host_tools_profile=host_tools_profile,
        )
    )


@app.command("install")
def install_cmd(
    interactive: bool = typer.Option(
        True,
        "--interactive/--non-interactive",
        help="Prompt for host tools profile and optional Postgres (default: interactive on TTY)",
    ),
    with_postgres: Optional[bool] = typer.Option(
        None,
        "--with-postgres/--no-postgres",
        help="Opt-in Postgres Memory Palace setup (prompt if omitted in interactive mode)",
    ),
    host_tools_profile: Optional[str] = typer.Option(
        None,
        "--host-tools-profile",
        help="core | agentic | cloud | full (prompt if interactive)",
    ),
    install_host_tools: Optional[bool] = typer.Option(
        None,
        "--install-host-tools/--skip-host-tools",
        help="Install missing host tools from chosen profile",
    ),
    live: bool = typer.Option(
        False,
        "--live",
        help="Perform live installs (default is dry-run / plan only)",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Non-interactive consent: live installs for requested components",
    ),
    skip_postgres: bool = typer.Option(False, "--skip-postgres", help="Skip Postgres entirely"),
    admin_password: Optional[str] = typer.Option(
        None,
        "--pg-admin-password",
        help="Postgres admin password (or set SUPERAI_PG_ADMIN_PASSWORD / PGPASSWORD)",
        envvar="SUPERAI_PG_ADMIN_PASSWORD",
    ),
):
    """
    Guided SuperAI installation: host tools (opt-in) + optional Postgres/pgvector.

    Examples:
      superai install
      superai install --with-postgres --live --yes
      superai install --host-tools-profile agentic --install-host-tools --live
      superai install --non-interactive --skip-postgres
    """
    from core.install_wizard import run_install_wizard

    data = run_install_wizard(
        interactive=interactive if not yes else False,
        with_postgres=False if skip_postgres else with_postgres,
        host_tools_profile=host_tools_profile,
        install_host_tools=install_host_tools,
        live=live,
        yes=yes,
        admin_password=admin_password,
        skip_host_tools=install_host_tools is False,
        skip_postgres=skip_postgres,
    )
    console.print_json(data=data)
    if not data.get("ok"):
        raise typer.Exit(1)


@app.command("install-postgres")
def install_postgres_cmd(
    setup_only: bool = typer.Option(
        False,
        "--setup-only",
        help="Do not install server; only create DB/extension/DSN if psql exists",
    ),
    live: bool = typer.Option(False, "--live", help="Apply changes (default dry-run)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Same as --live for this command"),
    admin_password: Optional[str] = typer.Option(
        None,
        "--pg-admin-password",
        envvar="SUPERAI_PG_ADMIN_PASSWORD",
    ),
    host: str = typer.Option("localhost", "--host"),
    port: int = typer.Option(5432, "--port"),
):
    """Opt-in Postgres detect/install + Memory Palace DB/vector/DSN setup."""
    from core.postgres_setup import detect_postgres, ensure_postgres_for_superai

    if not live and not yes:
        det = detect_postgres()
        plan = ensure_postgres_for_superai(
            live=False,
            install_if_missing=not setup_only,
            admin_password=admin_password,
            host=host,
            port=port,
        )
        console.print_json(data={"detect": det, "plan": plan})
        console.print(
            "[dim]Re-run with --live (and admin password if needed) to apply.[/dim]"
        )
        return

    data = ensure_postgres_for_superai(
        live=True,
        install_if_missing=not setup_only,
        admin_password=admin_password,
        host=host,
        port=port,
    )
    if isinstance(data.get("setup"), dict):
        data["setup"].pop("db_password", None)
    console.print_json(data=data)
    if not data.get("ok"):
        raise typer.Exit(1)


@app.command()
def compliance(
    action: str = typer.Argument("status", help="status | enable"),
):
    """N22: Compliance mode (local-only, strict approval)"""
    from core.compliance import compliance_status, enable_compliance_mode

    if action == "enable":
        console.print_json(data=enable_compliance_mode())
        return
    console.print_json(data=compliance_status())


@app.command()
def forecast(
    task: str = typer.Argument(..., help="Task to estimate"),
):
    """N20: Pre-run cost forecast"""
    from core.cost_forecast import forecast_task_cost

    console.print_json(data=forecast_task_cost(task))


@app.command("ab-route")
def ab_route_cmd(
    action: str = typer.Argument("stats", help="create | stats | pick"),
    name: Optional[str] = typer.Option(None, "--name"),
    model_a: Optional[str] = typer.Option(None, "--a"),
    model_b: Optional[str] = typer.Option(None, "--b"),
    pct: float = typer.Option(10.0, "--pct"),
    task_type: str = typer.Option("coding", "--type"),
):
    """N21: A/B routing experiments"""
    from core.ab_routing import ABRouter

    ab = ABRouter()
    if action == "create" and name and model_a and model_b:
        console.print_json(data=ab.create(name, model_a, model_b, traffic_b_pct=pct, task_type=task_type))
        return
    if action == "pick":
        console.print_json(data={"model": ab.pick(task_type)})
        return
    console.print_json(data=ab.stats())


@app.command("memory-forget")
def memory_forget_cmd(
    query: str = typer.Argument(..., help="Query or phrase to forget"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """N27: Forget memories matching query (GDPR-style)"""
    from core.memory_gdpr import forget_query

    console.print_json(data=forget_query(query, dry_run=dry_run))


@app.command("memory-ttl")
def memory_ttl_cmd(
    days: float = typer.Option(90.0, "--days"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """N27: Apply TTL decay/delete to old low-importance memories"""
    from core.memory_gdpr import apply_ttl

    console.print_json(data=apply_ttl(max_age_days=days, dry_run=dry_run))


@app.command("memory-sync")
def memory_sync_cmd(
    action: str = typer.Argument(..., help="export | import"),
    path: str = typer.Argument(...),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True),
    merge: str = typer.Option(
        "skip",
        "--merge",
        help="import merge: skip | overwrite | always",
    ),
    queue: bool = typer.Option(
        False,
        "--queue",
        help="import via write queue (safer under concurrent multi-CLI)",
    ),
):
    """N19: Encrypted memory sync (concurrent-safe export/import + merge)"""
    from core.memory_sync import export_encrypted_memory, import_encrypted_memory
    from pathlib import Path as P

    if action == "export":
        console.print(f"[green]{export_encrypted_memory(password, P(path))}[/green]")
        return
    if action == "import":
        console.print_json(
            data=import_encrypted_memory(
                password, P(path), merge=merge, use_queue=queue
            )
        )
        return
    raise typer.Exit(1)


@app.command()
def browse(
    url: str = typer.Argument(..., help="https URL"),
):
    """N17: Fetch page text (Playwright if installed)"""
    from core.browser_tool import fetch_page_text

    console.print_json(data=fetch_page_text(url))


@app.command()
def speak(
    text: str = typer.Argument(..., help="Text to speak"),
):
    """N18: Text-to-speech"""
    from core.voice_io import speak as _speak

    console.print_json(data=_speak(text))


@app.command()
def listen():
    """N18: Speech-to-text (optional deps)"""
    from core.voice_io import listen_once

    console.print_json(data=listen_once())


@app.command("langgraph-export")
def langgraph_export_cmd(
    task: str = typer.Argument(...),
    output: Optional[str] = typer.Option(None, "--output", "-o"),
):
    """N16: Export plan as LangGraph-style JSON"""
    from core.langgraph_export import plan_to_langgraph

    data = plan_to_langgraph(task)
    if output:
        from pathlib import Path as P

        P(output).write_text(json.dumps(data, indent=2), encoding="utf-8")
        console.print(f"[green]Wrote[/green] {output}")
    console.print_json(data=data)


@app.command("pr-review")
def pr_review_cmd(
    ref: str = typer.Option("HEAD~1", "--ref", help="git diff base"),
    mock: bool = typer.Option(True, "--mock/--live"),
    use_clis: bool = typer.Option(
        True,
        "--use-clis/--no-clis",
        help="Use available external AI CLIs as reviewers (default on)",
    ),
    clis: Optional[str] = typer.Option(
        None, "--clis", help="Comma-separated CLIs e.g. grok,gemini,claude"
    ),
    pr: Optional[int] = typer.Option(
        None, "--pr", help="Also fetch GitHub PR metadata by number"
    ),
    repo: Optional[str] = typer.Option(None, "--repo", "-R"),
):
    """N26: Multi-CLI + council review of local git diff (+ optional GitHub PR)"""
    from core.pr_review import review_local

    cli_list = [c.strip() for c in clis.split(",")] if clis else None
    out = review_local(
        ref=ref,
        use_mock=mock,
        use_clis=use_clis,
        clis=cli_list,
        dry_run=mock,
    )
    if pr is not None:
        from core.github_api import GitHubClient

        out["github_pr"] = GitHubClient(repo=repo).get_pr(pr)
    console.print_json(data=out)


@app.command("members")
def members_cmd(
    only_available: bool = typer.Option(
        False,
        "--available",
        help="Only show configured API models + CLIs on PATH",
    ),
    with_models: bool = typer.Option(
        True,
        "--with-models/--no-models",
        help="Include detected/curated inner models for each CLI",
    ),
    live: bool = typer.Option(
        False,
        "--live-probe",
        help="Try live CLI help/list commands (slow; results cached)",
    ),
    open_weight: Optional[bool] = typer.Option(
        None,
        "--open-weight/--no-open-weight",
        help="Filter open-weight family models (None=all)",
    ),
    local_only: bool = typer.Option(
        False, "--local", help="Only local models (Ollama/LM Studio/vLLM)"
    ),
    provider: Optional[str] = typer.Option(
        None, "--provider", help="Filter by provider id (nvidia, deepseek, …)"
    ),
    ollama_live: bool = typer.Option(
        False,
        "--ollama-live",
        help="Soft-include running Ollama tags (no write)",
    ),
    pick: bool = typer.Option(
        False,
        "--pick",
        help="Interactive multi-select; print chosen ids",
    ),
    max_pick: int = typer.Option(5, "--max", help="Max picks with --pick"),
):
    """List selectable API models, CLIs, and CLI inner models for workers/boards."""
    from core.member_selection import list_selectable_members

    data = list_selectable_members(
        only_available=only_available,
        with_cli_models=with_models,
        live_cli_models=live,
        open_weight=open_weight,
        local_only=local_only,
        provider=provider,
        include_ollama_live=ollama_live,
    )
    if pick:
        from core.approval_tui import prompt_pick_from_catalog

        chosen = prompt_pick_from_catalog(
            title="Select members",
            max_n=max_pick,
            only_available=only_available or True,
            open_weight=open_weight,
            local_only=local_only,
            provider=provider,
        )
        console.print_json(data={"ok": True, "selected": chosen})
        return
    console.print_json(data=data)


@app.command("review")
def multi_review_cmd(
    subject: str = typer.Argument(..., help="What to review"),
    members: Optional[str] = typer.Option(
        None,
        "--members",
        "-m",
        help="Mixed members: gpt-4o,cli:gemini@MODEL,cli:grok (default: auto mixed)",
    ),
    clis: Optional[str] = typer.Option(
        None, "--clis", help="CLI-only list (legacy); prefer --members"
    ),
    prefer: str = typer.Option(
        "mixed",
        "--prefer",
        help="Auto-pick preference when members omitted: mixed | cli | api",
    ),
    pick: bool = typer.Option(
        False, "--pick", help="Interactively pick API/CLI members"
    ),
    max_clis: int = typer.Option(3, "--max", help="Max members on the board"),
    dry_run: bool = typer.Option(True, "--dry-run/--live"),
    approve: bool = typer.Option(True, "--approve/--no-approve"),
):
    """Multi-member review board (API models + CLIs; structured verdict)."""
    from core.multi_cli_advisory import multi_cli_board

    member_list = [c.strip() for c in members.split(",")] if members else None
    if pick and not member_list:
        from core.approval_tui import prompt_pick_from_catalog

        member_list = prompt_pick_from_catalog(
            title="Pick review board members",
            max_n=max_clis,
            prefer=prefer,
        )
    cli_list = [c.strip() for c in clis.split(",")] if clis else None
    out = multi_cli_board(
        subject,
        mode="review",
        members=member_list,
        clis=cli_list,
        max_clis=max_clis,
        dry_run=dry_run,
        approve=approve,
        prefer=prefer,
    )
    board = out.get("board") or {}
    console.print(
        Panel.fit(
            f"[bold]Multi-member review[/bold]\n"
            f"Members: {', '.join(out.get('members') or [])}\n"
            f"Verdict: {board.get('verdict')}  conf={board.get('confidence')}\n"
            f"Tally: {board.get('tally')}",
            border_style="yellow",
        )
    )
    console.print_json(data=out)


@app.command("advise")
def multi_advise_cmd(
    subject: str = typer.Argument(..., help="Question / decision for advisors"),
    members: Optional[str] = typer.Option(
        None,
        "--members",
        "-m",
        help="Mixed members: gpt-4o,cli:gemini@MODEL,cli:grok (default: auto mixed)",
    ),
    clis: Optional[str] = typer.Option(
        None, "--clis", help="CLI-only list (legacy); prefer --members"
    ),
    prefer: str = typer.Option(
        "mixed",
        "--prefer",
        help="Auto-pick preference when members omitted: mixed | cli | api",
    ),
    pick: bool = typer.Option(
        False, "--pick", help="Interactively pick API/CLI advisors"
    ),
    max_clis: int = typer.Option(3, "--max", help="Max advisors"),
    dry_run: bool = typer.Option(True, "--dry-run/--live"),
    approve: bool = typer.Option(True, "--approve/--no-approve"),
):
    """Multi-member advisor board (API models + CLIs)."""
    from core.multi_cli_advisory import multi_cli_board

    member_list = [c.strip() for c in members.split(",")] if members else None
    if pick and not member_list:
        from core.approval_tui import prompt_pick_from_catalog

        member_list = prompt_pick_from_catalog(
            title="Pick advisor board members",
            max_n=max_clis,
            prefer=prefer,
        )
    cli_list = [c.strip() for c in clis.split(",")] if clis else None
    out = multi_cli_board(
        subject,
        mode="advise",
        members=member_list,
        clis=cli_list,
        max_clis=max_clis,
        dry_run=dry_run,
        approve=approve,
        prefer=prefer,
    )
    board = out.get("board") or {}
    console.print(
        Panel.fit(
            f"[bold]Multi-member advisors[/bold]\n"
            f"Members: {', '.join(out.get('members') or [])}\n"
            f"Board: {board.get('verdict')}  conf={board.get('confidence')}",
            border_style="cyan",
        )
    )
    console.print_json(data=out)


@app.command("notebook")
def notebook_cmd(
    action: str = typer.Argument(..., help="list | run"),
    path: str = typer.Argument(...),
    index: int = typer.Option(0, "--index", "-i"),
):
    """N25: List or run Jupyter notebook cells"""
    from core.notebook_runner import list_cells, run_notebook_cell

    if action == "list":
        console.print_json(data=list_cells(path))
        return
    if action == "run":
        console.print_json(data=run_notebook_cell(path, index=index))
        return
    raise typer.Exit(1)


@app.command("skill-perms")
def skill_perms_cmd(
    action: str = typer.Argument("list", help="list | set"),
    skill: Optional[str] = typer.Argument(None),
    tools: Optional[str] = typer.Option(None, "--tools", help="comma tools or *"),
):
    """N24: Fine-grained tool permissions per skill"""
    from core.skill_permissions import SkillPermissions

    sp = SkillPermissions()
    if action == "list":
        console.print_json(data=sp.list_all())
        return
    if action == "set" and skill and tools is not None:
        sp.set_tools(skill, [t.strip() for t in tools.split(",") if t.strip()])
        console.print_json(data=sp.list_all())
        return
    raise typer.Exit(1)


@app.command("plugin-catalog")
def plugin_catalog_cmd(
    url: Optional[str] = typer.Argument(
        None, help="Remote catalog JSON URL (omit for bundled marketplace)"
    ),
    install_id: Optional[str] = typer.Option(None, "--install", help="Install entry id (needs url)"),
    query: str = typer.Option("", "--query", "-q", help="Search plugins"),
    category: str = typer.Option("", "--category", "-c", help="Filter by category"),
    tag: str = typer.Option("", "--tag", "-t", help="Filter by tag"),
    sort: str = typer.Option(
        "name", "--sort", help="Sort: name|id|category|version|installed"
    ),
    limit: int = typer.Option(50, "--limit", "-n", help="Max results"),
    show_id: Optional[str] = typer.Option(None, "--show", help="Show one plugin by id"),
    categories: bool = typer.Option(False, "--categories", help="List categories"),
    status: bool = typer.Option(False, "--status", help="Marketplace status summary"),
    installed_only: bool = typer.Option(False, "--installed", help="Only installed"),
    available_only: bool = typer.Option(False, "--available", help="Only not installed"),
):
    """V1-N8: Browse plugin marketplace (offline bundled + optional remote)."""
    from core.plugin_catalog import (
        browse_catalog,
        fetch_catalog,
        get_plugin,
        install_from_catalog_entry,
        list_categories,
        marketplace_status,
    )

    if status:
        console.print_json(data=marketplace_status())
        return
    if categories:
        console.print_json(data=list_categories(url))
        return
    if show_id:
        console.print_json(data=get_plugin(show_id, url=url))
        return
    if install_id:
        if not url:
            console.print("[red]URL required for --install (remote catalog entry)[/red]")
            raise typer.Exit(1)
        cat = fetch_catalog(url)
        entries = cat.get("plugins") or cat.get("entries") or []
        entry = next((e for e in entries if e.get("id") == install_id), None)
        if not entry:
            console.print("[red]id not found in remote catalog[/red]")
            raise typer.Exit(1)
        console.print_json(data=install_from_catalog_entry(entry))
        return
    console.print_json(
        data=browse_catalog(
            url,
            query=query,
            category=category,
            tag=tag,
            sort=sort,
            limit=limit,
            installed_only=installed_only,
            available_only=available_only,
        )
    )


@app.command("explain-run")
def explain_run_cmd(
    run_id: str = typer.Argument(..., help="run-… id from agent/trail"),
    limit: int = typer.Option(50, "--limit"),
):
    """V5 S3: Explain a run_id (trail events + cost hints)."""
    from core.run_trail import recent_for_run
    from core.spend_guard import ensure_public_result

    rows = recent_for_run(run_id, limit=limit)
    console.print_json(
        data=ensure_public_result(
            {
                "ok": True,
                "run_id": run_id,
                "events": rows,
                "count": len(rows),
            },
            mock=False,
            ok=True,
        )
    )


@app.command("progress")
def progress_cmd(limit: int = typer.Option(20, "--limit")):
    """V5 S10: Recent progress bus + last trail lines."""
    from core.progress_events import get_progress_bus
    from pathlib import Path
    import json

    bus = get_progress_bus()
    events = []
    if hasattr(bus, "recent"):
        events = bus.recent(limit)
    elif hasattr(bus, "history"):
        events = list(bus.history)[-limit:]
    trail = []
    p = Path.home() / ".superai" / "run_trails.jsonl"
    if p.is_file():
        try:
            for line in p.read_text(encoding="utf-8").splitlines()[-limit:]:
                trail.append(json.loads(line))
        except Exception:
            pass
    console.print_json(
        data={"ok": True, "progress_events": events, "trail_tail": trail}
    )


@app.command("profile-suggest")
def profile_suggest_cmd():
    """V5 S5: Suggest cheap/local-only/balanced from today's spend."""
    from core.profile_suggest import suggest_profile

    console.print_json(data=suggest_profile())


@app.command("eval-golden")
def eval_golden_cmd(
    live: bool = typer.Option(False, "--live"),
):
    """V5 M8: Offline golden eval set (mock by default)."""
    from core.eval_golden import run_golden

    console.print_json(data=run_golden(use_mock=not live))


@app.command("v6-status")
def v6_status_cmd():
    """V6 phase completion report (honest done/partial/park/n/a)."""
    from core.v6_phase_status import phase_report

    console.print_json(data=phase_report())


@app.command("phase6-smoke")
def phase6_smoke_cmd(
    allow_live: bool = typer.Option(False, "--allow-live"),
):
    """Phase 6 full smoke path (live only with credentials; never false-pass)."""
    from core.live_smoke_complete import run_phase6_smoke

    console.print_json(data=run_phase6_smoke(allow_live=allow_live))


@app.command("parked")
def parked_cmd(
    action: str = typer.Argument(
        "catalog",
        help="catalog|flags|set|invoke|refuse-list|splash|chroma|agent-only|rbac|sso",
    ),
    key: Optional[str] = typer.Argument(None),
    value: Optional[str] = typer.Argument(None),
):
    """
    Phase 16 parked features (optional / stubs / refuse-closed).
    Abuse IDs P386–P400 always refuse.
    """
    from core import parked_features as pf
    from core.enterprise_stubs import data_residency, platform_catalog, rbac_roles, sso_status

    act = action.lower()
    if act == "catalog":
        console.print_json(data=pf.catalog())
        return
    if act == "flags":
        console.print_json(data={"ok": True, "flags": pf.load_flags()})
        return
    if act == "set" and key is not None:
        val: Any = value
        if value is not None and value.lower() in {"true", "false", "1", "0"}:
            val = value.lower() in {"true", "1"}
        console.print_json(data=pf.save_flags({key: val}))
        return
    if act == "invoke" and key:
        kw = {}
        if value:
            kw["text"] = value
            kw["name"] = value
            kw["enabled"] = value.lower() in {"true", "1", "yes"}
        console.print_json(data=pf.invoke(key, **kw))
        return
    if act in {"refuse-list", "refused"}:
        console.print_json(data=pf.list_refused())
        return
    if act == "splash":
        console.print(pf.splash_banner())
        return
    if act == "chroma":
        if key == "store" and value:
            pf.save_flags({"chroma_experimental": True})
            console.print_json(data=pf.experimental_chroma_store(value))
        else:
            console.print_json(data=pf.chroma_status())
        return
    if act == "agent-only":
        en = (key or "true").lower() in {"true", "1", "yes", "on"}
        console.print_json(data=pf.set_agent_only(en))
        return
    if act == "rbac":
        console.print_json(data=rbac_roles())
        return
    if act == "sso":
        console.print_json(data=sso_status())
        return
    if act == "residency":
        console.print_json(data=data_residency())
        return
    if act == "platforms":
        console.print_json(data={"ok": True, "platforms": platform_catalog()})
        return
    console.print_json(data=pf.catalog())


@app.command("todos")
def todos_cmd(
    action: str = typer.Argument("list", help="list|add|done|new"),
    text: Optional[str] = typer.Argument(None),
    list_id: Optional[str] = typer.Option(None, "--list"),
    item_id: Optional[str] = typer.Option(None, "--id"),
):
    """V6 S101: Agent todo lists."""
    from core.agent_todos import AgentTodoStore

    store = AgentTodoStore()
    lid = list_id or store.ensure()
    if action == "new":
        console.print_json(data={"ok": True, "list_id": store.ensure()})
        return
    if action == "add":
        console.print_json(data=store.add(lid, text or ""))
        return
    if action == "done":
        console.print_json(data={"ok": store.complete(lid, item_id or "")})
        return
    console.print_json(data={"list_id": lid, "items": store.list_items(lid)})


@app.command("spec")
def spec_cmd(
    action: str = typer.Argument("run", help="run|approve|get"),
    task: Optional[str] = typer.Argument(None),
    auto_approve: bool = typer.Option(False, "--auto-approve"),
):
    """V6 S102: Spec-first plan → approve → implement."""
    from core.spec_mode import approve_spec, get_spec, run_spec_first

    if action == "approve":
        console.print_json(data=approve_spec(task or ""))
        return
    if action == "get":
        console.print_json(data=get_spec(task or ""))
        return
    console.print_json(
        data=run_spec_first(task or "task", use_mock=True, auto_approve=auto_approve)
    )


@app.command("gates")
def gates_cmd():
    """V6 S105/S106: Run quality gates (pytest/lint if present)."""
    from core.quality_gates import detect_and_run

    console.print_json(data=detect_and_run())


@app.command("recipes")
def recipes_cmd(
    recipe_id: Optional[str] = typer.Argument(None),
):
    """V6 S196: List or show recipe prompts."""
    from core.recipes import get_recipe, list_recipes

    if recipe_id:
        console.print_json(data=get_recipe(recipe_id))
    else:
        console.print_json(data=list_recipes())


@app.command("onboard")
def onboard_cmd(
    mark: Optional[str] = typer.Option(None, "--mark", help="Mark step id done"),
):
    """V6 S199: Onboarding quest status."""
    from core.onboarding_quest import mark as mark_step
    from core.onboarding_quest import status

    if mark:
        console.print_json(data=mark_step(mark))
    else:
        console.print_json(data=status())


@app.command("whats-new")
def whats_new_cmd():
    """V6 S200: Changelog summary."""
    from core.changelog_cli import whats_new

    console.print_json(data=whats_new())


@app.command("macros")
def macros_cmd(
    action: str = typer.Argument("list", help="list|set|get"),
    name: Optional[str] = typer.Argument(None),
    command: Optional[str] = typer.Argument(None),
):
    """V6 N203: User macros."""
    from core.macros import get_macro, list_macros, set_macro

    if action == "set" and name and command:
        console.print_json(data=set_macro(name, command))
        return
    if action == "get" and name:
        console.print_json(data={"ok": True, "command": get_macro(name)})
        return
    console.print_json(data=list_macros())


@app.command("capabilities")
def capabilities_cmd(
    models: str = typer.Option("gpt-4o,deepseek-chat,llama3.2,cli:claude", "--models", "-m"),
    need: Optional[str] = typer.Option(None, "--need", help="Filter capability"),
):
    """V6 S152: Model capability tags."""
    from core.capability_tags import catalog_with_tags, filter_by_capability

    ms = [x.strip() for x in models.split(",") if x.strip()]
    if need:
        console.print_json(data={"ok": True, "models": filter_by_capability(ms, need)})
    else:
        console.print_json(data={"ok": True, "catalog": catalog_with_tags(ms)})


@app.command("ci-why")
def ci_why_cmd(
    log_file: Optional[str] = typer.Option(None, "--file", "-f"),
    text: Optional[str] = typer.Option(None, "--text", "-t"),
):
    """V6 N260: Analyze CI/log failure patterns."""
    from core.ci_why import analyze_log
    from pathlib import Path

    blob = text or ""
    if log_file:
        blob = Path(log_file).read_text(encoding="utf-8", errors="replace")
    if not blob:
        console.print("[red]Provide --file or --text[/red]")
        raise typer.Exit(2)
    console.print_json(data=analyze_log(blob))


@app.command("debate")
def debate_cmd(
    topic: str = typer.Argument(..., help="Debate topic"),
    live: bool = typer.Option(False, "--live"),
):
    """V6 N261: Multi-role plan/critic/build debate."""
    from core.role_debate import debate

    console.print_json(data=debate(topic, use_mock=not live))


@app.command("lsp-check")
def lsp_check_cmd(path: str = typer.Argument(..., help="File path")):
    """V6 N231: Lightweight diagnostics (compile/LSP if available)."""
    from core.lsp_bridge import diagnostics_stub

    console.print_json(data=diagnostics_stub(path))


@app.command("timeouts")
def timeouts_cmd(
    name: Optional[str] = typer.Option(None, "--name"),
    seconds: Optional[float] = typer.Option(None, "--seconds"),
):
    """V6 S161: Show/set tool timeouts."""
    from core.tool_timeouts import get, load, set_timeout

    if name and seconds is not None:
        console.print_json(data=set_timeout(name, seconds))
        return
    if name:
        console.print_json(data={"ok": True, "name": name, "seconds": get(name)})
        return
    console.print_json(data={"ok": True, "timeouts": load()})


@app.command("preview")
def preview_cmd(
    task: str = typer.Argument(..., help="Natural language — preview planned command only"),
    path: Optional[str] = typer.Option(
        None, "--path", help="Force front-door path: agent|board|run|ask"
    ),
    live: bool = typer.Option(False, "--live", help="Preview as live (not dry-run)"),
):
    """N202: NL → any command with preview (does not execute)."""
    from core.nl_preview import preview_nl

    console.print_json(data=preview_nl(task, force_path=path, live=live))


@app.command("shell")
def shell_cmd(
    command: str = typer.Argument(..., help="OS shell command to run"),
    cwd: Optional[str] = typer.Option(None, "--cwd", help="Working directory (workspace-jailed)"),
    timeout: float = typer.Option(120.0, "--timeout", "-t"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview only (also default under plan permission)"
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Allow real execution (not dry-run) when permitted"
    ),
):
    """Run an arbitrary OS shell command with SuperAI safety policy."""
    from core.os_shell import preview_shell, run_shell
    from core.permission_mode import force_dry_run, mode_from_config

    mode = mode_from_config()
    do_dry = dry_run or (force_dry_run(mode) and not yes)
    if do_dry and not yes:
        console.print_json(data=preview_shell(command, cwd=cwd))
        if force_dry_run(mode):
            console.print(
                "[yellow]plan/ask permission: dry-run only. Use --yes with auto/yolo to execute.[/yellow]"
            )
        return
    console.print_json(
        data=run_shell(
            command,
            cwd=cwd,
            timeout=timeout,
            dry_run=False if yes else do_dry,
        )
    )


@app.command("nl-eval")
def nl_eval_cmd():
    """Run English NL accuracy eval suite (target: 100% on SuperAI paraphrases)."""
    from core.nl_accuracy import run_eval

    console.print_json(data=run_eval())


@app.command("do")
def do_cmd(
    task: str = typer.Argument(..., help="Task — routed by front-door policy"),
    live: bool = typer.Option(False, "--live", help="Allow live model calls"),
    path: Optional[str] = typer.Option(
        None, "--path", help="Force path: agent|board|run|ask"
    ),
    preview: bool = typer.Option(
        False, "--preview", help="N202: show planned command only (no execute)"
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="N202: execute even when needs_confirm (after reviewing preview)",
    ),
    gui_confirm: bool = typer.Option(
        False,
        "--gui-confirm",
        help="N202: show desktop Confirm/Cancel dialog before execute",
    ),
):
    """
    One-shot SuperAI task with front-door routing (agent / board / run / ask).

    N202: use --preview for planned command; low-confidence routes need --yes
    or --gui-confirm.
    """
    from core.nl_preview import preview_and_maybe_execute, preview_nl
    from core.spend_guard import ensure_public_result

    if preview:
        console.print_json(data=preview_nl(task, force_path=path, live=live))
        return

    out = preview_and_maybe_execute(
        task,
        preview_only=False,
        yes=yes,
        live=live,
        force_path=path,
        verbose=False,
        gui_confirm=gui_confirm,
        confirm=gui_confirm,
    )
    if isinstance(out, dict):
        # Always show planned command for transparency
        if out.get("planned_command"):
            console.print(f"[dim]preview → {out.get('planned_command')}[/dim]")
        if out.get("needs_confirm") and not out.get("executed") and not yes:
            console.print(
                "[yellow]needs_confirm: re-run with --yes or --gui-confirm[/yellow]"
            )
        console.print_json(data=ensure_public_result(out, ok=bool(out.get("ok", True))))
    else:
        console.print_json(data={"result": out})


@app.command("agent")
def agent_cmd(
    prompt: Optional[str] = typer.Argument(
        None, help="One-shot task (omit for interactive SuperAI agent TUI)"
    ),
    session: Optional[str] = typer.Option(None, "--session", "-s"),
    agent: str = typer.Option("build", "--agent", "-a", help="build | plan | ask"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    permission: Optional[str] = typer.Option(None, "--permission"),
    mock: bool = typer.Option(True, "--mock/--live"),
    profile: Optional[str] = typer.Option(None, "--profile"),
):
    """
    SuperAI multi-agent (build/plan/ask) — tool loop + sessions + TUI.

    Interactive: superai   or   superai agent
    One-shot:    superai agent "add logging to config"
    """
    if profile:
        from core.config import Config
        from core.run_profiles import apply_profile_to_config

        apply_profile_to_config(Config(), profile)
    if prompt:
        from core.superai_agent.runtime import AgentRuntime

        rt = AgentRuntime(use_mock=mock)
        out = rt.run(
            prompt,
            session_id=session,
            agent=agent,
            model=model,
            permission=permission or "plan",
        )
        console.print_json(data=out.to_dict())
        return
    from core.superai_agent.tui import run_superai_agent_tui

    run_superai_agent_tui(
        session_id=session,
        agent=agent,
        model=model,
        permission=permission,
        use_mock=mock,
    )


@app.command("agent-tui")
def agent_tui_cmd(
    session: Optional[str] = typer.Option(None, "--session", "-s"),
    permission: Optional[str] = typer.Option(None, "--permission"),
    profile: Optional[str] = typer.Option(None, "--profile"),
    agent: str = typer.Option("build", "--agent", "-a", help="build | plan | ask"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
):
    """Alias for `superai agent` interactive TUI."""
    agent_cmd(
        prompt=None,
        session=session,
        agent=agent,
        model=model,
        permission=permission,
        mock=True,
        profile=profile,
    )


@app.command("agent-roles")
def agent_roles_cmd():
    """List SuperAI agent roles (build / plan / ask)."""
    from core.superai_agent.agents import list_agents

    console.print_json(data={"agents": list_agents()})


@app.command("agent-tools")
def agent_tools_cmd(
    prompt: str = typer.Argument(..., help="Task; model may emit tool_call JSON"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    rounds: int = typer.Option(2, "--rounds"),
):
    """V3: Model-driven tool protocol (read/write/grep/diff_apply)."""
    from core.tool_protocol import agent_with_tools

    console.print_json(
        data=agent_with_tools(prompt, model=model, max_rounds=rounds)
    )


@app.command("side-effects")
def side_effects_cmd(limit: int = typer.Option(30, "--limit")):
    """Show recent tool/CLI side-effect audit log."""
    from core.side_effect_audit import recent

    console.print_json(data={"events": recent(limit)})


@app.command("goals")
def goals_cmd(
    action: str = typer.Argument(
        "list",
        help="list | add | done | heartbeat | notify | schedule | execute | tick",
    ),
    title: Optional[str] = typer.Argument(None, help="Goal title (for add)"),
    goal_id: Optional[str] = typer.Option(None, "--id"),
    detail: str = typer.Option("", "--detail"),
    every_hours: float = typer.Option(24.0, "--every-hours"),
    max_goals: int = typer.Option(3, "--max"),
    execute_tick: bool = typer.Option(
        False, "--execute", help="With tick: also run due goals (safe caps)"
    ),
):
    """Phase 8 N2: Personal assistant goals + heartbeat + messenger + execute + tick."""
    from core.assistant_goals import GoalStore

    store = GoalStore()
    act = action.lower()
    if act == "list":
        console.print_json(data={"goals": store.list("open")})
        return
    if act == "add":
        if not title:
            console.print("[red]Need goal title[/red]")
            raise typer.Exit(1)
        console.print_json(data=store.add(title, detail=detail))
        return
    if act == "done":
        if not goal_id:
            console.print("[red]Need --id[/red]")
            raise typer.Exit(1)
        console.print_json(data={"ok": store.complete(goal_id)})
        return
    if act == "heartbeat":
        console.print_json(data=store.heartbeat(goal_id))
        return
    if act == "notify":
        console.print_json(data=store.notify_due())
        return
    if act == "schedule":
        if not goal_id:
            console.print("[red]Need --id[/red]")
            raise typer.Exit(1)
        console.print_json(
            data=store.schedule_reminder(goal_id, every_hours=every_hours)
        )
        return
    if act == "execute":
        console.print_json(data=store.execute_due(max_goals=max_goals, use_ask=True))
        return
    if act == "tick":
        # N2: daemon tick (schedule + heartbeat; optional execute)
        console.print_json(
            data=store.daemon_tick(
                max_goals=max_goals,
                execute=execute_tick,
                notify=True,
                schedule_due=True,
            )
        )
        return
    raise typer.Exit(1)


@app.command("bakeoff")
def bakeoff_cmd(
    prompt: str = typer.Argument(..., help="Prompt for all models"),
    models: str = typer.Option(
        "gpt-4o,deepseek-chat,llama3.2",
        "--models",
        "-m",
        help="Comma-separated registry names",
    ),
    live: bool = typer.Option(False, "--live", help="Disable mock (needs keys)"),
    pin: bool = typer.Option(False, "--pin", help="Persist winner as preferred_model"),
):
    """Phase 8 N6: Model bake-off ranking by success then latency."""
    from core.model_bakeoff import bakeoff, pin_winner

    model_list = [m.strip() for m in models.split(",") if m.strip()]
    out = bakeoff(prompt, model_list, use_mock=not live)
    if pin and out.get("winner"):
        out["pin"] = pin_winner(out["winner"], persist=True)
    console.print_json(data=out)


@app.command("models-refresh-openrouter")
def models_refresh_openrouter_cmd(
    dry_run: bool = typer.Option(False, "--dry-run"),
    limit: int = typer.Option(40, "--limit"),
    schedule: bool = typer.Option(
        False, "--schedule", help="Also add a weekly schedule job"
    ),
):
    """Phase 8 N5 / Sprint D: Pull OpenRouter public model list into user registry."""
    from core.model_catalog_refresh import refresh_openrouter_into_user_registry

    out = refresh_openrouter_into_user_registry(write=not dry_run, limit=limit)
    if schedule:
        try:
            from core.schedule_store import ScheduleStore

            out["schedule"] = ScheduleStore().add(
                "openrouter-refresh",
                "models-refresh-openrouter",
                every_hours=168.0,
            )
        except Exception as e:
            out["schedule_error"] = str(e)[:200]
    console.print_json(data=out)


@app.command("agent-graph")
def agent_graph_cmd(
    task_id: Optional[str] = typer.Option(None, "--task-id"),
):
    """Phase 8 N4: Print run/member graph JSON (also GET /api/agent-graph)."""
    from core.agent_graph import graph_from_run_result

    console.print_json(data=graph_from_run_result({"task_id": task_id} if task_id else {}))


@app.command("tenant-export")
def tenant_export_cmd(
    tenant: Optional[str] = typer.Option(None, "--tenant", "-t"),
    dest: Optional[str] = typer.Option(None, "--dest", "-o"),
):
    """N7: Export Memory Palace rows for a tenant to JSON."""
    from core.palace_tenant import export_tenant_memories
    from pathlib import Path

    console.print_json(
        data=export_tenant_memories(
            tenant=tenant,
            dest=Path(dest) if dest else None,
        )
    )


@app.command("tenant-import")
def tenant_import_cmd(
    src: str = typer.Argument(..., help="Path to tenant export JSON"),
    tenant: Optional[str] = typer.Option(None, "--tenant", "-t"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """N7: Import tenant memories from export JSON."""
    from core.palace_tenant import import_tenant_memories
    from pathlib import Path

    console.print_json(
        data=import_tenant_memories(Path(src), tenant=tenant, dry_run=dry_run)
    )


@app.command("worktree-run")
def worktree_run_cmd(
    task: str = typer.Argument(..., help="Task to run inside a git worktree"),
    cleanup: bool = typer.Option(True, "--cleanup/--keep"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    live: bool = typer.Option(False, "--live"),
):
    """N3: Run a task in an isolated git worktree subagent."""
    from core.worktree_subagent import run_in_worktree

    console.print_json(
        data=run_in_worktree(
            task,
            use_mock=not live,
            cleanup=cleanup,
            dry_run=dry_run,
        )
    )


@app.command("smoke-harness")
def smoke_harness_cmd(
    allow_live: bool = typer.Option(
        False,
        "--allow-live",
        help="Only when credentials present; never claim pass without keys",
    ),
):
    """N8: Live multi-vendor smoke HARNESS only (default: no live calls)."""
    from core.provider_smoke import smoke_harness

    console.print_json(data=smoke_harness(allow_live=allow_live))


@app.command("smoke-preflight")
def smoke_preflight_cmd(
    readiness: bool = typer.Option(
        False,
        "--readiness",
        help="Also run model readiness checks (not full chat smoke)",
    ),
):
    """W8: Inventory keys/local services + checklist before live smoke."""
    from core.smoke_preflight import smoke_preflight

    console.print_json(data=smoke_preflight(include_readiness=readiness))


@app.command()
def telemetry(
    action: str = typer.Argument("status", help="status | enable | disable"),
):
    """N29: Anonymous telemetry opt-in"""
    from core.telemetry import Telemetry

    t = Telemetry()
    if action == "enable":
        t.enable()
    elif action == "disable":
        t.disable()
    console.print_json(data={"enabled": t.is_enabled()})


@app.command()
def lang(
    code: Optional[str] = typer.Argument(None, help="en | es | fr | de"),
):
    """N30: Set CLI language (SUPERAI_LANG)"""
    from core.i18n import t, get_lang, MESSAGES
    import os

    if code:
        os.environ["SUPERAI_LANG"] = code
        Config().set("lang", code)
        console.print(f"[green]lang={code}[/green] {t('ready')}")
        return
    console.print_json(data={"lang": get_lang(), "available": list(MESSAGES.keys())})


@app.command("validate-json")
def validate_json_cmd(
    text: str = typer.Argument(..., help="JSON or text containing JSON"),
    keys: Optional[str] = typer.Option(None, "--keys", help="Required keys comma-list"),
):
    """S18: Validate structured JSON output"""
    from core.output_validate import extract_json, validate_json_schema_simple

    data = extract_json(text)
    req = [k.strip() for k in keys.split(",")] if keys else None
    console.print_json(data=validate_json_schema_simple(data, req))


@app.command("merge-results")
def merge_results_cmd(
    task: str = typer.Argument(..., help="Parent goal"),
    parts: str = typer.Argument(..., help="JSON list of partial result strings"),
):
    """S16: Merge parallel subtask results into one synthesis"""
    from core.model_caller import ModelCaller
    from core.model_registry import ModelRegistry

    try:
        items = json.loads(parts)
    except json.JSONDecodeError:
        items = [p.strip() for p in parts.split("||") if p.strip()]
    blob = "\n\n".join(f"### Part {i+1}\n{x}" for i, x in enumerate(items))
    reg = ModelRegistry()
    names = [n for n in reg.list_all_models() if not str(n).startswith("cli:")]
    model = names[0] if names else "gpt-4o"
    r = ModelCaller(use_mock=Config().use_mock, registry=reg).call(
        model=model,
        prompt=f"Goal: {task}\n\nMerge these parallel results into one answer:\n{blob}",
    )
    console.print_json(data={"model": model, "merged": r.get("response")})


@app.command("history-search")
def history_search_cmd(
    task: Optional[str] = typer.Option(None, "--task", help="Substring match task text"),
    model: Optional[str] = typer.Option(None, "--model", "-m"),
    min_cost: Optional[float] = typer.Option(None, "--min-cost"),
    max_cost: Optional[float] = typer.Option(None, "--max-cost"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """Search run history by task/model/cost (V6 M067)."""
    from core.history import TaskHistory
    from core.public_api import wrap_public_result

    rows = TaskHistory().search(
        task=task, model=model, min_cost=min_cost, max_cost=max_cost, limit=limit
    )
    console.print_json(
        data=wrap_public_result(
            {"ok": True, "count": len(rows), "results": rows},
            mock=True,
            record_spend=False,
        )
    )


@app.command("board-preflight")
def board_preflight_cmd(
    subject: str = typer.Argument(..., help="Board subject"),
    members: str = typer.Option(
        "gpt-4o-mini,deepseek-chat", "--members", "-m", help="Comma-separated members"
    ),
):
    """Pre-flight cost estimate before multi-member boards (V6 M003)."""
    from core.board_preflight import estimate_board
    from core.public_api import wrap_public_result

    mems = [m.strip() for m in members.split(",") if m.strip()]
    console.print_json(
        data=wrap_public_result(estimate_board(subject, mems), mock=True, record_spend=False)
    )


@app.command("spend-report")
def spend_report_cmd(days: int = typer.Option(7, "--days", "-d")):
    """Daily/weekly spend report + cache stats (V6 S134/S135)."""
    from core.public_api import wrap_public_result
    from core.spend_report import spend_report

    console.print_json(
        data=wrap_public_result(spend_report(days=days), mock=True, record_spend=False)
    )


@app.command("project-budget")
def project_budget_cmd(
    project: str = typer.Option("default", "--project", "-p"),
    daily: Optional[float] = typer.Option(None, "--daily-usd"),
    run: Optional[float] = typer.Option(None, "--run-usd"),
    apply: bool = typer.Option(False, "--apply", help="Apply policy to global BudgetGuard"),
):
    """Per-project budget policies (V6 S131)."""
    from core.project_budget import apply_to_global, get_policy, set_policy
    from core.public_api import wrap_public_result

    if daily is not None or run is not None:
        pol = set_policy(project, daily_usd_limit=daily, run_usd_limit=run)
    else:
        pol = get_policy(project)
    out = {"ok": True, "policy": pol}
    if apply:
        out["applied"] = apply_to_global(project)
    console.print_json(data=wrap_public_result(out, mock=True, record_spend=False))


@app.command("contract-smoke")
def contract_smoke_cmd():
    """Offline contract checks for top public APIs (V6 M090)."""
    from core.contract_registry import smoke_contracts_offline
    from core.public_api import wrap_public_result

    console.print_json(
        data=wrap_public_result(smoke_contracts_offline(), mock=True, record_spend=False)
    )


@app.command("mode")
def mode_cmd(
    mode: str = typer.Argument(..., help="architecture|implementation|plan|build|ask"),
):
    """Architecture vs implementation mode (V6 S103)."""
    from core.architecture_mode import resolve_mode
    from core.public_api import wrap_public_result

    console.print_json(
        data=wrap_public_result(resolve_mode(mode), mock=True, record_spend=False)
    )


@app.command("voice")
def voice_cmd(
    action: str = typer.Argument(
        "status",
        help="status|speak|listen|queue|backends|on|off|auto",
    ),
    text: Optional[str] = typer.Argument(
        None, help="Text for speak/queue, or 'on'/'off' for auto"
    ),
    timeout: float = typer.Option(5.0, "--timeout", "-t", help="STT timeout seconds"),
    mock: bool = typer.Option(
        False, "--mock", help="Force mock TTS (write outbox, no audio)"
    ),
):
    """MOS-N6: Voice hooks — TTS/STT for agent TUI and automation."""
    from core.voice_io import (
        handle_voice_slash,
        list_backends,
        listen_once,
        queue_voice_text,
        speak,
        status,
    )

    act = (action or "status").lower().strip()
    if act == "status":
        console.print_json(data=status())
        return
    if act == "backends":
        console.print_json(data=list_backends())
        return
    if act == "speak":
        console.print_json(
            data=speak(text or "SuperAI ready.", force_backend="mock" if mock else None)
        )
        return
    if act == "listen":
        console.print_json(
            data=listen_once(timeout=timeout, prefer_file=mock or False)
        )
        return
    if act == "queue":
        console.print_json(data=queue_voice_text(text or ""))
        return
    if act in {"on", "off", "auto"}:
        arg = act if act != "auto" else f"auto {text or 'on'}"
        console.print_json(data=handle_voice_slash(arg))
        return
    # generic slash handler
    blob = f"{act} {text}".strip() if text else act
    console.print_json(data=handle_voice_slash(blob))


@app.command("foundation-check")
def foundation_check_cmd(
    item: str = typer.Argument(
        "all",
        help="Item id e.g. M001 or 'all' for must foundation suite",
    ),
):
    """Run offline checks for foundation completion evidence (V1–V6)."""
    from core.foundation_complete import (
        dashboard_state,
        learning_distill,
        learning_promote_durable,
        learning_resolve_conflicts,
        mcp_parity,
        verify_top30_contracts,
    )
    from core.public_api import wrap_public_result
    from core.public_surface import emit_public, set_json_mode

    set_json_mode(True)
    suite = {
        "M090": verify_top30_contracts(),
        "M093": mcp_parity(),
        "M100": dashboard_state(),
        "M061": learning_promote_durable(limit=5),
        "M062": learning_resolve_conflicts(),
        "M063": learning_distill(),
    }
    if item and item.upper() != "ALL":
        key = item.upper()
        data = suite.get(key) or wrap_public_result(
            {"ok": False, "error": f"no suite for {key}", "available": list(suite)},
            ok=False,
            record_spend=False,
        )
        emit_public(data, print_json=True, record_spend=False)
        return
    emit_public(
        {"ok": True, "suite": suite, "count": len(suite)},
        mock=True,
        print_json=True,
        record_spend=False,
    )

