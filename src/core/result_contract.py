"""
Stable SuperAI result envelope (Improvement Phase 1).

Every major path (run, board, ask) should expose these fields so automation
and UIs never confuse mock/dry-run with live success.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


CONTRACT_VERSION = "superai.result.v1"

REQUIRED_KEYS = (
    "ok",
    "status",
    "mock",
    "dry_run",
    "model_chain",
    "tokens",
    "estimated_cost_usd",
    "members",
    "memory_ids",
    "contract",
)


def empty_contract(**overrides: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "ok": False,
        "status": "error",
        "mock": False,
        "dry_run": False,
        "model_chain": [],
        "tokens": 0,
        "estimated_cost_usd": 0.0,
        "members": [],
        "memory_ids": [],
        "contract": CONTRACT_VERSION,
    }
    base.update(overrides)
    return base


def normalize_status(ok: bool, *, failed: bool = False, cancelled: bool = False) -> str:
    if cancelled:
        return "cancelled"
    if failed or not ok:
        return "error" if not ok else "failed"
    return "success"


def extract_tokens(obj: Any) -> int:
    if not isinstance(obj, dict):
        return 0
    usage = obj.get("usage") if isinstance(obj.get("usage"), dict) else {}
    for key in ("total_tokens", "tokens", "token_count"):
        try:
            v = usage.get(key) if key in usage else obj.get(key)
            if v is not None:
                return max(0, int(v))
        except (TypeError, ValueError):
            continue
    # sum nested opinions/steps
    total = 0
    for nest_key in ("opinions", "steps", "results"):
        items = obj.get(nest_key)
        if isinstance(items, list):
            for it in items:
                total += extract_tokens(it)
    return total


def extract_cost(obj: Any) -> float:
    if not isinstance(obj, dict):
        return 0.0
    for key in ("estimated_cost_usd", "cost_usd", "total_cost", "cost"):
        try:
            if obj.get(key) is not None:
                return max(0.0, float(obj[key]))
        except (TypeError, ValueError):
            continue
    total = 0.0
    for nest_key in ("opinions", "steps", "results"):
        items = obj.get(nest_key)
        if isinstance(items, list):
            for it in items:
                total += extract_cost(it)
    return round(total, 6)


def extract_model_chain(obj: Any) -> List[str]:
    chain: List[str] = []
    if not isinstance(obj, dict):
        return chain

    def _add(x: Any) -> None:
        s = str(x or "").strip()
        if s and s not in chain:
            chain.append(s)

    for key in ("model_chain", "models_used", "members"):
        val = obj.get(key)
        if isinstance(val, list):
            for v in val:
                _add(v)
        elif val:
            _add(val)
    for key in ("model", "model_used", "model_or_cli", "primary"):
        _add(obj.get(key))
    for nest_key in ("steps", "opinions"):
        items = obj.get(nest_key)
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict):
                    _add(it.get("model") or it.get("member_id") or it.get("cli") or it.get("model_or_cli"))
    return chain


def extract_memory_ids(obj: Any) -> List[str]:
    ids: List[str] = []
    if not isinstance(obj, dict):
        return ids

    def _add(x: Any) -> None:
        s = str(x or "").strip()
        if s and s not in ids:
            ids.append(s)

    for key in ("memory_ids", "context_id", "memory_id"):
        val = obj.get(key)
        if isinstance(val, list):
            for v in val:
                _add(v)
        else:
            _add(val)
    mw = obj.get("memory_write")
    if isinstance(mw, dict):
        _add(mw.get("id") or mw.get("memory_id") or mw.get("context_id"))
    return ids


def apply_contract(
    result: Dict[str, Any],
    *,
    mock: Optional[bool] = None,
    dry_run: Optional[bool] = None,
    members: Optional[Sequence[str]] = None,
    ok: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Mutate/return result with normalized contract fields.
    Existing keys are preserved; contract fields are filled or corrected.
    """
    if not isinstance(result, dict):
        result = {"payload": result}

    if ok is None:
        ok = bool(result.get("ok", result.get("status") not in {"error", "failed", False}))
        if result.get("status") in {"error", "failed"}:
            ok = False
        if result.get("success") is False:
            ok = False
        if result.get("success") is True:
            ok = True

    if mock is None:
        mock = bool(result.get("mock"))
        if result.get("use_mock") is not None:
            mock = bool(result.get("use_mock"))
    if dry_run is None:
        dry_run = bool(result.get("dry_run"))

    status = result.get("status")
    if not status or status is True:
        status = normalize_status(bool(ok))
    if dry_run and ok and status == "success":
        # dry-run success is OK but callers must see dry_run=true
        pass
    if mock and status == "success":
        result.setdefault("note_mock", "Result produced under mock/offline mode")

    model_chain = list(result.get("model_chain") or []) or extract_model_chain(result)
    mem_ids = list(result.get("memory_ids") or []) or extract_memory_ids(result)
    tokens = result.get("tokens")
    if tokens is None:
        tokens = extract_tokens(result)
    else:
        try:
            tokens = int(tokens)
        except (TypeError, ValueError):
            tokens = extract_tokens(result)

    cost = result.get("estimated_cost_usd")
    if cost is None:
        cost = extract_cost(result)
    else:
        try:
            cost = float(cost)
        except (TypeError, ValueError):
            cost = extract_cost(result)

    member_list: List[str] = []
    if members is not None:
        member_list = [str(m) for m in members if str(m).strip()]
    elif isinstance(result.get("members"), list):
        member_list = [str(m) for m in result["members"]]
    else:
        member_list = list(model_chain)

    result["ok"] = bool(ok)
    result["status"] = str(status)
    result["mock"] = bool(mock)
    result["dry_run"] = bool(dry_run)
    result["model_chain"] = model_chain
    result["tokens"] = max(0, int(tokens or 0))
    result["estimated_cost_usd"] = round(float(cost or 0.0), 6)
    result["members"] = member_list
    result["memory_ids"] = mem_ids
    result["contract"] = CONTRACT_VERSION
    return result


def assert_contract(result: Dict[str, Any]) -> List[str]:
    """Return list of missing/invalid contract issues (empty = ok)."""
    issues: List[str] = []
    for k in REQUIRED_KEYS:
        if k not in result:
            issues.append(f"missing:{k}")
    if "status" in result and result["status"] not in {
        "success",
        "error",
        "failed",
        "cancelled",
        "partial",
    }:
        issues.append(f"bad_status:{result.get('status')}")
    return issues
