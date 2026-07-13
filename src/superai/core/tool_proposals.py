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
        import subprocess

        cmd = args.get("command")
        if not cmd:
            raise ValueError("run_shell requires command")
        # Safety: only allow simple list form
        if isinstance(cmd, str):
            raise ValueError("command must be a list of argv (not a shell string)")
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=float(args.get("timeout", 60))
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout[:8000],
            "stderr": proc.stderr[:4000],
        }

    def _exec_edit_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        path = Path(args["path"])
        content = args.get("content")
        if content is None:
            raise ValueError("edit_file requires content")
        # Atomic-Hermes style: snapshot before overwrite
        snap = None
        try:
            from .time_travel import FileTimeTravel

            snap = FileTimeTravel().snapshot(path, note="pre-edit_file proposal")
        except Exception:
            pass
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(content), encoding="utf-8")
        return {
            "path": str(path),
            "bytes": len(str(content).encode("utf-8")),
            "time_travel_snapshot": snap,
        }

    def _exec_web_search_stub(self, args: Dict[str, Any]) -> Dict[str, Any]:
        # Real search providers plugged in Track I; keep structured stub
        q = args.get("query", "")
        return {
            "query": q,
            "results": [],
            "message": "web_search executor placeholder — wire Tavily/Brave in Track I",
        }
