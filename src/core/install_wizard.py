"""
Interactive SuperAI installation wizard (opt-in components).

- Initialize home / config
- Host tools: choose profile, confirm live install of missing tools
- Postgres + pgvector: opt-in detect/install/setup/DSN write
- Final doctor-style summary

Non-interactive mode honors flags / env (for CI and bootstrap scripts).
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Sequence


PROFILES = ("core", "agentic", "cloud", "full")


def _is_tty() -> bool:
    try:
        return bool(sys.stdin.isatty() and sys.stdout.isatty())
    except Exception:
        return False


def _prompt_yes_no(question: str, *, default: bool = False) -> bool:
    if not _is_tty():
        return default
    suffix = " [Y/n] " if default else " [y/N] "
    try:
        raw = input(question + suffix).strip().lower()
    except EOFError:
        return default
    if not raw:
        return default
    return raw in {"y", "yes", "1", "true"}


def _prompt_choice(
    question: str,
    choices: Sequence[str],
    *,
    default: str,
) -> str:
    if not _is_tty():
        return default
    opts = "/".join(choices)
    try:
        raw = input(f"{question} ({opts}) [{default}]: ").strip().lower()
    except EOFError:
        return default
    if not raw:
        return default
    for c in choices:
        if raw == c.lower() or raw == c[0].lower():
            return c
    return default


def _prompt_text(question: str, *, default: str = "") -> str:
    if not _is_tty():
        return default
    try:
        raw = input(f"{question} [{default}]: ").strip()
    except EOFError:
        return default
    return raw if raw else default


def run_install_wizard(
    *,
    interactive: Optional[bool] = None,
    with_postgres: Optional[bool] = None,
    install_postgres_if_missing: bool = True,
    host_tools_profile: Optional[str] = None,
    install_host_tools: Optional[bool] = None,
    live: bool = False,
    yes: bool = False,
    admin_password: Optional[str] = None,
    skip_host_tools: bool = False,
    skip_postgres: bool = False,
) -> Dict[str, Any]:
    """
    Run SuperAI first-time / re-run install wizard.

    interactive: default True when TTY and not yes/non_interactive env
    live: actually install packages / mutate Postgres
    yes: assume consent for recommended opts (still respects skip_* flags)
    """
    from .config import Config
    from .constitution import ensure_default_constitution
    from .discovery import discover_environment
    from .policy import PolicyEngine

    non_int_env = (os.getenv("SUPERAI_NON_INTERACTIVE") or "").lower() in {
        "1",
        "true",
        "yes",
    }
    if interactive is None:
        interactive = _is_tty() and not non_int_env and not yes

    result: Dict[str, Any] = {
        "ok": True,
        "interactive": interactive,
        "live": live or yes,
        "steps": [],
    }
    live = bool(live or yes)

    # ── 1. Home + config ──────────────────────────────────────────────
    cfg = Config()
    dirs = cfg.initialize()
    ensure_default_constitution()
    PolicyEngine()
    env = discover_environment()
    if env.get("mock_recommended"):
        cfg.set("mock_mode", True)
    result["home"] = str(dirs.get("home"))
    result["config_path"] = str(cfg.config_path)
    result["steps"].append("initialize")

    # ── 2. Host tools ─────────────────────────────────────────────────
    host_report: Dict[str, Any] = {}
    if not skip_host_tools:
        from .host_tools import checklist, install_tools, save_checklist_report

        if interactive and host_tools_profile is None:
            print("\n=== SuperAI host tools ===")
            print(
                "SuperAI can install missing system CLIs (git, gh, cloud CLIs, AI CLIs)\n"
                "via winget/brew/apt/pip — not bundled in the Python package."
            )
            host_tools_profile = _prompt_choice(
                "Host tools profile",
                list(PROFILES) + ["skip"],
                default="core",
            )
            if host_tools_profile == "skip":
                skip_host_tools = True
                host_tools_profile = "core"

        profile = host_tools_profile or "core"
        if profile not in PROFILES:
            profile = "core"

        if not skip_host_tools:
            report = checklist(profile=profile)
            save_checklist_report(report)
            missing = [m.get("id") for m in (report.get("missing") or [])]
            result["host_tools_check"] = {
                "profile": profile,
                "totals": report.get("totals"),
                "missing": missing,
            }
            result["steps"].append("host_tools_check")

            do_install = install_host_tools
            if do_install is None:
                if interactive:
                    do_install = _prompt_yes_no(
                        f"Install missing host tools now? missing={missing or '[]'}",
                        default=bool(missing),
                    )
                else:
                    # non-interactive: only if live/yes or AUTO env
                    auto = (os.getenv("SUPERAI_AUTO_HOST_TOOLS") or "").lower()
                    do_install = live or auto in {
                        "1",
                        "true",
                        "yes",
                        "install",
                        "agentic",
                        "core",
                        "full",
                    }

            if do_install and missing:
                # Confirm live install separately when interactive
                do_live = live
                if interactive and not yes:
                    do_live = _prompt_yes_no(
                        "Run LIVE package installs (requires network/admin)?",
                        default=False,
                    )
                inst = install_tools(
                    profile=profile,
                    dry_run=not do_live,
                    only_missing=True,
                )
                result["host_tools_install"] = {
                    "dry_run": not do_live,
                    "totals": inst.get("totals"),
                    "results": [
                        {
                            "id": r.get("id"),
                            "status": r.get("status"),
                            "command_str": r.get("command_str"),
                        }
                        for r in (inst.get("results") or [])
                    ],
                }
                result["steps"].append(
                    "host_tools_install_live" if do_live else "host_tools_install_dry_run"
                )
            elif do_install and not missing:
                result["host_tools_install"] = {
                    "status": "nothing_missing",
                    "profile": profile,
                }

    # ── 3. Postgres (opt-in) ──────────────────────────────────────────
    if skip_postgres:
        result["postgres"] = {
            "skipped": True,
            "note": "Postgres setup skipped; SQLite cosine used by default",
        }
        result["steps"].append("postgres_skipped")
    else:
        from .postgres_setup import detect_postgres, ensure_postgres_for_superai

        want_pg = with_postgres
        det = detect_postgres()
        result["postgres_detect"] = det

        if want_pg is None and interactive:
            print("\n=== Memory Palace database (Postgres + pgvector) ===")
            print(
                "Default without Postgres: local SQLite cosine store.\n"
                "Postgres is recommended for multi-session / multi-CLI concurrent memory."
            )
            if det.get("available"):
                print(f"Detected PostgreSQL: {det.get('version') or 'yes'} "
                      f"(ready={det.get('ready')})")
                want_pg = _prompt_yes_no(
                    "Configure SuperAI to use this Postgres (create DB + vector + DSN)?",
                    default=True,
                )
            else:
                want_pg = _prompt_yes_no(
                    "Install and configure PostgreSQL for Memory Palace?",
                    default=True,
                )
        elif want_pg is None:
            # non-interactive: only if SUPERAI_INSTALL_POSTGRES=1 or with_postgres flag
            want_pg = (os.getenv("SUPERAI_INSTALL_POSTGRES") or "").lower() in {
                "1",
                "true",
                "yes",
                "install",
            }

        if want_pg:
            do_live = live
            if interactive and not yes:
                do_live = _prompt_yes_no(
                    "Apply Postgres changes LIVE (install/create DB/extension/write config)?",
                    default=False,
                )
            admin_pw = admin_password or os.getenv("SUPERAI_PG_ADMIN_PASSWORD")
            if interactive and do_live and not admin_pw and det.get("available"):
                admin_pw = _prompt_text(
                    "Postgres admin password for user 'postgres' (empty = trust/peer/auth env)",
                    default="",
                ) or None

            pg = ensure_postgres_for_superai(
                live=do_live,
                install_if_missing=install_postgres_if_missing,
                admin_password=admin_pw,
            )
            # never echo raw password in result
            if isinstance(pg.get("setup"), dict):
                pg["setup"].pop("db_password", None)
            result["postgres"] = pg
            result["steps"].append(
                "postgres_live" if do_live else "postgres_dry_run"
            )
            if do_live and not pg.get("ok"):
                result["ok"] = False
                result["postgres_error"] = pg.get("error")
        else:
            result["postgres"] = {
                "skipped": True,
                "note": "Using SQLite cosine under ~/.superai/memory until SUPERAI_MEMORY_DSN is set",
            }
            result["steps"].append("postgres_skipped")

    # ── 4. Summary ────────────────────────────────────────────────────
    result["mock_mode"] = cfg.use_mock
    result["memory_backend"] = cfg.get("memory_backend")
    result["memory_dsn_configured"] = bool(cfg.get("memory_dsn"))
    result["next"] = [
        "superai doctor",
        "superai host-tools check",
        'superai run "hello world"',
        "superai mcp-config --write",
    ]
    if result.get("memory_dsn_configured"):
        result["next"].insert(0, "superai memory-stats  # or memory-palace snapshot")
    result["steps"].append("done")
    return result
