"""
External CLI delegation layer (Phase 7 / Track H).

Deep integration with SuperAI:
  - Central Memory Palace inject + write-back
  - LearningEngine mid-task / task learnings
  - MCP-style context packs
  - Audit log
  - Invoked by ModelCaller as cli:* models and by ParallelCLIManager
  - Orchestrator can delegate worker steps to external CLIs (supervisor–worker)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ExternalCLISpec:
    name: str
    command: str
    args_template: List[str] = field(default_factory=list)
    # {prompt} placeholder in args
    detects: List[str] = field(default_factory=list)  # PATH names or files
    modifies_files: bool = True
    description: str = ""
    default_role: str = "worker"  # for supervisor-worker patterns


@dataclass
class CLIResultEnvelope:
    ok: bool
    cli: str
    command: List[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_sec: float
    modifies_files: bool
    approved: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Curated registry of common AI CLIs (Windows + Unix friendly)
DEFAULT_CLI_SPECS: List[ExternalCLISpec] = [
    ExternalCLISpec(
        name="claude",
        command="claude",
        args_template=["-p", "{prompt}"],
        detects=["claude", "claude.exe"],
        modifies_files=True,
        description="Claude Code CLI",
        default_role="implementer",
    ),
    ExternalCLISpec(
        name="aider",
        command="aider",
        args_template=["--message", "{prompt}", "--yes"],
        detects=["aider", "aider.exe"],
        modifies_files=True,
        description="Aider coding agent",
        default_role="implementer",
    ),
    ExternalCLISpec(
        name="cursor",
        command="cursor",
        args_template=["agent", "{prompt}"],
        detects=["cursor", "cursor.exe"],
        modifies_files=True,
        description="Cursor agent CLI (if available)",
        default_role="implementer",
    ),
    ExternalCLISpec(
        name="grok",
        command="grok",
        args_template=["--prompt", "{prompt}"],
        detects=["grok", "grok.exe"],
        modifies_files=True,
        description="Grok CLI",
        default_role="reviewer",
    ),
    ExternalCLISpec(
        name="gemini",
        command="gemini",
        args_template=["-p", "{prompt}"],
        detects=["gemini", "gemini.exe"],
        modifies_files=True,
        description="Gemini CLI",
        default_role="worker",
    ),
    ExternalCLISpec(
        name="codex",
        command="codex",
        args_template=["exec", "{prompt}"],
        detects=["codex", "codex.exe"],
        modifies_files=True,
        description="OpenAI Codex CLI",
        default_role="implementer",
    ),
    ExternalCLISpec(
        name="continue",
        command="continue",
        args_template=["{prompt}"],
        detects=["continue", "cn", "continue.exe"],
        modifies_files=True,
        description="Continue.dev CLI (if installed)",
        default_role="worker",
    ),
    ExternalCLISpec(
        name="cline",
        command="cline",
        args_template=["{prompt}"],
        detects=["cline", "cline.exe"],
        modifies_files=True,
        description="Cline agent CLI (if installed)",
        default_role="implementer",
    ),
    ExternalCLISpec(
        name="roo",
        command="roo",
        args_template=["{prompt}"],
        detects=["roo", "roo-code", "roo.exe"],
        modifies_files=True,
        description="Roo Code CLI (if installed)",
        default_role="implementer",
    ),
]


class ExternalCLIRegistry:
    def __init__(self, specs: Optional[List[ExternalCLISpec]] = None):
        self.specs: Dict[str, ExternalCLISpec] = {
            s.name: s for s in (specs or DEFAULT_CLI_SPECS)
        }

    def discover(self) -> List[Dict[str, Any]]:
        found = []
        for name, spec in self.specs.items():
            path = None
            for cand in [spec.command, *spec.detects]:
                path = shutil.which(cand)
                if path:
                    break
            found.append(
                {
                    "name": name,
                    "available": path is not None,
                    "path": path,
                    "modifies_files": spec.modifies_files,
                    "description": spec.description,
                    "default_role": spec.default_role,
                }
            )
        return found

    def available(self) -> List[str]:
        return [d["name"] for d in self.discover() if d["available"]]

    def get(self, name: str) -> Optional[ExternalCLISpec]:
        return self.specs.get(name)

    def pick_for_role(self, role: str = "worker") -> Optional[str]:
        """Prefer an available CLI whose default_role matches, else any available."""
        role = (role or "worker").lower()
        avail = {d["name"]: d for d in self.discover() if d.get("available")}
        if not avail:
            return None
        for name, d in avail.items():
            if str(d.get("default_role") or "").lower() in {
                role,
                "implementer" if role == "worker" else role,
            }:
                return name
        # map common roles
        prefer = {
            "implementer": ["aider", "claude", "codex", "cursor", "cline", "roo"],
            "worker": ["claude", "aider", "gemini", "codex"],
            "reviewer": ["grok", "claude", "gemini"],
            "tester": ["aider", "claude", "codex"],
        }.get(role, [])
        for p in prefer:
            if p in avail:
                return p
        return next(iter(avail.keys()))


class ExternalCLITool:
    """
    Invoke an external CLI with SuperAI integration:
    approval gate, Memory Palace context, learning write-back, audit.
    """

    def __init__(
        self,
        registry: Optional[ExternalCLIRegistry] = None,
        auto_approve: bool = False,
        timeout_sec: float = 300.0,
        dry_run: bool = False,
        with_context: bool = True,
        write_memory: bool = True,
    ):
        self.registry = registry or ExternalCLIRegistry()
        self.auto_approve = auto_approve
        self.timeout_sec = timeout_sec
        self.dry_run = dry_run
        self.with_context = with_context
        self.write_memory = write_memory
        self.approvals: Dict[str, bool] = {}  # session approvals by cli name

    def approve(self, cli_name: str, approved: bool = True) -> None:
        self.approvals[cli_name] = approved

    def run(
        self,
        cli_name: str,
        prompt: str,
        approve: Optional[bool] = None,
        cwd: Optional[str] = None,
        *,
        with_context: Optional[bool] = None,
        write_memory: Optional[bool] = None,
        task_type: str = "coding",
        role: str = "worker",
        workflow_id: Optional[str] = None,
        source: str = "external_cli",
        task_id: Optional[str] = None,
        step_id: Optional[int] = None,
    ) -> CLIResultEnvelope:
        """
        Run external CLI. By default injects SuperAI context and writes results
        into central Memory Palace + learning history.
        """
        use_ctx = self.with_context if with_context is None else bool(with_context)
        use_mem = self.write_memory if write_memory is None else bool(write_memory)

        spec = self.registry.get(cli_name)
        if not spec:
            return CLIResultEnvelope(
                ok=False,
                cli=cli_name,
                command=[],
                exit_code=-1,
                stdout="",
                stderr="",
                duration_sec=0.0,
                modifies_files=False,
                approved=False,
                error=f"Unknown CLI: {cli_name}",
            )

        resolved = shutil.which(spec.command) or next(
            (shutil.which(d) for d in spec.detects if shutil.which(d)), None
        )
        if not resolved:
            # Dry-run still works without binary (demos / CI / orchestrator mock)
            if self.dry_run:
                resolved = spec.command
            else:
                return CLIResultEnvelope(
                    ok=False,
                    cli=cli_name,
                    command=[spec.command],
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    duration_sec=0.0,
                    modifies_files=spec.modifies_files,
                    approved=False,
                    error=f"CLI not found on PATH: {spec.command}",
                    metadata={
                        "source": source,
                        "role": role,
                        "step_id": step_id,
                        "task_id": task_id,
                    },
                )

        approved = (
            True
            if self.auto_approve
            else (
                approve
                if approve is not None
                else self.approvals.get(cli_name, False)
            )
        )
        if spec.modifies_files and not approved:
            return CLIResultEnvelope(
                ok=False,
                cli=cli_name,
                command=[resolved],
                exit_code=-1,
                stdout="",
                stderr="",
                duration_sec=0.0,
                modifies_files=True,
                approved=False,
                error=(
                    "Approval required for file-modifying CLI. "
                    f"Re-run with approve=True or superai cli-run {cli_name} --approve"
                ),
            )

        # ── SuperAI context inject (Memory Palace + skills) ───────────
        orig_prompt = prompt
        context_id = None
        memory_count = 0
        if use_ctx:
            try:
                from .central_memory import inject_context

                ctx = inject_context(
                    orig_prompt,
                    prompt=orig_prompt,
                    use_memory=True,
                    metadata={
                        "source": source,
                        "cli": cli_name,
                        "role": role,
                        "workflow_id": workflow_id,
                        "task_id": task_id,
                    },
                )
                prompt = ctx.get("prompt") or prompt
                context_id = ctx.get("context_id")
                memory_count = int(ctx.get("memory_count") or 0)
            except Exception as e:  # noqa: BLE001
                # keep original prompt; record in metadata later
                context_id = f"ctx-error:{e}"[:80]

        # Role framing for supervisor–worker pattern
        if role and role not in {"worker", ""}:
            prompt = (
                f"You are the {role} worker in a SuperAI multi-agent workflow.\n"
                f"{prompt}"
            )

        args = [a.replace("{prompt}", prompt) for a in spec.args_template]
        cmd = [resolved, *args]
        meta: Dict[str, Any] = {
            "source": source,
            "role": role,
            "task_type": task_type,
            "context_id": context_id,
            "memory_injected": bool(use_ctx and context_id),
            "memory_count": memory_count,
            "workflow_id": workflow_id,
            "task_id": task_id,
            "step_id": step_id,
            "integrated": True,
        }

        if self.dry_run:
            env = CLIResultEnvelope(
                ok=True,
                cli=cli_name,
                command=cmd,
                exit_code=0,
                stdout=(
                    f"[dry-run] {cli_name} as {role}; "
                    f"context={context_id}; memories={memory_count}"
                ),
                stderr="",
                duration_sec=0.0,
                modifies_files=spec.modifies_files,
                approved=approved,
                metadata={**meta, "dry_run": True},
            )
            if use_mem:
                self._observe(env, orig_prompt, task_type=task_type, source=source)
            return env

        start = time.time()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                cwd=cwd or os.getcwd(),
                shell=False,
            )
            duration = time.time() - start
            env = CLIResultEnvelope(
                ok=proc.returncode == 0,
                cli=cli_name,
                command=cmd,
                exit_code=proc.returncode,
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
                duration_sec=round(duration, 3),
                modifies_files=spec.modifies_files,
                approved=approved,
                metadata=meta,
            )
        except subprocess.TimeoutExpired as e:
            env = CLIResultEnvelope(
                ok=False,
                cli=cli_name,
                command=cmd,
                exit_code=-1,
                stdout=e.stdout or "" if isinstance(e.stdout, str) else "",
                stderr=e.stderr or "" if isinstance(e.stderr, str) else "",
                duration_sec=time.time() - start,
                modifies_files=spec.modifies_files,
                approved=approved,
                error=f"Timeout after {self.timeout_sec}s",
                metadata=meta,
            )
        except Exception as e:  # noqa: BLE001
            env = CLIResultEnvelope(
                ok=False,
                cli=cli_name,
                command=cmd,
                exit_code=-1,
                stdout="",
                stderr="",
                duration_sec=time.time() - start,
                modifies_files=spec.modifies_files,
                approved=approved,
                error=str(e),
                metadata=meta,
            )

        if use_mem:
            self._observe(env, orig_prompt, task_type=task_type, source=source)
        return env

    def _observe(
        self,
        env: CLIResultEnvelope,
        task: str,
        *,
        task_type: str = "coding",
        source: str = "external_cli",
    ) -> None:
        """Write-back to central memory, learning engine, audit."""
        meta = env.metadata or {}
        try:
            from .central_memory import write_back

            wb = write_back(
                task=task[:500],
                source=source,
                model_or_cli=f"cli:{env.cli}",
                success=bool(env.ok or (meta.get("dry_run"))),
                latency=float(env.duration_sec or 0),
                output=(env.stdout or "")[:2000],
                error=env.error or env.stderr,
                context_id=meta.get("context_id"),
                task_type=task_type,
                tags=["external_cli", env.cli, task_type, str(meta.get("role") or "worker")],
                metadata={
                    "workflow_id": meta.get("workflow_id"),
                    "task_id": meta.get("task_id"),
                    "step_id": meta.get("step_id"),
                    "exit_code": env.exit_code,
                },
            )
            meta["memory_write"] = wb
        except Exception as e:  # noqa: BLE001
            meta["memory_write_error"] = str(e)[:200]

        # Mid-task style learning when step_id present
        try:
            if meta.get("step_id") is not None:
                from .learning_engine import LearningEngine
                from .memory_palace import MemoryPalace

                LearningEngine(MemoryPalace()).learn_from_step(
                    task_description=task[:400],
                    step_id=int(meta["step_id"]),
                    step_description=f"external CLI {env.cli}",
                    task_type=task_type,
                    model_used=f"cli:{env.cli}",
                    success=bool(env.ok),
                    output=(env.stdout or "")[:800],
                    error=env.error,
                    latency=float(env.duration_sec or 0),
                    task_id=meta.get("task_id"),
                )
                meta["mid_task_learned"] = True
        except Exception as e:  # noqa: BLE001
            meta["mid_task_learn_error"] = str(e)[:200]

        try:
            from .audit_log import AuditLog

            AuditLog().record(
                "external_cli_run",
                {
                    "cli": env.cli,
                    "ok": env.ok,
                    "duration": env.duration_sec,
                    "context_id": meta.get("context_id"),
                    "source": source,
                    "role": meta.get("role"),
                    "dry_run": meta.get("dry_run"),
                },
                outcome="ok" if env.ok else "fail",
            )
            meta["audited"] = True
        except Exception as e:  # noqa: BLE001
            meta["audit_error"] = str(e)[:120]

        env.metadata = meta

    def run_as_worker(
        self,
        task: str,
        *,
        cli_name: Optional[str] = None,
        role: str = "worker",
        **kwargs: Any,
    ) -> CLIResultEnvelope:
        """
        Supervisor–worker helper: pick a CLI for the role if not specified,
        inject SuperAI context, run, write back.
        """
        if not cli_name:
            cli_name = self.registry.pick_for_role(role) or "claude"
        return self.run(
            cli_name,
            task,
            role=role,
            source=kwargs.pop("source", "orchestrator_worker"),
            **kwargs,
        )


def parse_cli_model(model: str) -> Optional[str]:
    """cli:aider → aider; bare name if known."""
    m = str(model or "")
    if m.startswith("cli:"):
        return m[4:]
    return None
