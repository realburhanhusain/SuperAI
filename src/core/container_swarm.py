import subprocess
import os
import uuid
import json

class ContainerSwarmCoordinator:
    """
    Coordinates deep agents across isolated Docker containers.
    Agents coordinate through a shared markdown workspace.
    """
    def __init__(self, workspace_path: str = "./workspace"):
        self.workspace_path = os.path.abspath(workspace_path)
        self.active_containers = {}
        os.makedirs(self.workspace_path, exist_ok=True)
        self._init_shared_workspace()

    def _init_shared_workspace(self):
        """Initializes the shared markdown workspace."""
        index_path = os.path.join(self.workspace_path, "index.md")
        if not os.path.exists(index_path):
            with open(index_path, "w") as f:
                f.write("# Container Swarm Shared Workspace\n\nAgents can communicate and coordinate here.\n")

    def spawn_agent(self, agent_name: str, role: str, image: str = "ubuntu:latest"):
        """Spawns a new agent in an isolated Docker container."""
        container_name = f"agent_{agent_name}_{uuid.uuid4().hex[:8]}"
        
        # We mount the shared workspace into the container
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-v", f"{self.workspace_path}:/shared_workspace",
            image,
            "tail", "-f", "/dev/null" # Keep container alive
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.active_containers[agent_name] = {
                "container_name": container_name,
                "role": role,
                "status": "running"
            }
            self._log_to_workspace(f"Agent '{agent_name}' ({role}) joined the swarm in container {container_name}.")
            print(f"Spawned agent {agent_name} in {container_name}")
            return container_name
        except subprocess.CalledProcessError as e:
            print(f"Failed to spawn agent {agent_name}: {e.stderr.decode()}")
            return None

    def execute_command(self, agent_name: str, command: str):
        """Executes a command inside the agent's container."""
        if agent_name not in self.active_containers:
            print(f"Agent {agent_name} not found.")
            return None
        
        container_name = self.active_containers[agent_name]["container_name"]
        cmd = ["docker", "exec", container_name, "bash", "-c", command]
        
        try:
            result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.stdout.decode()
        except subprocess.CalledProcessError as e:
            return e.stderr.decode()

    def _log_to_workspace(self, message: str):
        index_path = os.path.join(self.workspace_path, "index.md")
        with open(index_path, "a") as f:
            f.write(f"- {message}\n")

    def shutdown_swarm(self):
        """Stops and removes all agent containers."""
        for agent_name, info in self.active_containers.items():
            container_name = info["container_name"]
            print(f"Shutting down agent {agent_name} ({container_name})...")
            subprocess.run(["docker", "rm", "-f", container_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self._log_to_workspace(f"Agent '{agent_name}' left the swarm.")
        self.active_containers.clear()

if __name__ == "__main__":
    swarm = ContainerSwarmCoordinator()
    swarm.spawn_agent("Alice", "Researcher")
    swarm.spawn_agent("Bob", "Coder")
    
    # Alice writes to shared workspace
    swarm.execute_command("Alice", "echo 'Hello from Alice!' >> /shared_workspace/alice.md")
    
    # Bob reads Alice's message
    bob_out = swarm.execute_command("Bob", "cat /shared_workspace/alice.md")
    print(f"Bob read: {bob_out}")
    
    swarm.shutdown_swarm()
