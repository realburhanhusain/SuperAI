"""
Unit tests for Security Scan Hooks for Secrets & Vulns (S114).
"""

from __future__ import annotations

import tempfile
import pytest

from core.security_scan import scan_file_for_secrets, scan_text_for_secrets


def test_scan_text_clean():
    res = scan_text_for_secrets("print('Hello world!')")
    assert res.has_secrets is False
    assert len(res.findings) == 0


def test_scan_text_openai_key():
    payload = "OPENAI_API_KEY = 'sk-1234567890123456789012345678901234'"
    res = scan_text_for_secrets(payload)
    assert res.has_secrets is True
    assert any(f.secret_type == "OPENAI_KEY_LEAK" for f in res.findings)


def test_scan_text_private_key():
    payload = "-----BEGIN RSA PRIVATE KEY-----\nMIIEogIBAAKCAQEA..."
    res = scan_text_for_secrets(payload)
    assert res.has_secrets is True
    assert any(f.secret_type == "PRIVATE_KEY_LEAK" for f in res.findings)


def test_scan_file_secrets():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write("AWS_ACCESS_KEY_ID = 'AKIA1234567890123456'\n")
        tf_path = tf.name

    res = scan_file_for_secrets(tf_path)
    assert res.has_secrets is True
    assert any(f.secret_type == "AWS_KEY_LEAK" for f in res.findings)
