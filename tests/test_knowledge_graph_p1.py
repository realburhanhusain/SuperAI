"""Memory Roadmap P1 — knowledge graph offline tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.knowledge_graph import KnowledgeGraph

pytestmark = pytest.mark.unit


@pytest.fixture
def kg(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_KG_DSN", f"sqlite:///{(tmp_path / 'kg.sqlite').as_posix()}")
    monkeypatch.delenv("SUPERAI_MEMORY_DSN", raising=False)
    return KnowledgeGraph(lock_root=tmp_path)


def test_status_empty(kg: KnowledgeGraph):
    st = kg.status()
    assert st["ok"] is True
    assert st["nodes"] == 0
    assert st["edges"] == 0


def test_upsert_node_idempotent(kg: KnowledgeGraph):
    a = kg.upsert_node(name="Cloud SQL", type="System", wing="technical")
    assert a["ok"] and a["created"] is True
    b = kg.upsert_node(name="Cloud SQL", type="System", wing="technical")
    assert b["ok"] and b["created"] is False
    assert a["node"]["id"] == b["node"]["id"]
    st = kg.status()
    assert st["nodes"] == 1


def test_edge_and_two_hop_path(kg: KnowledgeGraph):
    # A --USES--> B --PROTECTS--> C
    kg.upsert_edge(
        from_name="Banking App",
        from_type="System",
        to_name="Cloud SQL",
        to_type="System",
        relation="USES",
    )
    kg.upsert_edge(
        from_name="Cloud SQL",
        from_type="System",
        to_name="Policy Tags",
        to_type="RiskControl",
        relation="PROTECTS",
    )
    st = kg.status()
    assert st["nodes"] >= 3
    assert st["edges"] == 2

    path = kg.path(from_name="Banking App", to_name="Policy Tags", hops=2)
    assert path["ok"] is True
    assert path["found"] is True
    assert path["length"] == 2
    names = [step["node"]["name"] for step in path["path"]]
    assert names[0] == "Banking App"
    assert names[-1] == "Policy Tags"


def test_path_missing_within_hops(kg: KnowledgeGraph):
    kg.upsert_node(name="A", type="Entity")
    kg.upsert_node(name="Z", type="Entity")
    path = kg.path(from_name="A", to_name="Z", hops=1)
    assert path["ok"] is True
    assert path["found"] is False


def test_query_nodes_filter(kg: KnowledgeGraph):
    kg.upsert_node(name="Alice", type="Person", dataset_id="d360")
    kg.upsert_node(name="Bob", type="Person", dataset_id="personal")
    kg.upsert_node(name="Dataplex", type="System", dataset_id="d360")
    q = kg.query_nodes(type="Person", dataset_id="d360")
    assert q["count"] == 1
    assert q["nodes"][0]["name"] == "Alice"


def test_source_memory_link(kg: KnowledgeGraph):
    out = kg.upsert_node(
        name="Demo Decision",
        type="Decision",
        source_memory_id="mem-123",
    )
    assert out["node"]["source_memory_id"] == "mem-123"


def test_neighbors(kg: KnowledgeGraph):
    e = kg.upsert_edge(
        from_name="X", to_name="Y", relation="LINKS"
    )
    fid = e["edge"]["from_id"]
    nb = kg.neighbors(fid, direction="out")
    assert len(nb["out"]) == 1
    assert nb["out"][0]["relation"] == "LINKS"
