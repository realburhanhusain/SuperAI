"""
Model version pinning (Future Plan G9).

Pins map logical model names → concrete model_id / provider overrides.
Stored in ~/.superai/model_pins.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


class ModelPinStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "model_pins.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.pins: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except (OSError, json.JSONDecodeError):
                pass
        return {}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.pins, indent=2), encoding="utf-8")

    def pin(
        self,
        name: str,
        model_id: Optional[str] = None,
        provider: Optional[str] = None,
        note: str = "",
    ) -> Dict[str, Any]:
        entry = {
            "model_id": model_id,
            "provider": provider,
            "note": note,
        }
        self.pins[name] = {k: v for k, v in entry.items() if v is not None and v != ""}
        self.save()
        return self.pins[name]

    def unpin(self, name: str) -> bool:
        if name in self.pins:
            del self.pins[name]
            self.save()
            return True
        return False

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        return self.pins.get(name)

    def list_pins(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.pins)

    def apply_to_registry(self, registry: Any) -> int:
        """Apply pins onto ModelRegistry in-memory models. Returns count applied."""
        n = 0
        for name, pin in self.pins.items():
            model = registry.get_model(name)
            if not model:
                continue
            if pin.get("model_id"):
                model.model_id = pin["model_id"]
            if pin.get("provider"):
                model.provider = pin["provider"]
            n += 1
        return n
