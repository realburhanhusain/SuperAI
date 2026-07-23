"""Memory Roadmap P2 — cognify mock pipeline tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.cognify import cognify, extract_mock
from core.knowledge_graph import KnowledgeGraph

pytestmark = pytest.mark.unit

SAMPLE = """
# Banking Data Platform

Cloud SQL uses Dataplex for catalog.
Policy Tags protects Cloud SQL columns.
Alice owns Banking App.
Banking App uses Cloud SQL.
SuperAI is a System.
"""


@pytest.fixture
def iso(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("SUPERAI_KG_DSN", f"sqlite:///{(tmp_path / 'kg.sqlite').as_posix()}")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    # isolate palace under tmp
    mem = tmp_path / ".superai" / "memory"
    mem.mkdir(parents=True)
    monkeypatch.setenv(
        "SUPERAI_MEMORY_DSN", f"sqlite:///{(mem / 'palace.sqlite').as_posix()}"
    )
    return tmp_path


def test_extract_mock_finds_relations():
    out = extract_mock(SAMPLE)
    assert out["ok"]
    assert out["mode"] == "mock"
    assert len(out["entities"]) >= 3
    rels = {r["relation"] for r in out["relations"]}
    assert "USES" in rels or "PROTECTS" in rels or "OWNS" in rels


def test_cognify_dry_run_no_write(iso: Path):
    kg = KnowledgeGraph(lock_root=iso)
    before = kg.status()["nodes"]
    rep = cognify(SAMPLE, mode="mock", dry_run=True, store_palace=False, kg=kg)
    assert rep["ok"]
    assert rep["dry_run"] is True
    assert rep["entities_found"] >= 1
    assert kg.status()["nodes"] == before


def test_cognify_writes_graph(iso: Path):
    kg = KnowledgeGraph(lock_root=iso)
    rep = cognify(
        SAMPLE,
        mode="mock",
        dry_run=False,
        store_palace=False,
        dataset_id="test",
        kg=kg,
    )
    assert rep["ok"]
    assert rep["nodes_written"] >= 2
    assert rep["edges_written"] >= 1
    st = kg.status()
    assert st["nodes"] >= 2
    assert st["edges"] >= 1
    path = kg.path(from_name="Banking App", to_name="Cloud SQL", hops=2)
    assert path["ok"] is True
    assert path.get("found") is True
    assert path.get("length", 0) >= 1


def test_cognify_file(iso: Path):
    f = iso / "doc.md"
    f.write_text(SAMPLE, encoding="utf-8")
    kg = KnowledgeGraph(lock_root=iso)
    rep = cognify(str(f), mode="mock", store_palace=False, kg=kg, dataset_id="docs")
    assert rep["ok"]
    assert rep["source_kind"] == "file"
    assert rep["nodes_written"] >= 1


def test_cognify_empty_fails(iso: Path):
    kg = KnowledgeGraph(lock_root=iso)
    rep = cognify("   \n  ", mode="mock", store_palace=False, kg=kg)
    assert rep["ok"] is False
