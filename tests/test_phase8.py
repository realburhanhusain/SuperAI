"""Phase 8 nice-to-have modules."""

from pathlib import Path

from core.agent_graph import graph_from_run_result, graph_from_adaptation_events
from core.assistant_goals import GoalStore
from core.multimodal import prompt_with_images
from core.model_bakeoff import bakeoff
from core.palace_tenant import current_tenant, scope_metadata, tenant_tag
from core.plugin_catalog import browse_catalog
from core.agent_tui import compact_turns


def test_compact_turns():
    t = compact_turns(
        [{"user": "hello", "assistant": "hi"}, {"user": "next", "assistant": "ok"}],
        max_chars=500,
    )
    assert "hello" in t or "Compacted" in t


def test_goals_store(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    store = GoalStore()
    g = store.add("ship phase 8", detail="implement N1-N8")
    assert g["id"]
    assert store.list()
    assert store.complete(g["id"]) is True
    assert store.list("open") == []


def test_multimodal_missing_image():
    out = prompt_with_images("describe", ["no-such-file.png"])
    assert out["ok"] is True
    assert out["attachments"]


def test_agent_graph():
    g = graph_from_run_result(
        {
            "steps": [{"step": 1, "description": "plan", "model": "gpt-4o", "status": "success"}],
            "members": ["gpt-4o", "deepseek-chat"],
            "board": {"verdict": "approve"},
        }
    )
    assert g["counts"]["nodes"] >= 3
    g2 = graph_from_adaptation_events([{"kind": "worker_pool"}, {"kind": "step_done"}])
    assert g2["ok"] is True


def test_bakeoff_mock():
    out = bakeoff("say hi", ["gpt-4o", "deepseek-chat"], use_mock=True)
    assert out["ok"] is True
    assert out["winner"]
    assert len(out["results"]) == 2


def test_tenant_and_plugins():
    assert tenant_tag("acme") == "tenant:acme"
    meta = scope_metadata({"foo": 1}, tenant="acme")
    assert meta["tenant_id"] == "acme"
    assert "tenant:acme" in meta["tags"]
    cat = browse_catalog(query="memory")
    assert cat["ok"] is True
