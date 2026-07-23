"""
Auto Test Discovery and Impacted Test Runner (V6 S105).

Maps modified source files → impacted tests with exact/prefix/path rules
and an optional alias table for SuperAI module→test conventions.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Known module stem → test file stem patterns (SuperAI conventions)
_ALIAS_MAP: Dict[str, List[str]] = {
    "knowledge_graph": ["knowledge_graph_p1", "knowledge_graph"],
    "cognify": ["cognify_p2", "cognify"],
    "session_memory": ["session_memory_p3", "session_memory"],
    "recall_router": ["recall_router_p4", "recall_router"],
    "ingest": ["ingest_p5", "ingest"],
    "ontology": ["ontology_p6", "ontology"],
    "memory_dataset": ["memory_dataset_p7", "memory_dataset"],
    "session_capture": ["session_capture_p8", "session_capture"],
    "memory_eval": ["memory_eval_offline", "memory_eval"],
    "memory_otel": ["phase9_memory", "memory_otel"],
    "memory_cloud": ["phase9_memory", "memory_cloud"],
    "host_hooks": ["phase9_memory", "host_hooks"],
    "exit_codes": ["exit_codes_m080", "exit_codes"],
    "self_critique": ["self_critique_s104", "self_critique"],
    "auto_test_runner": ["auto_test_runner_s105", "auto_test_runner"],
    "ci_fixer": ["ci_fixer_s109", "ci_fixer"],
    "dep_upgrade": ["dep_upgrade_s112", "dep_upgrade"],
    "license_check": ["license_check_s115", "license_check"],
    "command_budget": ["command_budget_s132", "command_budget"],
    "prompt_injection": ["prompt_injection_m015", "prompt_injection"],
}


def _get_superai_root() -> Path:
    """Helper to locate SuperAI repository root directory."""
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "pyproject.toml").exists() or (curr / "tests").exists():
            return curr
        curr = curr.parent
    return Path.cwd()


def _norm_stem(path: Path) -> str:
    stem = path.stem.lower()
    # strip common suffixes from source modules
    for suf in ("_cmd", "_cli", "_app"):
        if stem.endswith(suf):
            stem = stem[: -len(suf)]
    return stem


def _match_test_body(body: str, stem: str, aliases: List[str]) -> bool:
    """True if test file body matches stem/aliases under tight rules."""
    candidates = [stem] + aliases
    for c in candidates:
        c = c.lower()
        if not c:
            continue
        if body == c:
            return True
        # test_foo_p1, test_foo_s104, test_foo_m080
        if re.match(rf"^{re.escape(c)}(_[a-z0-9]+)+$", body):
            return True
        if body.startswith(c + "_") or body.startswith(c + "-"):
            return True
        # reverse: knowledge_graph_p1 body ends with module
        if body.endswith("_" + c) and len(c) >= 4:
            return True
    return False


def find_impacted_tests(
    modified_files: List[str], repo_root: Optional[Path] = None
) -> List[str]:
    """Given modified source files, discover impacted test files (tight match)."""
    if not modified_files:
        return []

    root = repo_root or _get_superai_root()
    tests_dir = root / "tests"
    impacted: Set[str] = set()

    for mod_file in modified_files:
        file_path = Path(mod_file)
        stem = _norm_stem(file_path)

        # Modified path already a test
        if stem.startswith("test_") or file_path.name.startswith("test_"):
            target = (
                tests_dir / file_path.name
                if not file_path.is_absolute()
                else file_path
            )
            if target.exists():
                impacted.add(str(target.resolve()))
            elif file_path.exists():
                impacted.add(str(file_path.resolve()))
            continue

        aliases = list(_ALIAS_MAP.get(stem, []))
        # also try parent dir name for packages (core/foo.py)
        if file_path.parent.name and file_path.parent.name not in {
            "core",
            "cli",
            "src",
            "tests",
        }:
            aliases.append(file_path.parent.name.lower())

        if not tests_dir.exists():
            continue

        for test_file in tests_dir.glob("test_*.py"):
            t_stem = test_file.stem.lower()
            body = t_stem[5:] if t_stem.startswith("test_") else t_stem
            if _match_test_body(body, stem, aliases):
                impacted.add(str(test_file.resolve()))

        # If nothing matched and file under src/core/, try test_* containing stem
        # only when stem is long enough to avoid over-match
        if not any(stem in Path(x).stem for x in impacted) and len(stem) >= 6:
            for test_file in tests_dir.glob("test_*.py"):
                body = test_file.stem.lower()[5:]
                # token boundary: stem as whole token in body
                if re.search(rf"(^|_)({re.escape(stem)})(_|$)", body):
                    impacted.add(str(test_file.resolve()))

    return sorted(impacted)


def run_impacted_tests(
    modified_files: List[str],
    repo_root: Optional[Path] = None,
    use_subprocess: bool = True,
    timeout: int = 120,
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
            "matcher": "exact_prefix_alias",
        }

    if use_subprocess:
        try:
            cmd = [sys.executable, "-m", "pytest", "-q", "--tb=short"] + impacted
            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=max(30, int(timeout))
            )
            ret_code = res.returncode
            passed = ret_code == 0
            msg = res.stdout if passed else (res.stderr or res.stdout or "Pytest failure")
        except Exception as e:
            return {
                "ok": False,
                "impacted_tests": impacted,
                "exit_code": 1,
                "count": len(impacted),
                "message": str(e),
                "status": "failed",
                "matcher": "exact_prefix_alias",
            }
    else:
        import pytest

        ret_code = pytest.main(["-q", "--tb=short"] + impacted)
        passed = ret_code == 0
        msg = "Success" if passed else "Pytest failure"

    return {
        "ok": passed,
        "impacted_tests": impacted,
        "exit_code": ret_code,
        "count": len(impacted),
        "message": msg,
        "status": "success" if passed else "failed",
        "matcher": "exact_prefix_alias",
    }
