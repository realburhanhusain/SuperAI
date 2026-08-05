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


def generate_svg(graph: Dict[str, Any]) -> str:
    """Generate a robust SVG string from the graph dictionary."""
    import math

    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []

    width = 800
    height = 420
    cx = width / 2
    cy = height / 2
    radius = min(width, height) * 0.32

    # Layout nodes in a circle
    pos = {}
    n = len(nodes)
    for i, node in enumerate(nodes):
        if n == 1:
            pos[node["id"]] = (cx, cy)
        else:
            angle = (i / n) * 2 * math.pi
            pos[node["id"]] = (cx + math.cos(angle) * radius, cy + math.sin(angle) * radius)

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="420px" style="background:#121a33; border-radius:12px; font-family:system-ui;">',
        '<style>',
        '.node { fill: #3d7eff; stroke: #9ec1ff; stroke-width: 2px; }',
        '.edge { stroke: #6b7a99; stroke-width: 2px; }',
        '.label { fill: #e8eefc; font-size: 11px; }',
        '</style>'
    ]

    # Draw edges first
    for edge in edges:
        p1 = pos.get(edge["from"])
        p2 = pos.get(edge["to"])
        if p1 and p2:
            svg_parts.append(f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" class="edge" />')

    # Draw nodes
    for node in nodes:
        p = pos.get(node["id"])
        if p:
            svg_parts.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="14" class="node" />')
            label = str(node.get("label") or node.get("id"))[:28]
            label = label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            svg_parts.append(f'<text x="{p[0]+18:.1f}" y="{p[1]+4:.1f}" class="label">{label}</text>')

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)
