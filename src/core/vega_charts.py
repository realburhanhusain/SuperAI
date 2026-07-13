"""
Interactive Vega-Lite chart HTML rendering for Databao / data-ask.

Exports self-contained HTML using CDN Vega embeds (no build step).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


VEGA_CDN = {
    "vega": "https://cdn.jsdelivr.net/npm/vega@5",
    "vegalite": "https://cdn.jsdelivr.net/npm/vega-lite@5",
    "vegaembed": "https://cdn.jsdelivr.net/npm/vega-embed@6",
}


def render_vega_html(
    spec: Dict[str, Any],
    title: str = "SuperAI Chart",
    theme: str = "quartz",
) -> str:
    """Return a complete HTML document that embeds the Vega-Lite spec."""
    if not isinstance(spec, dict):
        raise TypeError("spec must be a dict (Vega-Lite JSON)")
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
  <script src="{VEGA_CDN['vega']}"></script>
  <script src="{VEGA_CDN['vegalite']}"></script>
  <script src="{VEGA_CDN['vegaembed']}"></script>
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
