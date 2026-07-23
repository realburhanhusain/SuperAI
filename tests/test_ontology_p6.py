"""Memory Roadmap P6 — ontology load, map, validate, cognify integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.cognify import cognify
from core.knowledge_graph import KnowledgeGraph
from core.ontology import (
    MemoryOntology,
    apply_ontology_to_extraction,
    clear_ontology_cache,
    default_ontology_path,
    get_ontology,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def ont():
    clear_ontology_cache()
    return MemoryOntology.load(default_ontology_path())


@pytest.fixture
def iso(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.delenv("SUPERAI_ONTOLOGY", raising=False)
    monkeypatch.setenv("SUPERAI_KG_DSN", f"sqlite:///{(tmp_path / 'kg.sqlite').as_posix()}")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    mem = tmp_path / ".superai" / "memory"
    mem.mkdir(parents=True)
    monkeypatch.setenv(
        "SUPERAI_MEMORY_DSN", f"sqlite:///{(mem / 'palace.sqlite').as_posix()}"
    )
    clear_ontology_cache()
    return tmp_path


def test_default_ontology_file_exists():
    p = default_ontology_path()
    assert p.is_file(), f"missing ontology at {p}"


def test_validate_core_ontology(ont: MemoryOntology):
    rep = ont.validate()
    assert rep["ok"] is True, rep.get("errors")
    assert rep["entity_type_count"] >= 8
    assert rep["relation_count"] >= 5
    assert not rep["errors"]


def test_show_lists_core_types(ont: MemoryOntology):
    s = ont.show()
    assert s["ok"]
    for t in ("Person", "System", "Dataset", "RiskControl", "Project", "Entity"):
        assert t in s["entity_types"]
    assert "USES" in s["relations"]
    assert "OWNS" in s["relations"]


def test_map_type_aliases(ont: MemoryOntology):
    m = ont.resolve_type("service")
    assert m["type"] == "System"
    assert m["provisional"] is False
    m2 = ont.resolve_type("policy")
    assert m2["type"] == "RiskControl"


def test_map_unknown_type_provisional(ont: MemoryOntology):
    m = ont.resolve_type("FlargleWidget")
    assert m["type"] == "Entity"
    assert m["provisional"] is True
    assert m["reason"] == "unknown_type_provisional"


def test_known_entity_overrides_type(ont: MemoryOntology):
    m = ont.resolve_type("Entity", entity_name="Cloud SQL")
    assert m["type"] == "System"
    assert m["provisional"] is False
    assert "known_entity" in m["reason"]


def test_map_relation_aliases(ont: MemoryOntology):
    r = ont.resolve_relation("depends_on")
    assert r["relation"] == "DEPENDS_ON"
    r2 = ont.resolve_relation("totally_unknown_rel")
    assert r2["relation"] == "RELATED_TO"
    assert r2["provisional"] is True


def test_edge_domain_range_ok(ont: MemoryOntology):
    ok = ont.edge_allowed("System", "USES", "System")
    assert ok["allowed"] is True
    assert ok["provisional"] is False


def test_edge_domain_violation_provisional(ont: MemoryOntology):
    # Person USES Dataset may be out of domain depending on yaml — OWNS is fine;
    # USES domain includes Person in our yaml. Use PROTECTS with Dataset domain wrong:
    bad = ont.edge_allowed("Document", "PROTECTS", "System")
    assert bad["allowed"] is True  # hybrid: not rejected
    assert bad["provisional"] is True
    assert "domain_range_violation" in bad["reason"]


def test_normalize_extraction(ont: MemoryOntology):
    raw = {
        "entities": [
            {"name": "Cloud SQL", "type": "service", "confidence": 0.9},
            {"name": "Mystery", "type": "Flargle", "confidence": 0.4},
        ],
        "relations": [
            {
                "from": "Cloud SQL",
                "to": "Mystery",
                "relation": "uses",
                "from_type": "service",
                "to_type": "Flargle",
                "confidence": 0.8,
            }
        ],
    }
    out = ont.normalize_extraction(raw)
    assert out["ontology_applied"] is True
    by_name = {e["name"]: e for e in out["entities"]}
    assert by_name["Cloud SQL"]["type"] == "System"
    assert by_name["Cloud SQL"]["provisional"] is False
    assert by_name["Mystery"]["type"] == "Entity"
    assert by_name["Mystery"]["provisional"] is True
    rel = out["relations"][0]
    assert rel["relation"] == "USES"
    assert rel["from_type"] == "System"


def test_cognify_applies_ontology(iso: Path):
    kg = KnowledgeGraph(lock_root=iso)
    sample = (
        "Cloud SQL uses Dataplex.\n"
        "Policy Tags protects Cloud SQL.\n"
        "Alice owns Banking App.\n"
    )
    rep = cognify(
        sample,
        mode="mock",
        dry_run=False,
        store_palace=False,
        dataset_id="p6",
        kg=kg,
    )
    assert rep["ok"]
    assert rep.get("ontology_applied") is True
    assert rep["nodes_written"] >= 2
    # Cloud SQL should be typed System in graph
    q = kg.query_nodes(name="Cloud SQL", dataset_id="p6", limit=5)
    assert q["count"] >= 1
    node = q["nodes"][0]
    assert node["type"] == "System"
    props = node.get("properties") or {}
    # provisional flag present for cognify writes
    assert "provisional" in props or props.get("cognify") is True


def test_cognify_can_disable_ontology(iso: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_ONTOLOGY", "0")
    clear_ontology_cache()
    kg = KnowledgeGraph(lock_root=iso)
    rep = cognify(
        "Cloud SQL uses Dataplex.",
        mode="mock",
        dry_run=True,
        store_palace=False,
        kg=kg,
    )
    assert rep["ok"]
    assert rep.get("ontology_applied") is False


def test_apply_helper_disabled():
    out = apply_ontology_to_extraction(
        {"entities": [{"name": "X", "type": "service"}], "relations": []},
        enabled=False,
    )
    assert out["ontology_applied"] is False
    assert out["entities"][0]["type"] == "service"


def test_induce_from_counts(ont: MemoryOntology):
    rep = ont.induce_from_counts(
        {"System": 10, "Flargle": 3, "Person": 2},
        {"USES": 5, "weird_rel": 2},
    )
    assert rep["ok"]
    assert any(u["label"] == "Flargle" for u in rep["unknown_types"])
    assert any(u["label"] == "weird_rel" for u in rep["unknown_relations"])


def test_get_ontology_cached():
    clear_ontology_cache()
    a = get_ontology()
    b = get_ontology()
    assert a is b
