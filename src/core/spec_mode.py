"""Spec-first mode: plan → approve → implement (V6 S102)."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional


def _store() -> Path:
    p = Path.home() / ".superai" / "specs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def create_spec(task: str, plan_text: str) -> Dict[str, Any]:
    sid = f"spec-{uuid.uuid4().hex[:8]}"
    data = {
        "id": sid,
        "task": task[:2000],
        "plan": plan_text[:20000],
        "status": "pending_approval",
        "created_at": time.time(),
        "approved_at": None,
    }
    path = _store() / f"{sid}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def approve_spec(spec_id: str) -> Dict[str, Any]:
    path = _store() / f"{spec_id}.json"
    if not path.is_file():
        return {"ok": False, "error": "not_found"}
    data = json.loads(path.read_text(encoding="utf-8"))
    data["status"] = "approved"
    data["approved_at"] = time.time()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"ok": True, "spec": data}


def get_spec(spec_id: str) -> Dict[str, Any]:
    path = _store() / f"{spec_id}.json"
    if not path.is_file():
        return {"ok": False, "error": "not_found"}
    return {"ok": True, "spec": json.loads(path.read_text(encoding="utf-8"))}


def run_spec_first(task: str, *, use_mock: bool = True, auto_approve: bool = False) -> Dict[str, Any]:
    """Generate plan via agent plan role; optionally auto-approve."""
    from .public_api import wrap_public_result
    from .superai_agent.runtime import AgentRuntime

    rt = AgentRuntime(use_mock=use_mock)
    plan_out = rt.run(
        f"Write a step-by-step implementation plan only (no code yet):\n{task}",
        agent="plan",
        permission="plan",
        max_rounds=1,
    )
    plan_text = plan_out.response or ""
    spec = create_spec(task, plan_text)
    if auto_approve:
        approve_spec(spec["id"])
        impl = rt.run(
            f"Implement according to this approved plan:\n{plan_text}\n\nTask: {task}",
            agent="build",
            permission="ask" if not use_mock else "plan",
            max_rounds=2,
        )
        return wrap_public_result(
            {
                "ok": impl.ok,
                "phase": "implemented",
                "spec": get_spec(spec["id"]).get("spec"),
                "plan_response": plan_text[:2000],
                "impl_response": (impl.response or "")[:2000],
                "mock": use_mock,
            },
            mock=use_mock,
            ok=impl.ok,
            record_spend=False,
        )
    return wrap_public_result(
        {
            "ok": True,
            "phase": "pending_approval",
            "spec_id": spec["id"],
            "plan": plan_text[:4000],
            "hint": f"superai spec-approve {spec['id']}",
            "mock": use_mock,
        },
        mock=use_mock,
        ok=True,
        record_spend=False,
    )
