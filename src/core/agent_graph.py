"""
Run/subagent graph for web dashboard (Phase 8 N4).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def graph_from_run_result(result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build a simple nodes/edges graph from orchestrator or board result."""
    result = result or {}
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    nodes.append({"id": "task", "label": "task", "kind": "root"})
    steps = result.get("steps") or []
    prev = "task"
    for s in steps:
        if not isinstance(s, dict):
            continue
        sid = f"step-{s.get('step') or s.get('step_id') or len(nodes)}"
        nodes.append(
            {
                "id": sid,
                "label": str(s.get("description") or sid)[:80],
                "kind": "step",
                "model": s.get("model"),
                "status": s.get("status"),
            }
        )
        edges.append({"from": prev, "to": sid})
        prev = sid

    members = result.get("members") or result.get("model_chain") or []
    for i, m in enumerate(members):
        mid = f"member-{i}"
        nodes.append({"id": mid, "label": str(m), "kind": "model"})
        edges.append({"from": "task", "to": mid})

    board = result.get("board")
    if isinstance(board, dict) and board.get("verdict"):
        nodes.append(
            {
                "id": "verdict",
                "label": f"verdict:{board.get('verdict')}",
                "kind": "decision",
            }
        )
        edges.append({"from": prev, "to": "verdict"})

    return {
        "ok": True,
        "nodes": nodes,
        "edges": edges,
        "counts": {"nodes": len(nodes), "edges": len(edges)},
    }


def graph_from_adaptation_events(events: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    events = events or []
    nodes = [{"id": "run", "label": "run", "kind": "root"}]
    edges = []
    for i, ev in enumerate(events[:40]):
        nid = f"ev-{i}"
        nodes.append(
            {
                "id": nid,
                "label": str(ev.get("kind") or "event"),
                "kind": "event",
                "detail": {k: v for k, v in ev.items() if k != "ts"},
            }
        )
        edges.append({"from": "run" if i == 0 else f"ev-{i-1}", "to": nid})
    return {"ok": True, "nodes": nodes, "edges": edges}
