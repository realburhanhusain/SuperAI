"""Offline tests for M079 JSON surface, M027 streaming, M093 MCP safety."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_m079_render_public_json_mode(capsys):
    from core.public_surface import render_public, set_json_mode, json_surface_report

    set_json_mode(True)
    try:
        out = render_public({"ok": True, "hello": "world", "product": "test"})
        assert out.get("contract") or out.get("ok") is True
        assert out.get("honesty") in {"MOCK", "LIVE"}
        assert "exit_code" in out
        captured = capsys.readouterr().out
        assert "hello" in captured or "world" in captured
        rep = json_surface_report()
        assert rep["ok"] is True
        assert rep["count"] >= 20
        assert "status" in rep["capable_commands"]
    finally:
        set_json_mode(False)


def test_m079_human_path_when_json_off():
    from core.public_surface import render_public, set_json_mode

    set_json_mode(False)
    seen = {}

    def human(data):
        seen["data"] = data

    out = render_public({"ok": True, "x": 1}, human_fn=human)
    assert seen["data"]["x"] == 1
    assert out.get("ok") is True


def test_m027_mock_stream_meta(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    from core.model_caller import ModelCaller
    from core.model_registry import ModelRegistry
    from core.token_stream import get_stream_meta, stream_capabilities

    caller = ModelCaller(use_mock=True, registry=ModelRegistry())
    chunks = list(caller.call_stream(model="gpt-4o-mini", prompt="say hello in a few words"))
    assert chunks
    assert "".join(chunks)
    meta = get_stream_meta()
    assert meta.get("mode") == "mock_chunked"
    assert meta.get("chunks", 0) >= 1
    # stream() delegates to call_stream
    more = list(caller.stream(model="gpt-4o-mini", prompt="hi again"))
    assert more
    caps = stream_capabilities(model="claude-3-5-sonnet", provider="anthropic")
    assert caps["ok"] is True
    assert caps["modes"]["mock_chunked"] is True
    assert caps["modes"]["chunked_fallback"] is True


def test_m093_safety_matrix_and_live_block(monkeypatch):
    monkeypatch.delenv("SUPERAI_MCP_ALLOW_LIVE", raising=False)
    from core.mcp_safety import audit_tool_dispatch, safety_matrix, wrap_mcp_tool

    m = safety_matrix()
    assert m["ok"] is True
    assert m["contract"] is True
    assert m["live_requires_env"] == "SUPERAI_MCP_ALLOW_LIVE"
    assert m["registered_count"] >= 1
    assert isinstance(m["budget_on_spend_tools"], list)

    # Live spend without env should fail closed
    def boom():
        return {"ok": True, "spent": True}

    blocked = wrap_mcp_tool(
        "superai_ask",
        boom,
        mock=False,
        args={"live": True},
    )
    assert blocked.get("ok") is False
    assert "SUPERAI_MCP_ALLOW_LIVE" in str(blocked.get("error") or "")

    audit = audit_tool_dispatch("superai_status", {})
    assert audit.get("mcp_safety") is True or audit.get("ok") is True


def test_m093_call_tool_status():
    from core.mcp_server import call_tool

    out = call_tool("superai_status", {})
    assert isinstance(out, dict)
    assert out.get("mcp_tool") == "superai_status" or out.get("ok") is not None
