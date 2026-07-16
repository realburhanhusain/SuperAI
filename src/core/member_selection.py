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
) -> Dict[str, Any]:
    """
    Catalog of selectable API models + external CLIs for review/advise/council UIs.
    """
    from .external_cli import ExternalCLIRegistry
    from .model_registry import ModelRegistry

    reg = ModelRegistry()
    try:
        reg.register_external_clis_as_models()
    except Exception:
        pass

    mock = _mock_mode()
    api_models: List[MemberSpec] = []
    for name in reg.list_all_models():
        if str(name).startswith("cli:"):
            continue
        info = reg.get_model(name)
        if not info or info.provider == "external_cli":
            continue
        key_ok = _api_key_present(info.api_key_env)
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
                },
            )
        )

    clis: List[MemberSpec] = []
    cli_reg = ExternalCLIRegistry()
    for d in cli_reg.discover():
        avail = bool(d.get("available"))
        if only_available and not avail:
            continue
        name = d["name"]
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
                    # common model flag hint for UIs
                    "model_flag_hint": "Use cli:{name}@MODEL or --cli-model MODEL",
                },
            )
        )

    all_ids = [m.id for m in api_models if m.available] + [
        m.id for m in clis if m.available
    ]
    return {
        "ok": True,
        "mock_mode": mock,
        "api_models": [m.to_dict() for m in api_models],
        "clis": [m.to_dict() for m in clis],
        "selectable_ids": all_ids,
        "counts": {
            "api_configured": sum(1 for m in api_models if m.available),
            "api_total": len(api_models),
            "cli_available": sum(1 for m in clis if m.available),
            "cli_total": len(clis),
        },
        "syntax": {
            "api": "gpt-4o | claude-3-5-sonnet | … (registry name)",
            "cli": "cli:gemini | cli:grok@MODEL | gemini@MODEL",
            "mixed": "gpt-4o,cli:gemini@gemini-2.5-pro,cli:grok",
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


def resolve_worker_pool(
    raw_members: Optional[Sequence[str]] = None,
    *,
    prefer: str = "mixed",  # mixed | cli | api | router
    role: str = "implementer",
    max_members: int = 5,
    forced_primary: Optional[str] = None,
    router_primary: Optional[str] = None,
    router_failover: Optional[Sequence[str]] = None,
) -> List[str]:
    """
    Ordered worker/failover pool for orchestrator steps.

    prefer=router → router_primary + router_failover (+ optional forced)
    prefer=mixed|api|cli → resolve_members pool (API registry + PATH CLIs)
    forced_primary always first when set.
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
        return pool[: max(1, max_members + (1 if forced_primary else 0))]

    # Explicit or auto members from unified catalog
    specs = resolve_members(
        raw_members,
        max_members=max_members,
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
    return pool


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
