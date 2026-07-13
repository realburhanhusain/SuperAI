"""
Version / update channel check (M11).
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict, Optional

from core import __version__ as LOCAL_VERSION


def check_update(
    remote_url: Optional[str] = None,
    timeout: float = 5.0,
) -> Dict[str, Any]:
    """
    Compare local version to optional remote version JSON:
    {"version": "0.2.0", "notes": "...", "url": "..."}
    Default: no network if SUPERAI_VERSION_URL unset.
    """
    import os

    url = remote_url or os.getenv("SUPERAI_VERSION_URL") or ""
    result: Dict[str, Any] = {
        "local": LOCAL_VERSION,
        "remote": None,
        "update_available": False,
        "notes": None,
        "checked": False,
    }
    if not url:
        result["message"] = "Set SUPERAI_VERSION_URL to enable remote version check"
        return result
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        remote = str(data.get("version") or "")
        result["remote"] = remote
        result["notes"] = data.get("notes")
        result["url"] = data.get("url")
        result["checked"] = True
        result["update_available"] = _is_newer(remote, LOCAL_VERSION)
        if result["update_available"]:
            result["message"] = f"Update available: {LOCAL_VERSION} → {remote}"
        else:
            result["message"] = "Up to date"
    except Exception as e:  # noqa: BLE001
        result["error"] = str(e)
        result["message"] = f"Could not check updates: {e}"
    return result


def _is_newer(remote: str, local: str) -> bool:
    def parts(v: str):
        out = []
        for p in v.strip().lstrip("v").split("."):
            try:
                out.append(int(p))
            except ValueError:
                out.append(0)
        return out

    r, l = parts(remote), parts(local)
    # pad
    n = max(len(r), len(l))
    r += [0] * (n - len(r))
    l += [0] * (n - len(l))
    return r > l
