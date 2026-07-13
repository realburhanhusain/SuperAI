"""
Export / import full profile bundle (S21).
"""

from __future__ import annotations

import json
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .secrets import redact_obj


INCLUDE = [
    "config.json",
    "constitution.md",
    "policy.json",
    "skills",
    "preferences.json",
]


def export_profile(
    dest: Optional[Path] = None,
    *,
    include_secrets: bool = False,
) -> Path:
    home = Path.home() / ".superai"
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out = Path(dest or (home / f"profile_export_{stamp}.zip"))
    out.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in INCLUDE:
            p = home / name
            if p.is_file():
                if name == "config.json":
                    data = json.loads(p.read_text(encoding="utf-8"))
                    if not include_secrets:
                        data = redact_obj(data)
                    zf.writestr(name, json.dumps(data, indent=2))
                else:
                    zf.write(p, arcname=name)
            elif p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        zf.write(f, arcname=str(f.relative_to(home)))
        zf.writestr(
            "MANIFEST.json",
            json.dumps(
                {"exported_at": stamp, "include_secrets": include_secrets},
                indent=2,
            ),
        )
    return out


def import_profile(src: Path, *, dry_run: bool = False) -> Dict[str, Any]:
    home = Path.home() / ".superai"
    home.mkdir(parents=True, exist_ok=True)
    src = Path(src)
    if not src.is_file():
        raise FileNotFoundError(src)
    written: List[str] = []
    with zipfile.ZipFile(src, "r") as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in name.split("/"):
                continue
            if name.endswith("/"):
                continue
            target = (home / name).resolve()
            try:
                target.relative_to(home.resolve())
            except ValueError:
                continue
            if dry_run:
                written.append(name)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src_f, open(target, "wb") as dst:
                shutil.copyfileobj(src_f, dst)
            written.append(name)
    return {"ok": True, "files": written, "dry_run": dry_run}
