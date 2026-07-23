"""
License & Compliance Check on Dependencies (V6 S115).

Offline compliance assistant:
  1) Curated package→SPDX map for common ecosystem packages
  2) Manifest license field when present
  3) Name heuristic last (explicitly labeled)

Not a live SPDX/API service — honest offline product.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

PERMISSIVE = {
    "mit",
    "apache-2.0",
    "apache 2.0",
    "bsd-2-clause",
    "bsd-3-clause",
    "bsd",
    "isc",
    "unlicense",
    "cc0-1.0",
    "psf-2.0",
    "python-2.0",
    "mpl-2.0",  # weak copyleft — treat separately below
}
COPYLEFT = {
    "gpl-2.0",
    "gpl-3.0",
    "agpl-3.0",
    "lgpl-2.1",
    "lgpl-3.0",
    "gpl",
    "agpl",
    "lgpl",
}
# Curated offline map (common SuperAI / Python ecosystem)
OFFLINE_SPDX_MAP: Dict[str, str] = {
    "typer": "MIT",
    "click": "BSD-3-Clause",
    "rich": "MIT",
    "pydantic": "MIT",
    "sqlalchemy": "MIT",
    "httpx": "BSD-3-Clause",
    "httpcore": "BSD-3-Clause",
    "anyio": "MIT",
    "idna": "BSD-3-Clause",
    "certifi": "MPL-2.0",
    "urllib3": "MIT",
    "requests": "Apache-2.0",
    "pyyaml": "MIT",
    "tomli": "MIT",
    "packaging": "Apache-2.0 OR BSD-2-Clause",
    "pytest": "MIT",
    "coverage": "Apache-2.0",
    "numpy": "BSD-3-Clause",
    "pandas": "BSD-3-Clause",
    "openai": "Apache-2.0",
    "anthropic": "MIT",
    "opentelemetry-api": "Apache-2.0",
    "opentelemetry-sdk": "Apache-2.0",
    "psycopg": "LGPL-3.0",
    "psycopg2": "LGPL-3.0",
    "psycopg2-binary": "LGPL-3.0",
    "cryptography": "Apache-2.0 OR BSD-3-Clause",
    "pypdf": "BSD-3-Clause",
    "pillow": "HPND",
}


@dataclass
class LicenseIssue:
    package_name: str
    license_name: str
    category: str  # PERMISSIVE | COPYLEFT | UNKNOWN | WEAK_COPYLEFT | ERROR
    message: str
    source: str = "heuristic"  # curated_map | manifest | heuristic


@dataclass
class LicenseCheckResult:
    is_compliant: bool
    manifest_file: str
    issues: List[LicenseIssue] = field(default_factory=list)
    total_packages: int = 0
    resolved: List[Dict[str, str]] = field(default_factory=list)
    mode: str = "offline_curated+heuristic"


def _normalize_license(lic: str) -> str:
    return re.sub(r"\s+", " ", (lic or "").strip().lower())


def _category(lic: str) -> str:
    n = _normalize_license(lic)
    if not n or n in {"unknown", "n/a", "proprietary"}:
        return "UNKNOWN"
    if "agpl" in n or n in {"gpl-2.0", "gpl-3.0", "gpl"}:
        return "COPYLEFT"
    if "lgpl" in n:
        return "WEAK_COPYLEFT"
    if "mpl" in n:
        return "WEAK_COPYLEFT"
    if any(p in n for p in PERMISSIVE) or n in PERMISSIVE:
        return "PERMISSIVE"
    if "gpl" in n:
        return "COPYLEFT"
    return "UNKNOWN"


def _resolve_package(pkg: str) -> Dict[str, str]:
    key = pkg.strip().lower().replace("_", "-")
    # strip extras: package[extra]
    key = key.split("[")[0]
    if key in OFFLINE_SPDX_MAP:
        lic = OFFLINE_SPDX_MAP[key]
        return {
            "package": pkg,
            "license": lic,
            "category": _category(lic),
            "source": "curated_map",
        }
    # fuzzy: django-foo not mapped
    if "gpl" in key or "agpl" in key:
        return {
            "package": pkg,
            "license": "GPL-family (name heuristic)",
            "category": "COPYLEFT",
            "source": "heuristic",
        }
    return {
        "package": pkg,
        "license": "UNKNOWN",
        "category": "UNKNOWN",
        "source": "unmapped",
    }


def _pkg_from_req(item: str) -> str:
    s = str(item).split(";")[0].strip().strip("\"'")
    for sep in (">=", "<=", "==", "~=", ">", "<", "!", "["):
        if sep in s:
            s = s.split(sep)[0]
            break
    return s.strip()


def scan_dependency_licenses(manifest_path: str) -> LicenseCheckResult:
    """Scan dependency manifest with curated map + heuristics."""
    p = Path(manifest_path)
    if not p.exists():
        return LicenseCheckResult(
            is_compliant=False,
            manifest_file=manifest_path,
            issues=[
                LicenseIssue(
                    "N/A", "N/A", "ERROR", f"Manifest file not found: {manifest_path}"
                )
            ],
        )

    issues: List[LicenseIssue] = []
    resolved: List[Dict[str, str]] = []
    packages: List[str] = []
    fname = p.name.lower()

    if fname.endswith("package.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            packages = list(deps.keys())
            # top-level license field
            if data.get("license"):
                resolved.append(
                    {
                        "package": "(project)",
                        "license": str(data["license"]),
                        "category": _category(str(data["license"])),
                        "source": "manifest",
                    }
                )
        except Exception as e:
            issues.append(
                LicenseIssue("N/A", "N/A", "ERROR", f"Failed to parse package.json: {e}")
            )

    elif fname.endswith("pyproject.toml"):
        try:
            import tomllib

            data = tomllib.loads(p.read_text(encoding="utf-8"))
            proj = data.get("project") or {}
            packages = [_pkg_from_req(x) for x in (proj.get("dependencies") or [])]
            lic = proj.get("license")
            if isinstance(lic, dict):
                lic = lic.get("text") or lic.get("file") or ""
            if lic:
                resolved.append(
                    {
                        "package": "(project)",
                        "license": str(lic),
                        "category": _category(str(lic)),
                        "source": "manifest",
                    }
                )
        except Exception as e:
            issues.append(
                LicenseIssue("N/A", "N/A", "ERROR", f"Failed to parse pyproject: {e}")
            )

    elif fname.endswith("requirements.txt"):
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                line_str = line.strip()
                if not line_str or line_str.startswith("#") or line_str.startswith("-"):
                    continue
                packages.append(_pkg_from_req(line_str))
        except Exception as e:
            issues.append(
                LicenseIssue("N/A", "N/A", "ERROR", f"Failed to parse manifest: {e}")
            )

    for pkg in packages:
        if not pkg:
            continue
        info = _resolve_package(pkg)
        resolved.append(info)
        cat = info["category"]
        if cat == "COPYLEFT":
            issues.append(
                LicenseIssue(
                    package_name=pkg,
                    license_name=info["license"],
                    category="COPYLEFT",
                    message=(
                        f"Copyleft license ({info['license']}) via {info['source']}. "
                        "Review redistribution obligations."
                    ),
                    source=info["source"],
                )
            )
        elif cat == "WEAK_COPYLEFT":
            issues.append(
                LicenseIssue(
                    package_name=pkg,
                    license_name=info["license"],
                    category="WEAK_COPYLEFT",
                    message=(
                        f"Weak copyleft ({info['license']}) via {info['source']}. "
                        "File-level obligations may apply."
                    ),
                    source=info["source"],
                )
            )
        elif cat == "UNKNOWN" and info["source"] == "unmapped":
            issues.append(
                LicenseIssue(
                    package_name=pkg,
                    license_name="UNKNOWN",
                    category="UNKNOWN",
                    message=(
                        "No curated SPDX mapping — verify license on PyPI/npm before ship. "
                        "Offline map only; not a live license API."
                    ),
                    source="unmapped",
                )
            )

    # Compliance: no COPYLEFT errors; UNKNOWN is warning-style but still listed
    hard = [i for i in issues if i.category in {"COPYLEFT", "ERROR"}]
    return LicenseCheckResult(
        is_compliant=len(hard) == 0,
        manifest_file=manifest_path,
        issues=issues,
        total_packages=len(packages),
        resolved=resolved,
        mode="offline_curated+heuristic",
    )
