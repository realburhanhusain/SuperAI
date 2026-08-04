"""
Read pinned external sources from ``vendor/``.

Everything here is offline by construction. SuperAI reads vendored bytes that
are committed to this repo; it never fetches the upstream source at runtime.
Refreshing a pin is a deliberate act performed by ``scripts/vendor_sync.py``.

See ``vendor/README.md`` for the policy and the two entry kinds.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class VendorError(RuntimeError):
    """A vendored source is missing, malformed, or does not match its pin."""


def vendor_root() -> Path:
    """Locate ``vendor/`` from an installed package or a source checkout."""
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "vendor",  # src/core/vendored.py -> repo/vendor
        here.parents[3] / "vendor",
        Path.cwd() / "vendor",
    ]
    for path in candidates:
        if (path / "manifest.json").is_file():
            return path
    raise VendorError(
        "vendor/manifest.json not found; expected a SuperAI checkout with a "
        f"vendor directory (looked in: {', '.join(str(c) for c in candidates)})"
    )


def load_manifest() -> Dict[str, Any]:
    path = vendor_root() / "manifest.json"
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or "sources" not in data:
        raise VendorError(f"{path} is not a vendor manifest")
    return data


def list_sources() -> List[Dict[str, Any]]:
    """One flat row per pinned source, for reporting."""
    rows: List[Dict[str, Any]] = []
    for name, entry in sorted(load_manifest()["sources"].items()):
        rows.append(
            {
                "name": name,
                "kind": entry.get("kind"),
                "repo": entry.get("repo"),
                "ref": entry.get("ref"),
                "commit": entry.get("commit"),
                "fetched_at": entry.get("fetched_at"),
                "file_count": len(entry.get("files") or []),
                "description": entry.get("description") or "",
            }
        )
    return rows


def pin_info(name: str) -> Dict[str, Any]:
    sources = load_manifest()["sources"]
    if name not in sources:
        raise VendorError(f"unknown vendored source: {name!r}")
    return dict(sources[name])


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_integrity(name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Check vendored bytes against their recorded sha256. Offline.

    This catches a vendored copy edited in place — the one failure mode a
    drift check against the upstream repo cannot see.
    """
    manifest = load_manifest()
    root = vendor_root()
    names = [name] if name else sorted(manifest["sources"])
    results: List[Dict[str, Any]] = []
    for src_name in names:
        entry = manifest["sources"].get(src_name)
        if entry is None:
            raise VendorError(f"unknown vendored source: {src_name!r}")
        for spec in entry.get("files") or []:
            path = root / spec["path"]
            row: Dict[str, Any] = {"source": src_name, "path": spec["path"]}
            if not path.is_file():
                row.update(ok=False, reason="missing")
            else:
                actual = sha256_of(path)
                row.update(
                    ok=actual == spec.get("sha256"),
                    reason="" if actual == spec.get("sha256") else "sha256_mismatch",
                    expected_sha256=spec.get("sha256"),
                    actual_sha256=actual,
                )
            results.append(row)
    return results


def load_json(name: str, filename: str) -> Any:
    """
    Load one vendored JSON file, verifying its sha256 first.

    A silently-modified vendored file would make every downstream check wrong
    while still looking authoritative, so integrity is not optional here.
    """
    entry = pin_info(name)
    spec = next(
        (f for f in entry.get("files") or [] if Path(f["path"]).name == filename),
        None,
    )
    if spec is None:
        raise VendorError(f"{name!r} does not vendor a file named {filename!r}")

    path = vendor_root() / spec["path"]
    if not path.is_file():
        raise VendorError(f"vendored file missing: {path}")

    actual = sha256_of(path)
    if actual != spec.get("sha256"):
        raise VendorError(
            f"{spec['path']} does not match its pin "
            f"(expected {spec.get('sha256')}, got {actual}). "
            "Re-run scripts/vendor_sync.py --update to re-pin deliberately."
        )

    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
