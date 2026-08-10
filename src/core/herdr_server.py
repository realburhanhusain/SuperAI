import asyncio
import logging
from typing import Dict, Any
from .fleet_goals import FleetAccountabilityRegistry

logger = logging.getLogger(__name__)

class HerdrBackgroundServer:
    def __init__(self):
        self.terminals = {}
        self.registry = FleetAccountabilityRegistry()

    async def start(self):
        logger.info("Starting Herdr background server for persistent agent terminals...")
        while True:
            # Persistent loop to keep agent terminals alive
            await self.manage_fleet()
            await asyncio.sleep(5)

    async def manage_fleet(self):
        # Health check on agent terminals
        for agent_id, terminal in self.terminals.items():
            if not terminal.is_alive():
                logger.warning(f"Terminal for agent {agent_id} died, restarting...")
                await terminal.restart()

    def register_terminal(self, agent_id: str, terminal_instance):
        self.terminals[agent_id] = terminal_instance
        logger.info(f"Registered persistent terminal for agent {agent_id}")

    def handle_goal_command(self, agent_id: str, goal: str, parameters: Dict[str, Any]):
        # Assign a /goal objective
        self.registry.assign_goal(agent_id, goal, parameters)
        logger.info(f"Assigned /goal to {agent_id} via Herdr server")

if __name__ == "__main__":
    server = HerdrBackgroundServer()
    asyncio.run(server.start())
