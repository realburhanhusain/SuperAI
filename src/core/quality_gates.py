"""Quality gates after edits (V6 S105/S106 foundations)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def run_cmd(cmd: List[str], cwd: Optional[Path] = None, timeout: float = 120) -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return {
            "ok": proc.returncode == 0,
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[:4000],
            "stderr": (proc.stderr or "")[:2000],
        }
    except Exception as e:
        return {"ok": False, "cmd": cmd, "error": str(e)[:300]}


def detect_and_run(cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Run lightweight tests/lint if project markers exist."""
    root = Path(cwd or Path.cwd())
    results = []
    if (root / "pytest.ini").exists() or (root / "tests").is_dir() or (
        root / "pyproject.toml"
    ).is_file():
        results.append(run_cmd(["python", "-m", "pytest", "-q", "--tb=no"], cwd=root, timeout=180))
    if (root / "package.json").is_file():
        results.append(run_cmd(["npm", "test", "--silent"], cwd=root, timeout=180))
    # ruff optional
    ruff = run_cmd(["python", "-m", "ruff", "check", "."], cwd=root, timeout=60)
    if "No module named" not in str(ruff.get("stderr") or ""):
        results.append(ruff)
    ok = all(r.get("ok") for r in results) if results else True
    return {
        "ok": ok,
        "gates": results,
        "ran": len(results),
        "contract": "superai.result.v1",
    }
