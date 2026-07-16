"""
Accumulated workspace change-set (V4 S10) — apply / reject staged writes.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class ChangeSet:
    def __init__(self, change_id: Optional[str] = None):
        self.id = change_id or f"cs-{uuid.uuid4().hex[:8]}"
        self.created_at = time.time()
        self.files: Dict[str, Dict[str, Any]] = {}  # path -> {content, action}

    def stage_write(self, path: str, content: str) -> None:
        self.files[path] = {
            "action": "write",
            "content": content,
            "ts": time.time(),
        }

    def stage_delete(self, path: str) -> None:
        self.files[path] = {"action": "delete", "ts": time.time()}

    def clear(self) -> None:
        self.files.clear()

    def summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "count": len(self.files),
            "paths": list(self.files.keys()),
            "actions": {
                p: v.get("action") for p, v in self.files.items()
            },
        }

    def apply(self, *, dry_run: bool = False) -> Dict[str, Any]:
        from .agent_tools import tool_write
        from .workspace import workspace_root

        root = Path(workspace_root())
        applied = []
        errors = []
        for path, meta in self.files.items():
            try:
                if meta.get("action") == "write":
                    r = tool_write(path, str(meta.get("content") or ""), dry_run=dry_run)
                    applied.append({"path": path, "result": r})
                elif meta.get("action") == "delete":
                    p = (root / path).resolve()
                    if not str(p).startswith(str(root.resolve())):
                        raise PermissionError("path escape")
                    if dry_run:
                        applied.append({"path": path, "dry_run": True, "action": "delete"})
                    else:
                        if p.is_file():
                            p.unlink()
                        applied.append({"path": path, "deleted": True})
            except Exception as e:
                errors.append({"path": path, "error": str(e)[:200]})
        if not dry_run and not errors:
            self.clear()
        return {
            "ok": not errors,
            "dry_run": dry_run,
            "applied": applied,
            "errors": errors,
            "change_set": self.summary(),
        }

    def reject(self) -> Dict[str, Any]:
        n = len(self.files)
        self.clear()
        return {"ok": True, "rejected": n, "change_set": self.summary()}
