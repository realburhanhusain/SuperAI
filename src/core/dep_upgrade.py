"""
Dependency Upgrade Assistant (V6 S112).

Audits manifests for pin quality, risk-ranks upgrades, and can emit an
apply plan (dry-run by default). Optional --apply writes a requirements
override file — never silent production upgrade.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DepUpgradeAdvice:
    package_name: str
    current_constraint: str
    risk_level: str  # LOW | MEDIUM | HIGH
    recommendation: str
    pin_quality: str = "unknown"  # exact | lower_bound | range | caret | star
    suggested_constraint: str = ""


@dataclass
class DepUpgradeResult:
    manifest_file: str
    total_dependencies: int
    recommendations: List[DepUpgradeAdvice] = field(default_factory=list)
    apply_plan: List[Dict[str, str]] = field(default_factory=list)
    mode: str = "audit"


def _pin_quality(constraint: str) -> str:
    c = constraint.strip()
    if c in {"*", "latest"}:
        return "star"
    if c.startswith("^") or c.startswith("~"):
        return "caret"
    if "==" in c:
        return "exact"
    if ">=" in c or "~=" in c:
        return "lower_bound"
    if re.match(r"^[\w.\-]+$", c):
        return "unpinned_name"
    return "unknown"


def _risk(pin: str, constraint: str) -> str:
    if pin in {"star", "unpinned_name"}:
        return "HIGH"
    if pin == "caret":
        return "MEDIUM"
    if pin == "lower_bound":
        return "MEDIUM"
    if pin == "exact":
        return "LOW"
    if not any(x in constraint for x in ("=", ">", "<", "~", "^")):
        return "HIGH"
    return "LOW"


def _suggest(pkg: str, constraint: str, pin: str) -> str:
    if pin == "exact":
        return constraint  # keep pin; upgrade intentionally
    if pin == "lower_bound":
        return constraint  # keep >= floor
    if pin in {"star", "unpinned_name", "caret"}:
        return f"{pkg}  # pin with == after testing upgrade"
    return constraint


def check_upgradable_dependencies(manifest_path: str) -> DepUpgradeResult:
    """Audit dependency file and offer upgrade risk assessment + apply plan."""
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
                ver_s = str(ver)
                pin = _pin_quality(ver_s)
                risk = _risk(pin, ver_s)
                recs.append(
                    DepUpgradeAdvice(
                        package_name=pkg,
                        current_constraint=ver_s,
                        risk_level=risk,
                        pin_quality=pin,
                        recommendation=(
                            f"npm update {pkg}"
                            if risk != "HIGH"
                            else f"Pin {pkg} then npm install {pkg}@latest in a branch"
                        ),
                        suggested_constraint=_suggest(pkg, ver_s, pin),
                    )
                )
        except Exception as e:
            recs.append(
                DepUpgradeAdvice(
                    "N/A",
                    "",
                    "HIGH",
                    f"Failed to parse package.json: {e}",
                )
            )

    elif fname.endswith("pyproject.toml"):
        try:
            import tomllib

            data = tomllib.loads(p.read_text(encoding="utf-8"))
            dep_list: List[str] = []
            proj = data.get("project") or {}
            dep_list.extend(str(x) for x in (proj.get("dependencies") or []))
            # optional deps
            for _extra, items in (proj.get("optional-dependencies") or {}).items():
                dep_list.extend(str(x) for x in (items or []))
            poetry = ((data.get("tool") or {}).get("poetry") or {}).get("dependencies") or {}
            for k, v in poetry.items():
                if k == "python":
                    continue
                dep_list.append(f"{k}{v}" if isinstance(v, str) else str(k))

            total = len(dep_list)
            for item in dep_list:
                raw = item.strip().strip("\"'")
                # strip env markers
                raw = raw.split(";")[0].strip()
                pkg_name = re.split(r"[><=~!;\[]", raw)[0].strip().strip("\"'")
                pin = _pin_quality(raw)
                risk = _risk(pin, raw)
                recs.append(
                    DepUpgradeAdvice(
                        package_name=pkg_name,
                        current_constraint=raw,
                        risk_level=risk,
                        pin_quality=pin,
                        recommendation=(
                            f"pip install --upgrade '{pkg_name}' && pytest -q"
                            if risk != "HIGH"
                            else f"Pin {pkg_name}==X.Y.Z after changelog review, then pytest"
                        ),
                        suggested_constraint=_suggest(pkg_name, raw, pin),
                    )
                )
        except Exception as e:
            recs.append(
                DepUpgradeAdvice("N/A", "", "HIGH", f"Failed to parse pyproject: {e}")
            )

    elif fname.endswith("requirements.txt"):
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                line_str = line.strip()
                if not line_str or line_str.startswith("#") or line_str.startswith("-"):
                    continue
                total += 1
                pkg_name = re.split(r"[><=~!;\[#]", line_str)[0].strip().strip("\"'")
                pin = _pin_quality(line_str)
                risk = _risk(pin, line_str)
                recs.append(
                    DepUpgradeAdvice(
                        package_name=pkg_name,
                        current_constraint=line_str,
                        risk_level=risk,
                        pin_quality=pin,
                        recommendation=f"pip install --upgrade '{pkg_name}' && pytest -q",
                        suggested_constraint=_suggest(pkg_name, line_str, pin),
                    )
                )
        except Exception as e:
            recs.append(
                DepUpgradeAdvice("N/A", "", "HIGH", f"Failed to parse requirements: {e}")
            )

    apply_plan = [
        {
            "package": r.package_name,
            "from": r.current_constraint,
            "to": r.suggested_constraint or r.current_constraint,
            "risk": r.risk_level,
            "action": r.recommendation,
        }
        for r in recs
        if r.package_name != "N/A"
    ]

    return DepUpgradeResult(
        manifest_file=manifest_path,
        total_dependencies=total,
        recommendations=recs,
        apply_plan=apply_plan,
        mode="audit",
    )


def write_upgrade_plan(
    result: DepUpgradeResult,
    dest: str,
    *,
    apply: bool = False,
) -> Dict[str, Any]:
    """
    Write upgrade plan JSON. If apply=True, also write a requirements.upgrade.txt
    next to dest for operator review (still not auto pip install).
    """
    path = Path(dest)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "product": "dep_upgrade_plan",
        "manifest": result.manifest_file,
        "total": result.total_dependencies,
        "mode": "apply_plan" if apply else "audit",
        "plan": result.apply_plan,
        "recommendations": [asdict(r) for r in result.recommendations],
        "honesty": (
            "Does not run pip/npm. apply=True only writes plan files for human review."
        ),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    out: Dict[str, Any] = {
        "ok": True,
        "path": str(path.resolve()),
        "items": len(result.apply_plan),
        "applied": False,
    }
    if apply:
        req = path.with_suffix(".upgrade.txt")
        lines = [
            "# SuperAI dep upgrade candidates (review before install)",
            f"# source: {result.manifest_file}",
        ]
        for step in result.apply_plan:
            if step.get("risk") == "HIGH":
                lines.append(f"# HIGH RISK: {step['package']}  # {step['action']}")
            else:
                lines.append(f"{step['package']}  # {step['from']} → {step['to']}")
        req.write_text("\n".join(lines) + "\n", encoding="utf-8")
        out["upgrade_txt"] = str(req.resolve())
        out["applied"] = True  # plan files written only
        out["message"] = "Wrote plan files; no packages installed"
    return out
