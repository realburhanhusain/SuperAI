"""Enterprise / platform stubs for parked P346–P365, P321–P345 (optional depth)."""

from __future__ import annotations

from typing import Any, Dict, List


def rbac_roles() -> Dict[str, Any]:
    """P349 simplified: 4 roles, not 50."""
    return {
        "ok": True,
        "roles": [
            {"id": "viewer", "permissions": ["read"]},
            {"id": "developer", "permissions": ["read", "run", "agent"]},
            {"id": "admin", "permissions": ["read", "run", "agent", "config"]},
            {"id": "owner", "permissions": ["*"]},
        ],
    }


def sso_status() -> Dict[str, Any]:
    """P229/P350 stub: reports not configured."""
    return {
        "ok": True,
        "sso_configured": False,
        "providers": [],
        "hint": "Configure OIDC via SUPERAI_OIDC_* when deploying web multi-user",
    }


def data_residency() -> Dict[str, Any]:
    return {
        "ok": True,
        "region": "local",
        "note": "Local-first SuperAI stores under ~/.superai by default",
    }


def platform_catalog() -> List[Dict[str, str]]:
    return [
        {"id": "P321", "name": "IDE replacement", "status": "out_of_scope_stub"},
        {"id": "P323", "name": "Multi-tenant SaaS", "status": "stub"},
        {"id": "P333", "name": "K8s operator", "status": "stub"},
        {"id": "P339", "name": "Custom terminal", "status": "stub"},
    ]
