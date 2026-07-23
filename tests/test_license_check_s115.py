"""
Unit tests for License & Compliance Check on Dependencies (S115).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from core.license_check import scan_dependency_licenses


def test_scan_clean_package_json():
    with tempfile.NamedTemporaryFile("w", suffix="package.json", delete=False) as tf:
        tf.write('{"dependencies": {"express": "^4.18.2", "lodash": "^4.17.21"}}')
        tf_path = tf.name

    res = scan_dependency_licenses(tf_path)
    assert res.is_compliant is True
    assert res.total_packages == 2


def test_scan_copyleft_package_json():
    with tempfile.NamedTemporaryFile("w", suffix="package.json", delete=False) as tf:
        tf.write('{"dependencies": {"gpl-lib": "^1.0.0"}}')
        tf_path = tf.name

    res = scan_dependency_licenses(tf_path)
    assert res.is_compliant is False
    assert any(i.category == "COPYLEFT" for i in res.issues)


def test_scan_requirements_txt():
    with tempfile.NamedTemporaryFile("w", suffix="requirements.txt", delete=False) as tf:
        tf.write("requests==2.31.0\ntyper==0.9.0\n")
        tf_path = tf.name

    res = scan_dependency_licenses(tf_path)
    assert res.is_compliant is True
    assert res.total_packages == 2
    # curated offline map
    assert any(r.get("source") == "curated_map" for r in res.resolved)
    assert res.mode.startswith("offline")


def test_scan_psycopg_weak_copyleft(tmp_path: Path):
    p = tmp_path / "requirements.txt"
    p.write_text("psycopg2-binary==2.9.9\n", encoding="utf-8")
    res = scan_dependency_licenses(str(p))
    assert any(i.category == "WEAK_COPYLEFT" for i in res.issues)
    # weak copyleft does not fail hard compliance
    assert res.is_compliant is True
