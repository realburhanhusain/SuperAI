"""
Local-first model ordering + escalate to premium (DoD-strict V4).
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence


def _is_local(mid: str) -> bool:
    s = str(mid or "").lower()
    return any(
        t in s
        for t in (
            "ollama",
            "local",
            "lmstudio",
            "vllm",
            "cli:",
        )
    )


def _is_cheap(mid: str) -> bool:
    s = str(mid or "").lower()
    if _is_local(s):
        return True
    return any(
        t in s
        for t in (
            "flash",
            "mini",
            "nano",
            "haiku",
            "deepseek",
            "qwen",
            "gemma",
            "llama",
            "groq",
        )
    )


def order_local_first(
    models: Sequence[str],
    *,
    primary: Optional[str] = None,
    local_only: bool = False,
    prefer_local: bool = True,
    max_n: int = 5,
) -> List[str]:
    """
    Order: primary (if allowed) → local → cheap → rest.
    local_only drops non-local names.
    """
    seen: List[str] = []

    def add(m: str) -> None:
        sm = str(m).strip()
        if not sm or sm in seen:
            return
        if local_only and not _is_local(sm):
            return
        seen.append(sm)

    if primary:
        add(primary)
    rest = [str(m).strip() for m in models if str(m).strip()]
    if prefer_local or local_only:
        for m in rest:
            if _is_local(m):
                add(m)
        if not local_only:
            for m in rest:
                if _is_cheap(m) and not _is_local(m):
                    add(m)
            for m in rest:
                add(m)
    else:
        for m in rest:
            add(m)
    if not seen and primary:
        seen = [str(primary)]
    if not seen:
        seen = ["gpt-4o"] if not local_only else ["llama3.2"]
    return seen[: max(1, max_n)]


def escalate_chain(
    primary: str,
    *,
    registry: Any = None,
    prefer_local: bool = False,
    local_only: bool = False,
    max_n: int = 4,
) -> List[str]:
    """
    Build failover chain for ModelCaller: try local/cheap first when preferred,
    then ready premium models.
    """
    pool: List[str] = [str(primary)]
    try:
        if registry is not None:
            for name in registry.list_all_models():
                sm = str(name)
                if sm not in pool:
                    pool.append(sm)
    except Exception:
        pass
    # Always allow known local aliases for escalate-from-local
    for extra in ("llama3.2", "lmstudio-local", "vllm-local", "deepseek-chat"):
        if extra not in pool:
            pool.append(extra)
    return order_local_first(
        pool,
        primary=primary,
        local_only=local_only,
        prefer_local=prefer_local or local_only,
        max_n=max_n,
    )


def profile_flags(config: Any = None) -> dict:
    try:
        if config is None:
            from .config import Config

            config = Config()
        return {
            "prefer_local": bool(config.get("prefer_local")),
            "local_only": bool(config.get("local_only")),
            "prefer_open_weight": bool(config.get("prefer_open_weight")),
            "run_profile": str(config.get("run_profile") or ""),
        }
    except Exception:
        return {
            "prefer_local": False,
            "local_only": False,
            "prefer_open_weight": False,
            "run_profile": "",
        }
