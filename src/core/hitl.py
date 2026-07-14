"""
Human-in-the-loop: clarification requests + veto (Future Plan G11).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class HITLStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "hitl.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return {"clarifications": [], "vetoes": []}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def request_clarification(
        self,
        task_id: str,
        question: str,
        context: str = "",
        *,
        kind: str = "clarification",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        entry = {
            "id": f"cl-{int(time.time()*1000)}",
            "task_id": task_id,
            "question": question,
            "context": context,
            "kind": kind,
            "payload": payload or {},
            "status": "open",
            "answer": None,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self.data.setdefault("clarifications", []).append(entry)
        self.save()
        return entry

    def answer_clarification(self, clar_id: str, answer: str) -> Optional[Dict[str, Any]]:
        for c in self.data.get("clarifications") or []:
            if c.get("id") == clar_id:
                c["answer"] = answer
                c["status"] = "answered"
                c["answered_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                # Normalize replan decisions
                if (c.get("kind") or "") == "replan_approval":
                    c["decision"] = self._parse_yes_no(answer)
                self.save()
                return c
        return None

    @staticmethod
    def _parse_yes_no(answer: str) -> str:
        a = (answer or "").strip().lower()
        if a in {"y", "yes", "approve", "approved", "ok", "true", "1", "go", "accept"}:
            return "approved"
        if a in {"n", "no", "reject", "rejected", "deny", "false", "0", "cancel"}:
            return "rejected"
        # free text containing keywords
        if "approv" in a or a.startswith("yes"):
            return "approved"
        if "reject" in a or a.startswith("no"):
            return "rejected"
        return "unknown"

    def request_replan_approval(
        self,
        task_id: str,
        steps_summary: List[Dict[str, Any]],
        reason: str = "",
    ) -> Dict[str, Any]:
        """Ask human to approve a recovery replan (opt-in orchestration)."""
        lines = [
            f"{i + 1}. {s.get('description') or s.get('step_id')}"
            for i, s in enumerate(steps_summary[:12])
        ]
        question = (
            "Approve SuperAI recovery replan? "
            "Answer: approve | reject\n"
            + ("\n".join(lines) if lines else "(empty plan)")
        )
        return self.request_clarification(
            task_id,
            question,
            context=reason[:2000],
            kind="replan_approval",
            payload={"steps": steps_summary, "reason": reason},
        )

    def replan_decision(
        self, task_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Latest replan_approval for task.
        Returns None if none; else clarification dict with decision if answered.
        """
        items = [
            c
            for c in (self.data.get("clarifications") or [])
            if c.get("task_id") == task_id
            and (c.get("kind") or "") == "replan_approval"
        ]
        if not items:
            return None
        # most recent
        items.sort(key=lambda c: c.get("ts") or "")
        latest = items[-1]
        if latest.get("status") == "answered" and not latest.get("decision"):
            latest["decision"] = self._parse_yes_no(str(latest.get("answer") or ""))
        return latest

    def veto(self, task_id: str, reason: str = "") -> Dict[str, Any]:
        entry = {
            "task_id": task_id,
            "reason": reason,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self.data.setdefault("vetoes", []).append(entry)
        # also mark open clarifications cancelled
        for c in self.data.get("clarifications") or []:
            if c.get("task_id") == task_id and c.get("status") == "open":
                c["status"] = "vetoed"
        self.save()
        return entry

    def is_vetoed(self, task_id: str) -> bool:
        return any(v.get("task_id") == task_id for v in (self.data.get("vetoes") or []))

    def open_clarifications(self, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
        out = []
        for c in self.data.get("clarifications") or []:
            if c.get("status") != "open":
                continue
            if task_id and c.get("task_id") != task_id:
                continue
            out.append(c)
        return out

    def list_all(self) -> Dict[str, Any]:
        return {
            "clarifications": list(self.data.get("clarifications") or [])[-20:],
            "vetoes": list(self.data.get("vetoes") or [])[-20:],
        }
