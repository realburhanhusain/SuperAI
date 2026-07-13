"""
User preference & modeling subsystem (OpenClaw-inspired, Track J).

Learns from:
- Explicit set/get preferences
- Implicit signals from task history (task types, models used, success)

Stored at ~/.superai/preferences.json
"""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional


class UserPreferenceModel:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "preferences.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    return raw
            except Exception:
                pass
        return {
            "explicit": {},
            "signals": {
                "task_types": {},
                "models": {},
                "successes": 0,
                "failures": 0,
            },
            "updated_at": None,
        }

    def save(self) -> None:
        self.data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    # --- explicit preferences ---
    def set(self, key: str, value: Any) -> None:
        self.data.setdefault("explicit", {})[key] = value
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get("explicit", {}).get(key, default)

    def delete(self, key: str) -> bool:
        ex = self.data.setdefault("explicit", {})
        if key in ex:
            del ex[key]
            self.save()
            return True
        return False

    def all_explicit(self) -> Dict[str, Any]:
        return dict(self.data.get("explicit") or {})

    # --- implicit learning ---
    def observe_task(
        self,
        task_type: str,
        model: str,
        success: bool,
        duration: float = 0.0,
    ) -> None:
        sig = self.data.setdefault(
            "signals",
            {"task_types": {}, "models": {}, "successes": 0, "failures": 0},
        )
        tt = sig.setdefault("task_types", {})
        tt[task_type] = int(tt.get(task_type) or 0) + 1
        models = sig.setdefault("models", {})
        m = models.setdefault(model, {"uses": 0, "successes": 0, "total_duration": 0.0})
        m["uses"] = int(m.get("uses") or 0) + 1
        m["total_duration"] = float(m.get("total_duration") or 0) + float(duration)
        if success:
            m["successes"] = int(m.get("successes") or 0) + 1
            sig["successes"] = int(sig.get("successes") or 0) + 1
        else:
            sig["failures"] = int(sig.get("failures") or 0) + 1
        self.save()

    def preferred_model_for(self, task_type: Optional[str] = None) -> Optional[str]:
        """Explicit preferred_model wins; else best success rate from signals."""
        explicit = self.get("preferred_model")
        if explicit:
            return str(explicit)
        models = (self.data.get("signals") or {}).get("models") or {}
        best = None
        best_score = -1.0
        for name, stats in models.items():
            uses = int(stats.get("uses") or 0)
            if uses < 1:
                continue
            rate = int(stats.get("successes") or 0) / uses
            # slight preference for more data
            score = rate + min(0.05, uses * 0.005)
            if score > best_score:
                best_score = score
                best = name
        return best

    def preferred_strategy(self) -> Optional[str]:
        return self.get("preferred_strategy") or self.get("load_balancing_strategy")

    def profile_summary(self) -> Dict[str, Any]:
        sig = self.data.get("signals") or {}
        models = sig.get("models") or {}
        ranked = sorted(
            (
                (
                    name,
                    {
                        "uses": s.get("uses"),
                        "success_rate": round(
                            int(s.get("successes") or 0) / max(1, int(s.get("uses") or 1)),
                            3,
                        ),
                    },
                )
                for name, s in models.items()
            ),
            key=lambda x: (x[1]["success_rate"], x[1]["uses"]),
            reverse=True,
        )
        return {
            "explicit": self.all_explicit(),
            "top_models": ranked[:8],
            "task_types": sig.get("task_types") or {},
            "successes": sig.get("successes") or 0,
            "failures": sig.get("failures") or 0,
            "inferred_preferred_model": self.preferred_model_for(),
            "updated_at": self.data.get("updated_at"),
        }

    def apply_to_config_defaults(self, config) -> None:
        """Non-destructive: fill config defaults from preferences when unset."""
        if not config.get("default_supervisor") and not config.get("default_model"):
            pm = self.preferred_model_for()
            if pm:
                config.set("default_model", pm, persist=False)
        if config.get("load_balancing_strategy") == "smart_fallback":
            ps = self.preferred_strategy()
            if ps and ps != "smart_fallback":
                config.set("load_balancing_strategy", ps, persist=False)
