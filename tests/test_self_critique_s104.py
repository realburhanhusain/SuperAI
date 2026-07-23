"""
Unit tests for Self-Critique Pass Before Claiming Done (S104).
"""

from __future__ import annotations

import tempfile
import pytest

from core.self_critique import run_self_critique_pass


def test_self_critique_clean_file():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write(
            '"""Module docstring."""\n\n'
            "def sample_function() -> bool:\n"
            '    """Func docstring."""\n'
            "    return True\n"
        )
        tf_path = tf.name

    res = run_self_critique_pass(tf_path)
    assert res.passed is True
    assert res.score == 100.0
    assert "return_annotations" in (res.checks_run or [])


def test_self_critique_missing_docstring():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write("def no_docstring():\n    return False\n")
        tf_path = tf.name

    res = run_self_critique_pass(tf_path, strict=True)
    assert res.passed is False
    assert len(res.findings) >= 1
    assert any(f.category == "DOCS" for f in res.findings)


def test_self_critique_bare_except_and_mutable_default():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write(
            '"""mod."""\n'
            "def bad(x=[]) -> None:\n"
            '    """d."""\n'
            "    try:\n"
            "        1/0\n"
            "    except:\n"
            "        pass\n"
        )
        tf_path = tf.name
    res = run_self_critique_pass(tf_path, strict=True)
    assert res.passed is False
    cats = {f.category for f in res.findings}
    assert "ERROR_HANDLING" in cats
