"""
SuperAI Configuration System (Phase 1)

JSON file under ~/.superai/config.json + SUPERAI_* environment overrides.
Guided by implementation_plan_v2 / detailed plan; reuses codes.md patterns.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Configuration manager for SuperAI."""

    DEFAULT_CONFIG: Dict[str, Any] = {
        "version": "0.1.0",
        "mock_mode": True,
        "log_level": "INFO",
        "default_supervisor": None,
        "default_model": None,
        "load_balancing_strategy": "smart_fallback",
        "max_delegation_depth": 3,
        "enable_logging": True,
        "backup_enabled": True,
        "non_interactive": False,
        # OpenClaw-style human approval for file-modifying external CLIs / tools
        "require_human_approval": True,
        # Council default voting: majority | supervisor | weighted
        "council_voting_mode": "majority",
        # Databao / NL data analytics
        "data_dsn": None,  # e.g. sqlite:////path or postgresql://...
        "databao_llm": "gpt-4o-mini",
        "use_databao_package": True,
        # Contextual bandit routing blend (H6)
        "use_bandit": True,
        "bandit_epsilon": 0.1,
        "bandit_blend": 0.25,
        "use_step_cache": True,
        # Failover chain (S5): ordered model names
        "failover_chain": [],
        # Budget defaults (S4)
        "budget_daily_usd": 5.0,
        "budget_run_usd": 1.0,
        # Databao read-only enforcement (M5)
        "data_read_only": True,
        # Inject constitution into runs (N14)
        "use_constitution": True,
        # Active profile name (N3)
        "profile": "default",
        # Prefer LLM planner when not mock (S3)
        "prefer_llm_planner": True,
        # Docker sandbox flag (N15) — informational / future hook
        "prefer_container_sandbox": False,
        "compliance_mode": False,
        "lang": "en",
        "telemetry_opt_in": False,
    }

    def __init__(self, config_path: Optional[str] = None):
        self.home_dir = Path.home() / ".superai"
        self.config_path = Path(config_path) if config_path else self.home_dir / "config.json"
        self.config: Dict[str, Any] = self.DEFAULT_CONFIG.copy()
        self._ensure_home()
        self._load_config()
        self._load_project_config()  # S7: .superai/config.json in cwd
        self._apply_env_overrides()

    def _ensure_home(self) -> None:
        self.home_dir.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> Dict[str, Path]:
        """First-run setup: create standard directory layout and save defaults."""
        dirs = {
            "home": self.home_dir,
            "logs": self.home_dir / "logs",
            "history": self.home_dir / "history",
            "memory": self.home_dir / "memory",
            "skills": self.home_dir / "skills",
            "backups": self.home_dir / "backups",
            "config_dir": self.home_dir / "config",
        }
        for path in dirs.values():
            path.mkdir(parents=True, exist_ok=True)

        if not self.config_path.exists():
            self.config = self.DEFAULT_CONFIG.copy()
            self.save(quiet=True)
        else:
            self._load_config()
            self._apply_env_overrides()

        return dirs

    def _load_config(self) -> None:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    file_config = json.load(f)
                if isinstance(file_config, dict):
                    self.config.update(file_config)
            except (OSError, json.JSONDecodeError):
                # Keep defaults if file is corrupt; next save will rewrite.
                pass

    def _apply_env_overrides(self) -> None:
        """Environment variables take precedence (SUPERAI_*)."""
        env_map = {
            "SUPERAI_MOCK_MODE": ("mock_mode", _as_bool),
            "SUPERAI_LOG_LEVEL": ("log_level", str),
            "SUPERAI_DEFAULT_SUPERVISOR": ("default_supervisor", str),
            "SUPERAI_DEFAULT_MODEL": ("default_model", str),
            "SUPERAI_NON_INTERACTIVE": ("non_interactive", _as_bool),
            "SUPERAI_BACKUP_ENABLED": ("backup_enabled", _as_bool),
            "SUPERAI_REQUIRE_HUMAN_APPROVAL": ("require_human_approval", _as_bool),
            "SUPERAI_COUNCIL_VOTING_MODE": ("council_voting_mode", str),
            "SUPERAI_DATA_DSN": ("data_dsn", str),
            "DATABASE_URL": ("data_dsn", str),
            "SUPERAI_DATABAO_LLM": ("databao_llm", str),
            "SUPERAI_USE_DATABAO": ("use_databao_package", _as_bool),
            "SUPERAI_USE_BANDIT": ("use_bandit", _as_bool),
            "SUPERAI_BANDIT_EPSILON": ("bandit_epsilon", float),
            "SUPERAI_BANDIT_BLEND": ("bandit_blend", float),
            "SUPERAI_USE_STEP_CACHE": ("use_step_cache", _as_bool),
            "SUPERAI_DATA_READ_ONLY": ("data_read_only", _as_bool),
            "SUPERAI_USE_CONSTITUTION": ("use_constitution", _as_bool),
            "SUPERAI_PROFILE": ("profile", str),
            "SUPERAI_PREFER_LLM_PLANNER": ("prefer_llm_planner", _as_bool),
            "SUPERAI_BUDGET_DAILY_USD": ("budget_daily_usd", float),
            "SUPERAI_BUDGET_RUN_USD": ("budget_run_usd", float),
        }
        for env_key, (cfg_key, caster) in env_map.items():
            raw = os.getenv(env_key)
            if raw is not None and raw != "":
                self.config[cfg_key] = caster(raw)

    def _load_project_config(self) -> None:
        """S7: merge project-local .superai/config.json from cwd if present."""
        proj = Path.cwd() / ".superai" / "config.json"
        if not proj.is_file():
            return
        try:
            data = json.loads(proj.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.config.update(data)
                self.config["_project_config"] = str(proj)
        except (OSError, json.JSONDecodeError):
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any, persist: bool = True) -> None:
        self.config[key] = value
        if persist:
            self.save(quiet=True)

    def save(self, quiet: bool = False) -> None:
        self._ensure_home()
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2)
        if not quiet:
            print(f"Configuration saved to {self.config_path}")

    def show(self) -> Dict[str, Any]:
        return dict(self.config)

    @property
    def use_mock(self) -> bool:
        # Support both historical and plan key names
        if "mock_mode" in self.config:
            return bool(self.config.get("mock_mode", True))
        return bool(self.config.get("use_mock", True))

    @property
    def mock_mode(self) -> bool:
        return self.use_mock

    @property
    def default_supervisor(self) -> Optional[str]:
        return self.get("default_supervisor") or self.get("default_model")

    @property
    def require_human_approval(self) -> bool:
        return bool(self.get("require_human_approval", True))

    @property
    def council_voting_mode(self) -> str:
        mode = str(self.get("council_voting_mode") or "majority").lower()
        if mode not in {"majority", "supervisor", "weighted"}:
            return "majority"
        return mode


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


# Lazy-friendly singleton for modules that import config at load time
config = Config()
