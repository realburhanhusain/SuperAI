"""
Unit tests for Safe Conflict Assistance for Merges (S117).
"""

from __future__ import annotations

import tempfile
import pytest

from core.merge_conflict_helper import analyze_file_conflicts, parse_conflict_markers


CONFLICT_SAMPLE = """
def foo():
<<<<<<< HEAD
    return "ours"
=======
    return "theirs"
>>>>>>> feature-branch
"""


def test_parse_conflict_markers():
    chunks = parse_conflict_markers(CONFLICT_SAMPLE)
    assert len(chunks) == 1
    assert "ours" in chunks[0].ours_content
    assert "theirs" in chunks[0].theirs_content
    assert chunks[0].branch_ours == "HEAD"
    assert chunks[0].branch_theirs == "feature-branch"


def test_analyze_file_conflicts():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf.write(CONFLICT_SAMPLE)
        tf_path = tf.name

    res = analyze_file_conflicts(tf_path)
    assert res.has_conflicts is True
    assert res.conflict_count == 1
