"""
SuperAI local MCP server — expose central Memory Palace + orchestration to
other AIs and their CLIs (Claude Code, Cursor, Codex, Gemini, Grok, …).

Transports:
  - stdio NDJSON (default MCP client pattern): `superai mcp-serve`
  - HTTP JSON-RPC (optional): POST /mcp on `superai web`

Clients never open SuperAI's DB; they call tools that inject/search/store via
central_memory / MemoryPalace and can run external CLIs *through* SuperAI so
outcomes write back into the same palace.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


SERVER_NAME = "superai"
SERVER_VERSION = "0.2.0"
PROTOCOL_VERSION = "2024-11-05"


def _tool(
    name: str,
    description: str,
    properties: Optional[Dict[str, Any]] = None,
    required: Optional[List[str]] = None,
) -> Dict[str, Any]:
    schema: Dict[str, Any] = {
        "type": "object",
        "properties": properties or {},
    }
    if required:
        schema["required"] = required
    return {
        "name": name,
        "description": description,
        "inputSchema": schema,
    }


TOOLS: List[Dict[str, Any]] = [
    _tool(
        "superai_status",
        "SuperAI doctor/status snapshot (env, central memory, host tools).",
    ),
    _tool(
        "superai_central_memory_status",
        "Central Memory Palace status: enabled, write-back, store path/count.",
    ),
    _tool(
        "superai_memory_search",
        "Multi-strategy memory recall over palace + graph + session (P4). Default strategy=auto.",
        {
            "query": {"type": "string", "description": "Search query"},
            "top_k": {"type": "integer", "description": "Max results (default 5)"},
            "tags": {
                "type": "string",
                "description": "Optional comma-separated tags filter",
            },
            "wing": {
                "type": "string",
                "description": "Optional wing filter (technical, learning, agentic, …)",
            },
            "room": {
                "type": "string",
                "description": "Optional room filter within wing",
            },
            "strategy": {
                "type": "string",
                "description": "auto|vector|keyword|graph|hybrid|session (default auto)",
            },
            "session_id": {
                "type": "string",
                "description": "Session buffer id for session/auto strategies",
            },
            "dataset_id": {"type": "string"},
        },
        ["query"],
    ),
    _tool(
        "superai_memory_palace",
        "Browse Memory Palace layout, clusters, room suggestions, or promote rooms.",
        {
            "action": {
                "type": "string",
                "description": "layout | browse | clusters | suggest | promote | snapshot",
            },
            "wing": {"type": "string"},
            "room": {"type": "string"},
            "limit": {"type": "integer"},
            "method": {
                "type": "string",
                "description": "For clusters: auto|embedding|wing|tag",
            },
            "apply": {
                "type": "boolean",
                "description": "For promote: write rooms into catalog",
            },
            "reassign": {
                "type": "boolean",
                "description": "For promote: re-tag memory metadata",
            },
            "min_size": {"type": "integer"},
        },
    ),
    _tool(
        "superai_memory_store",
        "Store a memory into central Memory Palace so other SuperAI-mediated AIs can retrieve it.",
        {
            "content": {"type": "string", "description": "Memory text"},
            "tags": {
                "type": "string",
                "description": "Comma-separated tags (e.g. learning,coding,cli:claude)",
            },
            "importance": {
                "type": "number",
                "description": "0.0–1.0 importance (default 0.7)",
            },
            "source": {
                "type": "string",
                "description": "Who is storing (e.g. claude-code, cursor)",
            },
        },
        ["content"],
    ),
    _tool(
        "superai_memory_context",
        "Build a prompt-ready context pack (memory + skills) for a task. Use before calling other tools/CLIs.",
        {
            "task": {"type": "string"},
            "prompt": {
                "type": "string",
                "description": "Optional user prompt to wrap; defaults to task",
            },
        },
        ["task"],
    ),
    _tool(
        "superai_kg_query",
        "Query SuperAI knowledge graph nodes or path between entities.",
        {
            "action": {
                "type": "string",
                "description": "status | query | path | neighbors (default query)",
            },
            "type": {"type": "string", "description": "Node type filter"},
            "name": {"type": "string", "description": "Name filter / path endpoint"},
            "from_name": {"type": "string"},
            "to_name": {"type": "string"},
            "node_id": {"type": "string"},
            "hops": {"type": "integer", "description": "Max path hops (default 2)"},
            "dataset_id": {"type": "string"},
            "limit": {"type": "integer"},
        },
    ),
    _tool(
        "superai_kg_upsert",
        "Upsert knowledge graph node or edge (mutating).",
        {
            "action": {
                "type": "string",
                "description": "node | edge (default node)",
            },
            "name": {"type": "string"},
            "type": {"type": "string"},
            "from_name": {"type": "string"},
            "to_name": {"type": "string"},
            "relation": {"type": "string"},
            "dataset_id": {"type": "string"},
            "source_memory_id": {"type": "string"},
        },
    ),
    _tool(
        "superai_session",
        "Session memory buffer: start/remember/recall/promote/end/clear (short-term → palace).",
        {
            "action": {
                "type": "string",
                "description": "start|remember|recall|promote|end|clear|status|list",
            },
            "session_id": {"type": "string"},
            "content": {"type": "string"},
            "query": {"type": "string"},
            "kind": {"type": "string"},
            "importance": {"type": "number"},
            "pinned": {"type": "boolean"},
            "dataset_id": {"type": "string"},
            "min_importance": {"type": "number"},
            "cognify": {"type": "boolean"},
            "cognify_mode": {"type": "string"},
        },
    ),
    _tool(
        "superai_cognify",
        "Cognify text/file into knowledge graph (mock or llm extract).",
        {
            "source": {
                "type": "string",
                "description": "Raw text or absolute file path",
            },
            "dataset_id": {"type": "string"},
            "mode": {"type": "string", "description": "mock | llm"},
            "dry_run": {"type": "boolean"},
            "store_palace": {"type": "boolean"},
        },
        ["source"],
    ),
    _tool(
        "superai_ingest",
        "Multi-format ingest (text/md/jsonl/pdf/url) into palace + optional cognify (P5).",
        {
            "source": {
                "type": "string",
                "description": "Local file/dir path or inline text",
            },
            "url": {
                "type": "string",
                "description": "HTTP(S) URL (SSRF-guarded); alternative to source",
            },
            "dataset_id": {"type": "string"},
            "cognify": {
                "type": "boolean",
                "description": "Also run cognify into knowledge graph",
            },
            "cognify_mode": {"type": "string", "description": "mock | llm"},
            "dry_run": {"type": "boolean"},
            "store_palace": {"type": "boolean"},
            "glob": {
                "type": "string",
                "description": "When source is a directory (default *.md)",
            },
        },
    ),
    _tool(
        "superai_ontology",
        "Memory ontology (P6): show, validate, or map a free type/relation label.",
        {
            "action": {
                "type": "string",
                "description": "show | validate | map (default show)",
            },
            "label": {
                "type": "string",
                "description": "For map: free type or relation label",
            },
            "kind": {
                "type": "string",
                "description": "For map: type | relation (default type)",
            },
        },
    ),
    _tool(
        "superai_dataset",
        "Memory datasets/namespaces (P7): list|create|use|status|export|import|forget.",
        {
            "action": {
                "type": "string",
                "description": "list|create|use|status|export|import|forget",
            },
            "dataset_id": {
                "type": "string",
                "description": "Dataset name (create/use/status/export/forget)",
            },
            "description": {"type": "string"},
            "path": {
                "type": "string",
                "description": "Export output or import source path",
            },
            "yes": {
                "type": "boolean",
                "description": "Required true for forget",
            },
            "dry_run": {"type": "boolean"},
        },
    ),
    _tool(
        "superai_capture",
        "Agent turn capture (P8): config|start|turn|end|stream into session memory.",
        {
            "action": {
                "type": "string",
                "description": "config|start|turn|end|stream (default config)",
            },
            "session_id": {"type": "string"},
            "hook": {
                "type": "string",
                "description": "user_prompt|tool_result|assistant_final|precompact|session_end",
            },
            "content": {"type": "string"},
            "tool": {"type": "string"},
            "level": {
                "type": "string",
                "description": "off|session|session+promote|full-cognify",
            },
            "dataset_id": {"type": "string"},
            "turns": {
                "type": "array",
                "description": "For stream: list of turn objects",
                "items": {"type": "object"},
            },
            "auto_end": {"type": "boolean"},
            "install_hooks": {"type": "boolean"},
        },
    ),
    _tool(
        "superai_learn",
        "Write back a completed outcome into central Memory Palace (learning + result snippet).",
        {
            "task": {"type": "string"},
            "model_or_cli": {
                "type": "string",
                "description": "e.g. cli:claude, gpt-4o, cursor",
            },
            "success": {"type": "boolean"},
            "output": {"type": "string"},
            "error": {"type": "string"},
            "source": {
                "type": "string",
                "description": "Caller id (default mcp_client)",
            },
            "task_type": {"type": "string", "description": "coding|reasoning|general"},
        },
        ["task", "model_or_cli", "success"],
    ),
    _tool(
        "superai_run",
        "Run an orchestrated SuperAI task (uses central memory inject + learn).",
        {
            "task": {"type": "string"},
            "verbose": {"type": "boolean"},
        },
        ["task"],
    ),
    _tool(
        "superai_cli_discover",
        "List external AI CLIs SuperAI knows about and which are on PATH.",
    ),
    _tool(
        "superai_cli_run",
        "Run an external AI CLI through SuperAI with central memory inject + write-back.",
        {
            "cli": {
                "type": "string",
                "description": "CLI name: claude, aider, gemini, codex, cursor, grok, …",
            },
            "prompt": {"type": "string"},
            "dry_run": {
                "type": "boolean",
                "description": "Default true for safety via MCP",
            },
            "approve": {
                "type": "boolean",
                "description": "Approve file-modifying CLIs (live runs)",
            },
            "use_memory": {
                "type": "boolean",
                "description": "Inject + write-back Memory Palace (default true)",
            },
        },
        ["cli", "prompt"],
    ),
    _tool(
        "superai_cli_parallel",
        "Fan-out a task to multiple external CLIs in parallel (agentic); all share Memory Palace.",
        {
            "task": {"type": "string"},
            "clis": {
                "type": "string",
                "description": "Comma-separated CLI names (optional)",
            },
            "dry_run": {"type": "boolean", "description": "Default true"},
            "workers": {"type": "integer"},
        },
        ["task"],
    ),
    _tool(
        "superai_host_tools",
        "Checklist of host tools (git, gh, cloud CLIs, agent CLIs) — not bundled.",
        {
            "profile": {
                "type": "string",
                "description": "core|agentic|cloud|full (default full)",
            }
        },
    ),
    # S7: shared ask session with agent-tui / CLI
    _tool(
        "superai_ask_session",
        "Create/load/append shared SuperAI ask session (same store as agent-tui).",
        {
            "action": {
                "type": "string",
                "description": "create | get | append | list | context",
            },
            "session_id": {
                "type": "string",
                "description": "Existing session id (optional for create)",
            },
            "user": {"type": "string", "description": "User text for append"},
            "assistant": {
                "type": "string",
                "description": "Assistant summary for append",
            },
        },
        ["action"],
    ),
]


RESOURCES = [
    {
        "uri": "superai://memory/status",
        "name": "Central Memory Palace status",
        "description": "JSON status of SuperAI central memory",
        "mimeType": "application/json",
    },
    {
        "uri": "superai://status",
        "name": "SuperAI doctor status",
        "description": "Quick doctor snapshot",
        "mimeType": "application/json",
    },
    {
        "uri": "superai://clis",
        "name": "External CLI discovery",
        "description": "Available external AI CLIs on PATH",
        "mimeType": "application/json",
    },
]


def list_tools() -> List[Dict[str, Any]]:
    return list(TOOLS)


def list_resources() -> List[Dict[str, Any]]:
    return list(RESOURCES)


def handle_request(req: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a single JSON-RPC MCP request dict."""
    rid = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    # Notifications (no id) — acknowledge silently with empty response for NDJSON clients
    if rid is None and method and str(method).startswith("notifications/"):
        return {"jsonrpc": "2.0", "result": None}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                },
                "instructions": (
                    "SuperAI local MCP: use superai_memory_search / superai_memory_store "
                    "for shared Memory Palace; superai_cli_run to invoke other CLIs through "
                    "SuperAI so they share the same central memory."
                ),
            },
        }

    if method in {"ping", "tools/list"}:
        if method == "ping":
            return {"jsonrpc": "2.0", "id": rid, "result": {}}
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": list_tools()}}

    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"resources": list_resources()}}

    if method == "resources/read":
        uri = str((params or {}).get("uri") or "")
        try:
            body = _read_resource(uri)
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(body, indent=2, default=str),
                        }
                    ]
                },
            }
        except Exception as e:  # noqa: BLE001
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "error": {"code": -32000, "message": str(e)},
            }

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        try:
            result = call_tool(name, args if isinstance(args, dict) else {})
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2, default=str),
                        }
                    ],
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

    # Some clients send "shutdown" / "exit"
    if method in {"shutdown", "exit"}:
        return {"jsonrpc": "2.0", "id": rid, "result": None}

    return {
        "jsonrpc": "2.0",
        "id": rid,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def call_tool(name: Optional[str], args: Dict[str, Any]) -> Any:
    """Dispatch MCP tool call — used by stdio and HTTP transports."""
    if not name:
        raise ValueError("tool name required")
    args = args or {}
    # MCP/CLI safety parity (M093): full wrap_mcp_tool gates (budget, live env, permission, jail)
    try:
        from .mcp_safety import wrap_mcp_tool

        def _run() -> Dict[str, Any]:
            result = _call_tool_impl(name, args)
            if not isinstance(result, dict):
                return {"ok": True, "result": result, "mcp_tool": name}
            result.setdefault("mcp_tool", name)
            return result

        live = bool(args.get("live") or args.get("live_run"))
        return wrap_mcp_tool(
            name,
            _run,
            mock=not live,
            estimated_usd=0.2,
            tokens=1000,
            args=args,
        )
    except Exception as e:
        from .public_api import wrap_public_result

        return wrap_public_result(
            {"ok": False, "error": str(e)[:500], "mcp_tool": name, "mcp_safety": True},
            ok=False,
            record_spend=False,
        )


def _call_tool_impl(name: str, args: Dict[str, Any]) -> Any:
    """Inner MCP tool dispatch."""
    if name == "superai_status":
        from .doctor import run_doctor

        return run_doctor(quick=True)

    if name == "superai_central_memory_status":
        from .central_memory import status as central_memory_status

        return central_memory_status()

    if name == "superai_memory_search":
        from .recall_router import recall as run_recall

        query = str(args.get("query") or "")
        top_k = int(args.get("top_k") or 5)
        tags_raw = args.get("tags")
        tag_list = None
        if tags_raw:
            tag_list = [t.strip() for t in str(tags_raw).split(",") if t.strip()]
        wing = args.get("wing")
        room = args.get("room")
        strategy = str(args.get("strategy") or "auto")
        # backward compatible: no strategy → still multi-strategy auto (includes vector)
        out = run_recall(
            query,
            strategy=strategy,
            top_k=top_k,
            session_id=args.get("session_id"),
            dataset_id=args.get("dataset_id"),
            tags=tag_list,
            wing=str(wing) if wing else None,
            room=str(room) if room else None,
        )
        out["wing"] = wing
        out["room"] = room
        out["store"] = "recall_router"
        out["note"] = (
            f"strategy={out.get('strategy')} reason={out.get('strategy_reason')}"
        )
        return out

    if name == "superai_kg_query":
        from .knowledge_graph import get_default_graph

        kg = get_default_graph()
        action = str(args.get("action") or "query").lower()
        if action == "status":
            return kg.status()
        if action == "path":
            return kg.path(
                from_name=args.get("from_name") or args.get("name"),
                to_name=args.get("to_name"),
                hops=int(args.get("hops") or 2),
                dataset_id=args.get("dataset_id"),
            )
        if action == "neighbors":
            nid = str(args.get("node_id") or "")
            if not nid:
                raise ValueError("node_id required for neighbors")
            return kg.neighbors(nid, dataset_id=args.get("dataset_id"))
        return kg.query_nodes(
            type=args.get("type"),
            name=args.get("name"),
            dataset_id=args.get("dataset_id"),
            limit=int(args.get("limit") or 20),
        )

    if name == "superai_kg_upsert":
        from .knowledge_graph import get_default_graph

        kg = get_default_graph()
        action = str(args.get("action") or "node").lower()
        dataset = str(args.get("dataset_id") or "default")
        if action == "edge":
            return kg.upsert_edge(
                from_name=args.get("from_name"),
                to_name=args.get("to_name"),
                relation=str(args.get("relation") or "RELATED_TO"),
                dataset_id=dataset,
                source_memory_id=args.get("source_memory_id"),
            )
        name_v = str(args.get("name") or "").strip()
        if not name_v:
            raise ValueError("name required for node upsert")
        return kg.upsert_node(
            name=name_v,
            type=str(args.get("type") or "Entity"),
            dataset_id=dataset,
            source_memory_id=args.get("source_memory_id"),
        )

    if name == "superai_session":
        from .session_memory import get_default_session_memory

        sm = get_default_session_memory()
        action = str(args.get("action") or "status").lower()
        sid = args.get("session_id")
        if action == "status":
            return sm.status()
        if action == "list":
            return sm.list_sessions(dataset_id=args.get("dataset_id"))
        if action == "start":
            return sm.start(
                session_id=sid,
                dataset_id=str(args.get("dataset_id") or "default"),
                source="mcp",
            )
        if not sid and action not in {"status", "list"}:
            raise ValueError("session_id required")
        if action == "remember":
            return sm.remember(
                str(sid),
                str(args.get("content") or ""),
                kind=str(args.get("kind") or "note"),
                importance=float(args.get("importance") or 0.5),
                pinned=bool(args.get("pinned")),
                dataset_id=str(args.get("dataset_id") or "default"),
                source="mcp",
            )
        if action == "recall":
            return sm.recall(str(sid), query=args.get("query"))
        if action == "promote":
            return sm.promote(
                str(sid),
                min_importance=float(args.get("min_importance") or 0.0),
                cognify_graph=bool(args.get("cognify")),
                cognify_mode=str(args.get("cognify_mode") or "mock"),
            )
        if action == "end":
            return sm.end(
                str(sid),
                auto_promote=True,
                min_importance=float(args.get("min_importance") or 0.6),
                cognify_graph=bool(args.get("cognify")),
                cognify_mode=str(args.get("cognify_mode") or "mock"),
            )
        if action == "clear":
            return sm.clear(str(sid))
        raise ValueError(
            "action must be start|remember|recall|promote|end|clear|status|list"
        )

    if name == "superai_cognify":
        from .cognify import cognify as run_cognify

        source = str(args.get("source") or "")
        if not source:
            raise ValueError("source required")
        return run_cognify(
            source,
            dataset_id=str(args.get("dataset_id") or "default"),
            mode=str(args.get("mode") or "mock"),
            dry_run=bool(args.get("dry_run")),
            store_palace=bool(args.get("store_palace", True)),
        )

    if name == "superai_ingest":
        from .ingest import ingest as run_ingest

        source = args.get("source")
        url = args.get("url")
        if not source and not url:
            raise ValueError("source or url required")
        return run_ingest(
            str(source) if source else None,
            url=str(url) if url else None,
            dataset_id=str(args.get("dataset_id") or "default"),
            cognify=bool(args.get("cognify")),
            cognify_mode=str(args.get("cognify_mode") or "mock"),
            dry_run=bool(args.get("dry_run")),
            store_palace=bool(args.get("store_palace", True)),
            glob_pat=str(args.get("glob") or "*.md"),
        )

    if name == "superai_ontology":
        from .ontology import MemoryOntology, clear_ontology_cache, default_ontology_path

        clear_ontology_cache()
        ont = MemoryOntology.load(default_ontology_path())
        action = str(args.get("action") or "show").lower()
        if action == "show":
            return ont.show()
        if action == "validate":
            return ont.validate()
        if action == "map":
            label = str(args.get("label") or "")
            if not label:
                raise ValueError("label required for map")
            return ont.map_label(label, kind=str(args.get("kind") or "type"))
        raise ValueError("action must be show|validate|map")

    if name == "superai_dataset":
        from pathlib import Path as _Path

        from .memory_dataset import (
            export_dataset,
            forget_dataset,
            get_registry,
            import_dataset,
            status as dataset_status,
        )

        action = str(args.get("action") or "list").lower()
        did = args.get("dataset_id")
        if action == "list":
            return get_registry().list_datasets()
        if action == "create":
            if not did:
                raise ValueError("dataset_id required")
            return get_registry().create(
                str(did), description=str(args.get("description") or "")
            )
        if action == "use":
            if not did:
                raise ValueError("dataset_id required")
            return get_registry().use(str(did))
        if action == "status":
            return dataset_status(str(did) if did else None)
        if action == "export":
            if not did:
                raise ValueError("dataset_id required")
            dest = _Path(str(args["path"])) if args.get("path") else None
            return export_dataset(str(did), dest=dest)
        if action == "import":
            path = args.get("path")
            if not path:
                raise ValueError("path required for import")
            return import_dataset(
                _Path(str(path)),
                dataset_id=str(did) if did else None,
                dry_run=bool(args.get("dry_run")),
            )
        if action == "forget":
            if not did:
                raise ValueError("dataset_id required")
            return forget_dataset(str(did), yes=bool(args.get("yes")))
        raise ValueError(
            "action must be list|create|use|status|export|import|forget"
        )

    if name == "superai_capture":
        from .session_capture import (
            SessionCapture,
            capture_config,
            install_tool_capture_hooks,
            process_turn_stream,
            set_active_capture,
        )

        action = str(args.get("action") or "config").lower()
        if action == "config":
            return capture_config()
        if action == "start":
            cap = SessionCapture.start(
                session_id=str(args["session_id"]) if args.get("session_id") else None,
                dataset_id=str(args["dataset_id"]) if args.get("dataset_id") else None,
                level=str(args["level"]) if args.get("level") else None,
                source="mcp",
            )
            set_active_capture(cap)
            if args.get("install_hooks"):
                install_tool_capture_hooks(cap)
            return cap.status()
        if action == "turn":
            sid = str(args.get("session_id") or "")
            if not sid:
                raise ValueError("session_id required for turn")
            cap = SessionCapture.start(
                session_id=sid,
                dataset_id=str(args["dataset_id"]) if args.get("dataset_id") else None,
                level=str(args["level"]) if args.get("level") else None,
                source="mcp",
            )
            hook = str(args.get("hook") or "user_prompt")
            if hook.lower() in {"tool_result", "tool"}:
                return cap.tool_result(
                    str(args.get("tool") or "tool"),
                    {"ok": True, "summary": str(args.get("content") or "")},
                )
            return cap.capture(hook, args.get("content"))
        if action == "end":
            sid = str(args.get("session_id") or "")
            if not sid:
                raise ValueError("session_id required for end")
            cap = SessionCapture.start(
                session_id=sid,
                dataset_id=str(args["dataset_id"]) if args.get("dataset_id") else None,
                level=str(args["level"]) if args.get("level") else None,
                source="mcp",
            )
            return cap.session_end()
        if action == "stream":
            turns = args.get("turns") or []
            if not isinstance(turns, list):
                raise ValueError("turns must be a list")
            return process_turn_stream(
                turns,
                session_id=str(args["session_id"]) if args.get("session_id") else None,
                level=str(args["level"]) if args.get("level") else None,
                dataset_id=str(args["dataset_id"]) if args.get("dataset_id") else None,
                auto_end=bool(args.get("auto_end", True)),
                source="mcp_stream",
            )
        raise ValueError("action must be config|start|turn|end|stream")

    if name == "superai_memory_palace":
        from .memory_palace import MemoryPalace

        mp = MemoryPalace()
        action = str(args.get("action") or "layout").lower()
        wing = args.get("wing")
        room = args.get("room")
        limit = int(args.get("limit") or 30)
        method = str(args.get("method") or "auto")
        min_size = int(args.get("min_size") or 3)
        if action == "layout":
            return mp.palace_layout()
        if action == "snapshot":
            return mp.browser_snapshot(
                wing=str(wing) if wing else None,
                room=str(room) if room else None,
                limit=limit,
            )
        if action == "browse":
            return {
                "items": mp.query_by_location(
                    wing=str(wing) if wing else None,
                    room=str(room) if room else None,
                    limit=limit,
                )
            }
        if action == "clusters":
            return {
                "clusters": mp.cluster_memories(
                    limit=max(limit, 50),
                    method=method,
                )
            }
        if action == "suggest":
            return {
                "suggestions": mp.suggest_rooms_from_clusters(
                    limit=max(limit, 50),
                    min_size=min_size,
                    method=method,
                )
            }
        if action == "promote":
            return mp.auto_promote_rooms(
                apply=bool(args.get("apply")),
                reassign=bool(args.get("reassign")),
                limit=max(limit, 50),
                min_size=min_size,
                method=method,
            )
        raise ValueError(
            "action must be layout|browse|clusters|suggest|promote|snapshot"
        )

    if name == "superai_memory_store":
        from .memory_palace import MemoryPalace

        content = str(args.get("content") or "").strip()
        if not content:
            raise ValueError("content required")
        tags_raw = args.get("tags") or "mcp,external_ai"
        tags = [t.strip() for t in str(tags_raw).split(",") if t.strip()]
        source = str(args.get("source") or "mcp_client")
        if source and source not in tags:
            tags.append(source)
        importance = float(args.get("importance") or 0.7)
        mid = MemoryPalace().store(
            content,
            tags=tags,
            metadata={
                "source": source,
                "via": "mcp",
            },
            importance=importance,
        )
        return {
            "ok": True,
            "memory_id": mid,
            "tags": tags,
            "source": source,
            "note": "Stored in central Memory Palace — other SuperAI clients can search it",
        }

    if name == "superai_memory_context":
        from .central_memory import inject_context

        task = str(args.get("task") or "")
        prompt = args.get("prompt")
        ctx = inject_context(
            task,
            prompt=str(prompt) if prompt is not None else task,
            use_memory=True,
            metadata={"via": "mcp", "source": "superai_memory_context"},
        )
        return {
            "context_id": ctx.get("context_id"),
            "memory_count": ctx.get("memory_count"),
            "skills": ctx.get("skills"),
            "prompt": ctx.get("prompt"),
            "enabled": ctx.get("enabled"),
        }

    if name == "superai_learn":
        from .central_memory import write_back

        return write_back(
            task=str(args.get("task") or ""),
            source=str(args.get("source") or "mcp_client"),
            model_or_cli=str(args.get("model_or_cli") or "unknown"),
            success=bool(args.get("success")),
            output=str(args.get("output") or ""),
            error=args.get("error"),
            task_type=str(args.get("task_type") or "general"),
            tags=["mcp", "learn"],
            use_memory=True,
        )

    if name == "superai_run":
        import os

        from .config import Config
        from .orchestrator import SuperAIOrchestrator
        from .public_api import wrap_public_result
        from .spend_guard import budget_precheck

        task = str(args.get("task") or "")
        if not task.strip():
            raise ValueError("task required")
        # Safe default: mock unless live=true + SUPERAI_MCP_ALLOW_LIVE=1
        live = bool(args.get("live") or args.get("live_run"))
        cfg = Config()
        use_mock = True
        if live:
            if (os.getenv("SUPERAI_MCP_ALLOW_LIVE") or "").lower() not in {
                "1",
                "true",
                "yes",
            }:
                return wrap_public_result(
                    {
                        "ok": False,
                        "error": (
                            "superai_run live requires SUPERAI_MCP_ALLOW_LIVE=1 "
                            "(and live=true). Default is mock."
                        ),
                        "mock": True,
                    },
                    mock=True,
                    ok=False,
                    record_spend=False,
                )
            block = budget_precheck(estimated_usd=0.2, tokens=1000)
            if block.get("blocked"):
                return block
            use_mock = False
        cfg.config["mock_mode"] = use_mock
        cfg.config["use_mock"] = use_mock
        orch = SuperAIOrchestrator(config=cfg)
        result = orch.run_task(task)
        if isinstance(result, dict):
            result.setdefault("mock", use_mock)
            result.setdefault("live", live and not use_mock)
            return wrap_public_result(
                result,
                mock=use_mock,
                ok=bool(result.get("ok", result.get("status") != "error")),
            )
        return wrap_public_result(
            {"ok": True, "result": result, "mock": use_mock},
            mock=use_mock,
            ok=True,
        )

    if name == "superai_ask_session":
        from .ask_session import AskSessionStore

        store = AskSessionStore()
        action = str(args.get("action") or "list").lower().strip()
        sid = args.get("session_id")
        if action == "create":
            new_id = store.ensure(str(sid) if sid else None)
            return {"ok": True, "session_id": new_id, "shared": True}
        if action == "list":
            return {"ok": True, "sessions": store.list_sessions()}
        if action == "get":
            if not sid:
                raise ValueError("session_id required for get")
            return {"ok": True, "session": store.get(str(sid))}
        if action == "context":
            if not sid:
                raise ValueError("session_id required for context")
            return {
                "ok": True,
                "session_id": sid,
                "context": store.context_preface(str(sid)),
            }
        if action == "append":
            if not sid:
                raise ValueError("session_id required for append")
            data = store.append_turn(
                str(sid),
                str(args.get("user") or ""),
                str(args.get("assistant") or ""),
                meta={"via": "mcp"},
            )
            return {"ok": True, "session_id": sid, "turns": len(data.get("turns") or [])}
        raise ValueError("action must be create|get|append|list|context")

    if name == "superai_cli_discover":
        from .discovery import discover_environment
        from .external_cli import ExternalCLIRegistry

        env = discover_environment()
        return {
            "clis": ExternalCLIRegistry().discover(),
            "available": env.get("clis_available") or [],
            "central_memory": True,
        }

    if name == "superai_cli_run":
        from .central_memory import inject_context, write_back
        from .external_cli import ExternalCLITool

        cli = str(args.get("cli") or "").strip()
        prompt = str(args.get("prompt") or "")
        if not cli or not prompt:
            raise ValueError("cli and prompt required")
        dry_run = args.get("dry_run")
        if dry_run is None:
            dry_run = True  # safe default for MCP
        dry_run = bool(dry_run)
        approve = bool(args.get("approve") or dry_run)
        use_memory = True if args.get("use_memory") is None else bool(args.get("use_memory"))

        orig = prompt
        ctx_id = None
        if use_memory:
            ctx = inject_context(
                orig,
                prompt=orig,
                use_memory=True,
                metadata={"via": "mcp", "cli": cli},
            )
            prompt = ctx.get("prompt") or prompt
            ctx_id = ctx.get("context_id")

        tool = ExternalCLITool(dry_run=dry_run, auto_approve=approve)
        env = tool.run(cli, prompt, approve=approve)
        mem = None
        if use_memory:
            mem = write_back(
                task=orig,
                source="mcp_cli_run",
                model_or_cli=f"cli:{cli}",
                success=bool(env.ok or dry_run),
                latency=float(env.duration_sec or 0),
                output=env.stdout or "",
                error=env.error or env.stderr,
                context_id=ctx_id,
                task_type="coding" if env.modifies_files else "general",
                tags=["mcp", "cli_run", cli],
            )
        return {
            "ok": env.ok or dry_run,
            "cli": cli,
            "dry_run": dry_run or env.dry_run if hasattr(env, "dry_run") else dry_run,
            "exit_code": env.exit_code,
            "stdout": (env.stdout or "")[:8000],
            "stderr": (env.stderr or "")[:2000],
            "error": env.error,
            "context_id": ctx_id,
            "memory_write": mem,
            "command": list(env.command or []),
        }

    if name == "superai_cli_parallel":
        from .cli_pool import ParallelCLIManager

        task = str(args.get("task") or "")
        if not task.strip():
            raise ValueError("task required")
        dry_run = True if args.get("dry_run") is None else bool(args.get("dry_run"))
        workers = int(args.get("workers") or 4)
        clis = None
        if args.get("clis"):
            clis = [c.strip() for c in str(args.get("clis")).split(",") if c.strip()]
        return ParallelCLIManager().run_agentic_parallel(
            task,
            clis=clis,
            max_workers=workers,
            dry_run=dry_run,
            auto_approve=dry_run,
        )

    if name == "superai_host_tools":
        from .host_tools import checklist

        profile = str(args.get("profile") or "full")
        return checklist(profile=profile)

    if name == "superai_mcp_safety":
        from .mcp_safety import safety_matrix

        return safety_matrix()

    raise ValueError(f"Unknown tool: {name}")


def _read_resource(uri: str) -> Any:
    if uri == "superai://memory/status":
        from .central_memory import status as central_memory_status

        return central_memory_status()
    if uri == "superai://status":
        from .doctor import run_doctor

        return run_doctor(quick=True)
    if uri == "superai://clis":
        from .external_cli import ExternalCLIRegistry

        return {"clis": ExternalCLIRegistry().discover()}
    raise ValueError(f"Unknown resource: {uri}")


def serve_stdio() -> None:
    """Read NDJSON / line-delimited JSON-RPC from stdin; write responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Skip pure notifications that must not get a response with id
        if isinstance(req, dict) and req.get("id") is None:
            method = req.get("method") or ""
            if str(method).startswith("notifications/"):
                continue
        resp = handle_request(req if isinstance(req, dict) else {})
        # Do not write null-result notification echoes with id None
        if resp.get("id") is None and resp.get("result") is None and "error" not in resp:
            continue
        sys.stdout.write(json.dumps(resp, default=str) + "\n")
        sys.stdout.flush()


def client_config_snippet(
    *,
    command: Optional[str] = None,
    cwd: Optional[str] = None,
    transport: str = "stdio",
) -> Dict[str, Any]:
    """
    Generate MCP client config fragment (Claude Desktop / Cursor / etc.).

    Place under mcpServers.superai (Claude) or equivalent.
    """
    # Prefer installed entry point; fall back to python -m
    import shutil
    import sys as _sys

    if command:
        cmd = command
        args: List[str] = ["mcp-serve"]
    elif shutil.which("superai"):
        cmd = "superai"
        args = ["mcp-serve"]
    else:
        cmd = _sys.executable
        args = ["-m", "scli", "mcp-serve"]

    entry: Dict[str, Any] = {
        "command": cmd,
        "args": args,
    }
    if cwd:
        entry["cwd"] = str(cwd)
    entry["env"] = {
        "SUPERAI_CENTRAL_MEMORY": "1",
        "SUPERAI_EMBEDDING_HASH": "1",
    }

    if transport == "stdio":
        return {
            "mcpServers": {
                "superai": entry,
            },
            "_comment": (
                "Add mcpServers.superai to Claude Desktop / Cursor MCP settings. "
                "Other AIs then share SuperAI central Memory Palace via tools."
            ),
            "tools": [t["name"] for t in TOOLS],
        }

    return {
        "url": "http://127.0.0.1:8787/mcp",
        "transport": "http",
        "note": "Start with: superai web  then POST JSON-RPC to /mcp",
        "tools": [t["name"] for t in TOOLS],
    }


def write_client_config(
    path: Optional[Path] = None,
    *,
    cwd: Optional[str] = None,
) -> Path:
    out = Path(path or (Path.home() / ".superai" / "mcp_client_config.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    data = client_config_snippet(cwd=cwd)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return out
