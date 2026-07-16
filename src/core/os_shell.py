"""
Arbitrary OS shell execution for SuperAI (N202 expansion).

Safety:
- Permission mode dry-run / plan blocks real execution
- Deny-list of catastrophic patterns (rm -rf /, format, fork bombs, etc.)
- Optional allow-list mode
- Workspace-relative cwd by default (jail)
- Timeouts + audit trail
- Contract-shaped results
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


# Catastrophic / clearly abusive patterns (case-insensitive)
_DENY_PATTERNS = [
    r"rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?(/\s|$|/\*|/\.\.)",
    r"rm\s+-rf\s+/",
    r"mkfs\.",
    r"dd\s+if=",
    r":\(\)\s*\{\s*:\|:&\s*\};:",  # fork bomb
    r"shutdown(\s|$)",
    r"reboot(\s|$)",
    r"format\s+[a-z]:",
    r"Remove-Item\s+.*-Recurse.*C:\\",
    r"del\s+/[fqs].*\\Windows",
    r"curl\s+[^\n]*\|\s*(ba)?sh",
    r"wget\s+[^\n]*\|\s*(ba)?sh",
    r"Invoke-Expression\s*\(\s*\(.*Download",
]


def _workspace_root() -> Path:
    try:
        from .workspace import workspace_root

        return Path(workspace_root()).resolve()
    except Exception:
        return Path(os.getenv("SUPERAI_WORKSPACE") or Path.cwd()).resolve()


def check_denied(command: str) -> Optional[str]:
    """Return deny reason or None if allowed by deny-list."""
    s = command or ""
    for pat in _DENY_PATTERNS:
        if re.search(pat, s, flags=re.I):
            return f"denied_pattern:{pat}"
    # bare destructive keywords with root paths
    low = s.lower()
    if "rm -rf /" in low or "rm -rf /*" in low:
        return "denied:rm_root"
    return None


def parse_shell_from_nl(text: str) -> Optional[str]:
    """
    Extract shell command from NL phrases like:
      run shell: ls -la
      execute in terminal: dir
      $ git status
      shell> pytest -q
    """
    raw = (text or "").strip()
    if not raw:
        return None
    # Explicit markers
    m = re.match(
        r"^(?:"
        r"run\s+(?:in\s+)?(?:shell|terminal|bash|powershell|cmd)|"
        r"execute\s+in\s+(?:shell|terminal|bash|powershell|cmd)|"
        r"exec(?:ute)?(?:\s+command)?(?:\s+in\s+(?:shell|terminal))?"
        r"|shell|bash|powershell|cmd"
        r")\s*[:\-]?\s+(.+)$",
        raw,
        flags=re.I,
    )
    if m:
        return m.group(1).strip().strip("`")
    if raw.startswith("$ "):
        return raw[2:].strip()
    if raw.startswith(">"):
        return raw[1:].strip()
    # backtick command
    m2 = re.search(r"`([^`]+)`", raw)
    if m2 and re.search(r"\b(run|execute|shell|terminal)\b", raw, re.I):
        return m2.group(1).strip()
    return None


def preview_shell(
    command: str,
    *,
    cwd: Optional[str] = None,
    shell: bool = True,
) -> Dict[str, Any]:
    """Preview shell command without executing."""
    from .spend_guard import ensure_public_result

    cmd = (command or "").strip()
    deny = check_denied(cmd)
    root = _workspace_root()
    work = Path(cwd).resolve() if cwd else root
    # jail: must stay under workspace unless SUPERAI_SHELL_ALLOW_ANY_CWD=1
    allow_any = (os.getenv("SUPERAI_SHELL_ALLOW_ANY_CWD") or "").lower() in {
        "1",
        "true",
        "yes",
    }
    outside = False
    try:
        work.relative_to(root)
    except ValueError:
        outside = True
    blocked = bool(deny) or (outside and not allow_any)
    return ensure_public_result(
        {
            "ok": not blocked,
            "preview": True,
            "executed": False,
            "command": cmd,
            "cwd": str(work),
            "workspace": str(root),
            "shell": bool(shell),
            "denied": deny,
            "cwd_outside_workspace": outside,
            "blocked": blocked,
            "risk": "high" if not deny else "blocked",
            "planned_command": f"superai shell {shlex.quote(cmd)}",
        },
        dry_run=True,
        ok=not blocked,
    )


def run_shell(
    command: str,
    *,
    cwd: Optional[str] = None,
    timeout: float = 120.0,
    dry_run: Optional[bool] = None,
    permission_mode: Optional[str] = None,
    shell: bool = True,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Run an OS shell command with SuperAI safety policy.
    """
    from .permission_mode import force_dry_run, mode_from_config
    from .spend_guard import ensure_public_result

    mode = permission_mode or mode_from_config()
    if dry_run is None:
        dry_run = force_dry_run(mode)
    dry_run = bool(dry_run)

    prev = preview_shell(command, cwd=cwd, shell=shell)
    if prev.get("blocked"):
        prev["error"] = prev.get("denied") or "shell_blocked"
        prev["error_code"] = "permission"
        return ensure_public_result(prev, ok=False, dry_run=True)

    cmd = prev["command"]
    work = Path(prev["cwd"])

    if dry_run:
        return ensure_public_result(
            {
                "ok": True,
                "dry_run": True,
                "executed": False,
                "command": cmd,
                "cwd": str(work),
                "message": "dry_run: shell not executed",
                "permission_mode": mode,
            },
            dry_run=True,
            ok=True,
        )

    started = time.time()
    try:
        # Prefer list form when possible without shell for simple tokens
        use_shell = bool(shell)
        if sys.platform == "win32":
            # PowerShell-friendly: run via cmd /c for broad compatibility
            proc = subprocess.run(
                cmd,
                cwd=str(work),
                shell=True,
                capture_output=True,
                text=True,
                timeout=float(timeout),
                env={**os.environ, **(env or {})},
            )
        else:
            proc = subprocess.run(
                cmd if use_shell else shlex.split(cmd),
                cwd=str(work),
                shell=use_shell,
                capture_output=True,
                text=True,
                timeout=float(timeout),
                env={**os.environ, **(env or {})},
            )
        out = {
            "ok": proc.returncode == 0,
            "executed": True,
            "dry_run": False,
            "command": cmd,
            "cwd": str(work),
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[:50_000],
            "stderr": (proc.stderr or "")[:20_000],
            "latency_sec": round(time.time() - started, 3),
            "permission_mode": mode,
        }
        try:
            from .side_effect_audit import record_side_effect

            record_side_effect(
                "shell",
                name="os_shell",
                ok=out["ok"],
                dry_run=False,
                detail=cmd[:200],
            )
        except Exception:
            pass
        return ensure_public_result(out, ok=out["ok"])
    except subprocess.TimeoutExpired:
        return ensure_public_result(
            {
                "ok": False,
                "error": "timeout",
                "error_code": "timeout",
                "command": cmd,
                "cwd": str(work),
                "timeout": timeout,
            },
            ok=False,
        )
    except Exception as e:
        return ensure_public_result(
            {
                "ok": False,
                "error": str(e)[:400],
                "command": cmd,
                "cwd": str(work),
            },
            ok=False,
        )
