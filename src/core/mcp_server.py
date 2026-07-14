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
        "Semantic search over SuperAI central Memory Palace (shared by all SuperAI-mediated AIs).",
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
        },
        ["query"],
    ),
    _tool(
        "superai_memory_palace",
        "Browse Memory Palace layout or list memories by wing/room.",
        {
            "action": {
                "type": "string",
                "description": "layout | browse | clusters",
            },
            "wing": {"type": "string"},
            "room": {"type": "string"},
            "limit": {"type": "integer"},
            "method": {
                "type": "string",
                "description": "For clusters: auto|embedding|wing|tag",
            },
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

    if name == "superai_status":
        from .doctor import run_doctor

        return run_doctor(quick=True)

    if name == "superai_central_memory_status":
        from .central_memory import status as central_memory_status

        return central_memory_status()

    if name == "superai_memory_search":
        from .memory_palace import MemoryPalace

        query = str(args.get("query") or "")
        top_k = int(args.get("top_k") or 5)
        tags_raw = args.get("tags")
        tag_list = None
        if tags_raw:
            tag_list = [t.strip() for t in str(tags_raw).split(",") if t.strip()]
        wing = args.get("wing")
        room = args.get("room")
        hits = MemoryPalace().query_semantic(
            query,
            top_k=top_k,
            tags=tag_list,
            wing=str(wing) if wing else None,
            room=str(room) if room else None,
        )
        return {
            "query": query,
            "wing": wing,
            "room": room,
            "count": len(hits) if isinstance(hits, list) else 0,
            "hits": hits,
            "store": "MemoryPalace",
            "note": "Shared central memory for all SuperAI-mediated AIs",
        }

    if name == "superai_memory_palace":
        from .memory_palace import MemoryPalace

        mp = MemoryPalace()
        action = str(args.get("action") or "layout").lower()
        wing = args.get("wing")
        room = args.get("room")
        limit = int(args.get("limit") or 30)
        if action == "layout":
            return mp.palace_layout()
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
                    method=str(args.get("method") or "auto"),
                )
            }
        raise ValueError("action must be layout|browse|clusters")

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
        from .orchestrator import SuperAIOrchestrator

        task = str(args.get("task") or "")
        if not task.strip():
            raise ValueError("task required")
        # Orchestrator already injects/learns via MemoryPalace
        return SuperAIOrchestrator().run_task(task)

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
