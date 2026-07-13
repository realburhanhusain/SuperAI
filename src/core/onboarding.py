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
    return {
        "ok": True,
        "steps": steps,
        "home": str(dirs.get("home")),
        "mock_mode": cfg.use_mock,
        "clis": env.get("clis_available"),
        "next": [
            "superai doctor",
            'superai run "hello world"',
            "superai budget show",
            "superai constitution show",
        ],
    }
