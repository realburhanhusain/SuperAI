"""
Security Scan Hooks for Secrets & Vulnerabilities (V6 S114).

Scans files, text snippets, and diffs for leaked secret keys, tokens, and credentials.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SECRET_PATTERNS: List[Tuple[str, str, str]] = [
    (
        r"(?i)api[_-]?key\s*[:=]\s*['\"]?([a-z0-9_-]{20,})['\"]?",
        "API_KEY_LEAK",
        "Leaked API key credential",
    ),
    (
        r"sk-[a-zA-Z0-9]{32,}",
        "OPENAI_KEY_LEAK",
        "Leaked OpenAI secret key",
    ),
    (
        r"sk-ant-[a-zA-Z0-9_-]{32,}",
        "ANTHROPIC_KEY_LEAK",
        "Leaked Anthropic secret key",
    ),
    (
        r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",
        "AWS_KEY_LEAK",
        "Leaked AWS Access Key ID",
    ),
    (
        r"-----BEGIN\s+[A-Z0-9\s_-]*KEY-----",
        "PRIVATE_KEY_LEAK",
        "Leaked RSA/SSH Private Key",
    ),
    (
        r"(?i)bearer\s+[a-z0-9_\-\.]{25,}",
        "BEARER_TOKEN_LEAK",
        "Leaked HTTP Bearer token",
    ),
]


@dataclass
class SecretFinding:
    secret_type: str
    description: str
    matched_snippet: str
    line_number: int


@dataclass
class SecurityScanResult:
    has_secrets: bool
    findings: List[SecretFinding] = field(default_factory=list)


def scan_text_for_secrets(text: str) -> SecurityScanResult:
    """Scan string content for leaked API keys, tokens, or private keys."""
    if not text or not isinstance(text, str):
        return SecurityScanResult(has_secrets=False)

    findings: List[SecretFinding] = []
    lines = text.splitlines()

    for idx, line in enumerate(lines, start=1):
        for pattern, s_type, s_desc in SECRET_PATTERNS:
            for match in re.finditer(pattern, line):
                # Redact match for safety
                raw_match = match.group(0)
                redacted = raw_match[:6] + "..." + raw_match[-4:] if len(raw_match) > 10 else "***"
                findings.append(
                    SecretFinding(
                        secret_type=s_type,
                        description=s_desc,
                        matched_snippet=redacted,
                        line_number=idx,
                    )
                )

    return SecurityScanResult(
        has_secrets=len(findings) > 0,
        findings=findings,
    )


def scan_file_for_secrets(file_path: str) -> SecurityScanResult:
    """Scan file path for leaked secrets."""
    p = Path(file_path)
    if not p.exists() or p.is_dir():
        return SecurityScanResult(has_secrets=False)

    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        return scan_text_for_secrets(content)
    except Exception:
        return SecurityScanResult(has_secrets=False)
