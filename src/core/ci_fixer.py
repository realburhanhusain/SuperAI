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
    pytest_failed_pattern = re.compile(r"FAILED\s+([^\s:]+)(?::([0-9]+))?(?:::[^\s]+)?(?:\s+-\s+(.*))?")
    import_err_pattern = re.compile(r"ModuleNotFoundError:\s+No module named\s+'([^']+)'")
    syntax_err_pattern = re.compile(r"SyntaxError:\s+(.*)\s+in\s+([^\s,:]+)(?::([0-9]+))?")
    timeout_err_pattern = re.compile(r"(?i)(timed out|timeout)\s*(?:after\s*([0-9]+)s)?")

    for idx, line in enumerate(lines):
        line_str = line.strip()

        match_failed = pytest_failed_pattern.search(line_str)
        if match_failed:
            f_path = match_failed.group(1)
            line_no = int(match_failed.group(2)) if match_failed.group(2) else 0
            err_msg = match_failed.group(3) or "Test assertion failed"

            # Check if previous lines contain file:line info
            if line_no == 0 and idx > 0:
                line_match = re.search(r"([^\s:]+\.py):([0-9]+):", lines[idx - 1])
                if line_match:
                    line_no = int(line_match.group(2))

            findings.append(
                CIFailureFinding(
                    failure_type="TEST_FAILURE",
                    failing_file=f_path,
                    line_number=line_no,
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

        match_syntax = syntax_err_pattern.search(line_str)
        if match_syntax:
            s_msg = match_syntax.group(1)
            s_file = match_syntax.group(2)
            s_line = int(match_syntax.group(3)) if match_syntax.group(3) else 0
            findings.append(
                CIFailureFinding(
                    failure_type="SYNTAX_ERROR",
                    failing_file=s_file,
                    line_number=s_line,
                    error_summary=f"Syntax error: {s_msg}",
                    suggested_patch=f"Fix invalid python syntax in {s_file} at line {s_line}.",
                )
            )

        match_timeout = timeout_err_pattern.search(line_str)
        if match_timeout and not any(f.failure_type == "TIMEOUT" for f in findings):
            findings.append(
                CIFailureFinding(
                    failure_type="TIMEOUT",
                    failing_file="CLI / Test Subprocess",
                    line_number=0,
                    error_summary="Command or test run timed out",
                    suggested_patch="Increase test timeout or optimize slow synchronous blocking operations.",
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
