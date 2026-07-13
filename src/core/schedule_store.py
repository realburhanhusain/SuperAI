"""
Scheduled tasks store (N10) — local schedule definitions.
Execution is via superai schedule run-due (manual or external cron).
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class ScheduleStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "schedules.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return {"jobs": []}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def add(
        self,
        name: str,
        command: str,
        every_hours: float = 24.0,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        job = {
            "id": uuid.uuid4().hex[:10],
            "name": name,
            "command": command,  # e.g. "backup" | "doctor" | "run:task text"
            "every_hours": float(every_hours),
            "enabled": enabled,
            "last_run": None,
            "next_run": time.time(),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self.data.setdefault("jobs", []).append(job)
        self.save()
        return job

    def list_jobs(self) -> List[Dict[str, Any]]:
        return list(self.data.get("jobs") or [])

    def due(self) -> List[Dict[str, Any]]:
        now = time.time()
        return [
            j
            for j in self.list_jobs()
            if j.get("enabled") and float(j.get("next_run") or 0) <= now
        ]

    def mark_run(self, job_id: str) -> None:
        for j in self.data.get("jobs") or []:
            if j.get("id") == job_id:
                j["last_run"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                j["next_run"] = time.time() + float(j.get("every_hours") or 24) * 3600
                self.save()
                return

    def run_due(self) -> List[Dict[str, Any]]:
        """Execute due jobs with built-in handlers."""
        results = []
        for j in self.due():
            cmd = str(j.get("command") or "")
            outcome: Dict[str, Any] = {"job": j.get("id"), "command": cmd}
            try:
                if cmd == "backup":
                    from .backup_manager import BackupManager

                    path = BackupManager().create_backup(incremental=True, quiet=True)
                    outcome["result"] = path or "no-changes"
                elif cmd == "doctor":
                    from .doctor import run_doctor

                    outcome["result"] = run_doctor(quick=True).get("ok")
                elif cmd.startswith("run:"):
                    from .orchestrator import SuperAIOrchestrator

                    task = cmd[4:].strip()
                    r = SuperAIOrchestrator().run_task(task)
                    outcome["result"] = r.get("status")
                else:
                    outcome["result"] = f"unknown command: {cmd}"
                    outcome["ok"] = False
                outcome["ok"] = outcome.get("ok", True)
            except Exception as e:  # noqa: BLE001
                outcome["ok"] = False
                outcome["error"] = str(e)
            self.mark_run(j["id"])
            results.append(outcome)
        return results
