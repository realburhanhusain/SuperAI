class QuotaExceededError(Exception):
    """Exception raised when an agent exceeds its budget."""
    pass

class QuotaManager:
    """Manages budgets and tracks spending for agents."""
    def __init__(self):
        self.budgets = {}  # agent_id -> budget
        self.spend = {}    # agent_id -> spend

    def set_budget(self, agent_id: str, budget: float):
        """Sets the budget for a specific agent."""
        self.budgets[agent_id] = budget
        if agent_id not in self.spend:
            self.spend[agent_id] = 0.0

    def get_budget(self, agent_id: str) -> float:
        """Returns the budget for a specific agent."""
        return self.budgets.get(agent_id, 0.0)

    def get_spend(self, agent_id: str) -> float:
        """Returns the current spend for a specific agent."""
        return self.spend.get(agent_id, 0.0)

    def record_spend(self, agent_id: str, amount: float):
        """Records spend for an agent and raises an exception if the budget is exceeded."""
        if agent_id not in self.budgets:
            raise ValueError(f"No budget set for agent {agent_id}")

        new_spend = self.spend.get(agent_id, 0.0) + amount
        if new_spend > self.budgets[agent_id]:
            raise QuotaExceededError(f"Quota exceeded for agent {agent_id}. Budget: {self.budgets[agent_id]}, Attempted spend: {new_spend}")

        self.spend[agent_id] = new_spend
