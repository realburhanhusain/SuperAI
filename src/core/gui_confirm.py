"""
GUI confirm dialog for NL command preview (N202 expansion).

Uses tkinter when available (standard on most Python desktops).
Headless/CI: returns non-interactive result without raising.
"""

from __future__ import annotations

import os
import sys
import threading
from typing import Any, Dict, Optional


def _can_use_gui() -> bool:
    if (os.getenv("SUPERAI_NO_GUI") or "").lower() in {"1", "true", "yes"}:
        return False
    if (os.getenv("CI") or "").lower() in {"1", "true", "yes"}:
        return False
    # Windows / mac / linux with display
    if sys.platform.startswith("linux") and not os.getenv("DISPLAY"):
        return False
    try:
        import tkinter  # noqa: F401

        return True
    except Exception:
        return False


def confirm_dialog(
    title: str,
    message: str,
    *,
    detail: str = "",
    default_no: bool = True,
    timeout_sec: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Show a blocking Confirm / Cancel dialog.

    Returns:
      {ok, confirmed, backend: tk|headless|error, ...}
    """
    if not _can_use_gui():
        return {
            "ok": True,
            "confirmed": False,
            "backend": "headless",
            "reason": "gui_unavailable_or_ci",
            "default_no": default_no,
        }

    result: Dict[str, Any] = {
        "ok": False,
        "confirmed": False,
        "backend": "tk",
    }

    def _run() -> None:
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            # messagebox returns True/False for askokcancel
            body = message
            if detail:
                body = f"{message}\n\n{detail[:2000]}"
            confirmed = messagebox.askokcancel(title or "SuperAI Confirm", body)
            result["ok"] = True
            result["confirmed"] = bool(confirmed)
            root.destroy()
        except Exception as e:
            result["ok"] = False
            result["error"] = str(e)[:300]
            result["backend"] = "error"

    # Always run on main thread if possible; tk often requires main thread
    try:
        _run()
    except Exception as e:
        result["ok"] = False
        result["error"] = str(e)[:300]
        result["backend"] = "error"
    return result


def confirm_nl_preview(preview: Dict[str, Any]) -> Dict[str, Any]:
    """
    GUI confirm for an nl_preview.preview_nl result.
    """
    planned = str((preview or {}).get("planned_command") or "")
    risk = str((preview or {}).get("risk") or "unknown")
    conf = (preview or {}).get("confidence")
    action = (preview or {}).get("action")
    summary = (preview or {}).get("summary") or planned
    msg = "Execute this SuperAI command?"
    detail = (
        f"Action: {action}\n"
        f"Risk: {risk}\n"
        f"Confidence: {conf}\n"
        f"Command:\n{planned}\n\n"
        f"{summary}"
    )
    out = confirm_dialog("SuperAI — Confirm command", msg, detail=detail)
    out["planned_command"] = planned
    out["preview_action"] = action
    return out
