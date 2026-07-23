"""
Unit tests for PR Explanation Generator with File-Level Findings (S110).
"""

from __future__ import annotations

import pytest

from core.pr_explainer import generate_pr_explanation, parse_git_diff


SAMPLE_DIFF = """diff --git a/src/core/git_helpers.py b/src/core/git_helpers.py
index 1234567..89abcdef 100644
--- a/src/core/git_helpers.py
+++ b/src/core/git_helpers.py
@@ -10,3 +10,5 @@ def foo():
+    # New line
+    return True
"""


def test_parse_git_diff():
    diffs = parse_git_diff(SAMPLE_DIFF)
    assert len(diffs) == 1
    assert diffs[0].file_path == "src/core/git_helpers.py"
    assert diffs[0].additions == 2
    assert diffs[0].deletions == 0


def test_generate_pr_explanation():
    res = generate_pr_explanation(SAMPLE_DIFF, pr_title="Feature: Git Helpers Update")
    assert res.total_files_changed == 1
    assert res.total_additions == 2
    assert "Feature: Git Helpers Update" in res.markdown_output
    assert "src/core/git_helpers.py" in res.markdown_output
