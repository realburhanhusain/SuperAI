"""
Jupyter notebook cell runner (N25).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .workspace import assert_in_workspace


def list_cells(path: str | Path) -> List[Dict[str, Any]]:
    p = assert_in_workspace(path, label="notebook")
    data = json.loads(p.read_text(encoding="utf-8"))
    cells = []
    for i, c in enumerate(data.get("cells") or []):
        src = c.get("source") or []
        if isinstance(src, list):
            src = "".join(src)
        cells.append(
            {
                "index": i,
                "cell_type": c.get("cell_type"),
                "preview": str(src)[:200],
            }
        )
    return cells


def run_code_cell(code: str, timeout: float = 30.0) -> Dict[str, Any]:
    """Execute a Python code cell in a restricted subprocess."""
    import subprocess
    import sys
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp = f.name
    try:
        proc = subprocess.run(
            [sys.executable, tmp],
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": (proc.stdout or "")[:8000],
            "stderr": (proc.stderr or "")[:4000],
            "exit_code": proc.returncode,
        }
    finally:
        Path(tmp).unlink(missing_ok=True)


def run_notebook_cell(path: str | Path, index: int = 0) -> Dict[str, Any]:
    p = assert_in_workspace(path, label="notebook")
    data = json.loads(p.read_text(encoding="utf-8"))
    cells = data.get("cells") or []
    if index < 0 or index >= len(cells):
        return {"ok": False, "error": "cell index out of range"}
    cell = cells[index]
    if cell.get("cell_type") != "code":
        return {"ok": False, "error": "not a code cell"}
    src = cell.get("source") or []
    if isinstance(src, list):
        src = "".join(src)
    return run_code_cell(str(src))
