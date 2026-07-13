"""
Tool proposal system (Phase 7 / Track H).

Workers propose actions → supervisor review → human approval → execution.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class ProposalStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


@dataclass
class ToolProposal:
    id: str
    action: str  # edit_file | run_shell | web_search | external_cli
    args: Dict[str, Any]
    rationale: str = ""
    status: str = ProposalStatus.PROPOSED.value
    requires_human: bool = True
    result: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    decided_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ToolProposalManager:
    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = Path(
            store_path or (Path.home() / ".superai" / "tool_proposals.json")
        )
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.proposals: Dict[str, ToolProposal] = {}
        self._load()
        self._executors: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            "run_shell": self._exec_run_shell,
            "edit_file": self._exec_edit_file,
            "web_search": self._exec_web_search_stub,
        }

    def _load(self) -> None:
        if self.store_path.exists():
            try:
                data = json.loads(self.store_path.read_text(encoding="utf-8"))
                for item in data.get("proposals", []):
                    p = ToolProposal(**item)
                    self.proposals[p.id] = p
            except Exception:
                self.proposals = {}

    def save(self) -> None:
        payload = {
            "proposals": [p.to_dict() for p in self.proposals.values()],
        }
        self.store_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def propose(
        self,
        action: str,
        args: Dict[str, Any],
        rationale: str = "",
        requires_human: bool = True,
    ) -> ToolProposal:
        pid = uuid.uuid4().hex[:12]
        p = ToolProposal(
            id=pid,
            action=action,
            args=args,
            rationale=rationale,
            requires_human=requires_human,
        )
        self.proposals[pid] = p
        self.save()
        return p

    def approve(self, proposal_id: str) -> ToolProposal:
        p = self._get(proposal_id)
        p.status = ProposalStatus.APPROVED.value
        p.decided_at = time.time()
        self.save()
        return p

    def reject(self, proposal_id: str) -> ToolProposal:
        p = self._get(proposal_id)
        p.status = ProposalStatus.REJECTED.value
        p.decided_at = time.time()
        self.save()
        return p

    def execute(self, proposal_id: str, force: bool = False) -> ToolProposal:
        p = self._get(proposal_id)
        if p.status == ProposalStatus.REJECTED.value:
            raise ValueError("Cannot execute rejected proposal")
        if p.requires_human and p.status != ProposalStatus.APPROVED.value and not force:
            raise ValueError("Proposal requires human approval first")
        executor = self._executors.get(p.action)
        if not executor:
            p.status = ProposalStatus.FAILED.value
            p.result = {"error": f"No executor for action {p.action}"}
            self.save()
            return p
        try:
            p.result = executor(p.args)
            p.status = ProposalStatus.EXECUTED.value
        except Exception as e:  # noqa: BLE001
            p.result = {"error": str(e)}
            p.status = ProposalStatus.FAILED.value
        self.save()
        return p

    def list(self, status: Optional[str] = None) -> List[ToolProposal]:
        items = list(self.proposals.values())
        if status:
            items = [p for p in items if p.status == status]
        return sorted(items, key=lambda x: x.created_at, reverse=True)

    def _get(self, proposal_id: str) -> ToolProposal:
        if proposal_id not in self.proposals:
            raise KeyError(f"Unknown proposal: {proposal_id}")
        return self.proposals[proposal_id]

    def _exec_run_shell(self, args: Dict[str, Any]) -> Dict[str, Any]:
        import os
        import subprocess

        cmd = args.get("command")
        if not cmd:
            raise ValueError("run_shell requires command")
        # Safety: only allow simple list form
        if isinstance(cmd, str):
            raise ValueError("command must be a list of argv (not a shell string)")
        if not isinstance(cmd, (list, tuple)) or not cmd:
            raise ValueError("command must be a non-empty list of argv")
        # Block common shell meta-runners unless SUPERAI_ALLOW_SHELL_META=1
        exe = str(cmd[0]).lower().replace("\\", "/")
        base = Path(exe).name
        blocked = {
            "powershell",
            "powershell.exe",
            "pwsh",
            "pwsh.exe",
            "cmd",
            "cmd.exe",
            "bash",
            "sh",
            "zsh",
            "wscript",
            "cscript",
            "mshta",
        }
        if base in blocked and os.getenv("SUPERAI_ALLOW_SHELL_META", "").lower() not in {
            "1",
            "true",
            "yes",
        }:
            raise ValueError(
                f"Blocked shell meta-executable '{base}'. "
                "Set SUPERAI_ALLOW_SHELL_META=1 to override (not recommended)."
            )
        proc = subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            timeout=float(args.get("timeout", 60)),
            shell=False,
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout[:8000],
            "stderr": proc.stderr[:4000],
        }

    def _exec_edit_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        import os

        path = Path(args["path"]).expanduser()
        content = args.get("content")
        if content is None:
            raise ValueError("edit_file requires content")
        # Jail under workspace root (cwd or SUPERAI_WORKSPACE)
        root = Path(
            os.getenv("SUPERAI_WORKSPACE") or Path.cwd()
        ).expanduser().resolve()
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as e:
            raise ValueError(
                f"edit_file path must be under workspace root {root}. "
                "Set SUPERAI_WORKSPACE to change."
            ) from e
        # Atomic-Hermes style: snapshot before overwrite
        snap = None
        try:
            from .time_travel import FileTimeTravel

            snap = FileTimeTravel().snapshot(resolved, note="pre-edit_file proposal")
        except Exception:
            pass
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(str(content), encoding="utf-8")
        return {
            "path": str(resolved),
            "bytes": len(str(content).encode("utf-8")),
            "time_travel_snapshot": snap,
        }

    def _exec_web_search_stub(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Full search path via EcosystemHub (Tavily/Brave/stub)."""
        q = args.get("query", "")
        try:
            from .ecosystem import EcosystemHub

            return EcosystemHub().search(str(q), provider=str(args.get("provider") or "auto"))
        except Exception as e:  # noqa: BLE001
            return {
                "query": q,
                "results": [],
                "ok": False,
                "error": str(e),
            }
