"""
Container sandbox for tool shell execution (N15).

When prefer_container_sandbox / SUPERAI_CONTAINER_SANDBOX=1 and Docker is
available, run_shell commands execute inside an ephemeral container with
the workspace mounted at /workspace.

Hardening applied:
  - All Linux capabilities dropped (--cap-drop ALL)
  - no-new-privileges set, blocking setuid escalation
  - PID and memory limits (SUPERAI_SANDBOX_PIDS_LIMIT / _MEMORY)
  - Network defaults to "none"
  - Fails closed: if Docker is missing or errors, the command is NOT run on
    the host unless SUPERAI_SANDBOX_FAIL_CLOSED is explicitly disabled
  - Does not use shell=True

Remaining limitations (documented):
  - Workspace is mounted read-write by default, because tool shells
    legitimately write build output. Set SUPERAI_SANDBOX_WORKSPACE_RO=1 for a
    read-only mount.
  - Container rootfs is not read-only.
  - Runs as the image's default user (often root inside the container) unless
    SUPERAI_SANDBOX_USER is set.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .workspace import workspace_root

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}


def sandbox_enabled(config_flag: bool = False) -> bool:
    env = os.getenv("SUPERAI_CONTAINER_SANDBOX", "").lower() in _TRUTHY
    return bool(config_flag or env)


def fail_closed() -> bool:
    """Whether a sandbox failure must block execution instead of falling back.

    Defaults to True. A sandbox that silently degrades to host execution
    offers no containment, so opting out must be explicit.
    """
    raw = (os.getenv("SUPERAI_SANDBOX_FAIL_CLOSED") or "").lower()
    if raw in _FALSY:
        return False
    return True


def _workspace_readonly() -> bool:
    return (os.getenv("SUPERAI_SANDBOX_WORKSPACE_RO") or "").lower() in _TRUTHY


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
    mount = f"{ws}:/workspace" + (":ro" if _workspace_readonly() else "")
    cmd = [
        "docker",
        "run",
        "--rm",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        str(os.getenv("SUPERAI_SANDBOX_PIDS_LIMIT", "512")),
        "--memory",
        str(os.getenv("SUPERAI_SANDBOX_MEMORY", "1g")),
        "-v",
        mount,
        "-w",
        "/workspace",
        "--network",
        network,
    ]
    sandbox_user = os.getenv("SUPERAI_SANDBOX_USER")
    if sandbox_user:
        cmd += ["--user", str(sandbox_user)]
    cmd += [img, *argv]
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
        "workspace_readonly": _workspace_readonly(),
        "command": cmd,
    }


def try_sandboxed_shell(
    argv: List[str],
    timeout: float = 60.0,
    prefer: bool = False,
) -> Optional[Dict[str, Any]]:
    """Return docker result if sandbox enabled and docker present; else None.

    When the sandbox is requested but unavailable or failing, the returned
    envelope carries fallback=False by default so callers do NOT silently run
    the command on the host. Set SUPERAI_SANDBOX_FAIL_CLOSED=0 to restore the
    permissive behaviour.
    """
    if not sandbox_enabled(prefer):
        return None
    closed = fail_closed()
    if not docker_available():
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": "Sandbox requested but docker not available",
            "sandbox": "unavailable",
            "fallback": not closed,
            "fail_closed": closed,
        }
    try:
        return run_in_docker(argv, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "sandbox": "error",
            "fallback": not closed,
            "fail_closed": closed,
        }
