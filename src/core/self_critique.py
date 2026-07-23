"""
Self-Critique Pass Before Claiming Done (V6 S104).

Deeper DoD-oriented AST audit: docs, error handling, type hints, mutables,
silent swallows, and TODO density — before declaring task completion.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CritiqueFinding:
    category: str  # DOCS | ERROR_HANDLING | TYPE_SAFETY | STYLE | QUALITY
    severity: str  # WARNING | INFO | ERROR
    line_number: int
    message: str


@dataclass
class SelfCritiqueResult:
    passed: bool
    file_path: str
    findings: List[CritiqueFinding] = field(default_factory=list)
    score: float = 100.0
    checks_run: List[str] = field(default_factory=list)


def run_self_critique_pass(file_path: str, strict: bool = True) -> SelfCritiqueResult:
    """Perform self-critique audit on python code file."""
    p = Path(file_path)
    if not p.exists() or p.suffix != ".py":
        return SelfCritiqueResult(
            passed=False,
            file_path=file_path,
            findings=[CritiqueFinding("FILE", "ERROR", 0, "Invalid file path")],
            score=0.0,
        )

    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(p))
    except Exception as e:
        return SelfCritiqueResult(
            passed=False,
            file_path=file_path,
            findings=[CritiqueFinding("SYNTAX", "ERROR", 0, f"Parse error: {e}")],
            score=0.0,
        )

    findings: List[CritiqueFinding] = []
    checks = [
        "module_docstring",
        "public_docstrings",
        "bare_except",
        "silent_except_pass",
        "return_annotations",
        "mutable_defaults",
        "todo_density",
        "print_debug",
    ]

    # Module docstring
    if not ast.get_docstring(tree):
        findings.append(
            CritiqueFinding("DOCS", "WARNING", 1, "Missing module-level docstring")
        )

    todo_hits = 0
    for i, line in enumerate(content.splitlines(), start=1):
        if re.search(r"\b(TODO|FIXME|XXX|HACK)\b", line):
            todo_hits += 1
            if todo_hits <= 5:
                findings.append(
                    CritiqueFinding(
                        "QUALITY",
                        "INFO",
                        i,
                        f"Outstanding marker in source: {line.strip()[:80]}",
                    )
                )
            if re.search(r"\bprint\s*\(", line) and "def " not in line:
                # debug prints outside obvious CLI consoles
                if "console.print" not in line and not line.strip().startswith("#"):
                    findings.append(
                        CritiqueFinding(
                            "STYLE",
                            "INFO",
                            i,
                            "Bare print() — prefer logger/console for product code",
                        )
                    )

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_public = not node.name.startswith("_")
            if is_public and not ast.get_docstring(node):
                findings.append(
                    CritiqueFinding(
                        "DOCS",
                        "INFO",
                        node.lineno,
                        f"Public function '{node.name}' lacks a docstring",
                    )
                )
            # Return annotation on public non-__init__
            if (
                is_public
                and node.name not in {"__init__", "__post_init__"}
                and node.returns is None
            ):
                findings.append(
                    CritiqueFinding(
                        "TYPE_SAFETY",
                        "INFO",
                        node.lineno,
                        f"Public function '{node.name}' missing return type annotation",
                    )
                )
            # Mutable defaults
            for d in node.args.defaults + list(node.args.kw_defaults or []):
                if d is None:
                    continue
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    findings.append(
                        CritiqueFinding(
                            "ERROR_HANDLING",
                            "WARNING",
                            getattr(d, "lineno", node.lineno),
                            f"Mutable default argument in '{node.name}'",
                        )
                    )

        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                findings.append(
                    CritiqueFinding(
                        "ERROR_HANDLING",
                        "WARNING",
                        node.lineno,
                        "Bare 'except:' catch block detected",
                    )
                )
            # silent swallow: except ...: pass
            body = node.body or []
            if len(body) == 1 and isinstance(body[0], ast.Pass):
                findings.append(
                    CritiqueFinding(
                        "ERROR_HANDLING",
                        "WARNING",
                        node.lineno,
                        "Silent except→pass swallows errors (prefer log/re-raise/flag)",
                    )
                )
            # except Exception: pass / return None only
            if (
                len(body) == 1
                and isinstance(body[0], ast.Return)
                and body[0].value is None
            ):
                findings.append(
                    CritiqueFinding(
                        "ERROR_HANDLING",
                        "INFO",
                        node.lineno,
                        "except returns None only — consider degraded flag or log",
                    )
                )

    # Weighted score
    weights = {"ERROR": 20.0, "WARNING": 8.0, "INFO": 3.0}
    deduction = sum(weights.get(f.severity, 5.0) for f in findings)
    final_score = max(0.0, 100.0 - deduction)
    has_errors = any(f.severity == "ERROR" for f in findings)
    has_warnings = any(f.severity == "WARNING" for f in findings)

    if not strict:
        passed = not has_errors
    else:
        # Strict DoD: no ERROR/WARNING and score ≥ 85 (INFO allowed)
        passed = not has_errors and not has_warnings and final_score >= 85.0

    return SelfCritiqueResult(
        passed=passed,
        file_path=file_path,
        findings=findings,
        score=final_score,
        checks_run=checks,
    )
