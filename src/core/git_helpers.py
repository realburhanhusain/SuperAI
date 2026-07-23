"""
Git Commit & Branch Naming Helpers (V6 S116).

Provides standardized branch naming and conventional commit message generation.
"""

from __future__ import annotations

import re
from typing import Optional

VALID_TYPES = {"feat", "fix", "docs", "style", "refactor", "test", "chore", "perf", "ci"}


def slugify(text: str, max_words: int = 6) -> str:
    """Convert text into a clean git branch/file slug."""
    if not isinstance(text, str) or not text.strip():
        return "update"

    # Lowercase and replace non-alphanumeric chars with dashes
    clean = text.lower().strip()
    clean = re.sub(r"[^\w\s-]", "", clean)
    words = clean.split()[:max_words]
    slug = "-".join(words)
    return re.sub(r"-+", "-", slug).strip("-") or "update"


def suggest_branch_name(description: str, branch_type: str = "feat") -> str:
    """Generate a clean conventional git branch name: type/description-slug."""
    b_type = (branch_type or "feat").lower().strip()
    if b_type not in VALID_TYPES:
        b_type = "feat"

    slug = slugify(description)
    return f"{b_type}/{slug}"


def suggest_commit_message(
    description: str,
    scope: str = "",
    commit_type: str = "feat",
    body: str = "",
) -> str:
    """Generate a Conventional Commits compliant message."""
    c_type = (commit_type or "feat").lower().strip()
    if c_type not in VALID_TYPES:
        c_type = "feat"

    desc = (description or "update codebase").strip()
    # Remove leading type prefixes if included as "type: description"
    for prefix in VALID_TYPES:
        if desc.lower().startswith(f"{prefix}:"):
            desc = desc[len(prefix) + 1 :].strip()
            break

    scope_str = f"({scope.strip().lower()})" if scope and scope.strip() else ""
    header = f"{c_type}{scope_str}: {desc}"

    if body and body.strip():
        return f"{header}\n\n{body.strip()}"
    return header
