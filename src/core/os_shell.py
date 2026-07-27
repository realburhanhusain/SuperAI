"""
Arbitrary OS shell execution for SuperAI (N202 expansion).

Safety:
- Permission mode dry-run / plan blocks real execution
- Deny-list of catastrophic patterns (rm -rf /, format, fork bombs, etc.)
- Optional allow-list mode
- Workspace-relative cwd by default (jail)
- Optional container sandbox; when enabled it fails closed, so a command is
  never silently promoted to host execution because Docker was missing
- Timeouts + audit trail
- Contract-shaped results

Note on the cwd jail: `cwd` confinement is a convenience boundary, not a
security boundary. A command is free to reference absolute paths outside the
workspace. Real confinement requires the container sandbox below.
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


def sandbox_argv(command: str) -> List[str]:
    """Build the argv used to run a shell string inside the container.

    The command keeps its shell semantics -- pipes, redirects, globs -- but the
    shell interpreting them belongs to the container, not the host. Inside a
    container with all capabilities dropped, no new privileges, no network and
    only the workspace mounted, shell metacharacters are not the threat; the
    container is the boundary.

    ``sh -lc`` is used regardless of host platform because the sandbox image is
    Linux. A useful side effect is that sandboxed execution behaves identically
    on Windows, macOS and Linux hosts.
    """
    return ["sh", "-lc", command]


def _run_in_container(
    command: str,
    *,
    cwd: str,
    timeout: float,
    mode: str,
) -> Optional[Dict[str, Any]]:
    """Try to run ``command`` inside the container sandbox.

    Returns:
      * ``None`` when the sandbox is not enabled, or when it is enabled but
        unavailable *and* fail-closed has been explicitly disabled. In both
        cases the caller proceeds with host execution.
      * A blocking result envelope (``ok=False``) when the sandbox is enabled,
        unavailable or failing, and fail-closed is in effect. The command is
        NOT run on the host.
      * A normal result envelope when the command ran inside the container.
    """
    from .spend_guard import ensure_public_result

    try:
        from .container_sandbox import try_sandboxed_shell
    except Exception:
        # Sandbox module unavailable: behave exactly as before it existed.
        return None

    try:
        from .config import Config

        prefer = bool(Config().get("prefer_container_sandbox"))
    except Exception:
        prefer = False

    started = time.time()
    try:
        sand = try_sandboxed_shell(
            sandbox_argv(command), timeout=float(timeout), prefer=prefer
        )
    except Exception as e:  # noqa: BLE001
        # Treat an unexpected sandbox failure as fail-closed. Falling through to
        # the host here would defeat the entire point of requesting a sandbox.
        return ensure_public_result(
            {
                "ok": False,
                "executed": False,
                "error": f"sandbox_error:{str(e)[:200]}",
                "error_code": "sandbox_unavailable",
                "command": command,
                "cwd": cwd,
                "sandbox": "error",
                "permission_mode": mode,
            },
            ok=False,
        )

    if sand is None:
        # Sandbox not requested.
        return None

    status = sand.get("sandbox")
    if status in {"unavailable", "error"}:
        if sand.get("fallback"):
            # SUPERAI_SANDBOX_FAIL_CLOSED=0 was set deliberately.
            return None
        return ensure_public_result(
            {
                "ok": False,
                "executed": False,
                "error": sand.get("stderr") or "sandbox unavailable",
                "error_code": "sandbox_unavailable",
                "command": command,
                "cwd": cwd,
                "sandbox": status,
                "fail_closed": sand.get("fail_closed", True),
                "permission_mode": mode,
                "remedy": (
                    "Install/start Docker, or set "
                    "SUPERAI_SANDBOX_FAIL_CLOSED=0 to allow host execution."
                ),
            },
            ok=False,
        )

    rc = sand.get("exit_code")
    out = {
        "ok": rc == 0,
        "executed": True,
        "dry_run": False,
        "command": command,
        "cwd": sand.get("workspace") or cwd,
        "returncode": rc,
        "stdout": sand.get("stdout") or "",
        "stderr": sand.get("stderr") or "",
        "latency_sec": round(time.time() - started, 3),
        "permission_mode": mode,
        "sandbox": sand.get("sandbox"),
        "image": sand.get("image"),
        "workspace_readonly": sand.get("workspace_readonly"),
    }
    try:
        from .side_effect_audit import record_side_effect

        record_side_effect(
            "shell",
            name="os_shell_sandboxed",
            ok=bool(out["ok"]),
            dry_run=False,
            detail=command[:200],
        )
    except Exception:
        pass
    return ensure_public_result(out, ok=bool(out["ok"]))


def parse_shell_from_nl(text: str) -> Optional[str]:
    """
    Extract shell command from NL phrases like:
      run shell: ls -la
      execute in terminal: dir
      execute command: dir
      $ git status
      shell> pytest -q

    Bare ``execute …`` / ``exec …`` without an explicit shell/command marker
    must NOT match — product intents like ``execute due goals`` (MOS-S9) would
    otherwise be stolen as OS shell subjects.
    """
    raw = (text or "").strip()
    if not raw:
        return None
    # Explicit markers only. Do not match bare "execute X" / "exec X":
    # both optional groups on the old exec(?:ute)? pattern made any
    # "execute <words>" look like a shell command.
    m = re.match(
        r"^(?:"
        r"run\s+(?:in\s+)?(?:shell|terminal|bash|powershell|cmd)|"
        r"execute\s+in\s+(?:shell|terminal|bash|powershell|cmd)|"
        r"exec(?:ute)?\s+command(?:\s+in\s+(?:shell|terminal))?"
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

    Order of checks, and why: deny-list and cwd jail first (cheapest, and a
    denied command should never reach an executor), then dry-run, then the
    container sandbox, then host execution. The sandbox is consulted only after
    we have decided the command is permitted and is actually meant to run.
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

    # Container sandbox, when requested. Returns None when the sandbox is not
    # enabled, or when it is unavailable and fail-closed was explicitly
    # disabled; in both cases we fall through to host execution below.
    sandboxed = _run_in_container(
        cmd, cwd=str(work), timeout=float(timeout), mode=mode
    )
    if sandboxed is not None:
        return sandboxed

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
            "sandbox": "none",
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
