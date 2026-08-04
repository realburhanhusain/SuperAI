"""
Chart HTML carries its own Vega runtime.

Before this, generated charts loaded `cdn.jsdelivr.net/npm/vega@5` — a floating
major. Any jsdelivr publish could change every chart SuperAI had ever written,
with no commit here, and an offline machine rendered nothing at all.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from core.vega_charts import (
    chart_from_table,
    pinned_versions,
    render_vega_html,
    write_chart_html,
)
from core.vendored import VendorError, vendor_root

SPEC = chart_from_table(["country", "revenue"], [["DE", 100], ["US", 200]], title="Revenue")


def test_default_output_references_no_network_host():
    html = render_vega_html(SPEC, title="Revenue")
    assert "cdn.jsdelivr.net" not in html
    assert "vegaEmbed" in html
    # The runtime itself is present, not merely linked.
    assert len(html) > 800_000


def test_written_chart_files_are_self_contained(tmp_path: Path):
    path = write_chart_html(SPEC, path=tmp_path / "c.html", title="T")
    html = path.read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net" not in html
    assert "<script>" in html


def test_script_elements_are_balanced():
    """An unescaped closing tag inside the payload would truncate the document."""
    html = render_vega_html(SPEC)
    assert html.count("<script") == html.count("</script>")
    assert "</html>" in html.strip()[-20:]


def test_cdn_mode_pins_exact_versions_never_a_floating_major():
    html = render_vega_html(SPEC, assets="cdn")
    urls = re.findall(r'src="([^"]+)"', html)
    assert urls, "cdn mode should emit script src tags"
    for url in urls:
        assert re.search(r"@\d+\.\d+\.\d+/", url), f"{url} is not pinned to an exact version"


def test_versions_come_from_the_manifest():
    versions = pinned_versions()
    manifest = json.loads((vendor_root() / "manifest.json").read_text(encoding="utf-8"))
    pinned = manifest["sources"]["vega"]["packages"]
    assert versions == pinned


def test_the_major_line_matches_the_specs_we_emit():
    """
    SuperAI emits `$schema: vega-lite/v5.json`. npm 'latest' is vega 6.x /
    vega-lite 6.x, and taking it would silently change how existing specs
    render — so the pin holds the major line deliberately.
    """
    versions = pinned_versions()
    assert versions["vega"].startswith("5.")
    assert versions["vega-lite"].startswith("5.")
    assert versions["vega-embed"].startswith("6.")
    assert '"$schema": "https://vega.github.io/schema/vega-lite/v5.json"' in json.dumps(
        SPEC, indent=1
    ).replace("\n ", "\n").replace('"$schema": ', '"$schema": ')


def test_inline_mode_refuses_a_runtime_that_drifted_from_its_pin(tmp_path, monkeypatch):
    """
    Serving a modified runtime silently is worse than not rendering: every
    chart would inherit whatever the edited bytes do.
    """
    import core.vendored as vendored

    manifest = json.loads((vendor_root() / "manifest.json").read_text(encoding="utf-8"))
    fake_root = tmp_path / "vendor"
    (fake_root / "vega").mkdir(parents=True)
    for spec in manifest["sources"]["vega"]["files"]:
        (fake_root / spec["path"]).write_text("/* not the real runtime */", encoding="utf-8")
    (fake_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    monkeypatch.setattr(vendored, "vendor_root", lambda: fake_root)
    with pytest.raises(VendorError, match="does not match its pin"):
        render_vega_html(SPEC, assets="inline")


def test_an_unknown_assets_mode_is_rejected():
    with pytest.raises(ValueError, match="assets must be"):
        render_vega_html(SPEC, assets="whatever")
