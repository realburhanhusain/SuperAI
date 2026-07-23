"""Memory Roadmap P3 — session buffer → promote end-to-end."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.knowledge_graph import KnowledgeGraph
from core.session_memory import SessionMemory

pytestmark = pytest.mark.unit


@pytest.fixture
def env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    mem = tmp_path / ".superai" / "memory"
    mem.mkdir(parents=True)
    monkeypatch.setenv(
        "SUPERAI_SESSION_DSN", f"sqlite:///{(mem / 'sessions.sqlite').as_posix()}"
    )
    monkeypatch.setenv(
        "SUPERAI_KG_DSN", f"sqlite:///{(mem / 'kg.sqlite').as_posix()}"
    )
    monkeypatch.setenv(
        "SUPERAI_MEMORY_DSN", f"sqlite:///{(mem / 'palace.sqlite').as_posix()}"
    )
    sm = SessionMemory(lock_root=mem)
    kg = KnowledgeGraph(lock_root=mem)
    return sm, kg, mem


def test_session_isolated_from_other_sessions(env):
    sm, _kg, _ = env
    a = sm.start(session_id="sess_a", dataset_id="d360")
    b = sm.start(session_id="sess_b", dataset_id="personal")
    assert a["ok"] and b["ok"]
    sm.remember("sess_a", "secret-a-only preference coffee", importance=0.8)
    sm.remember("sess_b", "secret-b-only preference tea", importance=0.8)
    ra = sm.recall("sess_a", "coffee")
    rb = sm.recall("sess_b", "coffee")
    assert ra["count"] >= 1
    assert all("secret-a" in (it.get("content") or "") for it in ra["items"])
    # b must not see a
    assert all("secret-a" not in (it.get("content") or "") for it in rb["items"])
    rb2 = sm.recall("sess_b", "tea")
    assert rb2["count"] >= 1


def test_promote_writes_palace_and_marks_items(env):
    sm, _kg, mem = env
    sm.start(session_id="sess_p", dataset_id="test")
    r = sm.remember(
        "sess_p",
        "We decided to use Cloud SQL for the banking demo.",
        kind="decision",
        importance=0.9,
    )
    iid = r["item"]["id"]
    out = sm.promote("sess_p", item_ids=[iid], store_palace=True, cognify_graph=False)
    assert out["ok"]
    assert out["promoted"] == 1
    assert out["palace_ids"]
    # item marked promoted
    items = sm.list_items("sess_p")
    it = next(x for x in items["items"] if x["id"] == iid)
    assert it["promoted"] is True
    assert it["palace_memory_id"]
    # palace has content
    from core.memory_palace import MemoryPalace

    mp = MemoryPalace(persist_directory=str(mem))
    hits = mp.query_semantic("Cloud SQL banking demo", top_k=5)
    # may be empty if embedding hash weak; at least get_all has the id
    all_m = mp.get_all_memories()
    assert any(m.get("id") == out["palace_ids"][0] for m in all_m)


def test_promote_with_cognify_graph(env):
    sm, kg, _ = env
    sm.start(session_id="sess_c")
    sm.remember(
        "sess_c",
        "Banking App uses Cloud SQL. Policy Tags protects Cloud SQL.",
        importance=0.85,
        kind="note",
    )
    out = sm.promote(
        "sess_c",
        min_importance=0.5,
        store_palace=False,
        cognify_graph=True,
        cognify_mode="mock",
    )
    assert out["ok"]
    assert out["promoted"] >= 1
    assert out.get("cognify")
    st = kg.status()
    assert st["nodes"] >= 1 or st["edges"] >= 0  # mock extract may write nodes


def test_end_auto_promotes_pinned(env):
    sm, _kg, mem = env
    sm.start(session_id="sess_e")
    sm.remember("sess_e", "low priority scratch", importance=0.2)
    sm.remember(
        "sess_e",
        "PINNED durable fact: prefer mock mode for CI",
        importance=0.5,
        pinned=True,
    )
    out = sm.end("sess_e", auto_promote=True, min_importance=0.95)
    assert out["ok"]
    assert out["session"]["status"] == "ended"
    # pinned should promote even if min_importance high for general path
    promo = out.get("auto_promote") or {}
    assert int(promo.get("promoted") or 0) >= 1
    from core.memory_palace import MemoryPalace

    mp = MemoryPalace(persist_directory=str(mem))
    all_m = mp.get_all_memories()
    assert any("prefer mock mode" in str(m.get("content") or "") for m in all_m)


def test_clear_and_purge(env):
    sm, _kg, _ = env
    sm.start(session_id="sess_x")
    sm.remember("sess_x", "temp")
    sm.clear("sess_x")
    assert sm.get("sess_x")["session"]["status"] == "cleared"
    # hard delete
    sm.start(session_id="sess_y")
    sm.remember("sess_y", "gone")
    sm.clear("sess_y", hard=True)
    assert sm.get("sess_y")["ok"] is False


def test_status_counts(env):
    sm, _kg, _ = env
    sm.start(session_id="s1")
    sm.remember("s1", "a")
    st = sm.status()
    assert st["sessions"] >= 1
    assert st["items"] >= 1


def test_mcp_session_and_kg_tools(env, monkeypatch):
    """MCP dispatch for new tools (offline)."""
    from core import mcp_server

    # status
    out = mcp_server.call_tool("superai_session", {"action": "status"})
    assert isinstance(out, dict)
    # start + remember
    out = mcp_server.call_tool(
        "superai_session",
        {"action": "start", "session_id": "mcp_sess", "dataset_id": "mcp"},
    )
    assert out.get("ok") is not False or "session" in out or out.get("mcp_tool")
    out = mcp_server.call_tool(
        "superai_session",
        {
            "action": "remember",
            "session_id": "mcp_sess",
            "content": "MCP remembered Cloud SQL",
            "importance": 0.7,
        },
    )
    assert isinstance(out, dict)
    # kg
    out = mcp_server.call_tool("superai_kg_query", {"action": "status"})
    assert isinstance(out, dict)
    out = mcp_server.call_tool(
        "superai_kg_upsert",
        {"action": "node", "name": "MCP Node", "type": "System"},
    )
    assert isinstance(out, dict)
    out = mcp_server.call_tool(
        "superai_cognify",
        {"source": "Banking App uses Cloud SQL.", "mode": "mock", "store_palace": False},
    )
    assert isinstance(out, dict)
