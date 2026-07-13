"""
Fine-grained tool permissions per skill (N24).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class SkillPermissions:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "skill_permissions.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return {"skills": {}}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def set_tools(self, skill: str, tools: List[str]) -> None:
        self.data.setdefault("skills", {})[skill] = {"allow": list(tools)}
        self.save()

    def allowed(self, skill: str, tool: str) -> bool:
        entry = (self.data.get("skills") or {}).get(skill)
        if not entry:
            return True  # default allow if unset
        allow = set(entry.get("allow") or [])
        return tool in allow or "*" in allow

    def list_all(self) -> Dict[str, Any]:
        return dict(self.data.get("skills") or {})
