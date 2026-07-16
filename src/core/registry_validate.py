"""Validate model registry entries (Improvement Phase 3)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .model_registry import ModelRegistry
from .provider_catalog import OPENAI_COMPAT_PROVIDERS, NATIVE_PROVIDERS


def validate_registry(registry: Optional[ModelRegistry] = None) -> Dict[str, Any]:
    reg = registry or ModelRegistry()
    issues: List[Dict[str, Any]] = []
    ok_count = 0
    for name in reg.list_all_models():
        info = reg.get_model(name)
        if not info:
            continue
        local_issues = []
        if not info.provider:
            local_issues.append("missing_provider")
        if not info.model_id:
            local_issues.append("missing_model_id")
        prov = (info.provider or "").lower()
        if prov not in OPENAI_COMPAT_PROVIDERS and prov not in NATIVE_PROVIDERS:
            if not info.base_url:
                local_issues.append("unknown_provider_without_base_url")
        if prov in OPENAI_COMPAT_PROVIDERS and not info.base_url:
            # catalog default OK
            pass
        if local_issues:
            issues.append({"name": name, "issues": local_issues})
        else:
            ok_count += 1
    return {
        "ok": len(issues) == 0,
        "valid": ok_count,
        "issue_count": len(issues),
        "issues": issues[:50],
        "total": len(reg.list_all_models()),
    }
