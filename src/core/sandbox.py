import subprocess
import uuid
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class EphemeralSandbox:
    """
    Manages ephemeral isolated containers (e.g., Docker/E2B) for agent shell command execution,
    preventing local host pollution.
    """
    def __init__(self, image: str = "ubuntu:latest"):
        self.image = image
        self.container_id = f"superai-sandbox-{uuid.uuid4().hex[:8]}"
        self._is_running = False

    def start(self):
        """Starts the isolated container sandbox."""
        logger.info(f"Starting ephemeral sandbox container {self.container_id}...")
        try:
            # We use Docker to spin up a sandboxed environment
            subprocess.run(
                ["docker", "run", "-d", "--name", self.container_id, "--entrypoint", "tail", self.image, "-f", "/dev/null"],
                check=True,
                capture_output=True
            )
            self._is_running = True
            logger.info("Sandbox started successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start sandbox: {e.stderr.decode()}")
            raise RuntimeError(f"Sandbox startup failed: {e}")

    def execute_command(self, command: str, timeout: Optional[int] = None) -> Tuple[int, str, str]:
        """
        Executes a shell command inside the ephemeral container.
        """
        if not self._is_running:
            raise RuntimeError("Sandbox is not running.")
        
        logger.info(f"Executing command in sandbox: {command}")
        
        # Execute using docker exec
        exec_cmd = ["docker", "exec", self.container_id, "sh", "-c", command]
        try:
            result = subprocess.run(
                exec_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.warning("Command execution timed out.")
            return -1, "", "Execution timed out."
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            return -1, "", str(e)

    def cleanup(self):
        """Destroys the container and cleans up resources."""
        if self._is_running:
            logger.info(f"Destroying ephemeral sandbox container {self.container_id}...")
            subprocess.run(
                ["docker", "rm", "-f", self.container_id],
                check=False,
                capture_output=True
            )
            self._is_running = False
            logger.info("Sandbox cleaned up.")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
