"""
External CLI delegation layer (Phase 7 / Track H).

Registers external AI CLIs as invocable tools with a consistent JSON envelope.
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
    ),
    ExternalCLISpec(
        name="aider",
        command="aider",
        args_template=["--message", "{prompt}", "--yes"],
        detects=["aider", "aider.exe"],
        modifies_files=True,
        description="Aider coding agent",
    ),
    ExternalCLISpec(
        name="cursor",
        command="cursor",
        args_template=["agent", "{prompt}"],
        detects=["cursor", "cursor.exe"],
        modifies_files=True,
        description="Cursor agent CLI (if available)",
    ),
    ExternalCLISpec(
        name="grok",
        command="grok",
        args_template=["--prompt", "{prompt}"],
        detects=["grok", "grok.exe"],
        modifies_files=True,
        description="Grok CLI",
    ),
    ExternalCLISpec(
        name="gemini",
        command="gemini",
        args_template=["-p", "{prompt}"],
        detects=["gemini", "gemini.exe"],
        modifies_files=False,
        description="Gemini CLI",
    ),
    ExternalCLISpec(
        name="codex",
        command="codex",
        args_template=["exec", "{prompt}"],
        detects=["codex", "codex.exe"],
        modifies_files=True,
        description="OpenAI Codex CLI",
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
                }
            )
        return found

    def available(self) -> List[str]:
        return [d["name"] for d in self.discover() if d["available"]]

    def get(self, name: str) -> Optional[ExternalCLISpec]:
        return self.specs.get(name)


class ExternalCLITool:
    """
    Invoke an external CLI with approval gate for file-modifying actions.
    """

    def __init__(
        self,
        registry: Optional[ExternalCLIRegistry] = None,
        auto_approve: bool = False,
        timeout_sec: float = 300.0,
        dry_run: bool = False,
    ):
        self.registry = registry or ExternalCLIRegistry()
        self.auto_approve = auto_approve
        self.timeout_sec = timeout_sec
        self.dry_run = dry_run
        self.approvals: Dict[str, bool] = {}  # session approvals by cli name

    def approve(self, cli_name: str, approved: bool = True) -> None:
        self.approvals[cli_name] = approved

    def run(
        self,
        cli_name: str,
        prompt: str,
        approve: Optional[bool] = None,
        cwd: Optional[str] = None,
    ) -> CLIResultEnvelope:
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
            )

        approved = (
            True
            if self.auto_approve
            else (approve if approve is not None else self.approvals.get(cli_name, False))
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

        args = [a.replace("{prompt}", prompt) for a in spec.args_template]
        cmd = [resolved, *args]

        if self.dry_run:
            return CLIResultEnvelope(
                ok=True,
                cli=cli_name,
                command=cmd,
                exit_code=0,
                stdout="[dry-run] command not executed",
                stderr="",
                duration_sec=0.0,
                modifies_files=spec.modifies_files,
                approved=approved,
                metadata={"dry_run": True},
            )

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
            return CLIResultEnvelope(
                ok=proc.returncode == 0,
                cli=cli_name,
                command=cmd,
                exit_code=proc.returncode,
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
                duration_sec=round(duration, 3),
                modifies_files=spec.modifies_files,
                approved=approved,
            )
        except subprocess.TimeoutExpired as e:
            return CLIResultEnvelope(
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
            )
        except Exception as e:  # noqa: BLE001
            return CLIResultEnvelope(
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
            )
