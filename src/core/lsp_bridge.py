"""Optional LSP bridge foundation (V6 N231) — no hard dependency."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def available() -> bool:
    try:
        import lsprotocol  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False




def python_provider_status(timeout_seconds: float = 5.0) -> Dict[str, Any]:
    """Probe an optional Python LSP with a bounded, non-failing check."""
    configured = os.environ.get("SUPERAI_PYTHON_LSP", "").strip()
    command: Optional[str] = configured or shutil.which("basedpyright-langserver") or shutil.which("pyright-langserver")
    if not command:
        return {"available": False, "language": "python", "reason": "no Python LSP provider found; install pyright/basedpyright or set SUPERAI_PYTHON_LSP", "capabilities": []}
    if configured and not Path(command).is_file():
        return {"available": False, "language": "python", "reason": f"configured provider not found: {command}", "capabilities": []}
    try:
        probe = subprocess.run([command, "--stdio"], input=b"", stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=timeout_seconds, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "language": "python", "reason": f"provider probe failed: {exc}", "capabilities": []}
    return {"available": True, "language": "python", "provider": Path(command).name, "capabilities": ["diagnostics", "references (provider-advertised; advisory only)"], "probe_exit_code": probe.returncode}


def diagnostics_stub(path: str) -> Dict[str, Any]:
    """
    Without a running language server, return structure-only response.
    Real LSP wiring is optional when python-lsp / pyright present.
    """
    from pathlib import Path

    p = Path(path)
    if not p.is_file():
        return {"ok": False, "error": "not_found", "path": path}
    # lightweight syntax-ish checks for Python
    diags: List[Dict[str, Any]] = []
    if p.suffix == ".py":
        try:
            compile(p.read_text(encoding="utf-8", errors="replace"), str(p), "exec")
        except SyntaxError as e:
            diags.append(
                {
                    "severity": "error",
                    "line": e.lineno or 1,
                    "message": e.msg,
                }
            )
    return {
        "ok": True,
        "path": str(p),
        "diagnostics": diags,
        "lsp_available": available(),
        "mode": "stub_or_compile",
    }
