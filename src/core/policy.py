"""
Lightweight policy engine (N4).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_RULES = [
    {
        "id": "no_shell_meta",
        "description": "Block powershell/cmd/bash unless SUPERAI_ALLOW_SHELL_META=1",
        "enabled": True,
    },
    {
        "id": "workspace_jail",
        "description": "File edits must stay under SUPERAI_WORKSPACE",
        "enabled": True,
    },
    {
        "id": "require_approval_file_cli",
        "description": "File-modifying external CLIs need approval",
        "enabled": True,
    },
    {
        "id": "no_cloud_without_keys",
        "description": "Refuse live mode when no provider keys present",
        "enabled": False,
    },
]


class PolicyEngine:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "policy.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.rules = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and isinstance(data.get("rules"), list):
                    return data["rules"]
            except (OSError, json.JSONDecodeError):
                pass
        self.save(DEFAULT_RULES)
        return list(DEFAULT_RULES)

    def save(self, rules: Optional[List[Dict[str, Any]]] = None) -> None:
        if rules is not None:
            self.rules = rules
        self.path.write_text(
            json.dumps({"rules": self.rules}, indent=2), encoding="utf-8"
        )

    def list_rules(self) -> List[Dict[str, Any]]:
        return list(self.rules)

    def set_enabled(self, rule_id: str, enabled: bool) -> bool:
        for r in self.rules:
            if r.get("id") == rule_id:
                r["enabled"] = bool(enabled)
                self.save()
                return True
        return False

    def is_enabled(self, rule_id: str) -> bool:
        for r in self.rules:
            if r.get("id") == rule_id:
                return bool(r.get("enabled"))
        return False

    def check_live_mode_allowed(self, mock_mode: bool, has_keys: bool) -> Optional[str]:
        if mock_mode:
            return None
        if self.is_enabled("no_cloud_without_keys") and not has_keys:
            return "Policy no_cloud_without_keys: refuse live mode without API keys"
        return None
