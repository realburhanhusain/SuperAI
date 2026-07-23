"""
Unit tests for Log Triage & Stack Trace Analyzer (S124).
"""

from __future__ import annotations

import tempfile
import pytest

from core.log_triage import triage_log_file, triage_stack_trace


def test_triage_python_traceback():
    log_content = """
2026-07-23 ERROR worker: Task failed
Traceback (most recent call last):
  File "src/core/main.py", line 42, in process_data
    val = data["key"]
KeyError: 'key'
"""
    res = triage_stack_trace(log_content)
    assert res.has_error is True
    assert res.exception_type == "KeyError"
    assert res.top_frame is not None
    assert res.top_frame.line_number == 42
    assert "KeyError" in res.exception_type or "key" in res.exception_message
    assert "dictionary" in res.suggested_fix.lower() or "key" in res.suggested_fix.lower()


def test_triage_attribute_error():
    log_content = """
Traceback (most recent call last):
  File "src/core/agent.py", line 100, in run
    agent.start()
AttributeError: 'NoneType' object has no attribute 'start'
"""
    res = triage_stack_trace(log_content)
    assert res.has_error is True
    assert res.exception_type == "AttributeError"
    assert "None" in res.suggested_fix or "initialized" in res.suggested_fix


def test_triage_log_file():
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as tf:
        tf.write("Traceback (most recent call last):\n  File \"app.py\", line 10, in foo\n    1/0\nZeroDivisionError: division by zero\n")
        tf_path = tf.name

    res = triage_log_file(tf_path)
    assert res.has_error is True
    assert res.exception_type == "ZeroDivisionError"
    assert res.top_frame.line_number == 10
