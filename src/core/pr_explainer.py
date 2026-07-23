"""
PR Explanation Generator with File-Level Findings (V6 S110).

Parses git diffs, extracts modified files, added/deleted line counts,
and generates structured Pull Request summaries with per-file findings.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class FileDiffSummary:
    file_path: str
    additions: int
    deletions: int
    summary_note: str


@dataclass
class PRExplanationResult:
    title: str
    overview: str
    total_files_changed: int
    total_additions: int
    total_deletions: int
    file_summaries: List[FileDiffSummary] = field(default_factory=list)
    markdown_output: str = ""


def parse_git_diff(diff_text: str) -> List[FileDiffSummary]:
    """Parse raw git diff patch text into per-file addition/deletion metrics."""
    if not diff_text or not isinstance(diff_text, str):
        return []

    file_diffs: List[FileDiffSummary] = []
    current_file = ""
    adds = 0
    dels = 0

    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            if current_file:
                file_diffs.append(
                    FileDiffSummary(
                        file_path=current_file,
                        additions=adds,
                        deletions=dels,
                        summary_note=f"+{adds}/-{dels} lines",
                    )
                )
            match = re.search(r"b/(.+)$", line)
            current_file = match.group(1) if match else "unknown"
            adds = 0
            dels = 0
        elif line.startswith("+") and not line.startswith("+++"):
            adds += 1
        elif line.startswith("-") and not line.startswith("---"):
            dels += 1

    if current_file:
        file_diffs.append(
            FileDiffSummary(
                file_path=current_file,
                additions=adds,
                deletions=dels,
                summary_note=f"+{adds}/-{dels} lines",
            )
        )

    return file_diffs


def generate_pr_explanation(diff_text: str, pr_title: str = "Automated PR Summary") -> PRExplanationResult:
    """Generate structured Markdown PR explanation with file-level findings."""
    file_diffs = parse_git_diff(diff_text)
    total_files = len(file_diffs)
    total_adds = sum(f.additions for f in file_diffs)
    total_dels = sum(f.deletions for f in file_diffs)

    overview = (
        f"This Pull Request updates {total_files} file(s) with +{total_adds}/-{total_dels} changes."
    )

    md_lines = [
        f"# {pr_title}\n",
        f"## Summary",
        overview,
        "\n## File-Level Findings\n",
        "| File | Changes | Notes |",
        "|------|---------|-------|",
    ]

    for f in file_diffs:
        md_lines.append(f"| `{f.file_path}` | +{f.additions}/-{f.deletions} | {f.summary_note} |")

    markdown_out = "\n".join(md_lines)

    return PRExplanationResult(
        title=pr_title,
        overview=overview,
        total_files_changed=total_files,
        total_additions=total_adds,
        total_deletions=total_dels,
        file_summaries=file_diffs,
        markdown_output=markdown_out,
    )


def generate_pr_explanation_from_repo(repo_dir: Optional[str] = None) -> PRExplanationResult:
    """Run git diff HEAD~1 or uncommitted changes and generate PR explanation."""
    r_dir = repo_dir or str(Path.cwd())
    try:
        res = subprocess.run(
            ["git", "-C", r_dir, "diff", "HEAD~1"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        diff_text = res.stdout if res.returncode == 0 and res.stdout else ""
        if not diff_text:
            res_staged = subprocess.run(
                ["git", "-C", r_dir, "diff", "--staged"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            diff_text = res_staged.stdout or ""
        return generate_pr_explanation(diff_text, pr_title="Git Branch Pull Request Summary")
    except Exception as e:
        return generate_pr_explanation("", pr_title=f"PR Explanation Error: {e}")
