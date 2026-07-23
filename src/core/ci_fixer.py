"""
Fix CI Failure from Log Paste (V6 S109).

Parses CI logs, harvests traceback lines, and produces structured
repair plans (suggested patch snippets — advice + optional apply plan).
Honest: does not auto-edit the repo unless caller applies the plan.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CIFailureFinding:
    failure_type: str  # TEST_FAILURE | SYNTAX_ERROR | IMPORT_ERROR | TIMEOUT | ASSERTION
    failing_file: str
    line_number: int
    error_summary: str
    suggested_patch: str
    test_name: str = ""
    repair_steps: List[str] = field(default_factory=list)
    patch_snippet: str = ""


@dataclass
class CIFixerResult:
    has_failures: bool
    total_failures: int
    findings: List[CIFailureFinding] = field(default_factory=list)
    summary_report: str = ""
    repair_plan: List[Dict[str, Any]] = field(default_factory=list)


def _patch_for_import(mod: str) -> tuple[str, str, List[str]]:
    snippet = f'# pyproject.toml / requirements.txt\n# add dependency:\n#   "{mod}"\n'
    steps = [
        f"Add '{mod}' to project dependencies (pyproject.toml or requirements.txt)",
        f"Run: pip install {mod}",
        "Re-run the failing test suite",
    ]
    advice = f"Add '{mod}' to dependency manifest and run `pip install {mod}`."
    return advice, snippet, steps


def _patch_for_assertion(f_path: str, line_no: int, err: str) -> tuple[str, str, List[str]]:
    snippet = (
        f"# {f_path}:{line_no}\n"
        f"# Failing assertion: {err[:120]}\n"
        f"# 1) Open the test and confirm expected vs actual.\n"
        f"# 2) Fix production code or update assertion intentionally.\n"
    )
    steps = [
        f"Open {f_path}" + (f" around line {line_no}" if line_no else ""),
        f"Inspect assertion: {err[:160]}",
        f"Run: pytest {f_path} -vv",
    ]
    advice = f"Run `pytest {f_path} -vv` and update assertion or fix production code."
    return advice, snippet, steps


def analyze_ci_log_paste(log_text: str) -> CIFixerResult:
    """Analyze raw CI log text, identify failures, and generate repair plans."""
    if not log_text or not isinstance(log_text, str):
        return CIFixerResult(
            has_failures=False, total_failures=0, summary_report="No log content provided."
        )

    findings: List[CIFailureFinding] = []
    lines = log_text.splitlines()

    pytest_failed_pattern = re.compile(
        r"FAILED\s+([^\s:]+)(?::([0-9]+))?(?:::([^\s]+))?(?:\s+-\s+(.*))?"
    )
    import_err_pattern = re.compile(
        r"ModuleNotFoundError:\s+No module named\s+'([^']+)'"
    )
    syntax_err_pattern = re.compile(
        r"SyntaxError:\s+(.*)\s+in\s+([^\s,:]+)(?::([0-9]+))?"
    )
    # also: File "x.py", line N\n    ...\nSyntaxError: ...
    syntax_err_simple = re.compile(r"SyntaxError:\s+(.*)")
    timeout_err_pattern = re.compile(
        r"(?i)(timed out|timeout)\s*(?:after\s*([0-9]+)s)?"
    )
    assert_pattern = re.compile(r"AssertionError(?::\s*(.*))?")
    tb_file_line = re.compile(r'File\s+"([^"]+\.py)",\s+line\s+(\d+)', re.I)
    tb_file_line_alt = re.compile(r"([^\s:]+\.py):(\d+):")

    def _harvest_traceback_line(idx: int) -> tuple[str, int]:
        for j in range(idx - 1, max(-1, idx - 40), -1):
            prev = lines[j].strip()
            m = tb_file_line.search(prev)
            if m:
                return m.group(1), int(m.group(2))
            m2 = tb_file_line_alt.search(prev)
            if m2:
                return m2.group(1), int(m2.group(2))
        return "", 0

    for idx, line in enumerate(lines):
        line_str = line.strip()

        match_failed = pytest_failed_pattern.search(line_str)
        if match_failed:
            f_path = match_failed.group(1)
            line_no = int(match_failed.group(2)) if match_failed.group(2) else 0
            test_name = match_failed.group(3) or ""
            err_msg = match_failed.group(4) or "Test assertion failed"
            if line_no == 0:
                tb_path, tb_line = _harvest_traceback_line(idx)
                if tb_line:
                    line_no = tb_line
                    if tb_path:
                        f_path = tb_path
            ftype = "TEST_FAILURE"
            advice, snippet, steps = _patch_for_assertion(f_path, line_no, err_msg)
            findings.append(
                CIFailureFinding(
                    failure_type=ftype,
                    failing_file=f_path,
                    line_number=line_no,
                    error_summary=err_msg,
                    suggested_patch=advice,
                    test_name=test_name,
                    repair_steps=steps,
                    patch_snippet=snippet,
                )
            )

        match_import = import_err_pattern.search(line_str)
        if match_import:
            missing_mod = match_import.group(1)
            advice, snippet, steps = _patch_for_import(missing_mod)
            findings.append(
                CIFailureFinding(
                    failure_type="IMPORT_ERROR",
                    failing_file="pyproject.toml / requirements.txt",
                    line_number=0,
                    error_summary=f"Missing dependency module '{missing_mod}'",
                    suggested_patch=advice,
                    repair_steps=steps,
                    patch_snippet=snippet,
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
                    repair_steps=[
                        f"Open {s_file}:{s_line}",
                        "Fix syntax (brackets/indent/colons)",
                        f"Run: python -m py_compile {s_file}",
                    ],
                    patch_snippet=f"# {s_file}:{s_line}\n# SyntaxError: {s_msg}\n",
                )
            )
        elif syntax_err_simple.search(line_str) and not any(
            f.failure_type == "SYNTAX_ERROR" for f in findings
        ):
            tb_path, tb_line = _harvest_traceback_line(idx)
            s_msg = syntax_err_simple.search(line_str).group(1)  # type: ignore[union-attr]
            findings.append(
                CIFailureFinding(
                    failure_type="SYNTAX_ERROR",
                    failing_file=tb_path or "unknown.py",
                    line_number=tb_line,
                    error_summary=f"Syntax error: {s_msg}",
                    suggested_patch="Fix syntax at harvested traceback location.",
                    repair_steps=["Open harvested file:line", "Fix syntax", "Re-run CI"],
                    patch_snippet=f"# {tb_path}:{tb_line}\n# SyntaxError: {s_msg}\n",
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
                    suggested_patch=(
                        "Increase test timeout or optimize slow blocking operations."
                    ),
                    repair_steps=[
                        "Identify slow test via pytest --durations=20",
                        "Raise timeout or mock network I/O",
                        "Re-run suite",
                    ],
                    patch_snippet="# pytest.ini / pyproject.toml\n# add: timeout = 120\n",
                )
            )

        # Standalone AssertionError lines (not only FAILED summary)
        m_assert = assert_pattern.search(line_str)
        if m_assert and "FAILED" not in line_str:
            tb_path, tb_line = _harvest_traceback_line(idx)
            if tb_path:
                err = m_assert.group(1) or "assertion failed"
                advice, snippet, steps = _patch_for_assertion(tb_path, tb_line, err)
                # de-dupe if already have same file:line
                if not any(
                    f.failing_file == tb_path and f.line_number == tb_line
                    for f in findings
                ):
                    findings.append(
                        CIFailureFinding(
                            failure_type="ASSERTION",
                            failing_file=tb_path,
                            line_number=tb_line,
                            error_summary=err,
                            suggested_patch=advice,
                            repair_steps=steps,
                            patch_snippet=snippet,
                        )
                    )

    has_fail = len(findings) > 0
    repair_plan = [
        {
            "type": f.failure_type,
            "file": f.failing_file,
            "line": f.line_number,
            "test": f.test_name,
            "steps": f.repair_steps,
            "patch_snippet": f.patch_snippet,
            "advice": f.suggested_patch,
        }
        for f in findings
    ]
    report = (
        f"CI Log Analysis: {len(findings)} failure(s) detected.\n"
        + "\n".join(
            f"• [{f.failure_type}] {f.failing_file}:{f.line_number} — {f.suggested_patch}"
            for f in findings
        )
        if has_fail
        else "CI Log Analysis: Clean run, no build/test failures detected."
    )

    return CIFixerResult(
        has_failures=has_fail,
        total_failures=len(findings),
        findings=findings,
        summary_report=report,
        repair_plan=repair_plan,
    )


def analyze_ci_log_file(file_path: str) -> CIFixerResult:
    """Read log file and analyze CI failures."""
    p = Path(file_path)
    if not p.exists():
        return CIFixerResult(
            has_failures=False,
            total_failures=0,
            summary_report=f"Log file not found: {file_path}",
        )
    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        return analyze_ci_log_paste(content)
    except Exception as e:
        return CIFixerResult(
            has_failures=False, total_failures=0, summary_report=f"Read error: {e}"
        )


def write_repair_plan(result: CIFixerResult, dest: str) -> Dict[str, Any]:
    """Write a JSON repair plan for operators (does not modify source)."""
    import json

    path = Path(dest)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "product": "ci_fixer_repair_plan",
        "has_failures": result.has_failures,
        "total_failures": result.total_failures,
        "summary": result.summary_report,
        "plan": result.repair_plan,
        "findings": [asdict(f) for f in result.findings],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "path": str(path.resolve()), "items": len(result.repair_plan)}
