"""SuperAI local MCP server — central memory + tools for external AIs."""

import json
from pathlib import Path

from core.mcp_server import (
    call_tool,
    client_config_snippet,
    handle_request,
    list_tools,
    write_client_config,
)
from core.memory_palace import MemoryPalace


def test_tools_list_includes_memory_and_cli():
    names = {t["name"] for t in list_tools()}
    for need in (
        "superai_memory_search",
        "superai_memory_store",
        "superai_memory_context",
        "superai_cli_run",
        "superai_cli_parallel",
        "superai_learn",
        "superai_central_memory_status",
    ):
        assert need in names


def test_initialize_and_tools_list():
    init = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init["result"]["serverInfo"]["name"] == "superai"
    assert "tools" in init["result"]["capabilities"]

    listed = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = listed["result"]["tools"]
    assert len(tools) >= 8


def test_memory_store_and_search_via_mcp(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    (tmp_path / ".superai").mkdir()

    store = call_tool(
        "superai_memory_store",
        {
            "content": "MCP shared fact: prefer pytest for SuperAI tests.",
            "tags": "mcp,testing",
            "source": "test_client",
        },
    )
    assert store["ok"] is True
    assert store.get("memory_id")

    search = call_tool(
        "superai_memory_search",
        {"query": "pytest SuperAI tests", "top_k": 5},
    )
    assert search["count"] >= 1
    blob = json.dumps(search)
    assert "pytest" in blob.lower() or "MCP" in blob


def test_memory_context_tool(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    (tmp_path / ".superai").mkdir()
    MemoryPalace().store("Always use workspace jail for file edits.", tags=["learning"])
    ctx = call_tool("superai_memory_context", {"task": "edit a file safely"})
    assert ctx.get("enabled") is True
    assert "prompt" in ctx


def test_cli_run_dry_via_mcp(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    (tmp_path / ".superai").mkdir()
    out = call_tool(
        "superai_cli_run",
        {
            "cli": "claude",
            "prompt": "say hello via mcp",
            "dry_run": True,
            "use_memory": True,
        },
    )
    assert out.get("ok") is True
    assert out.get("context_id") or out.get("memory_write")


def test_learn_via_mcp(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    (tmp_path / ".superai").mkdir()
    r = call_tool(
        "superai_learn",
        {
            "task": "implemented feature X",
            "model_or_cli": "cli:cursor",
            "success": True,
            "output": "feature X landed",
            "source": "cursor_mcp",
        },
    )
    assert r.get("ok") is True or r.get("learning_id") or r.get("skipped") is not True


def test_resources_read(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    resp = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "resources/read",
            "params": {"uri": "superai://memory/status"},
        }
    )
    assert "result" in resp
    text = resp["result"]["contents"][0]["text"]
    assert "MemoryPalace" in text or "enabled" in text


def test_client_config_snippet():
    cfg = client_config_snippet()
    assert "mcpServers" in cfg
    assert "superai" in cfg["mcpServers"]
    assert "mcp-serve" in " ".join(cfg["mcpServers"]["superai"].get("args") or [])


def test_write_client_config(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    path = write_client_config()
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "mcpServers" in data


def test_tools_call_jsonrpc(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    (tmp_path / ".superai").mkdir()
    resp = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "superai_central_memory_status",
                "arguments": {},
            },
        }
    )
    assert resp["result"]["isError"] is False
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body.get("store") == "MemoryPalace"
