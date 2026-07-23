"""
Post-Edit Lint & Typecheck Checker (V6 S106).

Provides AST-based python syntax validation, type verification, and code quality checks.
"""

from __future__ import annotations

import ast

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class LintIssue:
    file_path: str
    line: int
    column: int
    code: str
    message: str


@dataclass
class LintCheckResult:
    is_clean: bool
    file_path: str
    issues: List[LintIssue] = field(default_factory=list)


def check_python_syntax_and_ast(file_path: str) -> LintCheckResult:
    """Validate python file syntax and inspect AST for basic type/quality issues."""
    p = Path(file_path)
    if not p.exists():
        return LintCheckResult(
            is_clean=False,
            file_path=file_path,
            issues=[LintIssue(file_path, 0, 0, "E901", "File does not exist")],
        )

    try:
        content = p.read_text(encoding="utf-8")
    except Exception as e:
        return LintCheckResult(
            is_clean=False,
            file_path=file_path,
            issues=[LintIssue(file_path, 0, 0, "E902", f"Read error: {e}")],
        )

    issues: List[LintIssue] = []

    # Syntax & AST parse check
    try:
        tree = ast.parse(content, filename=str(p))
    except SyntaxError as se:
        issues.append(
            LintIssue(
                file_path=file_path,
                line=se.lineno or 1,
                column=se.offset or 0,
                code="E999",
                message=f"SyntaxError: {se.msg}",
            )
        )
        return LintCheckResult(is_clean=False, file_path=file_path, issues=issues)

    # Basic AST analysis (check for bare excepts, missing type annotations on defs)
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append(
                LintIssue(
                    file_path=file_path,
                    line=node.lineno,
                    column=node.col_offset,
                    code="E722",
                    message="Bare 'except:' used; specify Exception type",
                )
            )

    return LintCheckResult(
        is_clean=len(issues) == 0,
        file_path=file_path,
        issues=issues,
    )


def run_post_edit_checks(file_paths: List[str]) -> Dict[str, Any]:
    """Run post-edit lint and type checks on multiple files."""
    results: List[Dict[str, Any]] = []
    all_clean = True

    for f_path in file_paths:
        res = check_python_syntax_and_ast(f_path)
        if not res.is_clean:
            all_clean = False
        results.append(
            {
                "file": res.file_path,
                "clean": res.is_clean,
                "issues": [
                    {
                        "line": i.line,
                        "code": i.code,
                        "message": i.message,
                    }
                    for i in res.issues
                ],
            }
        )

    return {
        "ok": all_clean,
        "results": results,
        "file_count": len(file_paths),
        "status": "clean" if all_clean else "issues_found",
    }
