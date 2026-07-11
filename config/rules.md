# Human-in-the-Loop Rules

High-impact actions that require explicit human approval before execution:
- Writing or modifying files in the project
- Running shell commands that change state (git commit, pip install, docker, deployments, etc.)
- Any action that could affect production systems or user data
- Large token/cost delegations (over a threshold the supervisor should propose)

The supervisor must always surface an estimated cost and a clear description of the action before asking for approval.

Workers may propose actions, but only the supervisor can request final human approval.