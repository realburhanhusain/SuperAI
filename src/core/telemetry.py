"""
Anonymous telemetry opt-in (N29).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


class Telemetry:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "telemetry.jsonl"))
        self.enabled_path = Path.home() / ".superai" / "telemetry_enabled"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def is_enabled(self) -> bool:
        return self.enabled_path.exists()

    def enable(self) -> None:
        self.enabled_path.write_text("1", encoding="utf-8")

    def disable(self) -> None:
        if self.enabled_path.exists():
            self.enabled_path.unlink()

    def event(self, name: str, props: Optional[Dict[str, Any]] = None) -> None:
        if not self.is_enabled():
            return
        # never log free-text task content
        safe = {k: v for k, v in (props or {}).items() if k in {
            "status", "task_type", "model", "duration", "success", "command"
        }}
        entry = {
            "ts": time.time(),
            "event": name,
            "props": safe,
            "version": "0.1.0",
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
