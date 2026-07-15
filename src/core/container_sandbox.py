"""
Container sandbox for tool shell execution (N15).

When prefer_container_sandbox / SUPERAI_CONTAINER_SANDBOX=1 and Docker is
available, run_shell commands execute inside an ephemeral container with
the workspace mounted at /workspace.

Limitations (documented):
  - Workspace is mounted read-write (not a full host jail).
  - No non-root user / capability drop by default.
  - Network defaults to "none" (good) but rootfs is not read-only.
  - On Docker failure, try_sandboxed_shell may fall back to host shell
    unless SUPERAI_SANDBOX_FAIL_CLOSED=1.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .workspace import workspace_root


def sandbox_enabled(config_flag: bool = False) -> bool:
    env = os.getenv("SUPERAI_CONTAINER_SANDBOX", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return bool(config_flag or env)


def docker_available() -> bool:
    return shutil.which("docker") is not None


def run_in_docker(
    argv: List[str],
    timeout: float = 60.0,
    image: Optional[str] = None,
    network: str = "none",
) -> Dict[str, Any]:
    """
    Run argv inside docker with workspace bind-mount.
    Does not use shell=True.
    """
    if not docker_available():
        raise RuntimeError("Docker not found on PATH")
    img = image or os.getenv("SUPERAI_SANDBOX_IMAGE", "python:3.12-slim")
    ws = workspace_root()
    # docker run --rm -v workspace:/workspace -w /workspace --network none image cmd...
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{ws}:/workspace",
        "-w",
        "/workspace",
        "--network",
        network,
        img,
        *argv,
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
    return {
        "exit_code": proc.returncode,
        "stdout": (proc.stdout or "")[:8000],
        "stderr": (proc.stderr or "")[:4000],
        "sandbox": "docker",
        "image": img,
        "workspace": str(ws),
        "command": cmd,
    }


def try_sandboxed_shell(
    argv: List[str],
    timeout: float = 60.0,
    prefer: bool = False,
) -> Optional[Dict[str, Any]]:
    """Return docker result if sandbox enabled and docker present; else None."""
    if not sandbox_enabled(prefer):
        return None
    fail_closed = (os.getenv("SUPERAI_SANDBOX_FAIL_CLOSED") or "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not docker_available():
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": "Sandbox requested but docker not available",
            "sandbox": "unavailable",
            "fallback": not fail_closed,
            "fail_closed": fail_closed,
        }
    try:
        return run_in_docker(argv, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "sandbox": "error",
            "fallback": not fail_closed,
            "fail_closed": fail_closed,
        }
