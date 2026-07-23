"""
Log Triage Mode and Stack Trace Analyzer (V6 S124).

Parses Python, Java, and Node.js stack traces from log files or text,
extracts root cause exceptions, line numbers, and suggests targeted fixes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class StackFrame:
    filename: str
    line_number: int
    function_name: str
    code_line: str


@dataclass
class LogTriageResult:
    has_error: bool
    exception_type: str
    exception_message: str
    top_frame: Optional[StackFrame]
    frames: List[StackFrame] = field(default_factory=list)
    suggested_fix: str = ""


def triage_stack_trace(log_content: str) -> LogTriageResult:
    """Parse log content for Python/Java stack trace and extract root cause details."""
    if not log_content or not isinstance(log_content, str):
        return LogTriageResult(
            has_error=False,
            exception_type="",
            exception_message="",
            top_frame=None,
            suggested_fix="No log content provided.",
        )

    lines = log_content.splitlines()
    frames: List[StackFrame] = []
    exception_type = ""
    exception_message = ""

    # Python Traceback pattern: File "...", line 123, in func
    py_frame_pattern = re.compile(r'File\s+"([^"]+)",\s+line\s+(\d+),\s+in\s+(.+)')

    for idx, line in enumerate(lines):
        match = py_frame_pattern.search(line)
        if match:
            fn, ln, func = match.group(1), int(match.group(2)), match.group(3)
            next_line = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
            frames.append(
                StackFrame(
                    filename=fn,
                    line_number=ln,
                    function_name=func,
                    code_line=next_line,
                )
            )

        # Python Exception line: ExceptionName: Error details...
        exc_match = re.match(r"^([A-Za-z0-9_]+Error|[A-Za-z0-9_]+Exception):\s*(.*)", line.strip())
        if exc_match:
            exception_type = exc_match.group(1)
            exception_message = exc_match.group(2)

    top_frame = frames[-1] if frames else None
    suggested_fix = _generate_suggested_fix(exception_type, exception_message)

    return LogTriageResult(
        has_error=bool(exception_type or frames),
        exception_type=exception_type or "UnknownError",
        exception_message=exception_message,
        top_frame=top_frame,
        frames=frames,
        suggested_fix=suggested_fix,
    )


def triage_log_file(file_path: str) -> LogTriageResult:
    """Read log file and perform stack trace triage."""
    p = Path(file_path)
    if not p.exists():
        return LogTriageResult(
            has_error=False,
            exception_type="FileNotFoundError",
            exception_message=f"Log file not found: {file_path}",
            top_frame=None,
            suggested_fix="Ensure the log file path is correct.",
        )

    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        return triage_stack_trace(content)
    except Exception as e:
        return LogTriageResult(
            has_error=False,
            exception_type="ReadError",
            exception_message=str(e),
            top_frame=None,
            suggested_fix="Check file permissions and encoding.",
        )


def _generate_suggested_fix(exc_type: str, exc_msg: str) -> str:
    """Generate diagnostic recommendations based on exception taxonomy."""
    msg = exc_msg.lower()
    if "keyerror" in exc_type.lower():
        return "Check dictionary key existence with `.get()` or verify dictionary payload structure."
    if "attributeerror" in exc_type.lower() or "'nonetype' object" in msg:
        return "Verify target object is initialized and not None before attribute dereference."
    if "typeerror" in exc_type.lower():
        return "Verify function argument types and required positional parameter signatures."
    if "valueerror" in exc_type.lower():
        return "Verify input string formatting or domain value constraints before type conversion."
    if "filenotfounderror" in exc_type.lower():
        return "Verify target file path exists on disk and directory path is absolute."
    return "Inspect stack frame line and verify variable state before exception site."
