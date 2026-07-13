"""
Cost / token budget guards (S4).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


class BudgetGuard:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "budget.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return {
            "daily_usd_limit": 5.0,
            "run_usd_limit": 1.0,
            "daily_token_limit": 500_000,
            "spent_usd_today": 0.0,
            "tokens_today": 0,
            "day": time.strftime("%Y-%m-%d"),
        }

    def save(self) -> None:
        self.path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def _roll_day(self) -> None:
        today = time.strftime("%Y-%m-%d")
        if self.state.get("day") != today:
            self.state["day"] = today
            self.state["spent_usd_today"] = 0.0
            self.state["tokens_today"] = 0

    def configure(
        self,
        daily_usd: Optional[float] = None,
        run_usd: Optional[float] = None,
        daily_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        if daily_usd is not None:
            self.state["daily_usd_limit"] = float(daily_usd)
        if run_usd is not None:
            self.state["run_usd_limit"] = float(run_usd)
        if daily_tokens is not None:
            self.state["daily_token_limit"] = int(daily_tokens)
        self.save()
        return self.snapshot()

    def snapshot(self) -> Dict[str, Any]:
        self._roll_day()
        return dict(self.state)

    def check_can_spend(self, estimated_usd: float = 0.0, tokens: int = 0) -> None:
        self._roll_day()
        if estimated_usd > float(self.state.get("run_usd_limit") or 1e9):
            raise RuntimeError(
                f"Run budget exceeded: estimate ${estimated_usd:.4f} > "
                f"run limit ${self.state['run_usd_limit']}"
            )
        if (
            float(self.state.get("spent_usd_today") or 0) + estimated_usd
            > float(self.state.get("daily_usd_limit") or 1e9)
        ):
            raise RuntimeError(
                f"Daily USD budget would be exceeded "
                f"(spent {self.state['spent_usd_today']}, limit {self.state['daily_usd_limit']})"
            )
        if (
            int(self.state.get("tokens_today") or 0) + tokens
            > int(self.state.get("daily_token_limit") or 10**12)
        ):
            raise RuntimeError("Daily token budget would be exceeded")

    def record(self, usd: float = 0.0, tokens: int = 0) -> None:
        self._roll_day()
        self.state["spent_usd_today"] = float(self.state.get("spent_usd_today") or 0) + float(usd)
        self.state["tokens_today"] = int(self.state.get("tokens_today") or 0) + int(tokens)
        self.save()
