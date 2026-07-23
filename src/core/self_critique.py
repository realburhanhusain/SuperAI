"""
Self-Critique Pass Before Claiming Done (V6 S104).

Audits AST, docstrings, and error handling before declaring task completion.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class CritiqueFinding:
    category: str  # DOCS | ERROR_HANDLING | TYPE_SAFETY
    severity: str  # WARNING | INFO | ERROR
    line_number: int
    message: str


@dataclass
class SelfCritiqueResult:
    passed: bool
    file_path: str
    findings: List[CritiqueFinding] = field(default_factory=list)
    score: float = 100.0


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

    # Check module docstring
    if not ast.get_docstring(tree):
        findings.append(CritiqueFinding("DOCS", "WARNING", 1, "Missing module-level docstring"))

    # Walk AST nodes
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Public function missing docstring
            if not node.name.startswith("_") and not ast.get_docstring(node):
                findings.append(
                    CritiqueFinding(
                        "DOCS",
                        "INFO",
                        node.lineno,
                        f"Public function '{node.name}' lacks a docstring",
                    )
                )

        if isinstance(node, ast.ExceptHandler) and node.type is None:
            findings.append(
                CritiqueFinding(
                    "ERROR_HANDLING",
                    "WARNING",
                    node.lineno,
                    "Bare 'except:' catch block detected",
                )
            )

    deduction = len(findings) * 5.0
    final_score = max(0.0, 100.0 - deduction)
    has_errors = any(f.severity == "ERROR" for f in findings)
    has_warnings = any(f.severity == "WARNING" for f in findings)

    passed = not has_errors if not strict else (not has_errors and not has_warnings and final_score >= 90.0)

    return SelfCritiqueResult(
        passed=passed,
        file_path=file_path,
        findings=findings,
        score=final_score,
    )
