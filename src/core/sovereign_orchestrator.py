"""
Phase 11: The Sovereign Orchestrator (Business Layer)

This module implements the Sovereign Orchestrator which moves beyond coding tasks
to full "Company Goal" alignment. It acts as a high-level manager that translates
business goals into actionable technical tasks and routes them to appropriate agents.

References: paperclipai/paperclip, Conway-Research/automaton
"""

from typing import List, Dict, Any, Optional
import uuid
import time
from .logger import get_logger

logger = get_logger("superai.sovereign")

class SovereignOrchestrator:
    """
    High-level orchestrator for business goals.
    Translates a business goal into technical tasks and routes them to agents.
    """
    def __init__(self, agent_router=None, task_manager=None):
        self.agent_router = agent_router
        self.task_manager = task_manager
        self.active_goals: Dict[str, Dict[str, Any]] = {}

    def define_goal(self, goal_description: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Defines a new business goal and starts the breakdown process.
        Returns the goal ID.
        """
        goal_id = str(uuid.uuid4())
        logger.info(f"Defining new business goal [{goal_id}]: {goal_description}")
        
        self.active_goals[goal_id] = {
            "id": goal_id,
            "description": goal_description,
            "metadata": metadata or {},
            "status": "analyzing",
            "tasks": [],
            "created_at": time.time(),
        }
        
        # Simulated LLM breakdown
        tasks = self._breakdown_goal(goal_description)
        self.active_goals[goal_id]["tasks"] = tasks
        self.active_goals[goal_id]["status"] = "executing"
        
        self._route_tasks(goal_id, tasks)
        return goal_id

    def _breakdown_goal(self, goal: str) -> List[Dict[str, Any]]:
        """
        Translates a high-level business goal into technical tasks.
        """
        logger.info(f"Breaking down goal into technical tasks: {goal}")
        return [
            {"id": str(uuid.uuid4()), "title": "Setup infrastructure and database", "type": "infrastructure", "status": "pending"},
            {"id": str(uuid.uuid4()), "title": "Implement core backend APIs", "type": "backend", "status": "pending"},
            {"id": str(uuid.uuid4()), "title": "Develop frontend user interface", "type": "frontend", "status": "pending"},
            {"id": str(uuid.uuid4()), "title": "Deploy to production environment", "type": "devops", "status": "pending"}
        ]

    def _route_tasks(self, goal_id: str, tasks: List[Dict[str, Any]]):
        """
        Routes the generated technical tasks to the appropriate agents.
        """
        for task in tasks:
            logger.info(f"Routing task '{task['title']}' (Type: {task['type']})")
            
            if self.task_manager:
                self.task_manager.add_task(task)
                
            if self.agent_router:
                agent = self.agent_router.get_agent_for_task(task["type"])
                if agent:
                    logger.info(f"Assigned task {task['id']} to agent {agent.name}")
                    agent.assign(task)
                else:
                    logger.warning(f"No agent found for task type '{task['type']}'")

    def get_goal_status(self, goal_id: str) -> Optional[Dict[str, Any]]:
        return self.active_goals.get(goal_id)

    def ui_dashboard_data(self) -> List[Dict[str, Any]]:
        return list(self.active_goals.values())
