"""
cliproxy model ids, checked against the pinned CLIProxyAPI catalog.

A wrong ``model_id`` is invisible until the first real call, which then 404s.
The existing registry tests prove a row is well-formed; nothing proved the id
meant anything upstream. These do, offline, from vendored bytes.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.cliproxy_models import (
    backends,
    catalog,
    family_backends,
    ids_by_backend,
    known_ids,
    probe_live_models,
    suggest,
    validate_rows,
)


def _example_rows():
    path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "models.cliproxy.example.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_catalog_is_keyed_by_backend_not_by_vendor():
    """
    The same vendor is served by several backends with different id spellings.
    That is the whole reason a boolean "does this id exist" is not enough.
    """
    keys = set(backends())
    assert {"claude", "gemini", "vertex", "aistudio", "xai"} <= keys
    assert any(k.startswith("codex-") for k in keys)


def test_ids_are_indexed_to_the_backends_that_serve_them():
    index = ids_by_backend()
    assert index, "catalog should yield model ids"
    assert all(isinstance(v, list) and v for v in index.values())
    # The known portability trap: only Vertex spells it without -preview.
    assert index.get("gemini-3.1-pro") == ["vertex"]
    assert "gemini" in index.get("gemini-3.1-pro-preview", [])


def test_every_shipped_example_id_exists_upstream():
    """
    This is the regression that motivated the check: the example file shipped
    `gpt-5.6-codex`, which no backend serves.
    """
    results = validate_rows(_example_rows())
    missing = [r for r in results if r["status"] == "missing"]
    assert not missing, f"example rows reference ids no backend serves: {missing}"


def test_the_codex_row_works_on_every_subscription_tier():
    """
    The codex-* keys are subscription tiers. An id present only in the paid
    tiers would 404 for a free-tier-backed proxy, so the shipped example uses
    one that all four serve.
    """
    row = next(r for r in _example_rows() if r["name"] == "cliproxy:codex")
    serving = set(ids_by_backend()[row["model_id"]])
    assert {"codex-free", "codex-team", "codex-plus", "codex-pro"} <= serving


def test_a_missing_id_reports_close_alternatives():
    results = validate_rows([{"name": "cliproxy:x", "model_id": "gpt-5.6-codex"}])
    assert results[0]["status"] == "missing"
    assert results[0]["suggestions"], "a missing id should suggest real ones"


def test_single_backend_families_are_not_flagged_as_conditional():
    """
    `grok-4.5` is served only by `xai` — but `xai` is the only backend serving
    any grok id, so there is nothing conditional about it. Flagging on "one
    backend" alone would cry wolf; the comparison is against the backends that
    serve the model's *family*.
    """
    results = validate_rows([{"name": "cliproxy:grok", "model_id": "grok-4.5"}])
    assert results[0]["status"] == "ok"
    assert results[0]["missing_from"] == []


def test_a_bespoke_backend_does_not_drag_every_row_to_conditional():
    """
    `antigravity` mixes vendors and renames everything it serves
    (`claude-opus-4-6-thinking`, `gemini-3.1-pro-low`). Requiring *all* family
    backends would mark every id conditional — always true, never useful. The
    rule is a coverage majority, and `missing_from` still records the fact.
    """
    results = validate_rows([{"name": "cliproxy:c", "model_id": "claude-opus-4-6"}])
    row = results[0]
    assert row["status"] == "ok"
    assert row["missing_from"] == ["antigravity"]
    assert row["coverage"] >= 0.5


def test_a_backend_conditional_id_names_the_backends_that_lack_it():
    results = validate_rows([{"name": "cliproxy:g", "model_id": "gemini-3.1-pro"}])
    row = results[0]
    assert row["status"] == "backend_conditional"
    assert row["available_under"] == ["vertex"]
    assert "gemini" in row["missing_from"] and "aistudio" in row["missing_from"]


def test_family_backends_are_derived_from_the_catalog():
    families = family_backends()
    assert set(families["gemini"]) >= {"gemini", "vertex", "aistudio", "gemini-cli"}
    assert families["grok"] == ["xai"]


def test_live_probe_is_separate_and_fails_soft():
    """
    The static check says what CLIProxyAPI *can* serve; a live probe says what
    this install is authenticated for. An unreachable proxy must report itself
    as unreachable, never as an empty-but-successful answer.
    """
    result = probe_live_models("http://127.0.0.1:9/v1", timeout=0.5)
    assert result["reachable"] is False
    assert result["ids"] == []
    assert result["error"]


def test_suggest_returns_real_catalog_ids():
    everything = set(known_ids())
    assert all(s in everything for s in suggest("gpt-5.6-codex"))


def test_catalog_load_is_offline(monkeypatch):
    """
    The docs tell users to run the validator as the offline check, so prove it:
    with sockets blocked, reading the catalog and validating rows both work.
    """
    import socket

    def blocked(*_a, **_k):
        raise AssertionError("validation must not touch the network")

    monkeypatch.setattr(socket, "socket", blocked)
    assert isinstance(catalog(), dict)
    results = validate_rows(_example_rows())
    assert results and all(r["status"] != "missing" for r in results)
