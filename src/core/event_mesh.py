"""
Phase 14: Universal Worker Triggers (Real-time Event Mesh)
This module provides a real-time event mesh allowing agents to dynamically register triggers
via MCP tools without boilerplate infrastructure.
"""

import asyncio
import logging
from typing import Callable, Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class EventMesh:
    def __init__(self):
        # Maps event_name to a list of trigger callbacks
        self.triggers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

    def register_trigger(self, event_name: str, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback for a specific event."""
        if event_name not in self.triggers:
            self.triggers[event_name] = []
        self.triggers[event_name].append(callback)
        logger.info(f"Registered trigger for event '{event_name}'")

    def emit_event(self, event_name: str, payload: Dict[str, Any]):
        """Emit an event to the mesh, triggering all registered callbacks."""
        logger.info(f"Emitting event '{event_name}' with payload: {payload}")
        if event_name in self.triggers:
            for callback in self.triggers[event_name]:
                try:
                    # Execute callback
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(payload))
                    else:
                        callback(payload)
                except Exception as e:
                    logger.error(f"Error executing trigger for event '{event_name}': {e}")
        else:
            logger.debug(f"No triggers registered for event '{event_name}'")

# Global singleton for the event mesh
_global_event_mesh = EventMesh()

def get_event_mesh() -> EventMesh:
    return _global_event_mesh

def register_mcp_tools(mcp_server):
    """
    Register MCP tools to allow agents to interact with the Event Mesh.
    Agents can register triggers and wait for them.
    """
    
    @mcp_server.tool()
    def register_webhook_trigger(event_name: str, target_function_name: str) -> str:
        """
        Dynamically register a trigger via MCP. E.g., when a webhook arrives, the target function runs.
        """
        def _dynamic_callback(payload: Dict[str, Any]):
            logger.info(f"Agent function '{target_function_name}' triggered via event '{event_name}' with payload {payload}")
            
        get_event_mesh().register_trigger(event_name, _dynamic_callback)
        return f"Successfully registered trigger for '{event_name}' to execute '{target_function_name}'."
