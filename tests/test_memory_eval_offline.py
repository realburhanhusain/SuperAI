"""Offline memory roadmap eval harness (post P1–P8)."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.memory_eval import report_markdown, run_offline_memory_eval

pytestmark = pytest.mark.unit


def test_offline_memory_eval_all_phases(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    rep = run_offline_memory_eval(tmp_root=tmp_path / "eval_root")
    assert rep["total"] >= 8
    assert rep["passed"] == rep["total"], rep.get("message")
    assert rep["ok"] is True
    ids = {c["id"] for c in rep["cases"]}
    for need in (
        "p1_kg",
        "p2_cognify",
        "p3_session",
        "p4_recall",
        "p5_ingest",
        "p6_ontology",
        "p7_dataset",
        "p8_capture",
    ):
        assert need in ids
    md = report_markdown(rep)
    assert "PASS" in md
    assert "P1" in md
