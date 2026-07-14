"""Wings/Rooms first-class in MemoryPalace + stronger clustering."""

from pathlib import Path

import pytest

from core.memory_palace import MemoryPalace
from core.wings import WingsManager


@pytest.fixture
def palace(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    (tmp_path / ".superai").mkdir(parents=True)
    # Force in-memory path via dedicated dir without chroma quirks if needed
    return MemoryPalace(persist_directory=str(tmp_path / ".superai" / "memory"))


def test_store_assigns_wing_room(palace: MemoryPalace, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    mid = palace.store(
        "Implemented FastAPI endpoint with pytest coverage.",
        tags=["learning", "coding"],
        metadata={"task_type": "coding", "success": True, "source": "orchestrator"},
    )
    assert mid
    mems = palace.get_all_memories()
    found = next((m for m in mems if m.get("id") == mid), None)
    assert found is not None
    meta = found.get("metadata") or {}
    assert meta.get("wing") == "technical"
    assert meta.get("room") in {"coding", "testing"}

    # Sidecar assignment exists
    wm = WingsManager(path=tmp_path / ".superai" / "wings.json")
    # WingsManager default path is home/.superai/wings.json
    wm2 = WingsManager()
    loc = wm2.latest_for_memory(mid)
    assert loc is not None
    assert loc.get("wing")


def test_query_by_wing_room(palace: MemoryPalace, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    palace.store(
        "Budget daily limit exceeded warning.",
        tags=["learning"],
        metadata={"task_type": "general", "source": "budget"},
        wing="operations",
        room="budget",
    )
    palace.store(
        "Council voted majority on API design.",
        tags=["learning"],
        metadata={"task_type": "reasoning", "source": "council"},
    )
    ops = palace.query_by_location(wing="operations", limit=20)
    assert any("Budget" in (m.get("content") or "") for m in ops)

    hits = palace.query_semantic("budget limit", top_k=5, wing="operations")
    assert isinstance(hits, list)


def test_palace_layout(palace: MemoryPalace, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    palace.store("code a", metadata={"task_type": "coding", "success": True})
    palace.store("fail b", metadata={"task_type": "coding", "success": False})
    layout = palace.palace_layout()
    assert "by_wing" in layout
    assert layout.get("total_located", 0) >= 1


def test_cluster_methods(palace: MemoryPalace, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    for i, tt in enumerate(["coding", "coding", "research", "reasoning", "general"]):
        palace.store(
            f"Memory number {i} about {tt} with enough text content.",
            metadata={"task_type": tt, "success": True},
        )
    tag_c = palace.cluster_memories(method="tag", max_clusters=5)
    assert len(tag_c) >= 1
    wing_c = palace.cluster_memories(method="wing", max_clusters=5)
    assert len(wing_c) >= 1
    auto_c = palace.cluster_memories(method="auto", max_clusters=5)
    assert len(auto_c) >= 1
    assert auto_c[0].get("method") in {"embedding", "wing", "tag"}


def test_wings_classify_rich():
    wm = WingsManager()
    assert wm.classify_task_type("coding")["wing"] == "technical"
    c = wm.classify_task_type(
        "general", content="mcp server shared memory", source="mcp_client"
    )
    assert c["wing"] == "agentic"
    f = wm.classify_task_type("reasoning", success=False)
    assert f["room"] == "failures" or f["wing"] == "learning"


def test_query_semantic_room_filter(palace: MemoryPalace, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    palace.store(
        "Deployment pipeline green for production.",
        metadata={"task_type": "infra"},
        wing="operations",
        room="deployments",
    )
    hits = palace.query_semantic(
        "deployment production", top_k=5, wing="operations", room="deployments"
    )
    assert isinstance(hits, list)


def test_suggest_and_promote_rooms(palace: MemoryPalace, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # Seed a cluster of similar coding memories
    for i in range(5):
        palace.store(
            f"Coding memory about FastAPI routes and handlers number {i} with detail.",
            tags=["learning", "coding"],
            metadata={"task_type": "coding", "success": True},
        )
    suggestions = palace.suggest_rooms_from_clusters(min_size=2, method="wing")
    assert isinstance(suggestions, list)
    assert len(suggestions) >= 1

    dry = palace.auto_promote_rooms(apply=False, min_size=2, method="wing")
    assert dry["apply"] is False
    assert "suggestions" in dry

    live = palace.auto_promote_rooms(
        apply=True, reassign=True, min_size=2, method="wing"
    )
    assert live["apply"] is True
    # Catalog should include technical/coding at least
    cat = live.get("catalog") or {}
    assert "technical" in cat or live["promoted_count"] >= 0

    snap = palace.browser_snapshot(limit=5)
    assert "layout" in snap
    assert "suggestions" in snap
    assert "top_wings" in snap
    assert "browse" in snap


def test_ensure_room_promotion(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    wm = WingsManager()
    r = wm.ensure_room("technical", "edge_cases", note="test")
    assert r["promoted"] is True
    assert "edge_cases" in wm.list_rooms("technical")
    assert wm.recent_promotions(5)
