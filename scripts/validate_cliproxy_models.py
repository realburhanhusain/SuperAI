#!/usr/bin/env python
"""
Check ``cliproxy:*`` model ids against CLIProxyAPI's pinned model list.

    python scripts/validate_cliproxy_models.py                 # example rows
    python scripts/validate_cliproxy_models.py --registry      # your real registry
    python scripts/validate_cliproxy_models.py --live          # also ask a running proxy
    python scripts/validate_cliproxy_models.py --json

A wrong ``model_id`` costs nothing until the first real call, then 404s. The
static check reads the vendored catalog and needs no network or proxy. ``--live``
adds a second, separate answer: what a running proxy is actually authenticated
to serve. The two are reported apart — a static check that silently stands in
for a dynamic one is how coverage gets claimed without being proven.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from core.cliproxy_models import (  # noqa: E402
    probe_live_models,
    validate_rows,
)

EXAMPLE = REPO / "config" / "models.cliproxy.example.json"
STATUS_LABEL = {
    "ok": "ok        ",
    "backend_conditional": "CONDITIONAL",
    "missing": "MISSING   ",
}


def _example_rows() -> List[Dict[str, Any]]:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def _registry_rows() -> List[Dict[str, Any]]:
    from core.model_registry import ModelRegistry

    registry = ModelRegistry()
    rows: List[Dict[str, Any]] = []
    for name in registry.list_all_models():
        info = registry.get_model(name)
        if info is not None and getattr(info, "provider", "") == "cliproxy":
            rows.append({"name": name, "model_id": getattr(info, "model_id", "")})
    return rows


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--registry", action="store_true", help="check the live registry instead of the example file")
    parser.add_argument("--live", action="store_true", help="also probe a running proxy's /v1/models")
    parser.add_argument("--base-url", default="http://127.0.0.1:8317/v1")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    rows = _registry_rows() if args.registry else _example_rows()
    source = "registry" if args.registry else str(EXAMPLE.relative_to(REPO))
    results = validate_rows(rows)

    live: Dict[str, Any] = {}
    if args.live:
        live = probe_live_models(args.base_url, os.getenv("CLIPROXY_API_KEY"))
        for row in results:
            if live.get("reachable"):
                row["served_by_this_proxy"] = row["model_id"] in live["ids"]

    missing = [r for r in results if r["status"] == "missing"]
    conditional = [r for r in results if r["status"] == "backend_conditional"]
    payload = {
        "ok": not missing,
        "source": source,
        "checked": len(results),
        "rows": results,
        "live": live or None,
        "summary": {
            "ok": len(results) - len(missing) - len(conditional),
            "backend_conditional": len(conditional),
            "missing": len(missing),
        },
        "catalog": "vendor/cliproxy-models/models.json (pinned)",
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0 if payload["ok"] else 1

    print(f"Checking {len(results)} cliproxy row(s) from {source}")
    print("against the pinned catalog vendor/cliproxy-models/models.json\n")
    for row in results:
        label = STATUS_LABEL.get(row["status"], row["status"])
        backends = ", ".join(row["available_under"]) or "-"
        print(f"  {label}  {row['name']:<24} {row['model_id']:<24} backends: {backends}")
        if row.get("suggestions"):
            print(f"{'':>15}did you mean: {', '.join(row['suggestions'])}")
        if row.get("missing_from"):
            print(f"{'':>15}not served by: {', '.join(row['missing_from'])}")
        if "served_by_this_proxy" in row and not row["served_by_this_proxy"]:
            print(f"{'':>15}not served by the proxy at {args.base_url}")

    if conditional:
        print(
            "\nCONDITIONAL means only a minority of the backends serving this model"
            "\nfamily serve this exact id, so the row works only if your proxy is"
            "\nauthenticated against one of the backends listed."
        )
    if missing:
        print("\nMISSING ids will 404 on first use.")

    if args.live:
        if live.get("reachable"):
            print(f"\nLive proxy at {live['url']} serves {len(live['ids'])} model(s).")
        else:
            print(f"\nLive proxy not reachable at {live.get('url')}: {live.get('error', '')}")
            print("Static result above still stands; the live question is unanswered.")

    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
