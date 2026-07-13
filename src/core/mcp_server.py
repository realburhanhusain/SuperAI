"""
Minimal MCP-style JSON-RPC stdio server surface (N1).

Not a full MCP SDK implementation — exposes tools/list and tools/call
over newline-delimited JSON for integration testing and adapters.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional


TOOLS = [
    {
        "name": "superai_status",
        "description": "Return SuperAI status snapshot",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "superai_memory_search",
        "description": "Semantic memory search",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "top_k": {"type": "integer"}},
            "required": ["query"],
        },
    },
    {
        "name": "superai_run",
        "description": "Run an orchestrated task (mock by default)",
        "inputSchema": {
            "type": "object",
            "properties": {"task": {"type": "string"}},
            "required": ["task"],
        },
    },
]


def handle_request(req: Dict[str, Any]) -> Dict[str, Any]:
    rid = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "superai", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        try:
            result = _call_tool(name, args)
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, default=str)}],
                    "isError": False,
                },
            }
        except Exception as e:  # noqa: BLE001
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "content": [{"type": "text", "text": str(e)}],
                    "isError": True,
                },
            }
    return {
        "jsonrpc": "2.0",
        "id": rid,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def _call_tool(name: Optional[str], args: Dict[str, Any]) -> Any:
    if name == "superai_status":
        from .doctor import run_doctor

        return run_doctor(quick=True)
    if name == "superai_memory_search":
        from .memory_palace import MemoryPalace

        return MemoryPalace().query_semantic(
            str(args.get("query") or ""), top_k=int(args.get("top_k") or 5)
        )
    if name == "superai_run":
        from .orchestrator import SuperAIOrchestrator

        return SuperAIOrchestrator().run_task(str(args.get("task") or ""))
    raise ValueError(f"Unknown tool: {name}")


def serve_stdio() -> None:
    """Read NDJSON requests from stdin, write responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle_request(req)
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()
