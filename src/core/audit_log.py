"""
Append-only audit log (S8).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .secrets import redact_obj


class AuditLog:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "audit.jsonl"))
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        action: str,
        detail: Optional[Dict[str, Any]] = None,
        actor: str = "cli",
        outcome: str = "ok",
    ) -> Dict[str, Any]:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "action": action,
            "actor": actor,
            "outcome": outcome,
            "detail": redact_obj(detail or {}),
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        return entry

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").strip().splitlines()
        out = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return list(reversed(out))
