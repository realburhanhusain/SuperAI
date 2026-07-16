"""
Windows Task Scheduler installer for SuperAI goals daemon (N206 expansion).

Creates/removes a Scheduled Task that runs:
  superai daemon run --interval N ...

Uses `schtasks` (built into Windows). Non-Windows returns clear error.
Also emits a .ps1 helper script for inspection.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional


TASK_NAME_DEFAULT = "SuperAI-Goals-Daemon"


def is_windows() -> bool:
    return sys.platform == "win32"


def task_name(name: Optional[str] = None) -> str:
    return (name or os.getenv("SUPERAI_WINDOWS_TASK_NAME") or TASK_NAME_DEFAULT).strip()


def _superai_cmd(
    *,
    interval_sec: float = 60.0,
    execute_goals: bool = False,
    cli_path: str = "superai",
) -> str:
    parts = [
        cli_path,
        "daemon",
        "run",
        "--interval",
        str(float(interval_sec)),
    ]
    if execute_goals:
        parts.append("--execute-goals")
    # quote for schtasks /tr
    return " ".join(parts)


def render_ps1_installer(
    *,
    name: str = TASK_NAME_DEFAULT,
    interval_sec: float = 60.0,
    execute_goals: bool = False,
    cli_path: str = "superai",
    start_boundary: str = "2026-01-01T00:00:00",
) -> str:
    """PowerShell script that registers the scheduled task."""
    tr = _superai_cmd(
        interval_sec=interval_sec, execute_goals=execute_goals, cli_path=cli_path
    )
    # Escape single quotes for PowerShell
    tr_ps = tr.replace("'", "''")
    return textwrap.dedent(
        f"""
        # SuperAI Goals Daemon — Windows Task Scheduler installer (generated)
        # Requires: SuperAI CLI on PATH (or set -CliPath)
        $ErrorActionPreference = "Stop"
        $TaskName = "{name}"
        $Tr = '{tr_ps}'

        # Remove existing
        schtasks /Delete /TN $TaskName /F 2>$null | Out-Null

        # Create: at logon, restart on failure, run whether user logged on or not is admin-only;
        # default: ONLOGON for current user (no password prompt in most setups).
        schtasks /Create /TN $TaskName /TR $Tr /SC ONLOGON /RL LIMITED /F
        if ($LASTEXITCODE -ne 0) {{
          # Fallback: every hour once to launch the long-running process
          schtasks /Create /TN $TaskName /TR $Tr /SC HOURLY /MO 1 /RL LIMITED /F
        }}
        Write-Host "Created scheduled task: $TaskName"
        Write-Host "Command: $Tr"
        schtasks /Query /TN $TaskName /V /FO LIST
        """
    ).strip() + "\n"


def install_task(
    *,
    name: Optional[str] = None,
    interval_sec: float = 60.0,
    execute_goals: bool = False,
    cli_path: str = "superai",
    write_script: bool = True,
) -> Dict[str, Any]:
    """Install Windows Scheduled Task via schtasks."""
    from .spend_guard import ensure_public_result

    if not is_windows():
        return ensure_public_result(
            {
                "ok": False,
                "error": "not_windows",
                "hint": "Use K8s CronJob or systemd timer on Linux",
            },
            ok=False,
        )

    tname = task_name(name)
    tr = _superai_cmd(
        interval_sec=interval_sec,
        execute_goals=execute_goals,
        cli_path=cli_path,
    )
    script_path = Path.home() / ".superai" / "daemon" / "install_windows_task.ps1"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    ps1 = render_ps1_installer(
        name=tname,
        interval_sec=interval_sec,
        execute_goals=execute_goals,
        cli_path=cli_path,
    )
    if write_script:
        script_path.write_text(ps1, encoding="utf-8")

    # Prefer direct schtasks create
    # /SC ONLOGON runs daemon at login; long-running `daemon run` keeps ticking
    args = [
        "schtasks",
        "/Create",
        "/TN",
        tname,
        "/TR",
        tr,
        "/SC",
        "ONLOGON",
        "/RL",
        "LIMITED",
        "/F",
    ]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=60)
        ok = proc.returncode == 0
        if not ok:
            # hourly fallback
            args2 = [
                "schtasks",
                "/Create",
                "/TN",
                tname,
                "/TR",
                tr,
                "/SC",
                "HOURLY",
                "/MO",
                "1",
                "/RL",
                "LIMITED",
                "/F",
            ]
            proc = subprocess.run(args2, capture_output=True, text=True, timeout=60)
            ok = proc.returncode == 0
            args = args2
        return ensure_public_result(
            {
                "ok": ok,
                "task_name": tname,
                "command": tr,
                "schtasks_args": args,
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "")[:2000],
                "stderr": (proc.stderr or "")[:1000],
                "script": str(script_path) if write_script else None,
                "query_hint": f'schtasks /Query /TN "{tname}" /V /FO LIST',
            },
            ok=ok,
        )
    except FileNotFoundError:
        return ensure_public_result(
            {"ok": False, "error": "schtasks_not_found", "script": str(script_path)},
            ok=False,
        )
    except Exception as e:
        return ensure_public_result(
            {"ok": False, "error": str(e)[:300], "script": str(script_path)},
            ok=False,
        )


def uninstall_task(*, name: Optional[str] = None) -> Dict[str, Any]:
    from .spend_guard import ensure_public_result

    if not is_windows():
        return ensure_public_result(
            {"ok": False, "error": "not_windows"}, ok=False
        )
    tname = task_name(name)
    try:
        proc = subprocess.run(
            ["schtasks", "/Delete", "/TN", tname, "/F"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return ensure_public_result(
            {
                "ok": proc.returncode == 0,
                "task_name": tname,
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "")[:1000],
                "stderr": (proc.stderr or "")[:1000],
            },
            ok=proc.returncode == 0,
        )
    except Exception as e:
        return ensure_public_result(
            {"ok": False, "error": str(e)[:300]}, ok=False
        )


def query_task(*, name: Optional[str] = None) -> Dict[str, Any]:
    from .spend_guard import ensure_public_result

    if not is_windows():
        return ensure_public_result(
            {"ok": False, "error": "not_windows"}, ok=False
        )
    tname = task_name(name)
    try:
        proc = subprocess.run(
            ["schtasks", "/Query", "/TN", tname, "/V", "/FO", "LIST"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return ensure_public_result(
            {
                "ok": proc.returncode == 0,
                "task_name": tname,
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "")[:4000],
                "stderr": (proc.stderr or "")[:1000],
                "installed": proc.returncode == 0,
            },
            ok=True,
        )
    except Exception as e:
        return ensure_public_result(
            {"ok": False, "error": str(e)[:300]}, ok=False
        )
