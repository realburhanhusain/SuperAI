"""
Fix CI Failure from Log Paste (V6 S109).

Parses raw CI build logs, extracts failing test files, error tracebacks,
and generates targeted resolution recommendations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CIFailureFinding:
    failure_type: str  # TEST_FAILURE | SYNTAX_ERROR | IMPORT_ERROR | TIMEOUT
    failing_file: str
    line_number: int
    error_summary: str
    suggested_patch: str


@dataclass
class CIFixerResult:
    has_failures: bool
    total_failures: int
    findings: List[CIFailureFinding] = field(default_factory=list)
    summary_report: str = ""


def analyze_ci_log_paste(log_text: str) -> CIFixerResult:
    """Analyze raw CI log text, identify failing lines, and generate fix instructions."""
    if not log_text or not isinstance(log_text, str):
        return CIFixerResult(has_failures=False, total_failures=0, summary_report="No log content provided.")

    findings: List[CIFailureFinding] = []
    lines = log_text.splitlines()

    # Pytest failure pattern: FAILED tests/test_foo.py::test_bar - AssertionError: ...
    pytest_failed_pattern = re.compile(r"FAILED\s+([^\s:]+)(?:::[^\s]+)?(?:\s+-\s+(.*))?")
    # Import error pattern: ModuleNotFoundError: No module named 'foo'
    import_err_pattern = re.compile(r"ModuleNotFoundError:\s+No module named\s+'([^']+)'")

    for idx, line in enumerate(lines):
        line_str = line.strip()

        match_failed = pytest_failed_pattern.search(line_str)
        if match_failed:
            f_path = match_failed.group(1)
            err_msg = match_failed.group(2) or "Test assertion failed"
            findings.append(
                CIFailureFinding(
                    failure_type="TEST_FAILURE",
                    failing_file=f_path,
                    line_number=0,
                    error_summary=err_msg,
                    suggested_patch=f"Run `pytest {f_path}` locally and update assertion expectations.",
                )
            )

        match_import = import_err_pattern.search(line_str)
        if match_import:
            missing_mod = match_import.group(1)
            findings.append(
                CIFailureFinding(
                    failure_type="IMPORT_ERROR",
                    failing_file="pyproject.toml / requirements.txt",
                    line_number=0,
                    error_summary=f"Missing dependency module '{missing_mod}'",
                    suggested_patch=f"Add '{missing_mod}' to dependency manifest and run `pip install {missing_mod}`.",
                )
            )

    has_fail = len(findings) > 0
    report = (
        f"CI Log Analysis: {len(findings)} failure(s) detected.\n"
        + "\n".join(f"• [{f.failure_type}] {f.failing_file}: {f.suggested_patch}" for f in findings)
        if has_fail
        else "CI Log Analysis: Clean run, no build/test failures detected."
    )

    return CIFixerResult(
        has_failures=has_fail,
        total_failures=len(findings),
        findings=findings,
        summary_report=report,
    )


def analyze_ci_log_file(file_path: str) -> CIFixerResult:
    """Read log file and analyze CI failures."""
    p = Path(file_path)
    if not p.exists():
        return CIFixerResult(has_failures=False, total_failures=0, summary_report=f"Log file not found: {file_path}")

    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        return analyze_ci_log_paste(content)
    except Exception as e:
        return CIFixerResult(has_failures=False, total_failures=0, summary_report=f"Read error: {e}")
