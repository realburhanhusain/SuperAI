"""
Model Registry for SuperAI

Loads models from config/models.json when available (preferred),
with a small built-in fallback set so the package works without the file.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    name: str
    provider: str
    model_id: str
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    context_window: int = 128000
    is_latest: bool = False
    supports_tools: bool = True
    strengths: str = ""
    cost_per_1k_tokens: float = 0.0
    latency_tier: int = 2  # 1=fast .. 5=slow
    extra: Dict[str, Any] = field(default_factory=dict)


def _project_models_json() -> Optional[Path]:
    """Locate models.json: user override first, then project, then cwd."""
    # src/superai/core/model_registry.py → repo root is parents[3]
    here = Path(__file__).resolve()
    candidates = [
        Path.home() / ".superai" / "config" / "models.json",  # refresh writes here
        here.parents[3] / "config" / "models.json",
        here.parents[2] / "config" / "models.json",
        Path.cwd() / "config" / "models.json",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


class ModelRegistry:
    def __init__(self, models_path: Optional[str | Path] = None):
        self.models: Dict[str, ModelInfo] = {}
        self.source: str = "builtin"
        self.models_path: Optional[Path] = Path(models_path) if models_path else None
        self._load_models()

    def _load_models(self) -> None:
        path = self.models_path or _project_models_json()
        if path and path.is_file():
            try:
                self._load_from_json(path)
                self.source = str(path)
                self.models_path = path
                if self.models:
                    logger.debug("Loaded %d models from %s", len(self.models), path)
                    return
            except (OSError, json.JSONDecodeError, TypeError, KeyError) as e:
                logger.warning("Failed to load models.json (%s); using builtin fallback", e)

        self._load_builtin_fallback()
        self.source = "builtin"

    def _load_from_json(self, path: Path) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise TypeError("models.json must be a JSON array")

        self.models.clear()
        # Mark first model per provider as "latest" for simple UI flag
        seen_providers: set[str] = set()
        for entry in data:
            if not isinstance(entry, dict) or "name" not in entry:
                continue
            name = entry["name"]
            provider = entry.get("provider", "unknown")
            is_latest = provider not in seen_providers
            seen_providers.add(provider)
            self.models[name] = ModelInfo(
                name=name,
                provider=provider,
                model_id=entry.get("model_id", name),
                base_url=entry.get("base_url"),
                api_key_env=entry.get("api_key_env"),
                context_window=int(entry.get("context_window", 128000)),
                is_latest=bool(entry.get("is_latest", is_latest)),
                supports_tools=bool(entry.get("supports_tools", True)),
                strengths=str(entry.get("strengths", "")),
                cost_per_1k_tokens=float(entry.get("cost_per_1k_tokens", 0.0)),
                latency_tier=int(entry.get("latency_tier", 2)),
                extra={
                    k: v
                    for k, v in entry.items()
                    if k
                    not in {
                        "name",
                        "provider",
                        "model_id",
                        "base_url",
                        "api_key_env",
                        "context_window",
                        "is_latest",
                        "supports_tools",
                        "strengths",
                        "cost_per_1k_tokens",
                        "latency_tier",
                    }
                },
            )

    def _load_builtin_fallback(self) -> None:
        """Minimal set so mock mode works without models.json."""
        builtins = [
            ("grok-3", "xai", "grok-3", "https://api.x.ai/v1", "XAI_API_KEY", True),
            ("gpt-4o", "openai", "gpt-4o", "https://api.openai.com/v1", "OPENAI_API_KEY", True),
            (
                "claude-4-sonnet",
                "anthropic",
                "claude-3-5-sonnet-20241022",
                None,
                "ANTHROPIC_API_KEY",
                True,
            ),
            (
                "gemini-2.0-flash",
                "google",
                "gemini-2.0-flash",
                None,
                "GOOGLE_API_KEY",
                True,
            ),
            (
                "deepseek-coder",
                "deepseek",
                "deepseek-coder",
                "https://api.deepseek.com/v1",
                "DEEPSEEK_API_KEY",
                True,
            ),
        ]
        self.models.clear()
        for name, provider, model_id, base_url, env, latest in builtins:
            self._add_model(name, provider, model_id, base_url, env, is_latest=latest)

    def _add_model(
        self,
        name: str,
        provider: str,
        model_id: str,
        base_url: Optional[str],
        api_key_env: Optional[str],
        context_window: int = 128000,
        is_latest: bool = False,
    ) -> None:
        self.models[name] = ModelInfo(
            name=name,
            provider=provider,
            model_id=model_id,
            base_url=base_url,
            api_key_env=api_key_env,
            context_window=context_window,
            is_latest=is_latest,
        )

    def get_model(self, name: str) -> Optional[ModelInfo]:
        return self.models.get(name)

    def get_latest_models(self) -> List[ModelInfo]:
        return [m for m in self.models.values() if m.is_latest]

    def list_all_models(self) -> List[str]:
        return list(self.models.keys())

    def get_models_by_provider(self, provider: str) -> List[ModelInfo]:
        return [m for m in self.models.values() if m.provider == provider]

    def refresh(self, models_path: Optional[str | Path] = None) -> int:
        """Reload models from JSON path (or previous/default path)."""
        if models_path:
            self.models_path = Path(models_path)
        self._load_models()
        return len(self.models)

    def register_model(
        self,
        name: str,
        provider: str,
        model_id: str,
        base_url: Optional[str] = None,
        api_key_env: Optional[str] = None,
        **kwargs: Any,
    ) -> ModelInfo:
        """Register or overwrite a model (incl. dual CLI-as-model entries)."""
        info = ModelInfo(
            name=name,
            provider=provider,
            model_id=model_id,
            base_url=base_url,
            api_key_env=api_key_env,
            context_window=int(kwargs.get("context_window", 128000)),
            is_latest=bool(kwargs.get("is_latest", False)),
            supports_tools=bool(kwargs.get("supports_tools", True)),
            strengths=str(kwargs.get("strengths", "")),
            cost_per_1k_tokens=float(kwargs.get("cost_per_1k_tokens", 0.0)),
            latency_tier=int(kwargs.get("latency_tier", 2)),
            extra=dict(kwargs.get("extra") or {}),
        )
        self.models[name] = info
        return info

    def register_external_clis_as_models(self) -> List[str]:
        """
        Dual registration: external AI CLIs appear as synthetic models (G7).
        """
        try:
            from .external_cli import ExternalCLIRegistry
        except Exception:  # noqa: BLE001
            return []
        reg = ExternalCLIRegistry()
        added: List[str] = []
        for d in reg.discover():
            name = f"cli:{d['name']}"
            self.register_model(
                name=name,
                provider="external_cli",
                model_id=d["name"],
                base_url=None,
                api_key_env=None,
                strengths="external CLI worker",
                cost_per_1k_tokens=0.0,
                latency_tier=3,
                is_latest=bool(d.get("available")),
                extra={
                    "external_cli": True,
                    "available": d.get("available"),
                    "path": d.get("path"),
                    "modifies_files": d.get("modifies_files"),
                },
            )
            added.append(name)
        return added
