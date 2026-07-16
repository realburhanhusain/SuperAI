"""
Unified selection of API models (when keys configured) and external AI CLIs
(with optional inner model id for CLIs that support --model / -m).

Member id syntax:
  gpt-4o                         → API model from registry
  cli:gemini                     → external CLI default model
  cli:gemini@gemini-2.5-pro      → CLI + inner model
  cli:gemini/gemini-2.5-pro      → same
  gemini@gemini-2.5-pro          → if "gemini" is a known CLI name

Listing:
  list_selectable_members() → api_models + clis + selectable ids for UIs/CLI --list
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class MemberSpec:
    kind: str  # api | cli
    id: str  # canonical id used in boards
    display: str
    provider: Optional[str] = None
    model_id: Optional[str] = None  # API model_id or CLI inner model
    cli_name: Optional[str] = None
    configured: bool = False  # key present or CLI on PATH
    available: bool = False
    source: str = ""  # api_key_env | path | mock
    extra: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


def _api_key_present(env_name: Optional[str]) -> bool:
    if not env_name:
        return False
    if (os.getenv(env_name) or "").strip():
        return True
    try:
        from .keyring_store import SecretStore

        val = SecretStore().get(env_name)
        return bool(val)
    except Exception:
        return False


def _mock_mode() -> bool:
    if (os.getenv("SUPERAI_MOCK_MODE") or "").lower() in {"1", "true", "yes"}:
        return True
    try:
        from .config import Config

        return bool(Config().use_mock)
    except Exception:
        return True


def parse_member_spec(raw: str) -> MemberSpec:
    """
    Parse a member selector string into a MemberSpec (not yet validated against registry).
    """
    s = (raw or "").strip()
    if not s:
        raise ValueError("empty member id")

    # cli:name or cli:name@model or cli:name/model
    if s.startswith("cli:"):
        rest = s[4:]
        cli_name, model = _split_cli_model(rest)
        mid = f"cli:{cli_name}" + (f"@{model}" if model else "")
        return MemberSpec(
            kind="cli",
            id=mid,
            display=mid,
            cli_name=cli_name,
            model_id=model,
        )

    # name@model for known CLI short form
    if "@" in s and not s.startswith("http"):
        left, right = s.split("@", 1)
        left, right = left.strip(), right.strip()
        if left and right:
            # Prefer CLI if known
            try:
                from .external_cli import ExternalCLIRegistry

                if ExternalCLIRegistry().get(left):
                    mid = f"cli:{left}@{right}"
                    return MemberSpec(
                        kind="cli",
                        id=mid,
                        display=mid,
                        cli_name=left,
                        model_id=right,
                    )
            except Exception:
                pass
            # Else treat as API alias provider@model_id → still api name left
            return MemberSpec(
                kind="api",
                id=left,
                display=f"{left}@{right}",
                model_id=right,
            )

    # Bare name: CLI if in registry, else API model name
    try:
        from .external_cli import ExternalCLIRegistry

        if ExternalCLIRegistry().get(s):
            return MemberSpec(
                kind="cli",
                id=f"cli:{s}",
                display=f"cli:{s}",
                cli_name=s,
            )
    except Exception:
        pass

    return MemberSpec(kind="api", id=s, display=s, model_id=None)


def _split_cli_model(rest: str) -> tuple[str, Optional[str]]:
    rest = rest.strip()
    if "@" in rest:
        a, b = rest.split("@", 1)
        return a.strip(), b.strip() or None
    if "/" in rest:
        # only split first slash after name (cli:gemini/foo/bar → model foo/bar)
        a, b = rest.split("/", 1)
        return a.strip(), b.strip() or None
    return rest, None


def list_selectable_members(
    *,
    include_unconfigured: bool = True,
    only_available: bool = False,
    with_cli_models: bool = True,
    live_cli_models: bool = False,
    open_weight: Optional[bool] = None,
    local_only: bool = False,
    provider: Optional[str] = None,
    include_ollama_live: bool = False,
) -> Dict[str, Any]:
    """
    Catalog of selectable API models + external CLIs (+ inner models) for UIs.

    Filters:
      open_weight=True|False|None — registry open_weight / local flags
      local_only — Ollama/LM Studio/vLLM/local only
      provider — registry provider id (nvidia, deepseek, …)
      include_ollama_live — soft-merge Ollama tags when daemon up (no write)
    """
    from .external_cli import ExternalCLIRegistry
    from .model_registry import ModelRegistry

    reg = ModelRegistry()
    try:
        reg.register_external_clis_as_models()
    except Exception:
        pass

    # Soft-discover Ollama into in-memory registry for listing only
    ollama_soft: List[str] = []
    if not include_ollama_live:
        try:
            from .config import Config

            include_ollama_live = bool(Config().get("auto_ollama_discover"))
        except Exception:
            pass
    if include_ollama_live:
        try:
            from .model_discovery import list_ollama_tags, ollama_tags_to_catalog

            for entry in ollama_tags_to_catalog(list_ollama_tags(), use_openai_compat=True):
                n = entry["name"]
                if reg.get_model(n):
                    continue
                reg.register_model(
                    name=n,
                    provider=entry.get("provider") or "ollama_openai",
                    model_id=entry.get("model_id") or n,
                    base_url=entry.get("base_url"),
                    api_key_env=entry.get("api_key_env"),
                    strengths=entry.get("strengths") or "",
                    cost_per_1k_tokens=float(entry.get("cost_per_1k_tokens") or 0),
                    latency_tier=int(entry.get("latency_tier") or 2),
                    is_latest=bool(entry.get("is_latest")),
                    extra={
                        "open_weight": True,
                        "local": True,
                        "soft_discovered": True,
                    },
                )
                ollama_soft.append(n)
        except Exception:
            pass

    mock = _mock_mode()
    prov_filter = (provider or "").strip().lower() or None
    local_providers = {
        "ollama",
        "ollama_openai",
        "lmstudio",
        "vllm",
        "custom",
    }

    api_models: List[MemberSpec] = []
    for name in reg.list_all_models():
        if str(name).startswith("cli:"):
            continue
        info = reg.get_model(name)
        if not info or info.provider == "external_cli":
            continue
        extra_src = dict(info.extra or {})
        is_local = bool(
            extra_src.get("local")
            or str(info.provider or "").lower() in local_providers
            or (info.base_url or "").startswith("http://localhost")
            or (info.base_url or "").startswith("http://127.0.0.1")
        )
        is_ow = bool(
            extra_src.get("open_weight")
            or is_local
            or str(info.provider or "").lower()
            in {
                "deepseek",
                "qwen",
                "moonshot",
                "zhipu",
                "minimax",
                "groq",
                "together",
                "mistral",
                "nvidia",
                "openrouter",
                "fireworks",
                "siliconflow",
                "ollama",
                "ollama_openai",
                "lmstudio",
                "vllm",
            }
        )
        if local_only and not is_local:
            continue
        if open_weight is True and not is_ow:
            continue
        if open_weight is False and is_ow:
            continue
        if prov_filter and str(info.provider or "").lower() != prov_filter:
            continue

        # Local often needs no key
        key_ok = _api_key_present(info.api_key_env)
        if is_local and not info.api_key_env:
            key_ok = True
        if is_local and info.api_key_env in {
            "OLLAMA_API_KEY",
            "LMSTUDIO_API_KEY",
            "VLLM_API_KEY",
        }:
            key_ok = True
        configured = key_ok or mock
        if only_available and not configured:
            continue
        if not include_unconfigured and not configured:
            continue
        api_models.append(
            MemberSpec(
                kind="api",
                id=name,
                display=name,
                provider=info.provider,
                model_id=info.model_id,
                configured=configured,
                available=configured,
                source=(info.api_key_env or "") if key_ok else ("mock" if mock else "missing_key"),
                extra={
                    "strengths": info.strengths,
                    "cost_per_1k_tokens": info.cost_per_1k_tokens,
                    "api_key_env": info.api_key_env,
                    "open_weight": is_ow,
                    "local": is_local,
                    "base_url": info.base_url,
                },
            )
        )

    clis: List[MemberSpec] = []
    cli_model_rows: List[MemberSpec] = []
    cli_reg = ExternalCLIRegistry()
    cli_models_catalog: Dict[str, Any] = {}
    if with_cli_models:
        try:
            from .cli_models import list_cli_models_catalog

            cli_models_catalog = list_cli_models_catalog(
                only_available=only_available,
                live=live_cli_models,
            )
        except Exception:
            cli_models_catalog = {}

    by_cli_models = {
        c.get("cli"): c
        for c in (cli_models_catalog.get("clis") or [])
        if c.get("cli")
    }

    for d in cli_reg.discover():
        avail = bool(d.get("available"))
        if only_available and not avail:
            continue
        name = d["name"]
        minfo = by_cli_models.get(name) or {}
        models = list(minfo.get("models") or [])
        clis.append(
            MemberSpec(
                kind="cli",
                id=f"cli:{name}",
                display=f"cli:{name}",
                provider="external_cli",
                cli_name=name,
                model_id=None,
                configured=avail,
                available=avail,
                source=str(d.get("path") or ""),
                extra={
                    "default_role": d.get("default_role"),
                    "install_hint": d.get("install_hint") or cli_reg.install_hint(name),
                    "description": d.get("description"),
                    "model_flag_hint": "Use cli:{name}@MODEL or --cli-model MODEL",
                    "models": models,
                    "model_sources": minfo.get("sources") or [],
                    "model_flag": minfo.get("model_flag"),
                },
            )
        )
        # Expand selectable inner-model rows for pickers
        for mid in models:
            cid = f"cli:{name}@{mid}"
            cli_model_rows.append(
                MemberSpec(
                    kind="cli",
                    id=cid,
                    display=cid,
                    provider="external_cli",
                    cli_name=name,
                    model_id=mid,
                    configured=avail,
                    available=avail,
                    source=str(d.get("path") or ""),
                    extra={"parent_cli": name, "inner_model": mid},
                )
            )

    all_ids = [m.id for m in api_models if m.available] + [
        m.id for m in clis if m.available
    ]
    # Prefer expanded CLI@model ids for interactive pick lists
    pick_ids = [m.id for m in api_models if m.available] + [
        m.id for m in cli_model_rows if m.available
    ]
    if not pick_ids:
        pick_ids = list(all_ids)
    # Always allow bare cli:name as well
    for m in clis:
        if m.available and m.id not in pick_ids:
            pick_ids.append(m.id)

    return {
        "ok": True,
        "mock_mode": mock,
        "api_models": [m.to_dict() for m in api_models],
        "clis": [m.to_dict() for m in clis],
        "cli_models": [m.to_dict() for m in cli_model_rows],
        "cli_models_catalog": cli_models_catalog,
        "selectable_ids": all_ids,
        "pick_ids": pick_ids,
        "filters": {
            "open_weight": open_weight,
            "local_only": local_only,
            "provider": prov_filter,
            "include_ollama_live": include_ollama_live,
            "ollama_soft_added": ollama_soft,
        },
        "counts": {
            "api_configured": sum(1 for m in api_models if m.available),
            "api_total": len(api_models),
            "cli_available": sum(1 for m in clis if m.available),
            "cli_total": len(clis),
            "cli_model_variants": len(cli_model_rows),
            "open_weight": sum(
                1 for m in api_models if (m.extra or {}).get("open_weight")
            ),
            "local": sum(1 for m in api_models if (m.extra or {}).get("local")),
        },
        "syntax": {
            "api": "gpt-4o | deepseek-r1 | nvidia-… | ollama/…",
            "cli": "cli:gemini | cli:grok@MODEL | gemini@MODEL",
            "mixed": "gpt-4o,cli:gemini@gemini-2.5-pro,deepseek-chat",
        },
    }


def resolve_members(
    raw_members: Optional[Sequence[str]],
    *,
    max_members: int = 5,
    prefer: str = "mixed",  # mixed | cli | api
    role: str = "advisor",
) -> List[MemberSpec]:
    """
    Resolve user member list or auto-pick from available API models + CLIs.

    role affects mixed ordering:
      advisor/reviewer → CLI-leaning interleave
      implementer/worker/tester → API-first then CLI workers
    """
    if raw_members:
        out: List[MemberSpec] = []
        for r in raw_members:
            if not str(r).strip():
                continue
            spec = parse_member_spec(str(r).strip())
            # enrich availability
            enriched = _enrich(spec)
            out.append(enriched)
            if len(out) >= max_members:
                break
        return out

    catalog = list_selectable_members(only_available=True)
    api_ids = [m["id"] for m in catalog["api_models"] if m.get("available")]
    cli_ids = [m["id"] for m in catalog["clis"] if m.get("available")]

    # Role-ordered CLI ids (implementer prefers coding CLIs)
    try:
        from .multi_cli_advisory import pick_advisory_clis

        role_key = (role or "advisor").lower()
        if role_key in {"worker", "implementer"}:
            pick_role = "implementer"
        elif role_key in {"tester", "test"}:
            pick_role = "tester"
        elif role_key in {"reviewer", "critic"}:
            pick_role = "reviewer"
        else:
            pick_role = "advisor"
        cli_pref_ids = [
            f"cli:{c}" for c in pick_advisory_clis(role=pick_role, max_clis=max_members)
        ]
        # Keep catalog order for any remaining available CLIs
        for cid in cli_ids:
            if cid not in cli_pref_ids:
                cli_pref_ids.append(cid)
    except Exception:
        cli_pref_ids = list(cli_ids)

    chosen: List[str] = []
    if prefer == "cli":
        chosen = cli_pref_ids[:max_members]
        if len(chosen) < max_members:
            chosen += [a for a in api_ids if a not in chosen][: max_members - len(chosen)]
    elif prefer == "api":
        chosen = api_ids[:max_members]
        if len(chosen) < max_members:
            chosen += [
                c for c in cli_pref_ids if c not in chosen
            ][: max_members - len(chosen)]
    else:
        # mixed interleave — workers: API first; advisors/reviewers: CLI first
        workerish = (role or "").lower() in {
            "worker",
            "implementer",
            "tester",
            "test",
        }
        first = api_ids if workerish else cli_pref_ids
        second = cli_pref_ids if workerish else api_ids
        i = j = 0
        while len(chosen) < max_members and (i < len(first) or j < len(second)):
            if i < len(first):
                if first[i] not in chosen:
                    chosen.append(first[i])
                i += 1
            if len(chosen) >= max_members:
                break
            if j < len(second):
                if second[j] not in chosen:
                    chosen.append(second[j])
                j += 1

    return [_enrich(parse_member_spec(c)) for c in chosen[:max_members]]


def _is_cheap_member(mid: str) -> bool:
    s = str(mid or "").lower()
    if s.startswith("cli:"):
        return True
    cheap_tokens = (
        "ollama",
        "local",
        "lmstudio",
        "vllm",
        "flash",
        "mini",
        "nano",
        "haiku",
        "deepseek",
        "qwen",
        "gemma",
        "llama",
        "groq",
        "openrouter",
    )
    return any(t in s for t in cheap_tokens)


def _is_premium_member(mid: str) -> bool:
    s = str(mid or "").lower()
    if _is_cheap_member(s):
        return False
    premium_tokens = (
        "gpt-4o",
        "gpt-4.1",
        "o3",
        "o4",
        "claude-4",
        "claude-3-5",
        "opus",
        "sonnet",
        "gemini-2.5-pro",
        "grok-3",
        "grok-4",
    )
    return any(t in s for t in premium_tokens) or not s.startswith("cli:")


def diversify_pool(
    pool: List[str],
    *,
    max_members: int = 5,
    force_premium: Optional[str] = None,
) -> List[str]:
    """
    S4: ensure worker diversity — 1 premium + N cheap when possible.
    Order: premium first, then cheap fillers, then remaining.
    """
    seen: List[str] = []
    for m in pool:
        sm = str(m).strip()
        if sm and sm not in seen:
            seen.append(sm)
    if force_premium and force_premium not in seen:
        seen.insert(0, force_premium)

    premium = [m for m in seen if _is_premium_member(m)]
    cheap = [m for m in seen if _is_cheap_member(m)]
    other = [m for m in seen if m not in premium and m not in cheap]

    out: List[str] = []
    if force_premium:
        out.append(force_premium)
    elif premium:
        out.append(premium[0])
    elif other:
        out.append(other[0])
    elif seen:
        out.append(seen[0])

    for m in cheap + other + premium:
        if m not in out:
            out.append(m)
        if len(out) >= max(1, max_members):
            break
    return out[: max(1, max_members)]


def resolve_worker_pool(
    raw_members: Optional[Sequence[str]] = None,
    *,
    prefer: str = "mixed",  # mixed | cli | api | router
    role: str = "implementer",
    max_members: int = 5,
    forced_primary: Optional[str] = None,
    router_primary: Optional[str] = None,
    router_failover: Optional[Sequence[str]] = None,
    diversify: bool = True,
) -> List[str]:
    """
    Ordered worker/failover pool for orchestrator steps.

    prefer=router → router_primary + router_failover (+ optional forced)
    prefer=mixed|api|cli → resolve_members pool (API registry + PATH CLIs)
    forced_primary always first when set.
    S4 diversify=True → 1 premium + N cheap when catalog allows.
    """
    pref = (prefer or "mixed").lower().strip()
    if pref not in {"mixed", "cli", "api", "router", "off"}:
        pref = "mixed"

    pool: List[str] = []

    if forced_primary:
        pool.append(str(forced_primary).strip())

    if pref in {"router", "off"}:
        if router_primary and router_primary not in pool:
            pool.append(str(router_primary))
        for m in router_failover or []:
            sm = str(m).strip()
            if sm and sm not in pool:
                pool.append(sm)
        # Still append available CLIs/API as soft failover if room
        try:
            extra = resolve_members(
                None, max_members=max_members, prefer="mixed", role=role
            )
            for s in extra:
                if s.id not in pool:
                    pool.append(s.id)
                if len(pool) >= max(1, max_members) + (1 if forced_primary else 0):
                    break
        except Exception:
            pass
        cap = max(1, max_members + (1 if forced_primary else 0))
        pool = pool[:cap]
        if diversify and pref != "off":
            return diversify_pool(
                pool, max_members=cap, force_premium=forced_primary or router_primary
            )
        return pool

    # Explicit or auto members from unified catalog
    specs = resolve_members(
        raw_members,
        max_members=max_members * 2 if diversify else max_members,
        prefer=pref if pref in {"mixed", "cli", "api"} else "mixed",
        role=role,
    )
    for s in specs:
        if s.id not in pool:
            pool.append(s.id)

    # If pool thin, fold router suggestions
    if len(pool) < max_members:
        if router_primary and router_primary not in pool:
            pool.append(str(router_primary))
        for m in router_failover or []:
            sm = str(m).strip()
            if sm and sm not in pool:
                pool.append(sm)
            if len(pool) >= max_members + (1 if forced_primary else 0):
                break

    if not pool and router_primary:
        pool = [str(router_primary)]
    if not pool:
        pool = ["gpt-4o"]
    cap = max(1, max_members + (1 if forced_primary else 0))
    if diversify:
        return diversify_pool(
            pool[: cap * 2],
            max_members=min(cap, max_members if not forced_primary else cap),
            force_premium=forced_primary or router_primary,
        )
    return pool[:cap]


def _enrich(spec: MemberSpec) -> MemberSpec:
    if spec.kind == "cli":
        try:
            from .external_cli import ExternalCLIRegistry

            reg = ExternalCLIRegistry()
            name = spec.cli_name or ""
            avail = name in reg.available()
            path = reg.probe(name).get("path") if name else None
            spec.available = avail
            spec.configured = avail
            spec.source = str(path or "")
            spec.provider = "external_cli"
        except Exception:
            pass
        return spec

    # API
    try:
        from .model_registry import ModelRegistry

        reg = ModelRegistry()
        info = reg.get_model(spec.id)
        if info:
            key_ok = _api_key_present(info.api_key_env)
            mock = _mock_mode()
            spec.provider = info.provider
            if not spec.model_id:
                spec.model_id = info.model_id
            spec.configured = key_ok or mock
            spec.available = key_ok or mock
            spec.source = (info.api_key_env or "") if key_ok else ("mock" if mock else "missing_key")
        else:
            spec.available = _mock_mode()
            spec.configured = spec.available
            spec.source = "unknown_model"
    except Exception:
        pass
    return spec
