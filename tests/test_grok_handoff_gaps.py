"""Tests for AGY Grok handoff gap fixes (P1–P8 integrity)."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.knowledge_graph import KnowledgeGraph
from core.memory_dataset import export_dataset, forget_dataset
from core.ontology import MemoryOntology, clear_ontology_cache, default_ontology_path
from core.recall_router import recall
from core.session_memory import SessionMemory

pytestmark = pytest.mark.unit


@pytest.fixture
def iso(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("SUPERAI_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("SUPERAI_DATASETS_PATH", str(tmp_path / "datasets.json"))
    monkeypatch.setenv(
        "SUPERAI_KG_DSN", f"sqlite:///{(tmp_path / 'kg.sqlite').as_posix()}"
    )
    monkeypatch.setenv(
        "SUPERAI_SESSION_DSN",
        f"sqlite:///{(tmp_path / 'sessions.sqlite').as_posix()}",
    )
    mem = tmp_path / ".superai" / "memory"
    mem.mkdir(parents=True)
    monkeypatch.setenv(
        "SUPERAI_MEMORY_DSN", f"sqlite:///{(mem / 'palace.sqlite').as_posix()}"
    )
    clear_ontology_cache()
    return tmp_path


def test_p6_custom_core_type_not_forced_provisional(iso: Path):
    """AGY P6: types present in YAML entity_types must not be forced provisional
    solely because they were missing from a hardcoded set."""
    ont = MemoryOntology.load(default_ontology_path())
    # inject a custom core type as if it were in YAML
    ont.entity_types["Concept"] = {"description": "abstract concept", "aliases": ["idea"]}
    ont._type_alias["concept"] = "Concept"
    ont._type_alias["idea"] = "Concept"
    r = ont.resolve_type("Concept", confidence=0.5)
    assert r["type"] == "Concept"
    assert r["provisional"] is False


def test_p1_upsert_returns_ok_dict(iso: Path):
    kg = KnowledgeGraph(lock_root=iso)
    out = kg.upsert_node(name="N1", type="System", dataset_id="superai")
    assert out.get("ok") is True
    e = kg.upsert_edge(
        from_name="N1",
        to_name="N2",
        relation="USES",
        from_type="System",
        to_type="System",
        dataset_id="superai",
    )
    assert e.get("ok") is True


def test_p3_session_commit_ok(iso: Path):
    sm = SessionMemory(lock_root=iso)
    st = sm.start(session_id="s1", dataset_id="superai")
    assert st.get("ok") is True
    r = sm.remember("s1", "hello world", kind="note")
    assert r.get("ok") is True


def test_p4_recall_degraded_flag_on_missing_palace(iso: Path, monkeypatch):
    # Force palace init failure path by pointing at bad factory — use explicit None
    # and a strategy that needs palace; inject broken palace object
    class Boom:
        def get_all_memories(self):
            raise RuntimeError("palace down")

        def query_semantic(self, *a, **k):
            raise RuntimeError("vector down")

    out = recall("Cloud SQL", strategy="keyword", palace=Boom(), dataset_id="superai")
    assert out.get("ok") is True
    assert out.get("degraded") is True
    assert out.get("search_errors") or "keyword" in str(out.get("notes"))


def test_p7_export_pagination_fields(iso: Path):
    kg = KnowledgeGraph(lock_root=iso)
    for i in range(3):
        kg.upsert_node(name=f"Node{i}", type="System", dataset_id="scratch")
    dest = iso / "exp.zip"
    exp = export_dataset("scratch", dest=dest, kg=kg, limit=50_000)
    assert exp.get("ok") is True
    assert "truncated" in exp
    forget = forget_dataset("scratch", yes=True, kg=kg)
    assert forget.get("ok") is True
