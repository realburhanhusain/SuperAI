"""
File time-travel (Atomic-Hermes inspired).

Snapshots file contents before SuperAI-driven edits so users can list/restore versions.
Store: ~/.superai/time_travel/<safe_path_hash>/
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class FileTimeTravel:
    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root or (Path.home() / ".superai" / "time_travel"))
        self.root.mkdir(parents=True, exist_ok=True)

    def _key(self, path: Path) -> str:
        resolved = str(path.resolve())
        return hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:24]

    def _meta_path(self, key: str) -> Path:
        return self.root / key / "meta.json"

    def _load_meta(self, key: str) -> Dict[str, Any]:
        mp = self._meta_path(key)
        if mp.exists():
            try:
                return json.loads(mp.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"path": None, "versions": []}

    def _save_meta(self, key: str, meta: Dict[str, Any]) -> None:
        d = self.root / key
        d.mkdir(parents=True, exist_ok=True)
        self._meta_path(key).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def snapshot(self, path: str | Path, note: str = "") -> Dict[str, Any]:
        """Snapshot current file if it exists; returns version info."""
        p = Path(path)
        key = self._key(p)
        meta = self._load_meta(key)
        meta["path"] = str(p.resolve()) if p.exists() else str(p)
        versions = meta.setdefault("versions", [])
        ver = len(versions) + 1
        stamp = time.strftime("%Y%m%d_%H%M%S")
        dest_dir = self.root / key
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"v{ver}_{stamp}"
        if p.exists() and p.is_file():
            shutil.copy2(p, dest)
            size = p.stat().st_size
        else:
            # record missing baseline
            dest.write_text("", encoding="utf-8")
            size = 0
        entry = {
            "version": ver,
            "file": dest.name,
            "note": note,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "size": size,
            "existed": p.exists(),
        }
        versions.append(entry)
        self._save_meta(key, meta)
        return {"key": key, "path": meta["path"], **entry}

    def list_versions(self, path: str | Path) -> List[Dict[str, Any]]:
        p = Path(path)
        key = self._key(p)
        meta = self._load_meta(key)
        return list(meta.get("versions") or [])

    def restore(self, path: str | Path, version: int) -> Dict[str, Any]:
        p = Path(path)
        key = self._key(p)
        meta = self._load_meta(key)
        versions = meta.get("versions") or []
        match = next((v for v in versions if int(v.get("version")) == int(version)), None)
        if not match:
            raise KeyError(f"Version {version} not found for {path}")
        src = self.root / key / match["file"]
        if not src.exists():
            raise FileNotFoundError(f"Snapshot missing: {src}")
        # Snapshot current before restore
        if p.exists():
            self.snapshot(p, note=f"pre-restore-of-v{version}")
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, p)
        return {"restored": str(p), "from_version": version, "snapshot": match}

    def history_index(self) -> List[Dict[str, Any]]:
        out = []
        for d in self.root.iterdir():
            if not d.is_dir():
                continue
            meta = self._load_meta(d.name)
            out.append(
                {
                    "key": d.name,
                    "path": meta.get("path"),
                    "versions": len(meta.get("versions") or []),
                }
            )
        return out
