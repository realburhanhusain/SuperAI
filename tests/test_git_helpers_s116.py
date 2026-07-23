"""
Unit tests for Git Commit & Branch Naming Helpers (S116).
"""

from __future__ import annotations

import pytest
from core.git_helpers import slugify, suggest_branch_name, suggest_commit_message


def test_slugify():
    assert slugify("Add prompt injection defense!!") == "add-prompt-injection-defense"
    assert slugify("   Too    Many   Spaces  Here  ") == "too-many-spaces-here"
    assert slugify("") == "update"
    assert slugify(None) == "update"


def test_suggest_branch_name():
    assert suggest_branch_name("add exit codes") == "feat/add-exit-codes"
    assert suggest_branch_name("fix memory leaks", branch_type="fix") == "fix/fix-memory-leaks"
    assert suggest_branch_name("update readme", branch_type="docs") == "docs/update-readme"
    assert suggest_branch_name("random feature", branch_type="invalid_type") == "feat/random-feature"


def test_suggest_commit_message():
    assert suggest_commit_message("add exit code module", scope="cli") == "feat(cli): add exit code module"
    assert suggest_commit_message("fix crash on startup", scope="core", commit_type="fix") == "fix(core): fix crash on startup"
    assert suggest_commit_message("update docs", commit_type="docs") == "docs: update docs"


def test_suggest_commit_message_with_body():
    msg = suggest_commit_message("add git helpers", scope="tools", body="Detailed description of git helpers module")
    assert msg.startswith("feat(tools): add git helpers")
    assert "Detailed description of git helpers module" in msg
