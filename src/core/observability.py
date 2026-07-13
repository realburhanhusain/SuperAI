"""
Shared observability snapshot for terminal + web dashboards (H7).

Both surfaces read the same builders so feedback/status stays consistent.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def build_dashboard_snapshot(
    history_limit: int = 8,
    log_lines: int = 12,
) -> Dict[str, Any]:
    """Collect live-ish system snapshot from ~/.superai stores."""
    snap: Dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": None,
        "history": [],
        "memory": {},
        "skills": [],
        "clis": [],
        "bandit_arms": 0,
        "preferences": {},
        "plugins_enabled": 0,
        "provider_health": {},
        "recent_logs": [],
        "messengers": {},
    }

    try:
        from core import __version__

        snap["version"] = __version__
    except Exception:  # noqa: BLE001
        pass

    try:
        from .history import TaskHistory

        hist = TaskHistory()
        for r in hist.list(limit=history_limit):
            snap["history"].append(
                {
                    "task_id": r.get("task_id"),
                    "task": (r.get("task") or "")[:80],
                    "status": r.get("status") or ("success" if r.get("success") else "failed"),
                    "model": r.get("model_used"),
                    "duration": r.get("duration"),
                    "success": r.get("success"),
                }
            )
    except Exception as e:  # noqa: BLE001
        snap["history_error"] = str(e)

    try:
        from .memory_palace import MemoryPalace

        snap["memory"] = MemoryPalace().get_memory_stats()
    except Exception as e:  # noqa: BLE001
        snap["memory"] = {"error": str(e)}

    try:
        from .skills import SkillsManager

        sm = SkillsManager()
        # list_skills may vary — best effort
        if hasattr(sm, "list_skills"):
            skills = sm.list_skills()
            if isinstance(skills, list):
                snap["skills"] = [
                    s.get("name") if isinstance(s, dict) else str(s) for s in skills[:15]
                ]
    except Exception:  # noqa: BLE001
        pass

    try:
        from .discovery import discover_environment

        env = discover_environment()
        snap["clis"] = env.get("clis_available") or []
        snap["api_keys_present"] = env.get("api_keys_present")
        snap["mock_recommended"] = env.get("mock_recommended")
    except Exception:  # noqa: BLE001
        pass

    try:
        from .bandit_router import EpsilonGreedyBandit

        b = EpsilonGreedyBandit()
        snap["bandit_arms"] = len(b.state)
        snap["bandit_epsilon"] = b.epsilon
    except Exception:  # noqa: BLE001
        pass

    try:
        from .preferences import UserPreferenceModel

        snap["preferences"] = UserPreferenceModel().profile_summary()
    except Exception:  # noqa: BLE001
        pass

    try:
        from .plugin_registry import PluginRegistry

        reg = PluginRegistry()
        snap["plugins_enabled"] = sum(
            1 for p in reg.list_plugins() if p.get("enabled")
        )
        snap["plugins_total"] = reg.marketplace_summary().get("total")
    except Exception:  # noqa: BLE001
        pass

    try:
        from .provider_health import ProviderHealthStore

        store = ProviderHealthStore()
        if hasattr(store, "snapshot"):
            snap["provider_health"] = store.snapshot()
        elif hasattr(store, "all_scores"):
            snap["provider_health"] = store.all_scores()
        else:
            # best-effort file
            path = Path.home() / ".superai" / "provider_health.json"
            if path.exists():
                snap["provider_health"] = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass

    # Tail superai log if present
    log_path = Path.home() / ".superai" / "logs" / "superai.log"
    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            snap["recent_logs"] = lines[-log_lines:]
        except Exception:  # noqa: BLE001
            pass

    try:
        from .messengers import MessengerBus

        bus = MessengerBus()
        snap["messengers"] = {
            k: {"enabled": v.get("enabled"), "configured": v.get("configured")}
            for k, v in bus.list_channels().items()
            if not k.startswith("_")
        }
    except Exception:  # noqa: BLE001
        pass

    # Parallel multi-CLI agentic workers (live job registry)
    try:
        from .cli_pool import ParallelCLIManager

        snap["cli_pool"] = ParallelCLIManager().snapshot_for_dashboard()
    except Exception as e:  # noqa: BLE001
        snap["cli_pool"] = {"error": str(e)}

    return snap


def write_feedback(
    message: str,
    surface: str = "cli",
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record feedback visible on all surfaces (shared JSONL).
    """
    path = Path.home() / ".superai" / "feedback.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "surface": surface,
        "message": message,
        "task_id": task_id,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def recent_feedback(limit: int = 10) -> List[Dict[str, Any]]:
    path = Path.home() / ".superai" / "feedback.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    out = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(out))
