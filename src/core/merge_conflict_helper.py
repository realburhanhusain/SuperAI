"""
Safe Conflict Assistance for Merges (V6 S117).

Parses git merge conflict markers (<<<<<<<, =======, >>>>>>>) and generates
structured conflict resolution reports and recommendations.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ConflictChunk:
    line_number: int
    ours_content: str
    theirs_content: str
    branch_ours: str
    branch_theirs: str


@dataclass
class ConflictAnalysisResult:
    has_conflicts: bool
    file_path: str
    conflict_count: int
    conflicts: List[ConflictChunk] = field(default_factory=list)
    recommendation: str = ""


def parse_conflict_markers(content: str) -> List[ConflictChunk]:
    """Parse text for standard git merge conflict marker blocks."""
    if not content or not isinstance(content, str):
        return []

    chunks: List[ConflictChunk] = []
    lines = content.splitlines()

    in_conflict = False
    in_theirs = False
    ours_lines: List[str] = []
    theirs_lines: List[str] = []
    start_line = 0
    branch_ours = "OURS"
    branch_theirs = "THEIRS"

    for idx, line in enumerate(lines, start=1):
        if line.startswith("<<<<<<<"):
            in_conflict = True
            in_theirs = False
            start_line = idx
            branch_ours = line.replace("<<<<<<<", "").strip() or "OURS"
            ours_lines = []
            theirs_lines = []
        elif line.startswith("=======") and in_conflict:
            in_theirs = True
        elif line.startswith(">>>>>>>") and in_conflict:
            branch_theirs = line.replace(">>>>>>>", "").strip() or "THEIRS"
            chunks.append(
                ConflictChunk(
                    line_number=start_line,
                    ours_content="\n".join(ours_lines),
                    theirs_content="\n".join(theirs_lines),
                    branch_ours=branch_ours,
                    branch_theirs=branch_theirs,
                )
            )
            in_conflict = False
            in_theirs = False
        elif in_conflict:
            if in_theirs:
                theirs_lines.append(line)
            else:
                ours_lines.append(line)

    return chunks


def analyze_file_conflicts(file_path: str) -> ConflictAnalysisResult:
    """Read target file and analyze merge conflicts."""
    p = Path(file_path)
    if not p.exists():
        return ConflictAnalysisResult(has_conflicts=False, file_path=file_path, conflict_count=0)

    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        conflicts = parse_conflict_markers(content)
        has_c = len(conflicts) > 0
        rec = (
            f"Found {len(conflicts)} conflict marker block(s). Review ours vs theirs lines or perform union merge."
            if has_c
            else "Clean file; no git conflict markers detected."
        )
        return ConflictAnalysisResult(
            has_conflicts=has_c,
            file_path=file_path,
            conflict_count=len(conflicts),
            conflicts=conflicts,
            recommendation=rec,
        )
    except Exception as e:
        return ConflictAnalysisResult(has_conflicts=False, file_path=file_path, conflict_count=0, recommendation=f"Read error: {e}")
