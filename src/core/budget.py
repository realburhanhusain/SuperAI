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
        decision = self.can_spend(estimated_usd=estimated_usd, tokens=tokens)
        if not decision.get("ok"):
            raise RuntimeError(decision.get("error") or "budget_exceeded")

    def can_spend(
        self, estimated_usd: float = 0.0, tokens: int = 0
    ) -> Dict[str, Any]:
        """
        V4 M1: soft budget check (no exception) for all spend paths.
        """
        self._roll_day()
        snap = self.snapshot()
        run_lim = float(self.state.get("run_usd_limit") or 1e9)
        day_lim = float(self.state.get("daily_usd_limit") or 1e9)
        tok_lim = int(self.state.get("daily_token_limit") or 10**12)
        spent = float(self.state.get("spent_usd_today") or 0)
        toks = int(self.state.get("tokens_today") or 0)
        if estimated_usd > run_lim:
            return {
                "ok": False,
                "error": (
                    f"Run budget exceeded: estimate ${estimated_usd:.4f} > "
                    f"run limit ${run_lim}"
                ),
                "code": "run_budget",
                "snapshot": snap,
            }
        if spent + estimated_usd > day_lim:
            return {
                "ok": False,
                "error": (
                    f"Daily USD budget would be exceeded "
                    f"(spent {spent}, limit {day_lim})"
                ),
                "code": "daily_usd",
                "snapshot": snap,
            }
        if toks + int(tokens or 0) > tok_lim:
            return {
                "ok": False,
                "error": "Daily token budget would be exceeded",
                "code": "daily_tokens",
                "snapshot": snap,
            }
        return {"ok": True, "snapshot": snap, "estimated_usd": estimated_usd}

    def record(self, usd: float = 0.0, tokens: int = 0) -> None:
        self._roll_day()
        self.state["spent_usd_today"] = float(self.state.get("spent_usd_today") or 0) + float(usd)
        self.state["tokens_today"] = int(self.state.get("tokens_today") or 0) + int(tokens)
        self.save()

    def enforce_or_block(
        self,
        estimated_usd: float = 0.0,
        tokens: int = 0,
        *,
        enforce: bool = True,
    ) -> Dict[str, Any]:
        """Return block envelope if over budget and enforce=True."""
        d = self.can_spend(estimated_usd=estimated_usd, tokens=tokens)
        if d.get("ok") or not enforce:
            d["blocked"] = False
            d["enforced"] = enforce
            return d
        from .result_contract import apply_contract

        return apply_contract(
            {
                "ok": False,
                "status": "error",
                "error": d.get("error"),
                "budget": d,
                "blocked": True,
                "enforced": True,
            },
            mock=False,
            dry_run=False,
            ok=False,
        )
