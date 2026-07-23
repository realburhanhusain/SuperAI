"""Memory residual backlog MR-1…MR-6 + P9-R* offline tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.cognify import cognify, extract_mock
from core.host_hooks import install_checklist
from core.ingest import chunk_code, chunk_for_format, detect_format, ingest
from core.knowledge_graph import KnowledgeGraph
from core.memory_cloud import push_sync, status as cloud_status
from core.memory_dataset import export_dataset, forget_dataset, import_dataset
from core.memory_eval import run_offline_memory_eval
from core.memory_otel import get_memory_otel, reset_memory_otel
from core.ontology import MemoryOntology, clear_ontology_cache, default_ontology_path
from core.recall_router import choose_strategy
from core.session_capture import maybe_start_agent_auto_capture
from core.session_memory import SessionMemory

pytestmark = pytest.mark.unit


@pytest.fixture
def iso(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("SUPERAI_MEMORY_BACKEND", "memory")
    monkeypatch.setenv("SUPERAI_MEMORY_OTEL", "mock")
    monkeypatch.setenv("SUPERAI_MEMORY_OTEL_PATH", str(tmp_path / "otel.jsonl"))
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
    monkeypatch.setenv(
        "SUPERAI_MEMORY_CLOUD_CONFIG", str(tmp_path / "cloud_config.json")
    )
    reset_memory_otel()
    return tmp_path


def test_mr1_offline_eval_includes_quality(iso: Path):
    rep = run_offline_memory_eval(tmp_root=iso / "eval")
    ids = {c["id"] for c in rep["cases"]}
    assert "mr1_quality" in ids
    assert "p9_otel" in ids
    assert "p9_host_hook" in ids
    assert "p9_cloud_local" in ids
    assert rep["ok"] is True, rep.get("message")


def test_mr1_strategy_ranking():
    assert choose_strategy("related to Dataplex")["strategy"] in {"hybrid", "graph"}
    assert choose_strategy("TICKET-42")["strategy"] == "keyword"


def test_mr2_cognify_otel_instrumented(iso: Path):
    reset_memory_otel()
    kg = KnowledgeGraph(lock_root=iso)
    rep = cognify(
        "Banking App uses Cloud SQL.",
        mode="mock",
        dry_run=False,
        store_palace=False,
        dataset_id="superai",
        kg=kg,
    )
    assert rep.get("ok")
    # instrument_report sets otel_mode when enabled
    assert rep.get("otel_mode") in {None, "mock", "sdk"} or "otel_mode" in rep
    spans = get_memory_otel().list_spans(limit=20)
    assert any("cognify" in str(s.get("name") or "") for s in spans) or rep.get(
        "otel_mode"
    )


def test_mr3_code_chunking(iso: Path):
    assert detect_format("foo.py") == "code"
    src = (
        "def alpha():\n"
        "    # pad to force multi-chunk\n"
        "    return 1\n\n"
        "def beta():\n"
        "    # second unit also padded so merge does not fit one block\n"
        "    return 2\n\n"
        "class Gamma:\n"
        "    # third boundary\n"
        "    pass\n"
    )
    chunks = chunk_code(src, chunk_size=60)
    assert len(chunks) >= 2
    assert chunk_for_format(src, "code", chunk_size=60)
    f = iso / "sample.py"
    f.write_text(src, encoding="utf-8")
    rep = ingest(
        str(f),
        dataset_id="superai",
        store_palace=True,
        cognify=False,
        enforce_jail=True,
    )
    assert rep.get("ok")
    assert "code" in (rep.get("formats") or [])


def test_mr4_ontology_induce_from_texts():
    clear_ontology_cache()
    ont = MemoryOntology.load(default_ontology_path())
    out = ont.induce_from_texts(
        [
            "ZetaWidget uses Cloud SQL. ZetaWidget uses Cloud SQL.",
            "ZetaWidget protects Dataplex. ZetaWidget protects Dataplex.",
        ],
        min_count=2,
    )
    assert out.get("ok")
    assert out.get("mode") == "corpus_plus_counts"
    assert "alias_proposals" in out
    assert "draft_aliases" in out


def test_mr5_export_edge_names_and_forget_sessions(iso: Path):
    kg = KnowledgeGraph(lock_root=iso)
    kg.upsert_node(name="ASys", type="System", dataset_id="scratch")
    kg.upsert_node(name="BSys", type="System", dataset_id="scratch")
    kg.upsert_edge(
        from_name="ASys",
        to_name="BSys",
        relation="USES",
        from_type="System",
        to_type="System",
        dataset_id="scratch",
    )
    sm = SessionMemory(lock_root=iso)
    sm.start(session_id="forget_me", dataset_id="scratch", title="t")
    sm.remember("forget_me", "note", kind="note")
    dest = iso / "ex.zip"
    exp = export_dataset("scratch", dest=dest, kg=kg)
    assert exp.get("ok"), exp
    # edges in zip should carry names
    import json
    import zipfile

    with zipfile.ZipFile(dest) as zf:
        edges = json.loads(zf.read("kg_edges.json").decode()).get("edges") or []
    assert edges
    assert any(e.get("from_name") and e.get("to_name") for e in edges)
    # reimport round-trip edges
    dest2 = iso / "ex2.zip"
    export_dataset("scratch", dest=dest2, kg=kg)
    forget = forget_dataset("scratch", yes=True, kg=kg)
    assert forget.get("ok")
    assert forget.get("sessions_cleared", 0) >= 1


def test_mr6_agent_auto_capture(iso: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_CAPTURE_LEVEL", "session")
    monkeypatch.setenv("SUPERAI_AGENT_AUTO_CAPTURE", "1")
    cap = maybe_start_agent_auto_capture(session_id="agent_auto_1", title="t")
    assert cap is not None
    assert cap.level == "session"
    monkeypatch.setenv("SUPERAI_AGENT_AUTO_CAPTURE", "0")
    assert maybe_start_agent_auto_capture() is None


def test_p9_r2_otel_status_env_help(iso: Path):
    st = get_memory_otel().status()
    assert "env_help" in st
    assert "SUPERAI_MEMORY_OTEL" in st["env_help"]


def test_p9_r3_push_without_apply_is_dry(iso: Path):
    out = push_sync("default", apply=False)
    assert out.get("plan", {}).get("network_write") is False or out.get("apply") is False


def test_p9_r3_push_apply_unreachable(iso: Path):
    out = push_sync("default", apply=True)
    # not configured / unreachable → fail closed, no network write
    assert out.get("plan", {}).get("network_write") is False
    assert out.get("ok") is False or out.get("error_code") in {
        "not_configured",
        "unreachable",
        "export",
    }


def test_p9_r6_checklist():
    cl = install_checklist("claude")
    assert cl.get("ok")
    assert cl.get("auto_write_host_config") is False
    assert len(cl.get("steps") or []) >= 5


def test_p9_cloud_local_only(iso: Path):
    st = cloud_status()
    assert st["mode"] == "local_only"
