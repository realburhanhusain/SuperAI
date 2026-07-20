"""
M018 — mandatory timeouts for SuperAI subprocess invocations.

Long-lived intentional processes (daemon background, process-mux panes) are
registered as exceptions and must not use this helper for lifetime control.
All finite tool/git/host operations must go through ``run()`` (or pass an
explicit ``timeout=`` that this module records).
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any, Dict, List, Optional, Sequence, Union

from .tool_timeouts import get as get_timeout

# Kind → default seconds (also in tool_timeouts.DEFAULTS; kept here for discovery)
KIND_DEFAULTS: Dict[str, float] = {
    "git": 60.0,
    "gh": 60.0,
    "rclone": 300.0,
    "bash": 120.0,
    "cli": 300.0,
    "host": 60.0,
    "backup": 300.0,
    "default": 60.0,
}

# Call sites that intentionally keep a process alive without a wall-clock timeout.
# Audits skip these paths (must stay short and reviewed).
LONG_LIVED_ALLOWLIST = (
    "goals_daemon.py:Popen",  # background daemon
    "tui_process_mux.py:Popen",  # interactive process panes
    "tui_conpty.py",  # ConPTY session lifetime
    "windows_task_scheduler.py",  # schtasks install only (uses run with timeout)
)


def resolve_timeout(
    *,
    timeout: Optional[float] = None,
    kind: str = "default",
) -> float:
    if timeout is not None:
        return float(timeout)
    try:
        return float(get_timeout(kind))
    except Exception:
        return float(KIND_DEFAULTS.get(kind, KIND_DEFAULTS["default"]))


def run(
    args: Union[str, Sequence[str]],
    *,
    kind: str = "default",
    timeout: Optional[float] = None,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    input: Optional[str] = None,
    text: bool = True,
    capture_output: bool = True,
    check: bool = False,
    shell: bool = False,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """
    subprocess.run with a mandatory wall-clock timeout.

    ``timeout`` / ``kind`` always resolve to a positive limit unless the caller
    explicitly passes timeout=0 to mean "use kind default" — never infinite.
    """
    seconds = resolve_timeout(timeout=timeout if timeout not in (0, 0.0) else None, kind=kind)
    if seconds <= 0:
        seconds = float(KIND_DEFAULTS.get(kind, 60.0))
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        input=input,
        text=text,
        capture_output=capture_output,
        check=check,
        shell=shell,
        timeout=seconds,
        **kwargs,
    )


def run_result(
    args: Union[str, Sequence[str]],
    *,
    kind: str = "default",
    timeout: Optional[float] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Contract-shaped wrapper around ``run()`` (timeout → error_code)."""
    from .spend_guard import ensure_public_result

    seconds = resolve_timeout(timeout=timeout, kind=kind)
    try:
        proc = run(args, kind=kind, timeout=seconds, **kwargs)
        return ensure_public_result(
            {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "")[:8000] if isinstance(proc.stdout, str) else proc.stdout,
                "stderr": (proc.stderr or "")[:4000] if isinstance(proc.stderr, str) else proc.stderr,
                "timeout_sec": seconds,
                "kind": kind,
                "args": list(args) if not isinstance(args, str) else [args],
            },
            ok=proc.returncode == 0,
        )
    except subprocess.TimeoutExpired as e:
        return ensure_public_result(
            {
                "ok": False,
                "error": f"{kind}_timeout_after_{seconds}s",
                "error_code": "timeout",
                "timeout_sec": seconds,
                "kind": kind,
                "partial_stdout": (e.stdout or "")[:2000] if e.stdout else "",
            },
            ok=False,
        )
    except Exception as e:
        return ensure_public_result(
            {
                "ok": False,
                "error": str(e)[:300],
                "error_code": "subprocess",
                "kind": kind,
            },
            ok=False,
        )


def inventory_subprocess_sites(root: Optional[str] = None) -> Dict[str, Any]:
    """
    Static scan of src/**/*.py for subprocess.run/Popen/call/check_*.

    Classifies each site as: timed | long_lived_allowlisted | missing_timeout.
    """
    import re
    from pathlib import Path

    base = Path(root) if root else Path(__file__).resolve().parents[1]
    if (base / "core").is_dir() and not (base / "src").is_dir():
        # base is already src/
        src = base
    else:
        src = base / "src" if (base / "src").is_dir() else base

    sites: List[Dict[str, Any]] = []
    pat = re.compile(r"subprocess\.(run|Popen|call|check_output|check_call)\s*\(")

    for path in sorted(src.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        try:
            rel = str(path.relative_to(src.parent if src.name == "src" else src)).replace("\\", "/")
        except ValueError:
            rel = str(path).replace("\\", "/")
        # This module is the timeout authority — its internal subprocess.run is timed.
        if path.name == "subprocess_safety.py":
            for i, line in enumerate(text.splitlines()):
                if pat.search(line):
                    sites.append(
                        {
                            "file": rel,
                            "line": i + 1,
                            "call": line.strip()[:120],
                            "status": "timed_wrapper",
                        }
                    )
            continue
        lines = text.splitlines()
        file_imports_safety = (
            "subprocess_safety" in text
            or "safe_run" in text
        )
        for i, line in enumerate(lines):
            if not pat.search(line):
                continue
            # window: previous 3 + next 15 lines (timeout often on later kwarg line)
            window = "\n".join(lines[max(0, i - 3) : min(len(lines), i + 16)])
            has_timeout = bool(re.search(r"\btimeout\s*=", window))

            allow = False
            for a in LONG_LIVED_ALLOWLIST:
                if a.endswith(".py") and a.replace("\\", "/") in rel.replace("\\", "/"):
                    if "Popen" in line or "conpty" in rel.lower():
                        allow = True
                        break
                if ":" in a:
                    file_part, kind = a.split(":", 1)
                    if file_part in rel and kind in line:
                        allow = True
                        break

            # Direct calls through safety wrapper (not subprocess.run itself)
            if "subprocess.run" not in line and "subprocess.Popen" not in line:
                if "safe_run" in line or "subprocess_safety" in line:
                    status = "timed_wrapper"
                elif has_timeout:
                    status = "timed_explicit"
                elif allow:
                    status = "long_lived_allowlisted"
                else:
                    status = "missing_timeout"
            elif has_timeout:
                status = "timed_explicit"
            elif allow:
                status = "long_lived_allowlisted"
            elif file_imports_safety and "safe_run" in window:
                # assignment like result = safe_run( — already counted if line matches
                status = "timed_wrapper"
            else:
                status = "missing_timeout"

            sites.append(
                {
                    "file": rel,
                    "line": i + 1,
                    "call": line.strip()[:120],
                    "status": status,
                }
            )

    missing = [s for s in sites if s["status"] == "missing_timeout"]
    return {
        "ok": len(missing) == 0,
        "total": len(sites),
        "missing": missing,
        "timed": [s for s in sites if s["status"].startswith("timed")],
        "allowlisted": [s for s in sites if s["status"] == "long_lived_allowlisted"],
        "sites": sites,
        "platform": sys.platform,
    }
