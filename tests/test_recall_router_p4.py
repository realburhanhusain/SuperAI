"""Memory Roadmap P4 — multi-strategy recall."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.cognify import cognify
from core.knowledge_graph import KnowledgeGraph
from core.recall_router import choose_strategy, recall
from core.session_memory import SessionMemory

pytestmark = pytest.mark.unit


@pytest.fixture
def iso(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    mem = tmp_path / ".superai" / "memory"
    mem.mkdir(parents=True)
    monkeypatch.setenv(
        "SUPERAI_KG_DSN", f"sqlite:///{(mem / 'kg.sqlite').as_posix()}"
    )
    monkeypatch.setenv(
        "SUPERAI_SESSION_DSN", f"sqlite:///{(mem / 'sessions.sqlite').as_posix()}"
    )
    monkeypatch.setenv(
        "SUPERAI_MEMORY_DSN", f"sqlite:///{(mem / 'palace.sqlite').as_posix()}"
    )
    kg = KnowledgeGraph(lock_root=mem)
    sm = SessionMemory(lock_root=mem)
    return tmp_path, mem, kg, sm


def test_choose_strategy_heuristics():
    assert choose_strategy("what is related to Cloud SQL")["strategy"] in {
        "hybrid",
        "graph",
    }
    assert (
        choose_strategy("prefer dark mode", session_id="s1")["strategy"] == "session"
    )
    assert choose_strategy('find "exact phrase"')["strategy"] == "keyword"


def test_graph_and_hybrid(iso):
    _tmp, mem, kg, _sm = iso
    cognify(
        "Banking App uses Cloud SQL. Policy Tags protects Cloud SQL.",
        mode="mock",
        store_palace=False,
        kg=kg,
        dataset_id="demo",
    )
    g = recall(
        "Cloud SQL",
        strategy="graph",
        top_k=10,
        dataset_id="demo",
        kg=kg,
        palace=None,
    )
    assert g["ok"]
    assert g["strategy"] == "graph"
    assert g["count"] >= 1
    assert "strategy_reason" in g

    h = recall(
        "related to Banking App",
        strategy="auto",
        top_k=10,
        dataset_id="demo",
        kg=kg,
    )
    assert h["ok"]
    assert h["strategy"] in {"hybrid", "graph", "vector", "keyword"}
    assert h.get("strategy_requested") == "auto"


def test_session_then_fallthrough(iso):
    _tmp, mem, kg, sm = iso
    sm.start(session_id="s1")
    sm.remember("s1", "In this session we chose PSC for Datastream", importance=0.8)
    r = recall(
        "PSC Datastream",
        strategy="session",
        session_id="s1",
        session_memory=sm,
        palace=None,
        kg=None,
        fallthrough=False,
    )
    assert r["ok"]
    assert r["strategy"] == "session"
    assert r["count"] >= 1
    assert any("PSC" in str(h.get("content")) for h in r["hits"])

    # empty session falls through when allowed
    sm.start(session_id="s2")
    r2 = recall(
        "related to Cloud SQL",
        strategy="session",
        session_id="s2",
        session_memory=sm,
        kg=kg,
        fallthrough=True,
    )
    assert r2["ok"]
    # may be session+hybrid
    assert "session" in str(r2.get("strategy"))


def test_keyword_strategy(iso):
    _tmp, mem, kg, _sm = iso
    from core.memory_palace import MemoryPalace

    mp = MemoryPalace(persist_directory=str(mem))
    mp.store(
        "Ticket ABC-123 fixed Policy Tags on banking_customers",
        tags=["ops"],
        metadata={"source": "test"},
    )
    r = recall(
        "ABC-123",
        strategy="keyword",
        top_k=5,
        palace=mp,
        kg=None,
    )
    assert r["ok"]
    assert r["strategy"] == "keyword"
    assert r["count"] >= 1


def test_unknown_strategy():
    r = recall("x", strategy="nope")
    assert r["ok"] is False
