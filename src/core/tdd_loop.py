"""
Test-driven coding loop (S14).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .workspace import workspace_root


def detect_test_command(root: Optional[Path] = None) -> List[str]:
    root = root or workspace_root()
    if (root / "pytest.ini").exists() or (root / "pyproject.toml").exists():
        if (root / "tests").is_dir() or list(root.glob("test_*.py")):
            return ["python", "-m", "pytest", "-q"]
    if (root / "package.json").exists():
        return ["npm", "test", "--", "--watchAll=false"]
    if (root / "Cargo.toml").exists():
        return ["cargo", "test"]
    return ["python", "-m", "pytest", "-q"]


def run_tests(
    command: Optional[List[str]] = None,
    timeout: float = 300.0,
    cwd: Optional[Path] = None,
) -> Dict[str, Any]:
    root = cwd or workspace_root()
    cmd = command or detect_test_command(root)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "command": cmd,
            "stdout": (proc.stdout or "")[:12000],
            "stderr": (proc.stderr or "")[:6000],
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e), "command": cmd}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "command": cmd}


def tdd_cycle(
    task: str,
    max_rounds: int = 2,
    *,
    run_orchestrator: bool = True,
) -> Dict[str, Any]:
    """
    Run task via orchestrator, then tests; on failure re-run with failure context.
    """
    from .orchestrator import SuperAIOrchestrator

    rounds = []
    orch = SuperAIOrchestrator()
    current_task = task
    for i in range(max_rounds):
        result = None
        if run_orchestrator:
            result = orch.run_task(current_task, verbose=False)
        test = run_tests()
        rounds.append(
            {
                "round": i + 1,
                "task": current_task[:200],
                "run_status": (result or {}).get("status"),
                "tests_ok": test.get("ok"),
                "test_exit": test.get("exit_code"),
            }
        )
        if test.get("ok"):
            return {"ok": True, "rounds": rounds, "final_tests": test, "result": result}
        # replan with failure
        current_task = (
            f"{task}\n\nPrevious attempt failed tests:\n"
            f"{(test.get('stdout') or '')[:1500]}\n"
            f"{(test.get('stderr') or '')[:800]}\n"
            "Fix the failures."
        )
    return {"ok": False, "rounds": rounds, "final_tests": test, "result": result}
