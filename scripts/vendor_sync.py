#!/usr/bin/env python
"""
Manage pinned external sources in ``vendor/``.

    python scripts/vendor_sync.py --list
    python scripts/vendor_sync.py --check [--json]
    python scripts/vendor_sync.py --update <name>

``--check`` asks two independent questions and never conflates them:

  local integrity   do vendored bytes still match their recorded sha256?
                    Offline. A mismatch is a proven problem.
  upstream drift    has the source repo moved past the pinned commit?
                    Needs network. Unreachable is reported as unknown, not as
                    a pass — an unanswered question is not a clean bill.

Exit code is non-zero only for problems we can prove: a tampered or missing
vendored file, or confirmed upstream drift. Never for "could not reach GitHub".

This is a script, not a CLI command, on purpose: ``core/surface_inventory.py``
derives SuperAI's public surface from Click metadata, and a new ``@app.command``
obligates contract wrapping and a scorecard regeneration. Same reasoning as
``scripts/probe_cli_contracts.py``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.vendored import (  # noqa: E402
    load_manifest,
    sha256_of,
    vendor_root,
    verify_integrity,
)

GITHUB_API = "https://api.github.com"
DRIFT_UNKNOWN = "unknown"


def _api(url: str, timeout: float = 20.0) -> Optional[Any]:
    headers = {"User-Agent": "SuperAI-vendor-sync", "Accept": "application/vnd.github+json"}
    token = (os.getenv("GITHUB_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _remote_commit(repo: str, ref: str) -> Optional[str]:
    data = _api(f"{GITHUB_API}/repos/{repo}/commits/{ref}")
    if isinstance(data, dict) and data.get("sha"):
        return str(data["sha"])
    return None


def cmd_list() -> int:
    manifest = load_manifest()
    for name, entry in sorted(manifest["sources"].items()):
        files = entry.get("files") or []
        print(f"{name}")
        print(f"  kind    : {entry.get('kind')}")
        print(f"  repo    : {entry.get('repo')} @ {entry.get('ref')}")
        print(f"  commit  : {str(entry.get('commit'))[:12]}  (fetched {entry.get('fetched_at')})")
        print(f"  files   : {len(files)}" + ("" if files else "  (reference only — stores no bytes)"))
        for spec in files:
            print(f"            {spec['path']}  {spec.get('bytes', '?')} bytes")
        for spec in entry.get("skipped") or []:
            print(f"  skipped : {spec['path']} — {spec.get('reason', '')}")
        print()
    return 0


def cmd_check(as_json: bool = False) -> int:
    manifest = load_manifest()
    integrity = verify_integrity()

    drift: List[Dict[str, Any]] = []
    for name, entry in sorted(manifest["sources"].items()):
        repo, ref = entry.get("repo"), entry.get("ref")
        pinned = entry.get("commit")
        row: Dict[str, Any] = {"source": name, "repo": repo, "ref": ref, "pinned": pinned}
        remote = _remote_commit(str(repo), str(ref)) if repo and ref else None
        if remote is None:
            row.update(status=DRIFT_UNKNOWN, detail="remote unreachable; drift not determined")
        elif remote == pinned:
            row.update(status="current", remote=remote)
        else:
            row.update(status="behind", remote=remote)
        drift.append(row)

    tampered = [r for r in integrity if not r["ok"]]
    behind = [r for r in drift if r["status"] == "behind"]
    unknown = [r for r in drift if r["status"] == DRIFT_UNKNOWN]

    payload = {
        "ok": not tampered and not behind,
        "integrity": integrity,
        "drift": drift,
        "summary": {
            "files_checked": len(integrity),
            "tampered": len(tampered),
            "behind": len(behind),
            "undetermined": len(unknown),
        },
    }

    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Local integrity: {len(integrity) - len(tampered)}/{len(integrity)} files match their pin")
        for row in tampered:
            print(f"  TAMPERED  {row['path']} — {row['reason']}")
        print("Upstream drift:")
        for row in drift:
            if row["status"] == "current":
                print(f"  current   {row['source']}  ({row['repo']} @ {row['ref']})")
            elif row["status"] == "behind":
                print(
                    f"  BEHIND    {row['source']}  pinned {str(row['pinned'])[:12]}"
                    f" -> upstream {str(row['remote'])[:12]}"
                )
            else:
                print(f"  unknown   {row['source']} — {row['detail']}")
        if unknown and not tampered and not behind:
            print("\nNothing proven wrong, but drift for some sources was not determined.")

    return 0 if payload["ok"] else 1


def cmd_update(name: str) -> int:
    root = vendor_root()
    manifest_path = root / "manifest.json"
    manifest = load_manifest()
    entry = manifest["sources"].get(name)
    if entry is None:
        print(f"unknown source: {name!r}", file=sys.stderr)
        return 2

    repo, ref = str(entry.get("repo")), str(entry.get("ref"))
    remote = _remote_commit(repo, ref)
    if remote is None:
        print(f"could not reach {repo} @ {ref}; nothing updated", file=sys.stderr)
        return 2

    files = entry.get("files") or []
    if not files:
        # pinned_reference: move the pin, store no bytes.
        entry["commit"] = remote
        entry["fetched_at"] = _today()
        if entry.get("reference_url"):
            entry["reference_url"] = f"https://github.com/{repo}/tree/{ref}"
        _write_manifest(manifest_path, manifest)
        print(f"{name}: reference re-pinned to {remote[:12]} ({repo} @ {ref})")
        return 0

    for spec in files:
        upstream_name = Path(spec["path"]).name
        url = f"https://raw.githubusercontent.com/{repo}/{remote}/{upstream_name}"
        req = urllib.request.Request(url, headers={"User-Agent": "SuperAI-vendor-sync"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                blob = resp.read()
        except Exception as exc:  # noqa: BLE001
            print(f"failed to download {url}: {exc}", file=sys.stderr)
            return 2
        dest = root / spec["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob)
        spec["url"] = url
        spec["bytes"] = len(blob)
        spec["sha256"] = sha256_of(dest)
        print(f"{name}: {spec['path']} <- {len(blob)} bytes, sha256 {spec['sha256'][:12]}")

    entry["commit"] = remote
    entry["fetched_at"] = _today()
    _write_manifest(manifest_path, manifest)
    print(f"{name}: pinned to {remote[:12]} ({repo} @ {ref})")
    return 0


def _today() -> str:
    from datetime import date

    return date.today().isoformat()


def _write_manifest(path: Path, manifest: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="show what is pinned")
    group.add_argument("--check", action="store_true", help="local integrity + upstream drift")
    group.add_argument("--update", metavar="NAME", help="deliberately re-pin one source")
    parser.add_argument("--json", action="store_true", help="machine-readable output for --check")
    args = parser.parse_args(argv)

    if args.list:
        return cmd_list()
    if args.check:
        return cmd_check(as_json=args.json)
    return cmd_update(args.update)


if __name__ == "__main__":
    raise SystemExit(main())
