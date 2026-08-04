"""
Pinned external sources (vendor/).

The policy these tests defend: SuperAI reads external data from bytes committed
to this repo, pinned to a commit, never from a live URL that can change without
a decision on our side. See vendor/README.md.
"""

from __future__ import annotations

import json
import re

import pytest

from core.vendored import (
    VendorError,
    list_sources,
    load_json,
    load_manifest,
    pin_info,
    pin_of,
    vendor_root,
    verify_integrity,
)


def test_manifest_is_present_and_shaped():
    manifest = load_manifest()
    assert manifest["version"] == 1
    assert manifest["sources"], "manifest must pin at least one source"


def test_every_source_records_a_pin():
    """
    An unpinned source is the thing this directory exists to prevent. The pin
    takes different forms — a git commit, or exact npm versions — so the check
    is "is it pinned", not "does it have a SHA".
    """
    for row in list_sources():
        assert row["kind"] in {"vendored_files", "pinned_reference"}
        assert row["origin"] in {"github", "npm"}
        assert pin_of(row), f"{row['name']} records no pin"
        if row["origin"] == "github":
            assert len(row["commit"]) == 40, f"{row['name']} pin is not a full SHA"
        else:
            for package, version in row["packages"].items():
                assert re.fullmatch(
                    r"\d+\.\d+\.\d+", version
                ), f"{row['name']}:{package} is pinned to {version!r}, not an exact version"


def test_vendored_files_match_their_recorded_hashes():
    """Offline integrity: catches a vendored copy edited in place."""
    results = verify_integrity()
    assert results, "expected at least one vendored file to check"
    bad = [r for r in results if not r["ok"]]
    assert not bad, f"vendored files do not match their pins: {bad}"


def test_pinned_reference_stores_no_bytes():
    """
    CLIProxyAPI is spoken to over HTTP; none of its source is read. A mirror
    nothing reads would bloat the repo and drift silently, so the entry pins
    the reference and stores nothing.
    """
    entry = pin_info("cliproxy")
    assert entry["kind"] == "pinned_reference"
    assert entry.get("files") == []
    assert entry["ref"].startswith("v"), "a reference should pin a tag, not a branch"


def test_load_json_refuses_a_file_that_drifted_from_its_pin(tmp_path, monkeypatch):
    """
    A silently modified vendored file would make every downstream check wrong
    while still looking authoritative. Loading must fail loudly instead.
    """
    import core.vendored as vendored

    real_root = vendor_root()
    manifest = json.loads((real_root / "manifest.json").read_text(encoding="utf-8"))

    fake_root = tmp_path / "vendor"
    (fake_root / "cliproxy-models").mkdir(parents=True)
    (fake_root / "cliproxy-models" / "models.json").write_text(
        '{"claude": []}', encoding="utf-8"
    )
    (fake_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    monkeypatch.setattr(vendored, "vendor_root", lambda: fake_root)
    with pytest.raises(VendorError, match="does not match its pin"):
        load_json("cliproxy-models", "models.json")


def test_the_cliproxy_model_catalog_loads():
    catalog = load_json("cliproxy-models", "models.json")
    assert isinstance(catalog, dict)
    # Vendor-keyed: claude, gemini, codex-*, kimi, xai, ...
    assert "claude" in catalog and "xai" in catalog
    assert all(isinstance(rows, list) for rows in catalog.values())
