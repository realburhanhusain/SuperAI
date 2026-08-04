"""
Validate ``cliproxy:*`` registry rows against CLIProxyAPI's published model list.

The catalog is read from ``vendor/cliproxy-models/models.json`` — bytes pinned in
this repo, not a live URL. See ``vendor/README.md``.

Why this exists: a wrong ``model_id`` is invisible until the first real call,
which then 404s. The registry's own tests can only prove a row is well-formed,
not that the id means anything upstream.

The catalog is keyed by *backend*, not by vendor: ``claude``, ``gemini``,
``vertex``, ``gemini-cli``, ``aistudio``, ``codex-free``, ``codex-team``,
``codex-plus``, ``codex-pro``, ``kimi``, ``antigravity``, ``xai``. The same
vendor is served by several backends with different id spellings, so
"does this id exist" is the wrong question — **which backends serve it** is the
right one. ``gemini-3.1-pro`` exists only under ``vertex``; the OAuth backends
spell it ``gemini-3.1-pro-preview``. A boolean would call that row valid and it
would still 404 on a non-Vertex proxy.
"""

from __future__ import annotations

import difflib
from typing import Any, Dict, Iterable, List, Optional

from .vendored import load_json

VENDOR_SOURCE = "cliproxy-models"
CATALOG_FILE = "models.json"

#: Fraction of a family's backends that must serve an id for it to count as
#: portable. A judgment call, documented rather than hidden: `antigravity`
#: renames everything it serves, so demanding full coverage would mark every
#: id conditional and the signal would be worthless.
PORTABLE_COVERAGE = 0.5


def catalog() -> Dict[str, List[Dict[str, Any]]]:
    """The pinned catalog, keyed by backend."""
    data = load_json(VENDOR_SOURCE, CATALOG_FILE)
    if not isinstance(data, dict):
        raise ValueError(f"{CATALOG_FILE} should be an object keyed by backend")
    return data


def backends() -> List[str]:
    return sorted(catalog())


def ids_by_backend() -> Dict[str, List[str]]:
    """model_id -> the backends that serve it, sorted."""
    index: Dict[str, List[str]] = {}
    for backend, rows in catalog().items():
        for row in rows or []:
            model_id = (row or {}).get("id")
            if model_id:
                index.setdefault(str(model_id), []).append(backend)
    return {mid: sorted(set(bks)) for mid, bks in sorted(index.items())}


def known_ids() -> List[str]:
    return sorted(ids_by_backend())


def suggest(model_id: str, limit: int = 5) -> List[str]:
    """Closest catalog ids, for a row whose id does not exist at all."""
    return difflib.get_close_matches(model_id, known_ids(), n=limit, cutoff=0.5)


def _family(model_id: str) -> str:
    """``gemini-3.1-pro`` -> ``gemini``. Derived, not a hardcoded vendor map."""
    return model_id.split("-", 1)[0].lower()


def family_backends() -> Dict[str, List[str]]:
    """
    family -> every backend that serves *any* id in that family.

    This is the denominator that makes "one backend serves it" meaningful.
    ``grok-4.5`` is served only by ``xai``, but ``xai`` is the only backend
    serving any grok id at all — so there is nothing conditional about it.
    ``gemini-3.1-pro`` is served only by ``vertex`` while four other backends
    serve gemini ids, which is a real portability trap.
    """
    index: Dict[str, set] = {}
    for backend, rows in catalog().items():
        for row in rows or []:
            model_id = (row or {}).get("id")
            if model_id:
                index.setdefault(_family(str(model_id)), set()).add(backend)
    return {fam: sorted(bks) for fam, bks in sorted(index.items())}


def validate_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Check each registry row's ``model_id`` against the pinned catalog.

    status:
      ``ok``                   most backends serving this model's family serve
                               this exact id — it is portable in practice
      ``backend_conditional``  a minority do — the row works only if the proxy
                               is authenticated against a backend listed in
                               ``available_under``
      ``missing``              no backend serves this id; the call will 404

    "Most" is a coverage majority (see :data:`PORTABLE_COVERAGE`), not "all".
    Requiring all would flag every id, because ``antigravity`` mixes vendors and
    spells everything its own way (``claude-opus-4-6-thinking``,
    ``gemini-3.1-pro-low``) — always true, never useful. ``missing_from`` is
    reported on every row regardless, so the raw facts do not depend on where
    the threshold sits.
    """
    index = ids_by_backend()
    families = family_backends()
    out: List[Dict[str, Any]] = []
    for row in rows:
        model_id = str((row or {}).get("model_id") or "")
        serving = index.get(model_id, [])
        siblings = families.get(_family(model_id), [])
        missing_from = [b for b in siblings if b not in serving]
        coverage = (len(serving) / len(siblings)) if siblings else 0.0
        if not serving:
            status = "missing"
        elif coverage < PORTABLE_COVERAGE:
            status = "backend_conditional"
        else:
            status = "ok"
        entry: Dict[str, Any] = {
            "name": (row or {}).get("name"),
            "model_id": model_id,
            "status": status,
            "available_under": serving,
            "family_backends": siblings,
            "missing_from": missing_from,
            "coverage": round(coverage, 3),
        }
        if status == "missing":
            entry["suggestions"] = suggest(model_id)
        out.append(entry)
    return out


def probe_live_models(
    base_url: str, api_key: Optional[str] = None, timeout: float = 4.0
) -> Dict[str, Any]:
    """
    Ask a running proxy what it actually serves (``GET /v1/models``).

    Optional and separate from :func:`validate_rows` on purpose: the vendored
    catalog says what CLIProxyAPI *can* serve, a live proxy says what *this*
    install is authenticated for. Reporting them separately keeps a static
    check from being mistaken for a dynamic one.
    """
    import json
    import urllib.request

    url = base_url.rstrip("/") + "/models"
    headers = {"User-Agent": "SuperAI-cliproxy-probe"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"reachable": False, "url": url, "error": str(exc)[:200], "ids": []}

    rows = payload.get("data") if isinstance(payload, dict) else payload
    ids = [
        str(r.get("id"))
        for r in (rows or [])
        if isinstance(r, dict) and r.get("id")
    ]
    return {"reachable": True, "url": url, "ids": sorted(ids)}
