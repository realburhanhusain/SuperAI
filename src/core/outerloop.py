import time
import logging
import enum
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)

class OuterloopState(enum.Enum):
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

class ExecutionCheckpoint:
    def __init__(self, state_data: dict):
        self.state_data = state_data
        self.timestamp = time.time()

class BoundedOuterloop:
    """
    A rigorous outerloop mechanic that handles infinite task processing with
    bounded retry logic, pausing, resuming, and explicit fallback checkpoints
    in a tightly controlled sandbox.
    """
    def __init__(
        self,
        task_processor: Callable[..., Any],
        max_retries: int = 3,
        pause_duration: float = 1.0,
        checkpoint_interval: int = 10,
    ):
        self.task_processor = task_processor
        self.max_retries = max_retries
        self.pause_duration = pause_duration
        self.checkpoint_interval = checkpoint_interval
        
        self.state = OuterloopState.STOPPED
        self.current_retry = 0
        self.tasks_processed = 0
        self.last_checkpoint: Optional[ExecutionCheckpoint] = None
        self._sandbox_data = {}

    def start(self, initial_data: dict = None):
        self.state = OuterloopState.RUNNING
        self._sandbox_data = initial_data or {}
        logger.info("Outerloop started.")
        self._run_loop()

    def pause(self):
        self.state = OuterloopState.PAUSED
        logger.info("Outerloop paused.")

    def resume(self):
        if self.state == OuterloopState.PAUSED:
            self.state = OuterloopState.RUNNING
            logger.info("Outerloop resumed.")
            self._run_loop()

    def stop(self):
        self.state = OuterloopState.STOPPED
        logger.info("Outerloop stopped.")

    def _save_checkpoint(self):
        self.last_checkpoint = ExecutionCheckpoint(self._sandbox_data.copy())

    def _rollback_to_checkpoint(self):
        if self.last_checkpoint:
            self._sandbox_data = self.last_checkpoint.state_data.copy()

    def _run_loop(self):
        while self.state == OuterloopState.RUNNING:
            try:
                if self.tasks_processed > 0 and self.tasks_processed % self.checkpoint_interval == 0:
                    self._save_checkpoint()
                self.task_processor(self._sandbox_data)
                self.tasks_processed += 1
                self.current_retry = 0
                time.sleep(self.pause_duration)
            except Exception as e:
                logger.error(f"Task processing failed: {e}")
                self.current_retry += 1
                if self.current_retry > self.max_retries:
                    self._rollback_to_checkpoint()
                    self.state = OuterloopState.ERROR
                    break
                else:
                    time.sleep(self.pause_duration * (2 ** self.current_retry))
