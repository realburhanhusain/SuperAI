"""Memory Roadmap P7 — dataset namespace isolation, export/import, forget."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.knowledge_graph import KnowledgeGraph
from core.memory_dataset import (
    DatasetRegistry,
    export_dataset,
    filter_by_dataset,
    forget_dataset,
    import_dataset,
    memory_dataset_id,
    resolve_dataset_id,
    validate_dataset_id,
)
from core.memory_palace import MemoryPalace
from core.recall_router import recall

pytestmark = pytest.mark.unit


@pytest.fixture
def iso(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("SUPERAI_DATASET_SCOPE", "on")
    monkeypatch.delenv("SUPERAI_DATASET_ID", raising=False)
    reg = tmp_path / "datasets_registry.json"
    monkeypatch.setenv("SUPERAI_DATASETS_PATH", str(reg))
    monkeypatch.setenv(
        "SUPERAI_KG_DSN", f"sqlite:///{(tmp_path / 'kg.sqlite').as_posix()}"
    )
    mem = tmp_path / ".superai" / "memory"
    mem.mkdir(parents=True)
    monkeypatch.setenv(
        "SUPERAI_MEMORY_DSN", f"sqlite:///{(mem / 'palace.sqlite').as_posix()}"
    )
    # force memory backend (no pgvector)
    monkeypatch.setenv("SUPERAI_MEMORY_BACKEND", "memory")
    return tmp_path


def test_validate_dataset_id():
    assert validate_dataset_id("d360") is None
    assert validate_dataset_id("work-uat") is None
    assert validate_dataset_id("") is not None
    assert validate_dataset_id("1bad") is not None
    assert validate_dataset_id("all") is not None


def test_registry_builtins_and_create(iso: Path):
    reg = DatasetRegistry()
    listed = reg.list_datasets()
    ids = {d["id"] for d in listed["datasets"]}
    for name in ("personal", "d360", "superai", "scratch", "default", "shared"):
        assert name in ids
    out = reg.create("work-uat", description="UAT work")
    assert out["ok"] and out["created"]
    assert reg.exists("work-uat")
    use = reg.use("work-uat")
    assert use["active"] == "work-uat"
    assert reg.get_active() == "work-uat"


def test_resolve_prefers_env(iso: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_DATASET_ID", "scratch")
    assert resolve_dataset_id(None) == "scratch"
    assert resolve_dataset_id("d360") == "d360"


def test_store_stamps_dataset(iso: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_DATASET_ID", "scratch")
    mp = MemoryPalace()
    mid = mp.store("scratch secret alpha", tags=["t"], metadata={})
    # find memory
    mems = [m for m in mp.get_all_memories() if m.get("id") == mid]
    assert mems
    assert memory_dataset_id(mems[0]) == "scratch"
    assert "dataset:scratch" in (mems[0].get("tags") or [])


def test_no_cross_dataset_leakage_keyword(iso: Path, monkeypatch):
    mp = MemoryPalace()
    monkeypatch.setenv("SUPERAI_DATASET_ID", "d360")
    mp.store("UNIQUE_D360_TOKEN banking dataplex", metadata={"dataset_id": "d360"})
    monkeypatch.setenv("SUPERAI_DATASET_ID", "personal")
    mp.store("UNIQUE_PERSONAL_TOKEN family note", metadata={"dataset_id": "personal"})

    # Active personal should not see d360 token
    monkeypatch.setenv("SUPERAI_DATASET_ID", "personal")
    hits = mp.query_semantic("UNIQUE_D360_TOKEN", top_k=10, dataset_id="personal")
    blob = " ".join(str(h.get("content") or "") for h in hits)
    assert "UNIQUE_D360_TOKEN" not in blob

    hits_ok = mp.query_semantic(
        "UNIQUE_PERSONAL_TOKEN", top_k=10, dataset_id="personal"
    )
    blob2 = " ".join(str(h.get("content") or "") for h in hits_ok)
    assert "UNIQUE_PERSONAL_TOKEN" in blob2


def test_shared_visible_with_active(iso: Path):
    rows = [
        {"content": "a", "metadata": {"dataset_id": "d360"}, "tags": ["dataset:d360"]},
        {
            "content": "b",
            "metadata": {"dataset_id": "shared"},
            "tags": ["dataset:shared"],
        },
        {
            "content": "c",
            "metadata": {"dataset_id": "personal"},
            "tags": ["dataset:personal"],
        },
    ]
    filtered = filter_by_dataset(rows, "d360", include_shared=True)
    contents = {r["content"] for r in filtered}
    assert contents == {"a", "b"}


def test_kg_delete_dataset(iso: Path):
    kg = KnowledgeGraph(lock_root=iso)
    kg.upsert_node(name="SysA", type="System", dataset_id="scratch")
    kg.upsert_node(name="SysB", type="System", dataset_id="d360")
    kg.upsert_edge(
        from_name="SysA",
        to_name="SysA",
        relation="RELATED_TO",
        dataset_id="scratch",
    )
    out = kg.delete_dataset("scratch")
    assert out["ok"]
    assert out["nodes_deleted"] >= 1
    assert kg.query_nodes(name="SysA", dataset_id="scratch")["count"] == 0
    assert kg.query_nodes(name="SysB", dataset_id="d360")["count"] >= 1


def test_export_import_roundtrip(iso: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_DATASET_ID", "superai")
    mp = MemoryPalace()
    mp.store(
        "SuperAI export payload TOKEN_EXPORT_ZZ",
        metadata={"dataset_id": "superai"},
        tags=["dataset:superai"],
    )
    kg = KnowledgeGraph(lock_root=iso)
    kg.upsert_node(
        name="ExportNode", type="System", dataset_id="superai"
    )
    dest = iso / "superai_export.zip"
    exp = export_dataset("superai", dest=dest, palace=mp, kg=kg)
    assert exp["ok"], exp
    assert dest.is_file()
    assert exp["counts"]["memories"] >= 1
    assert exp["counts"]["nodes"] >= 1

    # forget then re-import into new id
    forget_dataset("superai", yes=True, palace=mp, kg=kg)
    imp = import_dataset(
        dest, dataset_id="superai_restored", dry_run=False, palace=mp, kg=kg
    )
    assert imp["ok"], imp
    assert imp["imported"]["memories"] >= 1
    assert imp["imported"]["nodes"] >= 1


def test_forget_requires_yes(iso: Path):
    out = forget_dataset("scratch", yes=False)
    assert out["ok"] is False
    assert out["error_code"] == "confirmation"


def test_recall_scopes_dataset(iso: Path, monkeypatch):
    mp = MemoryPalace()
    kg = KnowledgeGraph(lock_root=iso)
    mp.store(
        "DATASET_ALPHA_ONLY unique content",
        metadata={"dataset_id": "scratch"},
        tags=["dataset:scratch"],
    )
    mp.store(
        "DATASET_BETA_ONLY other content",
        metadata={"dataset_id": "personal"},
        tags=["dataset:personal"],
    )
    monkeypatch.setenv("SUPERAI_DATASET_ID", "scratch")
    out = recall(
        "DATASET_ALPHA_ONLY",
        strategy="keyword",
        dataset_id="scratch",
        palace=mp,
        kg=kg,
    )
    assert out["ok"]
    blob = " ".join(str(h.get("content") or "") for h in out.get("hits") or [])
    assert "DATASET_ALPHA_ONLY" in blob
    assert "DATASET_BETA_ONLY" not in blob
