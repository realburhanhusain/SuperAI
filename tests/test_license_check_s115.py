"""
Unit tests for License & Compliance Check on Dependencies (S115).
"""

from __future__ import annotations

import tempfile
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
