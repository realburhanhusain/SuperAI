"""
Onboarding wizard helpers (N28).

Interactive path delegates to install_wizard (host tools + optional Postgres).
Non-interactive path stays quiet (checklist + SUPERAI_AUTO_HOST_TOOLS only).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import Config
from .constitution import ensure_default_constitution
from .discovery import discover_environment
from .policy import PolicyEngine


def run_onboarding(
    non_interactive: bool = True,
    *,
    with_postgres: Optional[bool] = None,
    live: bool = False,
    yes: bool = False,
    host_tools_profile: Optional[str] = None,
) -> Dict[str, Any]:
    # Interactive full install wizard
    if not non_interactive:
        from .install_wizard import run_install_wizard

        wiz = run_install_wizard(
            interactive=True,
            with_postgres=with_postgres,
            host_tools_profile=host_tools_profile,
            live=live,
            yes=yes,
        )
        # project local config template
        proj = Path.cwd() / ".superai"
        proj.mkdir(exist_ok=True)
        pc = proj / "config.json"
        if not pc.exists():
            pc.write_text('{\n  "mock_mode": true\n}\n', encoding="utf-8")
            wiz.setdefault("steps", []).append("project_config")
        wiz["onboarding"] = True
        return wiz

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

        host_tools = checklist(profile=host_tools_profile or "core")
        save_checklist_report(host_tools)
        steps.append("host_tools_check")
        host_install = maybe_auto_install_on_setup()
        if host_install is not None:
            steps.append("host_tools_auto")
    except Exception:  # noqa: BLE001
        pass

    # Optional non-interactive Postgres via env SUPERAI_INSTALL_POSTGRES
    postgres = None
    try:
        import os

        if (os.getenv("SUPERAI_INSTALL_POSTGRES") or "").lower() in {
            "1",
            "true",
            "yes",
            "install",
        } or with_postgres:
            from .postgres_setup import ensure_postgres_for_superai

            postgres = ensure_postgres_for_superai(
                live=live or yes,
                install_if_missing=True,
            )
            if isinstance(postgres.get("setup"), dict):
                postgres["setup"].pop("db_password", None)
            steps.append("postgres")
    except Exception as e:  # noqa: BLE001
        postgres = {"ok": False, "error": str(e)}

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
        "postgres": postgres,
        "memory_dsn_configured": bool(cfg.get("memory_dsn")),
        "next": [
            "superai doctor",
            "superai install   # interactive host tools + optional Postgres",
            "superai host-tools check",
            "superai host-tools install --profile core --dry-run",
            'superai run "hello world"',
            "superai budget show",
            "superai constitution show",
        ],
    }
