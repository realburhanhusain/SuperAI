"""G3 streaming honesty + G4 dashboard MOCK/LIVE labels."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_stream_capabilities_matrix():
    from core.token_stream import stream_capabilities, supports_stream

    caps = stream_capabilities(model="gpt-4o-mini", provider="openai")
    assert caps["ok"] is True
    assert caps["modes"]["mock_chunked"] is True
    assert caps["modes"]["chunked_fallback"] is True
    assert caps.get("provider_matrix")
    kinds = {r["provider_kind"] for r in caps["provider_matrix"]}
    assert "anthropic" in kinds
    assert "ollama_local" in kinds
    assert "mock" in kinds

    ant = supports_stream(model="claude-3-5-sonnet", provider="anthropic")
    assert ant["supports_stream"] is True
    assert "anthropic" in ant["preferred_mode"] or ant["preferred_mode"].startswith("sse")

    ol = supports_stream(model="llama3", provider="ollama")
    assert ol["supports_stream"] is True


def test_mock_stream_meta_and_fallback_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    from core.model_caller import ModelCaller
    from core.model_registry import ModelRegistry
    from core.token_stream import get_stream_meta

    caller = ModelCaller(use_mock=True, registry=ModelRegistry())
    chunks = list(caller.call_stream(model="gpt-4o-mini", prompt="hello world stream test"))
    assert chunks
    meta = get_stream_meta()
    assert meta.get("mode") == "mock_chunked"
    assert meta.get("cancelled") is False
    assert meta.get("chunks", 0) >= 1


def test_chunked_fallback_sets_reason(tmp_path, monkeypatch):
    """Non-mock path that fails OpenAI stream should label chunked_fallback."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "0")
    from core.model_caller import ModelCaller
    from core.model_registry import ModelRegistry
    from core.token_stream import get_stream_meta

    caller = ModelCaller(use_mock=False, registry=ModelRegistry())

    def boom(*a, **k):
        raise RuntimeError("no_network_fixture")

    monkeypatch.setattr(caller, "_stream_anthropic", boom)
    monkeypatch.setattr(
        caller,
        "_resolve_openai_endpoint",
        lambda *a, **k: ("http://127.0.0.1:9", "fake", None),
    )
    monkeypatch.setattr(
        caller,
        "call",
        lambda **kw: {"response": "fallback body full response", "ok": True, "mock": True},
    )

    class _FailClient:
        def __init__(self, *a, **k):
            pass

        @property
        def chat(self):
            return self

        @property
        def completions(self):
            return self

        def create(self, *a, **k):
            raise RuntimeError("forced_stream_failure")

    import sys
    import types

    fake_openai = types.ModuleType("openai")
    fake_openai.OpenAI = _FailClient
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    chunks = list(
        caller.call_stream(model="gpt-4o-mini", prompt="x", provider="openai")
    )
    assert chunks
    meta = get_stream_meta()
    assert meta.get("mode") == "chunked_fallback"
    assert meta.get("fallback_reason")


def test_dashboard_snapshot_honesty_mock(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    (tmp_path / ".superai").mkdir(parents=True)
    # Force config mock
    from core.config import Config

    cfg = Config()
    cfg.set("mock_mode", True, persist=False)

    from core.observability import build_dashboard_snapshot

    snap = build_dashboard_snapshot(history_limit=2, log_lines=2)
    assert snap.get("honesty") == "MOCK" or snap.get("label") == "MOCK"
    assert snap.get("mock_mode") is True
    assert snap.get("live") is False
    assert "spend" in snap


def test_dashboard_honesty_live_flag():
    from core.foundation_modules import dashboard_honesty

    h = dashboard_honesty({"use_mock": False})
    assert h["label"] == "LIVE"
    assert h["live"] is True
    assert h["mock"] is False
    assert "LIVE" in h["banner"]

    m = dashboard_honesty({"use_mock": True})
    assert m["label"] == "MOCK"
    assert "MOCK" in m["banner"]


def test_dashboard_state_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    (tmp_path / ".superai").mkdir(parents=True)
    from core.foundation_complete import dashboard_state

    st = dashboard_state()
    assert st.get("ok") is True
    assert st.get("label") in {"MOCK", "LIVE"}
    assert st.get("honesty") in {"MOCK", "LIVE", st.get("label")}
    assert "spend" in st
