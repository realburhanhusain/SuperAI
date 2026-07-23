"""
Unit tests for Symbol-Aware Code Navigation (S108).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from core.symbol_nav import index_symbols_in_file, search_symbols


def test_index_symbols_in_file():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write(
            "class MyClass:\n"
            "    def my_method(self):\n"
            "        pass\n\n"
            "def standalone_func():\n"
            "    pass\n"
        )
        tf_path = tf.name

    symbols = index_symbols_in_file(tf_path)
    assert len(symbols) >= 2
    kinds = [s.kind for s in symbols]
    names = [s.name for s in symbols]
    assert "class" in kinds
    assert "MyClass" in names
    assert "standalone_func" in names
    # Methods must appear as method kind only (not double-counted as function)
    assert "method" in kinds
    assert "MyClass.my_method" in names
    assert names.count("my_method") == 0  # bare method name must not appear as function


def test_search_symbols(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    py_file = src_dir / "sample.py"
    py_file.write_text("def find_me_helper():\n    pass\n", encoding="utf-8")

    results = search_symbols("find_me", root_dir=str(tmp_path))
    assert len(results) >= 1
    assert "find_me_helper" in results[0].name
