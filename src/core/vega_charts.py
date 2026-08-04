"""
Interactive Vega-Lite chart HTML rendering for Databao / data-ask.

Exports genuinely self-contained HTML: the Vega runtime is vendored in this
repo (``vendor/vega/``, pinned by version and sha256) and inlined into the
document, so a chart renders with no network at all.

This replaced ``<script src="https://cdn.jsdelivr.net/npm/vega@5">`` — a
floating major, meaning any jsdelivr publish could change every chart SuperAI
had ever produced, with no commit on our side. Charts written months apart now
render identically because they carry their own runtime.

Falling back to the CDN is still possible (``assets="cdn"``), and even then the
URLs carry exact versions rather than a major.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

#: Last-resort pins used when ``vendor/`` is unavailable (e.g. an odd install
#: layout). Deliberately exact: a floating major is the thing being fixed.
VEGA_FALLBACK_VERSIONS = {
    "vega": "5.33.1",
    "vega-lite": "5.23.0",
    "vega-embed": "6.29.0",
}

VENDOR_SOURCE = "vega"


def _vendored_files() -> list:
    """The manifest's file specs for the vega entry, or [] if unavailable."""
    try:
        from .vendored import pin_info

        return list(pin_info(VENDOR_SOURCE).get("files") or [])
    except Exception:
        return []


def pinned_versions() -> Dict[str, str]:
    """Exact versions in use, from the manifest when present."""
    versions = {
        str(spec.get("package")): str(spec.get("version"))
        for spec in _vendored_files()
        if spec.get("package") and spec.get("version")
    }
    return versions or dict(VEGA_FALLBACK_VERSIONS)


def _cdn_urls() -> Dict[str, str]:
    versions = pinned_versions()
    builds = {
        "vega": "build/vega.min.js",
        "vega-lite": "build/vega-lite.min.js",
        "vega-embed": "build/vega-embed.min.js",
    }
    return {
        pkg: f"https://cdn.jsdelivr.net/npm/{pkg}@{versions[pkg]}/{builds[pkg]}"
        for pkg in builds
        if pkg in versions
    }


#: Kept for callers that referenced the old constant; now exact, not floating.
VEGA_CDN = _cdn_urls()


def _inline_scripts() -> Optional[str]:
    """
    Inline `<script>` blocks for the vendored runtime, or None if unavailable.

    Each file is hash-verified on read (``vendored.load_json`` does the same for
    JSON): silently serving a modified runtime would be a worse failure than
    not rendering.
    """
    from .vendored import VendorError, sha256_of, vendor_root

    specs = _vendored_files()
    if not specs:
        return None
    try:
        root = vendor_root()
    except VendorError:
        return None

    blocks = []
    for spec in specs:
        path = root / str(spec["path"])
        if not path.is_file():
            return None
        if sha256_of(path) != spec.get("sha256"):
            raise VendorError(
                f"{spec['path']} does not match its pin; refusing to inline a "
                "runtime that was modified in place. Re-run "
                "scripts/vendor_sync.py --update vega to re-pin deliberately."
            )
        source = path.read_text(encoding="utf-8")
        # A closing tag inside the payload would end the script element early.
        # None of the pinned builds contain one today; a future one might.
        source = source.replace("</script", "<\\/script")
        blocks.append(
            f"  <!-- {spec['package']}@{spec['version']} "
            f"(vendored, sha256 {str(spec['sha256'])[:12]}) -->\n"
            f"  <script>{source}</script>"
        )
    return "\n".join(blocks)


def _asset_scripts(assets: str) -> str:
    """Resolve `assets` to the `<script>` block that belongs in the document."""
    if assets not in {"auto", "inline", "cdn"}:
        raise ValueError(f"assets must be 'auto', 'inline' or 'cdn'; got {assets!r}")

    if assets in {"auto", "inline"}:
        inlined = _inline_scripts()
        if inlined is not None:
            return inlined
        if assets == "inline":
            raise RuntimeError(
                "vendored Vega runtime not found under vendor/vega/. Run "
                "scripts/vendor_sync.py --update vega, or pass assets='cdn'."
            )

    return "\n".join(
        f'  <script src="{url}"></script>' for url in _cdn_urls().values()
    )


def render_vega_html(
    spec: Dict[str, Any],
    title: str = "SuperAI Chart",
    theme: str = "quartz",
    assets: str = "auto",
) -> str:
    """
    Return a complete HTML document that embeds the Vega-Lite spec.

    assets:
      ``auto``   inline the vendored runtime; fall back to pinned CDN URLs if
                 ``vendor/`` is missing (the default)
      ``inline`` inline, or raise — for when offline rendering is required
      ``cdn``    exact-version CDN script tags; ~828KB smaller per document

    Inlining costs about 828KB per file. That buys a document that renders
    offline, in an air-gapped review, and identically in a year's time.
    """
    if not isinstance(spec, dict):
        raise TypeError("spec must be a dict (Vega-Lite JSON)")
    asset_scripts = _asset_scripts(assets)
    # Ensure schema present
    out_spec = dict(spec)
    out_spec.setdefault(
        "$schema", "https://vega.github.io/schema/vega-lite/v5.json"
    )
    # Pretty-escape for script tag
    spec_json = json.dumps(out_spec, ensure_ascii=False)
    # Prevent </script> breakouts
    safe_json = spec_json.replace("</", "<\\/")
    safe_title = (
        str(title)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{safe_title}</title>
{asset_scripts}
  <style>
    :root {{ color-scheme: light dark; }}
    body {{
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      margin: 0; padding: 1.25rem 1.5rem 2rem;
      background: #0f1419; color: #e7ecf1;
    }}
    @media (prefers-color-scheme: light) {{
      body {{ background: #f7f9fc; color: #1a1f26; }}
    }}
    h1 {{ font-size: 1.15rem; font-weight: 600; margin: 0 0 .75rem; }}
    #vis {{
      background: rgba(255,255,255,.04);
      border: 1px solid rgba(127,127,127,.25);
      border-radius: 12px;
      padding: 1rem;
      min-height: 280px;
    }}
    .meta {{ opacity: .65; font-size: .85rem; margin-top: .75rem; }}
    details {{ margin-top: 1rem; }}
    pre {{
      overflow: auto; max-height: 320px; font-size: .78rem;
      background: rgba(0,0,0,.2); padding: .75rem; border-radius: 8px;
    }}
  </style>
</head>
<body>
  <h1>{safe_title}</h1>
  <div id="vis">Loading chart…</div>
  <p class="meta">SuperAI · Vega-Lite · generated {time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}</p>
  <details>
    <summary>Chart JSON</summary>
    <pre id="raw"></pre>
  </details>
  <script>
    const spec = {safe_json};
    document.getElementById('raw').textContent = JSON.stringify(spec, null, 2);
    vegaEmbed('#vis', spec, {{
      actions: true,
      theme: {json.dumps(theme)},
      renderer: 'canvas'
    }}).catch(err => {{
      document.getElementById('vis').textContent = 'Render error: ' + err;
    }});
  </script>
</body>
</html>
"""


def write_chart_html(
    spec: Dict[str, Any],
    path: Optional[Path] = None,
    title: str = "SuperAI Chart",
) -> Path:
    """Write interactive chart HTML to path (default under ~/.superai/charts/)."""
    out = Path(
        path
        or (
            Path.home()
            / ".superai"
            / "charts"
            / f"chart_{time.strftime('%Y%m%d_%H%M%S')}.html"
        )
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    html = render_vega_html(spec, title=title)
    out.write_text(html, encoding="utf-8")
    return out


def chart_from_table(
    columns: list,
    rows: list,
    title: str = "Table chart",
    mark: str = "bar",
) -> Dict[str, Any]:
    """Build a simple Vega-Lite bar/line spec from tabular data."""
    if not columns:
        return {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "description": title,
            "data": {"values": []},
            "mark": mark,
        }
    cat = columns[0]
    val = columns[1] if len(columns) > 1 else columns[0]
    values = []
    for r in rows[:200]:
        if not r:
            continue
        values.append(
            {
                str(cat): r[0],
                str(val): r[1] if len(r) > 1 else 1,
            }
        )
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": title,
        "data": {"values": values},
        "mark": {"type": mark, "tooltip": True},
        "encoding": {
            "x": {"field": str(cat), "type": "nominal", "sort": "-y"},
            "y": {"field": str(val), "type": "quantitative"},
            "tooltip": [
                {"field": str(cat), "type": "nominal"},
                {"field": str(val), "type": "quantitative"},
            ],
        },
        "width": "container",
        "height": 320,
    }
