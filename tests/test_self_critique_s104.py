"""
Unit tests for Self-Critique Pass Before Claiming Done (S104).
"""

from __future__ import annotations

import tempfile
import pytest

from core.self_critique import run_self_critique_pass


def test_self_critique_clean_file():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write('"""Module docstring."""\n\ndef sample_function():\n    """Func docstring."""\n    return True\n')
        tf_path = tf.name

    res = run_self_critique_pass(tf_path)
    assert res.passed is True
    assert res.score == 100.0


def test_self_critique_missing_docstring():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write("def no_docstring():\n    return False\n")
        tf_path = tf.name

    res = run_self_critique_pass(tf_path)
    assert len(res.findings) >= 1
    assert any(f.category == "DOCS" for f in res.findings)
