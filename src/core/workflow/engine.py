import yaml
import logging
from typing import Dict, Any

from .gates import DiffAwareGate

logger = logging.getLogger(__name__)

class WorkflowEngine:
    """
    Deterministic YAML Workflow Engine for agent execution.
    Parses a YAML workflow definition (e.g. plan -> implement -> validate -> review)
    and executes it deterministically.
    """
    def __init__(self, workflow_path: str):
        self.workflow_path = workflow_path
        self.workflow_def = self._load_workflow()
        self.current_step_index = 0
        
        # Pre-register quality gates
        self.gates = {
            "diff_aware": DiffAwareGate()
        }

    def _load_workflow(self) -> Dict[str, Any]:
        """Loads and parses the YAML workflow definition."""
        try:
            with open(self.workflow_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load YAML workflow from {self.workflow_path}: {e}")
            return {"steps": []}

    def execute(self, context: Dict[str, Any] = None) -> bool:
        """
        Executes the workflow deterministically. 
        Each step must complete before moving to the next.
        """
        if context is None:
            context = {}

        steps = self.workflow_def.get('steps', [])
        if not steps:
            logger.error("No steps defined in the workflow.")
            return False

        logger.info(f"Starting deterministic workflow execution: {len(steps)} steps.")

        for i in range(self.current_step_index, len(steps)):
            step = steps[i]
            step_name = step.get('name', f'step_{i}')
            action = step.get('action')
            gate_name = step.get('gate')

            logger.info(f"Executing step [{step_name}] with action '{action}'")
            
            # Step execution (Deterministic phase)
            success = self._execute_action(action, context)
            if not success:
                logger.error(f"Action '{action}' failed at step '{step_name}'. Halting workflow.")
                return False

            # Quality Gate validation (Guard phase)
            if gate_name:
                gate = self.gates.get(gate_name)
                if gate:
                    logger.info(f"Running quality gate: {gate_name}")
                    if not gate.validate(context):
                        logger.error(f"Quality gate '{gate_name}' failed at step '{step_name}'. Halting workflow.")
                        return False
                else:
                    logger.warning(f"Warning: Quality gate '{gate_name}' not registered.")

            self.current_step_index += 1

        logger.info("Workflow execution completed successfully.")
        return True

    def _execute_action(self, action: str, context: Dict[str, Any]) -> bool:
        """
        Executes the requested action deterministically.
        In a full implementation, this maps to specific agent tasks or API calls.
        """
        if not action:
            return True
            
        logger.info(f"Deterministic dispatch for action: {action}")
        # Placeholder for specific action-to-function routing
        # E.g. if action == 'generate_plan': return run_planner()
        
        return True
