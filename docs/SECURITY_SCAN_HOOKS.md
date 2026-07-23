# Security Scan Hooks for Secrets & Vulnerabilities (S114)

## Overview

SuperAI provides automated **secret** scanning (`src/core/security_scan.py`) for files
and text (API keys, tokens, private-key headers). This is regex-based detection — **not**
full CVE/SCA vulnerability scanning. Pre-commit hooks are not auto-installed; use the CLI.

---

## Detection Capabilities

The secret scanner checks for:
* **LLM API Keys:** OpenAI (`sk-`), Anthropic (`sk-ant-`).
* **Cloud Credentials:** AWS Access Keys (`AKIA...`), GCP Service Keys.
* **Private Keys:** RSA, DSA, EC, and OpenSSH private key headers (`-----BEGIN PRIVATE KEY-----`).
* **Generic API Keys & Bearer Tokens:** Pattern matching for key assignments and headers.

---

## API & CLI Usage

```python
from core.security_scan import scan_text_for_secrets, scan_file_for_secrets

# Scan string payload
res = scan_text_for_secrets("api_key = 'sk-12345678901234567890123456789012'")
if res.has_secrets:
    print("Security alert: Secret detected!", res.findings)

# Scan target file
file_res = scan_file_for_secrets("src/core/config.py")
```

### CLI Command

```bash
superai security scan-secrets src/core/config.py
```

---

## Verification & Testing

Unit test coverage is enforced in `tests/test_security_scan_s114.py`.
