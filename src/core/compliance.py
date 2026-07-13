"""
Compliance mode (N22) — local-only, strict audit.
"""

from __future__ import annotations

from typing import Any, Dict

from .config import Config


def enable_compliance_mode() -> Dict[str, Any]:
    cfg = Config()
    updates = {
        "mock_mode": True,
        "require_human_approval": True,
        "data_read_only": True,
        "use_constitution": True,
        "prefer_container_sandbox": True,
        "compliance_mode": True,
        "failover_chain": [],
    }
    for k, v in updates.items():
        cfg.set(k, v, persist=True)
    # policy
    try:
        from .policy import PolicyEngine

        pe = PolicyEngine()
        pe.set_enabled("no_cloud_without_keys", True)
        pe.set_enabled("require_approval_file_cli", True)
        pe.set_enabled("workspace_jail", True)
    except Exception:
        pass
    return {"ok": True, "settings": updates}


def compliance_status() -> Dict[str, Any]:
    cfg = Config()
    return {
        "compliance_mode": bool(cfg.get("compliance_mode")),
        "mock_mode": cfg.use_mock,
        "require_human_approval": cfg.get("require_human_approval"),
        "data_read_only": cfg.get("data_read_only"),
    }
