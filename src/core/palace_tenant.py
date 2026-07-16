"""
Multi-user Memory Palace tenant context (Phase 8 N7).
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


def current_tenant(config: Any = None) -> str:
    env = (os.getenv("SUPERAI_TENANT_ID") or "").strip()
    if env:
        return env
    try:
        if config is None:
            from .config import Config

            config = Config()
        t = (config.get("tenant_id") or config.get("palace_tenant") or "").strip()
        if t:
            return t
    except Exception:
        pass
    return "default"


def tenant_tag(tenant: Optional[str] = None) -> str:
    t = (tenant or current_tenant()).strip() or "default"
    return f"tenant:{t}"


def scope_metadata(meta: Optional[Dict[str, Any]] = None, tenant: Optional[str] = None) -> Dict[str, Any]:
    m = dict(meta or {})
    m["tenant_id"] = (tenant or current_tenant())
    tag = tenant_tag(m["tenant_id"])
    tags = m.get("tags")
    if isinstance(tags, list):
        if tag not in tags:
            tags = list(tags) + [tag]
        m["tags"] = tags
    else:
        m["tags"] = [tag]
    return m
