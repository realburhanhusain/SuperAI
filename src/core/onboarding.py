"""
Onboarding wizard helpers (N28).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .config import Config
from .constitution import ensure_default_constitution
from .discovery import discover_environment
from .policy import PolicyEngine


def run_onboarding(non_interactive: bool = True) -> Dict[str, Any]:
    cfg = Config()
    dirs = cfg.initialize()
    ensure_default_constitution()
    PolicyEngine()  # ensure defaults
    env = discover_environment()
    if env.get("mock_recommended"):
        cfg.set("mock_mode", True)
    steps: List[str] = [
        "initialized_home",
        "constitution",
        "policy",
        "discovery",
    ]
    # project local config template
    proj = Path.cwd() / ".superai"
    proj.mkdir(exist_ok=True)
    pc = proj / "config.json"
    if not pc.exists():
        pc.write_text('{\n  "mock_mode": true\n}\n', encoding="utf-8")
        steps.append("project_config")

    # Host tools checklist (+ optional auto-install via SUPERAI_AUTO_HOST_TOOLS)
    host_tools = None
    host_install = None
    try:
        from .host_tools import checklist, maybe_auto_install_on_setup, save_checklist_report

        host_tools = checklist(profile="core")
        save_checklist_report(host_tools)
        steps.append("host_tools_check")
        host_install = maybe_auto_install_on_setup()
        if host_install is not None:
            steps.append("host_tools_auto")
    except Exception:  # noqa: BLE001
        pass

    return {
        "ok": True,
        "steps": steps,
        "home": str(dirs.get("home")),
        "mock_mode": cfg.use_mock,
        "clis": env.get("clis_available"),
        "host_tools": {
            "totals": (host_tools or {}).get("totals"),
            "missing": [m.get("id") for m in ((host_tools or {}).get("missing") or [])],
        }
        if host_tools
        else None,
        "host_tools_install": host_install,
        "next": [
            "superai doctor",
            "superai host-tools check",
            "superai host-tools install --profile core --dry-run",
            'superai run "hello world"',
            "superai budget show",
            "superai constitution show",
        ],
    }
