"""
Unit tests for Post-Edit Lint & Typecheck Integration (S106).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from core.lint_typecheck import check_python_syntax_and_ast, run_post_edit_checks


def test_lint_clean_file():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write("def foo(x: int) -> int:\n    return 42\n")
        tf_path = tf.name

    res = check_python_syntax_and_ast(tf_path)
    assert res.is_clean is True
    assert len(res.issues) == 0


def test_lint_missing_annotations():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write("def foo(x):\n    return x\n")
        tf_path = tf.name

    res = check_python_syntax_and_ast(tf_path)
    assert res.is_clean is False
    codes = {i.code for i in res.issues}
    assert "ANN001" in codes or "ANN201" in codes


def test_lint_syntax_error():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write("def bad_func(\n")
        tf_path = tf.name

    res = check_python_syntax_and_ast(tf_path)
    assert res.is_clean is False
    assert len(res.issues) == 1
    assert res.issues[0].code == "E999"


def test_lint_bare_except():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write("try:\n    x = 1\nexcept:\n    pass\n")
        tf_path = tf.name

    res = check_python_syntax_and_ast(tf_path)
    assert res.is_clean is False
    assert any(i.code == "E722" for i in res.issues)


def test_run_post_edit_checks_batch():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write("x = 10\n")
        tf_path = tf.name

    batch_res = run_post_edit_checks([tf_path])
    assert batch_res["ok"] is True
    assert batch_res["file_count"] == 1
