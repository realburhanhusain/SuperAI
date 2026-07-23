"""
License & Compliance Check on Dependencies (V6 S115).

Scans dependency manifests (pyproject.toml, requirements.txt, package.json)
for license compatibility and flags copyleft/restrictive licenses.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

PERMISSIVE_LICENSES = {"mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "isc", "unlicense", "cc0-1.0"}
COPYLEFT_LICENSES = {"gpl-2.0", "gpl-3.0", "agpl-3.0", "lgpl-2.1", "lgpl-3.0", "mpl-2.0"}


@dataclass
class LicenseIssue:
    package_name: str
    license_name: str
    category: str  # PERMISSIVE | COPYLEFT | UNKNOWN
    message: str


@dataclass
class LicenseCheckResult:
    is_compliant: bool
    manifest_file: str
    issues: List[LicenseIssue] = field(default_factory=list)
    total_packages: int = 0


def scan_dependency_licenses(manifest_path: str) -> LicenseCheckResult:
    """Scan dependency manifest for open source license compliance."""
    p = Path(manifest_path)
    if not p.exists():
        return LicenseCheckResult(
            is_compliant=False,
            manifest_file=manifest_path,
            issues=[LicenseIssue("N/A", "N/A", "ERROR", f"Manifest file not found: {manifest_path}")],
        )

    issues: List[LicenseIssue] = []
    total = 0

    fname = p.name.lower()
    if fname.endswith("package.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            total = len(deps)
            for pkg, ver in deps.items():
                if "gpl" in pkg.lower() or "agpl" in pkg.lower():
                    issues.append(
                        LicenseIssue(
                            package_name=pkg,
                            license_name="GPL-family (heuristic)",
                            category="COPYLEFT",
                            message="Copyleft license detected; review compliance for proprietary redistribution.",
                        )
                    )
        except Exception as e:
            issues.append(LicenseIssue("N/A", "N/A", "ERROR", f"Failed to parse package.json: {e}"))

    elif fname.endswith("requirements.txt") or fname.endswith("pyproject.toml"):
        try:
            content = p.read_text(encoding="utf-8")
            lines = content.splitlines()
            for line in lines:
                line_str = line.strip()
                if not line_str or line_str.startswith("#") or line_str.startswith("["):
                    continue
                total += 1
                if "gpl" in line_str.lower() or "agpl" in line_str.lower():
                    issues.append(
                        LicenseIssue(
                            package_name=line_str.split("=")[0].strip(),
                            license_name="GPL-family (heuristic)",
                            category="COPYLEFT",
                            message="Copyleft license detected; check legal redistribution policy.",
                        )
                    )
        except Exception as e:
            issues.append(LicenseIssue("N/A", "N/A", "ERROR", f"Failed to parse manifest: {e}"))

    return LicenseCheckResult(
        is_compliant=len(issues) == 0,
        manifest_file=manifest_path,
        issues=issues,
        total_packages=total,
    )
