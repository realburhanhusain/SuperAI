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
    """Initialize SuperAI home directory, config, and discover environment"""
    config = Config()
    if non_interactive:
        config.set("non_interactive", True, persist=True)
    dirs = config.initialize()

    from superai.core.discovery import discover_environment

    env = discover_environment()
    if env.get("mock_recommended"):
        config.set("mock_mode", True, persist=True)
    config.set("discovered_clis", env.get("clis_available") or [], persist=True)

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
            f"mock_mode: {config.use_mock}\n"
            f"CLIs found: {', '.join(env.get('clis_available') or []) or '(none)'}\n"
            f"Models registered: {env.get('models_registered')}\n"
            f"rclone: {env.get('rclone_on_path')} | ollama: {env.get('ollama_on_path')}",
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


@app.command()
def discover():
    """Discover installed AI CLIs, API keys, and environment"""
    from superai.core.discovery import discover_environment

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


@app.command("cli-run")
def cli_run(
    name: str = typer.Argument(..., help="External CLI name from discover"),
    prompt: str = typer.Argument(..., help="Prompt/task for the CLI"),
    approve: bool = typer.Option(
        False, "--approve", help="Approve file-modifying actions this run"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show command only"),
):
    """Run an external AI CLI with approval gate (config: require_human_approval)"""
    from superai.core.external_cli import ExternalCLITool
    from superai.core.learning_engine import LearningEngine
    from superai.core.memory_palace import MemoryPalace

    cfg = Config()
    # If require_human_approval is False, auto-approve file-modifying CLIs
    auto = not cfg.require_human_approval
    tool = ExternalCLITool(dry_run=dry_run, auto_approve=auto)
    result = tool.run(name, prompt, approve=True if auto else approve)
    data = result.to_dict()
    # Log delegation to memory palace
    try:
        le = LearningEngine(MemoryPalace())
        le.learn_from_task(
            task_description=f"external_cli:{name} {prompt[:200]}",
            task_type="coding" if result.modifies_files else "general",
            model_used=f"cli:{name}",
            success=result.ok,
            latency=result.duration_sec,
            steps_completed=1 if result.ok else 0,
            steps_failed=0 if result.ok else 1,
            error_message=result.error,
        )
    except Exception:  # noqa: BLE001
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

    from superai.core.tool_proposals import ToolProposalManager

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
    from superai.core.tool_proposals import ToolProposalManager

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
    from superai.core.tool_proposals import ToolProposalManager

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
    from superai.core.agentic import AgenticWorkflows

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
        None, "--models", help="Comma-separated council members"
    ),
    supervisor: Optional[str] = typer.Option(
        None, "--supervisor", help="Supervisor model (for supervisor voting)"
    ),
    critique: bool = typer.Option(False, "--critique", help="Add critique refinement round"),
):
    """Multi-model council with selectable voting (LLM Council inspired)"""
    from superai.core.council import Council, VOTING_MODES

    cfg = Config()
    mode = voting or cfg.council_voting_mode
    if mode not in VOTING_MODES:
        console.print(f"[red]Invalid voting mode. Use one of: {VOTING_MODES}[/red]")
        raise typer.Exit(code=1)
    model_list = [m.strip() for m in models.split(",")] if models else None
    sup = supervisor or cfg.default_supervisor
    c = Council(voting_mode=mode, supervisor_model=sup)
    result = c.run(
        topic,
        models=model_list,
        voting_mode=mode,
        supervisor_model=sup,
        with_critique=critique,
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
    mock: bool = typer.Option(False, "--mock", help="Force mock/heuristic backend"),
):
    """Ask natural-language questions over SQL data (Databao-inspired)"""
    from superai.core.databao_adapter import DatabaoAdapter
    from superai.core.learning_engine import LearningEngine
    from superai.core.memory_palace import MemoryPalace
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
    if answer.error:
        raise typer.Exit(code=1)


@app.command("data-schema")
def data_schema(
    dsn: Optional[str] = typer.Option(None, "--dsn", help="SQLAlchemy DSN"),
):
    """Show registered/demo data schema summary"""
    from superai.core.databao_adapter import DatabaoAdapter

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
    from superai.core.preferences import UserPreferenceModel

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
    from superai.core.time_travel import FileTimeTravel

    info = FileTimeTravel().snapshot(path, note=note)
    console.print_json(data=info)


@app.command("tt-list")
def tt_list(path: str = typer.Argument(..., help="File path")):
    """List time-travel versions for a file"""
    from superai.core.time_travel import FileTimeTravel

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
    from superai.core.time_travel import FileTimeTravel

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
    """Send via messenger bus (cli/file/webhook/…)"""
    from superai.core.messengers import MessengerBus

    result = MessengerBus().send(message, channel=channel)
    console.print_json(data=result)
    if not result.get("ok"):
        raise typer.Exit(1)


@app.command("msg-channels")
def msg_channels():
    """List messenger channels"""
    from superai.core.messengers import MessengerBus

    console.print_json(data=MessengerBus().list_channels())


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8787, "--port"),
):
    """Start web memory/status UI (requires pip install -e \".[web]\")"""
    try:
        import uvicorn
        from superai.web_app import create_app
    except ImportError as e:
        console.print(
            "[red]Web extras missing.[/red] Install: pip install -e \".[web]\""
        )
        raise typer.Exit(1) from e
    console.print(f"[green]Starting SuperAI web on http://{host}:{port}[/green]")
    uvicorn.run(create_app(), host=host, port=port, log_level="info")


@app.command("delegate")
def delegate(
    goal: str = typer.Argument(..., help="High-level goal to decompose and run"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Hierarchical delegation of a goal into subtasks"""
    from superai.core.hierarchy import HierarchicalDelegator

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
    list_all: bool = typer.Option(False, "--list", help="List wings and rooms"),
    memory_id: Optional[str] = typer.Option(None, "--memory-id"),
    wing: Optional[str] = typer.Option(None, "--wing"),
    room: Optional[str] = typer.Option(None, "--room"),
    note: str = typer.Option("", "--note"),
):
    """Memory wings & rooms organization (I4)"""
    from superai.core.wings import WingsManager

    wm = WingsManager()
    if list_all or not (memory_id and wing and room):
        console.print_json(data=wm.list_wings())
        return
    entry = wm.assign(memory_id, wing, room, note=note)
    console.print(f"[green]Assigned[/green] {entry}")


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
