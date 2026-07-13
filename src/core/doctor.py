"""
SuperAI doctor / health pack (M1 + M7).
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

from .config import Config
from .discovery import discover_environment
from .workspace import workspace_root


def run_doctor(quick: bool = False) -> Dict[str, Any]:
    """Collect environment, config, and optional smoke checks."""
    checks: List[Dict[str, Any]] = []
    cfg = Config()
    home = Path.home() / ".superai"

    def add(name: str, ok: bool, detail: str = "", level: str = "info") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail, "level": level if not ok else "ok"})

    # Python
    add("python", sys.version_info >= (3, 10), f"{sys.version.split()[0]}")

    # Home layout
    add("superai_home", home.is_dir(), str(home))
    add("config", cfg.config_path.exists(), str(cfg.config_path))
    add("mock_mode", True, f"mock_mode={cfg.use_mock}")

    # Workspace
    try:
        ws = workspace_root()
        add("workspace", ws.is_dir(), str(ws))
    except Exception as e:  # noqa: BLE001
        add("workspace", False, str(e), "error")

    # Packages
    try:
        import core  # noqa: F401

        add("package_core", True, getattr(core, "__version__", "?"))
    except Exception as e:  # noqa: BLE001
        add("package_core", False, str(e), "error")
    try:
        import scli  # noqa: F401

        add("package_scli", True, "importable")
    except Exception as e:  # noqa: BLE001
        add("package_scli", False, str(e), "error")

    # Discovery
    env = discover_environment()
    keys = env.get("api_keys_present") or {}
    any_key = any(keys.values())
    add(
        "api_keys",
        True,
        f"any={any_key} present={[k for k,v in keys.items() if v]}",
    )
    add("ollama", bool(env.get("ollama_on_path")), "on PATH" if env.get("ollama_on_path") else "missing")
    add("rclone", bool(env.get("rclone_on_path")), "on PATH" if env.get("rclone_on_path") else "missing")
    add(
        "external_clis",
        True,
        f"available={env.get('clis_available') or []}",
    )

    # Host tools checklist (not bundled; PATH discovery)
    host_tools_report = None
    try:
        from .host_tools import checklist as host_tools_checklist

        host_tools_report = host_tools_checklist(profile="full")
        totals = host_tools_report.get("totals") or {}
        missing_ids = [m["id"] for m in (host_tools_report.get("missing") or [])[:12]]
        add(
            "host_tools",
            True,
            (
                f"present={totals.get('present', 0)}/"
                f"{totals.get('checked', 0)} "
                f"missing={missing_ids or []}"
            ),
        )
    except Exception as e:  # noqa: BLE001
        add("host_tools", False, str(e), "warn")

    # Backup key
    key = home / ".backup_key"
    add("backup_key", key.exists(), str(key) if key.exists() else "not generated yet")

    # Security defaults
    add(
        "require_human_approval",
        bool(cfg.get("require_human_approval", True)),
        f"value={cfg.get('require_human_approval')}",
        level="warn" if not cfg.get("require_human_approval", True) else "ok",
    )
    add(
        "web_token",
        True,
        "set" if (os.getenv("SUPERAI_WEB_TOKEN") or "").strip() else "unset (loopback-only OK)",
    )

    # Optional smoke
    smoke = None
    if not quick:
        try:
            from .provider_smoke import run_provider_smoke

            smoke = run_provider_smoke(use_mock=True)
            n = len(smoke.get("results") or []) if isinstance(smoke, dict) else 0
            add("provider_smoke_mock", True, f"results={n}")
        except Exception as e:  # noqa: BLE001
            # try simpler
            try:
                from .model_caller import ModelCaller
                from .model_registry import ModelRegistry

                reg = ModelRegistry()
                names = reg.list_all_models()
                if names:
                    r = ModelCaller(use_mock=True, registry=reg).call(
                        model=names[0], prompt="ping"
                    )
                    add("mock_model_call", r.get("status") != "error", str(r.get("status")))
                else:
                    add("mock_model_call", False, "no models", "warn")
            except Exception as e2:  # noqa: BLE001
                add("mock_model_call", False, str(e2), "error")

        # Incomplete runs
        try:
            from .step_cache import StepResultCache

            runs = StepResultCache().list_runs()
            open_runs = [r for r in runs if r.get("remaining_step_ids")]
            add(
                "incomplete_runs",
                True,
                f"count={len(open_runs)}",
                level="warn" if open_runs else "ok",
            )
        except Exception as e:  # noqa: BLE001
            add("incomplete_runs", False, str(e), "warn")

    ok_all = all(c["ok"] for c in checks if c.get("level") == "error" or not c["ok"] and c.get("level") == "error")
    # simpler: any level error fails
    failed = [c for c in checks if not c["ok"] and c.get("level") == "error"]
    summary = {
        "ok": len(failed) == 0,
        "checks": checks,
        "mock_mode": cfg.use_mock,
        "home": str(home),
        "workspace": str(workspace_root()),
        "next_steps": _next_steps(cfg, any_key, checks),
        "smoke": smoke,
        "host_tools": {
            "totals": (host_tools_report or {}).get("totals"),
            "missing": [
                m.get("id") for m in ((host_tools_report or {}).get("missing") or [])
            ],
            "package_managers": (host_tools_report or {}).get("package_managers"),
        }
        if host_tools_report
        else None,
    }
    return summary


def _next_steps(cfg: Config, any_key: bool, checks: List[Dict[str, Any]]) -> List[str]:
    steps = []
    if not (Path.home() / ".superai" / "config.json").exists():
        steps.append('Run: superai init --non-interactive')
    steps.append('Mock path: superai run "hello" --format json')
    if cfg.use_mock and any_key:
        steps.append("Keys detected — try: superai config set mock_mode false")
    if not any_key:
        steps.append("Optional live: set OPENAI_API_KEY / XAI_API_KEY / …")
    open_runs = next((c for c in checks if c["name"] == "incomplete_runs"), None)
    if open_runs and "count=" in str(open_runs.get("detail")) and open_runs["detail"] != "count=0":
        steps.append("Resume: superai runs list && superai runs resume <task_id>")
    ht = next((c for c in checks if c["name"] == "host_tools"), None)
    if ht and "missing=[" in str(ht.get("detail")) and "missing=[]" not in str(
        ht.get("detail")
    ):
        steps.append(
            "Host tools: superai host-tools check  ·  "
            "superai host-tools install --profile core --dry-run"
        )
    steps.append("Security: keep require_human_approval true; set SUPERAI_WORKSPACE")
    return steps
