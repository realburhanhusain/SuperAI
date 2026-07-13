"""
SuperAI CLI (Phase 1 + stabilized higher-phase commands)

Entry point: superai = "superai.cli.main:app"
"""

from __future__ import annotations

import atexit
import json
import traceback
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from superai import __version__
from superai.core.config import Config
from superai.core.errors import SuperAIError
from superai.core.history import TaskHistory
from superai.core.logger import get_logger
from superai.core.orchestrator import SuperAIOrchestrator
from superai.core.task_planner import TaskPlanner

app = typer.Typer(
    name="superai",
    help="SuperAI - Intelligent Multi-Model AI Orchestration Platform",
    add_completion=True,  # G3: enable `superai --install-completion`
    no_args_is_help=True,
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
                from superai.core.backup_manager import BackupManager

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
    no_auto_backup: bool = typer.Option(
        False,
        "--no-auto-backup",
        help="Disable atexit auto-backup for this process",
    ),
) -> None:
    if not no_auto_backup:
        _register_auto_backup_if_enabled()


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
    if "chromadb" in msg or "embedding" in msg:
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
        "- Core Foundation (stabilized SuperAI_v1)"
    )


@app.command("init")
def init_cmd(
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Skip prompts (also set SUPERAI_NON_INTERACTIVE=1)",
    ),
):
    """Initialize SuperAI home directory and default configuration"""
    config = Config()
    if non_interactive:
        config.set("non_interactive", True, persist=True)
    dirs = config.initialize()
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
            f"mock_mode: {config.use_mock}",
            border_style="green",
        )
    )


@app.command()
def run(
    task: str = typer.Argument(..., help="The task to execute"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Force a specific model"),
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
):
    """Run a task using SuperAI orchestration (mock by default)"""
    try:
        orchestrator = SuperAIOrchestrator()

        if plan_only:
            planner = TaskPlanner(orchestrator.model_router)
            steps = planner.create_plan(task)
            planner.print_plan(steps)
            return

        console.print(Panel.fit(f"[bold]Task:[/bold] {task}", border_style="blue"))
        result = orchestrator.run_task(task=task, forced_model=model, verbose=verbose)

        if output:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str)
            console.print(f"[green]Result saved to {output}[/green]")

        if output_format.lower() == "json":
            console.print_json(data=result)
        else:
            summary = result.get("result") or result.get("message") or ""
            status = result.get("status", "unknown")
            color = "green" if result.get("success") else "yellow"
            console.print(
                Panel(
                    f"[bold]Status:[/bold] {status}\n"
                    f"[bold]Task ID:[/bold] {result.get('task_id')}\n"
                    f"[bold]Model:[/bold] {result.get('model_used')}\n"
                    f"[bold]Duration:[/bold] {result.get('duration')}s\n"
                    f"[bold]Mode:[/bold] {result.get('mode')}\n\n"
                    f"{summary}",
                    title="Result",
                    border_style=color,
                )
            )
    except Exception as e:  # noqa: BLE001
        _print_error(e, debug=debug)
        raise typer.Exit(code=1) from e


@app.command()
def plan(
    task: str = typer.Argument(..., help="Task to create execution plan for"),
):
    """Show execution plan without running the task"""
    orchestrator = SuperAIOrchestrator()
    planner = TaskPlanner(orchestrator.model_router)
    steps = planner.create_plan(task)
    planner.print_plan(steps)


@app.command()
def status():
    """Show current SuperAI system status"""
    config = Config()
    history = TaskHistory()
    emb = "n/a"
    mem_count = "n/a"
    try:
        from superai.core.memory_palace import MemoryPalace

        mp = MemoryPalace()
        st = mp.get_memory_stats()
        emb = st.get("embedding", "n/a")
        mem_count = st.get("total_memories", "n/a")
    except Exception:  # noqa: BLE001
        pass
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
    from superai.core.learning_engine import LearningEngine
    from superai.core.memory_palace import MemoryPalace

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
    from superai.core.learning_engine import LearningEngine
    from superai.core.memory_palace import MemoryPalace

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
                f"(chromadb={stats.get('using_chromadb')})",
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
    from superai.core.learning_engine import LearningEngine
    from superai.core.memory_palace import MemoryPalace

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
):
    """Create an encrypted incremental backup of SuperAI home data"""
    from superai.core.backup_manager import BackupManager

    bm = BackupManager()
    if not bm.key_file.exists():
        console.print(
            "[yellow]Warning: encryption key will be created. "
            f"Back up {bm.key_file} securely.[/yellow]"
        )
    path = bm.create_backup(force_full=full, incremental=not full)
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
    from superai.core.backup_manager import BackupManager

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
    from superai.core.backup_manager import BackupManager

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
    from superai.core.backup_manager import BackupManager

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
    from superai.core.skills import SkillsManager

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
    from superai.core.skills import SkillsManager

    sm = SkillsManager()
    if sm.promote_skill(name):
        console.print(f"[green]Promoted skill:[/green] {name}")
    else:
        console.print(f"[red]Skill not found:[/red] {name}")
        raise typer.Exit(code=1)


@app.command("skill-rollback")
def skill_rollback(name: str = typer.Argument(..., help="Skill name to rollback last improvement")):
    """Rollback last improvement section on a skill"""
    from superai.core.skills import SkillsManager

    sm = SkillsManager()
    if sm.rollback_skill(name):
        console.print(f"[green]Rolled back skill:[/green] {name}")
    else:
        console.print(f"[yellow]Nothing to rollback or skill missing:[/yellow] {name}")
        raise typer.Exit(code=1)


@app.command("list-models")
def list_models(
    refresh: bool = typer.Option(
        False,
        "--refresh",
        help="Refresh catalog (project + SUPERAI_MODELS_URL) into ~/.superai/config/models.json",
    ),
):
    """List models known to the registry"""
    from superai.core.model_registry import ModelRegistry

    if refresh:
        from superai.core.model_refresh import refresh_models

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
    table.add_column("Latest")
    for name in registry.list_all_models():
        m = registry.get_model(name)
        if not m:
            continue
        table.add_row(m.name, m.provider, m.model_id, "yes" if m.is_latest else "")
    console.print(table)


@app.command("smoke-providers")
def smoke_providers(
    mock: bool = typer.Option(
        False, "--mock", help="Force mock mode (always runs without keys)"
    ),
):
    """Live multi-provider smoke test (skips providers without credentials)"""
    from superai.core.provider_smoke import run_provider_smoke

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
    from superai.core.provider_health import ProviderHealthStore

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
    from superai.core.learning_engine import LearningEngine
    from superai.core.memory_palace import MemoryPalace

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
    from superai.core.history import TaskHistory
    from superai.core.learning_engine import LearningEngine
    from superai.core.memory_palace import MemoryPalace

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
    from superai.core.load_balancer import parse_strategy

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
    from superai.core.load_balancer import LoadBalancer, parse_strategy
    from superai.core.model_registry import ModelRegistry
    from superai.core.model_router import ModelRouter
    from superai.core.routing_stats import summarize_routing

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
