"""
Unit tests for Dependency Upgrade Assistant (S112).
"""

from __future__ import annotations

import tempfile
import pytest

from core.dep_upgrade import check_upgradable_dependencies


def test_check_upgradable_requirements():
    with tempfile.NamedTemporaryFile("w", suffix="requirements.txt", delete=False) as tf:
        tf.write("pytest>=8.0.0\ntyper==0.9.0\n")
        tf_path = tf.name

    res = check_upgradable_dependencies(tf_path)
    assert res.total_dependencies == 2
    assert len(res.recommendations) == 2
    assert res.recommendations[0].package_name == "pytest"


def test_check_upgradable_package_json():
    with tempfile.NamedTemporaryFile("w", suffix="package.json", delete=False) as tf:
        tf.write('{"dependencies": {"express": "^4.18.0"}}')
        tf_path = tf.name

    res = check_upgradable_dependencies(tf_path)
    assert res.total_dependencies == 1
    assert len(res.recommendations) == 1
    assert res.recommendations[0].package_name == "express"


def test_check_upgradable_pyproject_pep621(tmp_path):
    p = tmp_path / "pyproject.toml"
    p.write_text(
        """
[project]
name = "demo"
dependencies = [
  "typer>=0.12",
  "rich>=13.0",
]
""",
        encoding="utf-8",
    )
    res = check_upgradable_dependencies(str(p))
    assert res.total_dependencies == 2
    names = {r.package_name for r in res.recommendations}
    assert "typer" in names
    assert "rich" in names
    assert not any(n.startswith('"') for n in names)
