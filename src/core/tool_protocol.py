"""
Model-driven tool protocol (V3 Sprint A M1).

Model may emit JSON lines:
  {"tool_call": {"name": "read", "arguments": {"path": "foo.py"}}}
After tools run, optional follow-up ask with results (single iteration by default).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


TOOL_CALL_RE = re.compile(
    r"\{[^{}]*\"tool_call\"\s*:\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)?\}[^{}]*\}",
    re.DOTALL,
)


def extract_tool_calls(text: str) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []
    if not text:
        return calls
    # Try full JSON
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict) and "tool_call" in data:
            calls.append(data["tool_call"])
            return calls
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "tool_call" in item:
                    calls.append(item["tool_call"])
            if calls:
                return calls
    except Exception:
        pass
    for m in TOOL_CALL_RE.finditer(text):
        try:
            obj = json.loads(m.group(0))
            tc = obj.get("tool_call")
            if isinstance(tc, dict) and tc.get("name"):
                calls.append(tc)
        except Exception:
            continue
    # Also support {"name":"read","arguments":{...}} shorthand lines
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{") or "name" not in line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and obj.get("name") and (
                "arguments" in obj or "args" in obj
            ):
                calls.append(
                    {
                        "name": obj["name"],
                        "arguments": obj.get("arguments") or obj.get("args") or {},
                    }
                )
        except Exception:
            continue
    return calls


def run_tool_calls(
    calls: List[Dict[str, Any]],
    *,
    permission_mode: Optional[str] = None,
) -> List[Dict[str, Any]]:
    from .agent_tools import run_tool
    from .progress_events import get_progress_bus

    results = []
    bus = get_progress_bus()
    for tc in calls[:8]:
        name = str(tc.get("name") or "")
        args = tc.get("arguments") or tc.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        bus.emit("tool_call", name=name, args=list(args.keys()))
        r = run_tool(name, permission_mode=permission_mode, **args)
        # Prompt-injection defense on tool outputs (V6 M015)
        try:
            from .injection_defense import sanitize_tool_result

            sanitized = sanitize_tool_result(r)
            if isinstance(r, dict):
                r = {**r, "injection": sanitized.get("injection"), "sanitized": True}
                if sanitized.get("blocked"):
                    r["ok"] = False
                    r["error"] = "tool_result_blocked_injection"
                    r["blocked"] = True
        except Exception:
            pass
        bus.emit("tool_result", name=name, ok=r.get("ok"))
        results.append({"tool_call": tc, "result": r})
        try:
            from .side_effect_audit import record_side_effect

            record_side_effect(
                "tool",
                name=name,
                ok=bool(r.get("ok")),
                dry_run=bool(r.get("dry_run")),
                detail=str(r.get("path") or r.get("error") or "")[:200],
            )
        except Exception:
            pass
    return results


def agent_with_tools(
    prompt: str,
    *,
    model: Optional[str] = None,
    use_mock: Optional[bool] = None,
    max_rounds: int = 2,
    permission_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call model; if tool_call JSON present, execute and optionally re-call once.
    """
    from .config import Config
    from .model_caller import ModelCaller
    from .model_registry import ModelRegistry
    from .permission_mode import mode_from_config
    from .result_contract import apply_contract

    cfg = Config()
    mock = cfg.use_mock if use_mock is None else use_mock
    pmode = permission_mode or mode_from_config(cfg)
    reg = ModelRegistry()
    caller = ModelCaller(use_mock=mock, registry=reg)
    mid = model or cfg.get("preferred_model") or cfg.get("default_model") or "gpt-4o"

    system = (
        "You are SuperAI coding agent. You may request tools by emitting JSON:\n"
        '{"tool_call": {"name": "read|write|glob|grep|diff_apply", '
        '"arguments": {...}}}\n'
        "After tools run you will receive results. Prefer minimal tools."
    )
    transcript = prompt
    all_tools: List[Dict[str, Any]] = []
    last: Dict[str, Any] = {}
    for round_i in range(max(1, max_rounds)):
        last = caller.call(model=mid, prompt=transcript, system_prompt=system)
        text = str(last.get("response") or "")
        calls = extract_tool_calls(text)
        if not calls:
            break
        tool_results = run_tool_calls(calls, permission_mode=pmode)
        all_tools.extend(tool_results)
        transcript = (
            f"{prompt}\n\n[Prior assistant]\n{text[:2000]}\n\n"
            f"[Tool results]\n{json.dumps(tool_results, default=str)[:4000]}\n"
            "Continue. If done, answer without more tool_call JSON."
        )
    out = {
        "ok": str(last.get("status")) != "error",
        "status": last.get("status") or "success",
        "response": last.get("response"),
        "model": mid,
        "tool_rounds": len(all_tools),
        "tool_results": all_tools,
        "mock": bool(last.get("mock") or mock),
        "raw_model": last,
    }
    apply_contract(
        out,
        mock=bool(out.get("mock")),
        dry_run=False,
        members=[mid],
        ok=bool(out.get("ok")),
    )
    return out
