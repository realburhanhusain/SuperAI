"""
Crash report / diagnostics bundle (M12).
"""

from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

from .secrets import redact_obj, redact_text


def build_diagnostics_bundle(dest: Optional[Path] = None) -> Path:
    home = Path.home() / ".superai"
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out = Path(dest or (home / "diagnostics" / f"superai_diag_{stamp}.zip"))
    out.parent.mkdir(parents=True, exist_ok=True)

    payload: Dict[str, Any] = {"created_at": stamp}

    # doctor
    try:
        from .doctor import run_doctor

        payload["doctor"] = run_doctor(quick=True)
    except Exception as e:  # noqa: BLE001
        payload["doctor_error"] = str(e)

    # config redacted
    cfg_path = home / "config.json"
    if cfg_path.exists():
        try:
            payload["config"] = redact_obj(json.loads(cfg_path.read_text(encoding="utf-8")))
        except Exception as e:  # noqa: BLE001
            payload["config_error"] = str(e)

    # last few history ids only + redacted snippets
    hist = home / "history"
    hist_snip = []
    if hist.is_dir():
        for p in sorted(hist.glob("*.json"), reverse=True)[:5]:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                hist_snip.append(
                    {
                        "task_id": data.get("task_id"),
                        "status": data.get("status"),
                        "task": redact_text(str(data.get("task") or "")[:200]),
                    }
                )
            except Exception:
                continue
    payload["recent_history"] = hist_snip

    # log tail redacted
    log_path = home / "logs" / "superai.log"
    log_tail = ""
    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            log_tail = redact_text("\n".join(lines[-80:]))
        except Exception:
            pass

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("report.json", json.dumps(payload, indent=2, default=str))
        if log_tail:
            zf.writestr("superai.log.tail.txt", log_tail)
        zf.writestr(
            "README.txt",
            "SuperAI diagnostics bundle (secrets redacted). Safe to share for support.\n",
        )
    return out
