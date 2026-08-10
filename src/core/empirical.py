import subprocess
import logging
from typing import Callable

logger = logging.getLogger(__name__)

class EmpiricalAutoResearch:
    """
    Phase 13: The Overnight Evolution Loop (Empirical Auto-Research)
    The agent modifies the code, runs a strict benchmark, checks if the metric improved, 
    and auto-commits overnight.
    """
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir

    def run_benchmark(self) -> float:
        """Runs the strict benchmark and returns a metric (higher is better)."""
        logger.info("Running strict benchmark...")
        # Placeholder for actual benchmark logic, which would execute a test suite
        # and parse out a score (e.g., accuracy, speed, token usage reduction).
        return 0.85

    def check_metric_improvement(self, old_metric: float, new_metric: float) -> bool:
        """Checks if the new metric is strictly better than the old metric."""
        return new_metric > old_metric

    def auto_commit(self, message: str):
        """Auto-commits the changes overnight if the metric improved."""
        logger.info(f"Auto-committing improvements: {message}")
        subprocess.run(["git", "add", "."], cwd=self.workspace_dir, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=self.workspace_dir, check=True)

    def revert_changes(self):
        """Reverts the changes if the metric did not improve."""
        logger.info("Reverting changes due to no metric improvement.")
        subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=self.workspace_dir, check=True)
        subprocess.run(["git", "clean", "-fd"], cwd=self.workspace_dir, check=True)

    def run_overnight_loop(self, agent_modify_callback: Callable[[str], None]) -> bool:
        """
        The Overnight Evolution Loop:
        1. Evaluate current baseline.
        2. Let agent modify code.
        3. Evaluate new benchmark.
        4. If improved, commit. Else, revert.
        """
        logger.info("Starting Empirical Overnight Evolution Loop (empirical-mode)...")
        baseline = self.run_benchmark()
        logger.info(f"Baseline metric: {baseline}")
        
        logger.info("Applying agent code modifications...")
        agent_modify_callback(self.workspace_dir)
        
        new_metric = self.run_benchmark()
        logger.info(f"New metric: {new_metric}")
        
        if self.check_metric_improvement(baseline, new_metric):
            self.auto_commit(f"Empirical mode: Metric improved from {baseline} to {new_metric}")
            return True
        else:
            self.revert_changes()
            return False
