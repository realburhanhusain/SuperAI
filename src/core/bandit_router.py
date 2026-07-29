"""
Contextual bandit foundation for routing (Phase 7 / H6).

Epsilon-greedy over models using reward from outcomes.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class EpsilonGreedyBandit:
    def __init__(
        self,
        epsilon: float = 0.1,
        path: Optional[Path] = None,
    ):
        self.epsilon = epsilon
        self.path = Path(path or (Path.home() / ".superai" / "bandit_state.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state: Dict[str, Dict[str, float]] = self._load()

    def _load(self) -> Dict[str, Dict[str, float]]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def save(self) -> None:
        """Atomic multi-process-safe write (store_lock + tmp replace)."""
        try:
            from .store_lock import atomic_write_json, store_lock

            root = self.path.parent
            with store_lock(root, name="bandit_state.lock", timeout=30.0):
                atomic_write_json(self.path, self.state)
        except Exception:
            self.path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def _arm(self, model: str) -> Dict[str, float]:
        if model not in self.state:
            self.state[model] = {"n": 0.0, "reward_sum": 0.0}
        return self.state[model]

    def select(self, candidates: List[str]) -> str:
        if not candidates:
            raise ValueError("No candidates")
        if random.random() < self.epsilon:
            return random.choice(candidates)
        best = None
        best_score = -1e9
        for m in candidates:
            arm = self._arm(m)
            n = arm["n"] or 1.0
            score = arm["reward_sum"] / n
            if score > best_score:
                best_score = score
                best = m
        return best or candidates[0]

    def update(self, model: str, reward: float, *, event_id: Optional[str] = None) -> bool:
        """Record one outcome; ignore a replayed event for the same model."""
        arm = self._arm(model)
        seen = list(arm.get("event_ids") or [])
        if event_id and event_id in seen:
            return False
        arm["n"] += 1
        arm["reward_sum"] += float(reward)
        arm["updated_at"] = time.time()
        if event_id:
            arm["event_ids"] = (seen + [event_id])[-100:]
        self.save()
        return True

    def reset(self) -> None:
        self.state = {}
        self.save()

    def mean(self, model: str) -> float:
        arm = self.state.get(model) or {}
        n = float(arm.get("n") or 0.0)
        if n <= 0:
            return 0.0
        return float(arm.get("reward_sum") or 0.0) / n

    def status(self) -> Dict[str, Any]:
        """Operator view: arms ranked by mean reward (M050 continuous product)."""
        arms: List[Dict[str, Any]] = []
        for name, arm in (self.state or {}).items():
            n = float(arm.get("n") or 0.0)
            rsum = float(arm.get("reward_sum") or 0.0)
            arms.append(
                {
                    "model": name,
                    "n": int(n),
                    "reward_sum": round(rsum, 4),
                    "mean_reward": round(rsum / n, 4) if n else 0.0,
                    "updated_at": arm.get("updated_at"),
                }
            )
        arms.sort(key=lambda a: (a["mean_reward"], a["n"]), reverse=True)
        return {
            "ok": True,
            "product": "bandit.status",
            "epsilon": self.epsilon,
            "arm_count": len(arms),
            "arms": arms,
            "path": str(self.path),
            "pipeline": "preferences.bias_candidates → bandit.select → call",
            "message": (
                f"{len(arms)} arm(s), epsilon={self.epsilon}"
                if arms
                else "No bandit arms yet — outcomes will train after model calls."
            ),
        }

    @staticmethod
    def reward_from_outcome(
        success: bool,
        latency: float = 1.0,
        cost: float = 0.0,
        user_satisfaction: float = 0.5,
    ) -> float:
        """Weighted reward: success, cost, latency, satisfaction."""
        s = 1.0 if success else 0.0
        lat = 1.0 / (1.0 + max(latency, 0.0))
        cost_s = 1.0 / (1.0 + max(cost, 0.0) * 100)
        return 0.5 * s + 0.2 * lat + 0.15 * cost_s + 0.15 * user_satisfaction


def route_candidates(
    candidates: List[str],
    *,
    apply_preferences: bool = True,
    apply_bandit: bool = True,
    epsilon: Optional[float] = None,
    bandit_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Shared routing pipeline: preferences first (M068), then bandit (M050).

    Returns ordered candidates + honesty about which stages ran.
    """
    ordered = [str(c) for c in (candidates or [])]
    stages: List[str] = []
    if not ordered:
        return {
            "ok": True,
            "candidates": [],
            "order": [],
            "stages": [],
            "pipeline": "preferences → bandit",
            "message": "No candidates",
        }
    if apply_preferences:
        try:
            from .preferences import UserPreferenceModel

            ordered = UserPreferenceModel().bias_candidates(ordered)
            stages.append("preferences.bias_candidates")
        except Exception as e:
            stages.append(f"preferences_skipped:{e!s}"[:80])
    pick = ordered[0] if ordered else None
    if apply_bandit and len(ordered) > 1:
        try:
            b = EpsilonGreedyBandit(
                epsilon=0.1 if epsilon is None else float(epsilon),
                path=bandit_path,
            )
            pick = b.select(list(ordered))
            if pick in ordered:
                ordered = [pick] + [m for m in ordered if m != pick]
            stages.append("bandit.select")
        except Exception as e:
            stages.append(f"bandit_skipped:{e!s}"[:80])
    return {
        "ok": True,
        "candidates": ordered,
        "order": ordered,
        "selected": ordered[0] if ordered else None,
        "stages": stages,
        "pipeline": "preferences → bandit",
        "product": "routing.route_candidates",
    }
