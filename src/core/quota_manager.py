import json
from pathlib import Path
from typing import Dict, Any
from filelock import FileLock

class QuotaExceededError(Exception):
    """Exception raised when an agent exceeds its budget."""
    pass

class QuotaManager:
    """Manages budgets and tracks spending for agents with persistent storage."""
    
    def __init__(self, storage_path: str = None):
        if storage_path:
            self.path = Path(storage_path)
        else:
            self.path = Path.home() / ".superai" / "config" / "agent_quotas.json"
        
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(self.path) + ".lock")
        self._load()

    def _load(self):
        self.data = {"budgets": {}, "spend": {}}
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        self.data = json.loads(content)
                        self.data.setdefault("budgets", {})
                        self.data.setdefault("spend", {})
            except (json.JSONDecodeError, IOError):
                pass

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def set_budget(self, agent_id: str, budget: float):
        """Sets the budget for a specific agent."""
        with self.lock:
            self._load()
            self.data["budgets"][agent_id] = float(budget)
            if agent_id not in self.data["spend"]:
                self.data["spend"][agent_id] = 0.0
            self._save()

    def get_budget(self, agent_id: str) -> float:
        """Returns the budget for a specific agent."""
        with self.lock:
            self._load()
            return float(self.data["budgets"].get(agent_id, 0.0))

    def get_spend(self, agent_id: str) -> float:
        """Returns the current spend for a specific agent."""
        with self.lock:
            self._load()
            return float(self.data["spend"].get(agent_id, 0.0))

    def record_spend(self, agent_id: str, amount: float):
        """Records spend for an agent and raises an exception if the budget is exceeded."""
        with self.lock:
            self._load()
            if agent_id not in self.data["budgets"]:
                # If no budget is set, assume unlimited or just don't crash
                budget = float('inf')
            else:
                budget = float(self.data["budgets"][agent_id])

            new_spend = float(self.data["spend"].get(agent_id, 0.0)) + float(amount)
            if new_spend > budget:
                raise QuotaExceededError(f"Quota exceeded for agent {agent_id}. Budget: ${budget:.4f}, Attempted spend: ${new_spend:.4f}")

            self.data["spend"][agent_id] = new_spend
            self._save()
