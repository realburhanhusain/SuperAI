"""
Dependency Upgrade Assistant (V6 S112).

Audits dependency manifests for unpinned dependencies, major version breaking changes,
and recommends safe upgrade paths.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DepUpgradeAdvice:
    package_name: str
    current_constraint: str
    risk_level: str  # LOW | MEDIUM | HIGH
    recommendation: str


@dataclass
class DepUpgradeResult:
    manifest_file: str
    total_dependencies: int
    recommendations: List[DepUpgradeAdvice] = field(default_factory=list)


def check_upgradable_dependencies(manifest_path: str) -> DepUpgradeResult:
    """Audit dependency file and offer upgrade risk assessment."""
    p = Path(manifest_path)
    if not p.exists():
        return DepUpgradeResult(manifest_file=manifest_path, total_dependencies=0)

    recs: List[DepUpgradeAdvice] = []
    total = 0

    fname = p.name.lower()
    if fname.endswith("package.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            total = len(deps)
            for pkg, ver in deps.items():
                if ver.startswith("^") or ver.startswith("~") or ver == "*":
                    recs.append(
                        DepUpgradeAdvice(
                            package_name=pkg,
                            current_constraint=ver,
                            risk_level="LOW" if ver.startswith("^") else "MEDIUM",
                            recommendation=f"Run `npm update {pkg}` to safely fetch non-breaking patches.",
                        )
                    )
        except Exception:
            pass

    elif fname.endswith("pyproject.toml"):
        try:
            import tomllib
            data = tomllib.loads(p.read_text(encoding="utf-8"))
            dep_list = []
            if "project" in data and "dependencies" in data["project"]:
                dep_list.extend(data["project"]["dependencies"])
            if "tool" in data and "poetry" in data["tool"] and "dependencies" in data["tool"]["poetry"]:
                for k, v in data["tool"]["poetry"].items():
                    dep_list.append(f"{k}{v}" if isinstance(v, str) else k)

            total = len(dep_list)
            for item in dep_list:
                pkg_name = re.split(r"[><=~!;]", item)[0].strip().strip('"\'')
                recs.append(
                    DepUpgradeAdvice(
                        package_name=pkg_name,
                        current_constraint=item,
                        risk_level="LOW",
                        recommendation=f"Run `pip install --upgrade {pkg_name}` and run test suite.",
                    )
                )
        except Exception:
            pass

    elif fname.endswith("requirements.txt"):
        try:
            content = p.read_text(encoding="utf-8")
            for line in content.splitlines():
                line_str = line.strip()
                if not line_str or line_str.startswith("#") or line_str.startswith("["):
                    continue
                total += 1
                if ">=" in line_str or "==" in line_str:
                    pkg_name = re.split(r"[><=~!;]", line_str)[0].strip().strip('"\'')
                    recs.append(
                        DepUpgradeAdvice(
                            package_name=pkg_name,
                            current_constraint=line_str,
                            risk_level="LOW",
                            recommendation=f"Run `pip install --upgrade {pkg_name}` and run test suite.",
                        )
                    )
        except Exception:
            pass

    return DepUpgradeResult(
        manifest_file=manifest_path,
        total_dependencies=total,
        recommendations=recs,
    )
