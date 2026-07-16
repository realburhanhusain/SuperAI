"""Quality gates after edits (V6 S105/S106) — auto test discovery + lint."""

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


def discover_tests(cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Auto-discover test entrypoints for the project."""
    root = Path(cwd or Path.cwd())
    found: List[str] = []
    if (root / "tests").is_dir():
        found.append("pytest:tests/")
    if (root / "pytest.ini").is_file() or (root / "pyproject.toml").is_file():
        if "pytest:tests/" not in found:
            found.append("pytest:.")
    if (root / "package.json").is_file():
        found.append("npm:test")
    if (root / "Cargo.toml").is_file():
        found.append("cargo:test")
    if (root / "go.mod").is_file():
        found.append("go:test")
    return {"ok": True, "discovered": found, "cwd": str(root)}


def detect_and_run(cwd: Optional[Path] = None, *, lint: bool = True) -> Dict[str, Any]:
    """Run discovered tests + optional lint/typecheck after edits."""
    root = Path(cwd or Path.cwd())
    results: List[Dict[str, Any]] = []
    disc = discover_tests(root)
    for item in disc.get("discovered") or []:
        if item.startswith("pytest:"):
            target = item.split(":", 1)[1]
            results.append(
                run_cmd(
                    ["python", "-m", "pytest", target, "-q", "--tb=no"],
                    cwd=root,
                    timeout=180,
                )
            )
        elif item == "npm:test":
            results.append(run_cmd(["npm", "test", "--silent"], cwd=root, timeout=180))
        elif item == "cargo:test":
            results.append(run_cmd(["cargo", "test", "--quiet"], cwd=root, timeout=300))
        elif item == "go:test":
            results.append(run_cmd(["go", "test", "./..."], cwd=root, timeout=300))

    if lint:
        # ruff
        ruff = run_cmd(["python", "-m", "ruff", "check", "."], cwd=root, timeout=60)
        if "No module named" not in str(ruff.get("stderr") or "") and "error" not in ruff:
            results.append({**ruff, "gate": "ruff"})
        # mypy optional
        mypy = run_cmd(["python", "-m", "mypy", ".", "--no-error-summary"], cwd=root, timeout=90)
        if "No module named" not in str(mypy.get("stderr") or "") and mypy.get("returncode") is not None:
            # only record if mypy is installed (returncode present and not import error)
            if "No module named mypy" not in str(mypy.get("stderr") or ""):
                results.append({**mypy, "gate": "mypy"})

    ok = all(r.get("ok") for r in results) if results else True
    return {
        "ok": ok,
        "gates": results,
        "ran": len(results),
        "discovered": disc.get("discovered"),
        "contract": "superai.result.v1",
    }


def run_after_edits(paths: Optional[List[str]] = None, cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Entry used by agent post-edit hook."""
    out = detect_and_run(cwd=cwd, lint=True)
    out["edited_paths"] = list(paths or [])
    return out
