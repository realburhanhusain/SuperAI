class TokenTracker:
    def __init__(self, spend_cap: float, cost_per_token: float = 0.0001):
        self.usage_per_agent = {}
        self.spend_cap = spend_cap
        self.cost_per_token = cost_per_token
        self.total_spend = 0.0

    def record_usage(self, agent_id: str, tokens: int):
        cost = tokens * self.cost_per_token
        if self.total_spend + cost > self.spend_cap:
            raise Exception(f"Spend cap of {self.spend_cap} exceeded. Cannot process request.")
        
        if agent_id not in self.usage_per_agent:
            self.usage_per_agent[agent_id] = 0
        self.usage_per_agent[agent_id] += tokens
        self.total_spend += cost

    def get_agent_usage(self, agent_id: str) -> int:
        return self.usage_per_agent.get(agent_id, 0)
    
    def get_total_spend(self) -> float:
        return self.total_spend
