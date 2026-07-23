"""
Auto Test Discovery and Impacted Test Runner (V6 S105).

Automatically maps modified source files to impacted test files in tests/.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def _get_superai_root() -> Path:
    """Helper to locate SuperAI repository root directory."""
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "pyproject.toml").exists() or (curr / "tests").exists():
            return curr
        curr = curr.parent
    return Path.cwd()


def find_impacted_tests(
    modified_files: List[str], repo_root: Optional[Path] = None
) -> List[str]:
    """Given a list of modified source files, discover impacted test files."""
    if not modified_files:
        return []

    root = repo_root or _get_superai_root()
    tests_dir = root / "tests"

    impacted: set[str] = set()

    for mod_file in modified_files:
        file_path = Path(mod_file)
        stem = file_path.stem.lower()

        # If modified file is already a test file, include it directly
        if stem.startswith("test_") or "test" in stem:
            target = tests_dir / file_path.name if not file_path.is_absolute() else file_path
            if target.exists():
                impacted.add(str(target))
            else:
                impacted.add(str(file_path))
            continue

        # Look for matching tests/test_<stem>*.py files
        if tests_dir.exists():
            for test_file in tests_dir.glob("*.py"):
                t_stem = test_file.stem.lower()
                if stem in t_stem or t_stem.replace("test_", "").startswith(stem):
                    impacted.add(str(test_file))

    return sorted(list(impacted))


def run_impacted_tests(
    modified_files: List[str], repo_root: Optional[Path] = None
) -> Dict[str, Any]:
    """Discover and execute impacted pytest files."""
    impacted = find_impacted_tests(modified_files, repo_root=repo_root)
    if not impacted:
        return {
            "ok": True,
            "impacted_tests": [],
            "message": "No impacted test files discovered.",
            "passed": 0,
            "total": 0,
            "count": 0,
        }

    import pytest

    # Run pytest on the discovered test files
    ret_code = pytest.main(["-q", "--tb=short"] + impacted)
    passed = ret_code == 0

    return {
        "ok": passed,
        "impacted_tests": impacted,
        "exit_code": ret_code,
        "count": len(impacted),
        "status": "success" if passed else "failed",
    }
