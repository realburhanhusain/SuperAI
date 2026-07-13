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

    def update(self, model: str, reward: float) -> None:
        arm = self._arm(model)
        arm["n"] += 1
        arm["reward_sum"] += float(reward)
        arm["updated_at"] = time.time()
        self.save()

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
