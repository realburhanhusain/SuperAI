"""
Persistent model/provider blacklist (Future Plan G4).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class ModelBlacklist:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(
            path or (Path.home() / ".superai" / "model_blacklist.json")
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return {"models": {}, "providers": {}, "auto_threshold": 5}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def is_model_blocked(self, name: str) -> bool:
        entry = (self.data.get("models") or {}).get(name)
        if not entry:
            return False
        until = entry.get("until")
        if until and time.time() > float(until):
            return False
        return bool(entry.get("blocked", True))

    def is_provider_blocked(self, provider: str) -> bool:
        entry = (self.data.get("providers") or {}).get(provider)
        if not entry:
            return False
        until = entry.get("until")
        if until and time.time() > float(until):
            return False
        return bool(entry.get("blocked", True))

    def block_model(self, name: str, reason: str = "", hours: Optional[float] = None) -> None:
        until = time.time() + hours * 3600 if hours else None
        self.data.setdefault("models", {})[name] = {
            "blocked": True,
            "reason": reason,
            "until": until,
            "ts": time.time(),
        }
        self.save()

    def unblock_model(self, name: str) -> bool:
        if name in (self.data.get("models") or {}):
            del self.data["models"][name]
            self.save()
            return True
        return False

    def record_failure(self, model: str, provider: Optional[str] = None) -> Optional[str]:
        """
        Count failures; auto-blacklist model after threshold.
        Returns model name if newly blacklisted.
        """
        models = self.data.setdefault("models", {})
        entry = models.setdefault(model, {"fail_count": 0, "blocked": False})
        entry["fail_count"] = int(entry.get("fail_count") or 0) + 1
        entry["last_fail"] = time.time()
        thr = int(self.data.get("auto_threshold") or 5)
        newly = None
        if entry["fail_count"] >= thr and not entry.get("blocked"):
            entry["blocked"] = True
            entry["reason"] = f"auto: {entry['fail_count']} failures"
            entry["until"] = time.time() + 24 * 3600
            newly = model
        if provider:
            pe = self.data.setdefault("providers", {}).setdefault(
                provider, {"fail_count": 0, "blocked": False}
            )
            pe["fail_count"] = int(pe.get("fail_count") or 0) + 1
        self.save()
        return newly

    def record_success(self, model: str) -> None:
        models = self.data.setdefault("models", {})
        entry = models.get(model)
        if not entry:
            return
        entry["fail_count"] = max(0, int(entry.get("fail_count") or 0) - 1)
        self.save()

    def list_blocked(self) -> Dict[str, Any]:
        return {
            "models": {
                k: v
                for k, v in (self.data.get("models") or {}).items()
                if v.get("blocked") and self.is_model_blocked(k)
            },
            "providers": {
                k: v
                for k, v in (self.data.get("providers") or {}).items()
                if v.get("blocked") and self.is_provider_blocked(k)
            },
            "auto_threshold": self.data.get("auto_threshold"),
        }
