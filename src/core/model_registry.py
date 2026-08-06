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
    source_file: str = "builtin"
    extra: Dict[str, Any] = field(default_factory=dict)


def _project_models_json() -> Optional[Path]:
    """Locate models.json: user override first, then project, then cwd."""
    # src/core/model_registry.py → repo root is parents[2]
    here = Path(__file__).resolve()
    candidates = [
        Path.home() / ".superai" / "config" / "models.json",  # refresh writes here
        here.parents[2] / "config" / "models.json",  # repo root
        here.parents[1] / "config" / "models.json",  # src/
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
        self.models.clear()
        self._load_builtin_fallback()
        
        if self.models_path is not None:
            path = Path(self.models_path)
            if path.is_file():
                try:
                    self._load_from_json(path)
                    self.source = str(path)
                    return
                except (OSError, json.JSONDecodeError, TypeError, KeyError) as e:
                    logger.warning("Failed to load models.json (%s)", e)
            self.source = "builtin"
            return

        here = Path(__file__).resolve()
        candidates = [
            Path.cwd() / "config" / "models.json",
            here.parents[1] / "config" / "models.json",  # src/
            here.parents[2] / "config" / "models.json",  # repo root
            Path.home() / ".superai" / "config" / "models.json",  # override
        ]
        
        loaded_any = False
        # Load from lowest to highest precedence, overwriting
        for path in candidates:
            if path.is_file():
                try:
                    self._load_from_json(path)
                    loaded_any = True
                except (OSError, json.JSONDecodeError, TypeError, KeyError) as e:
                    logger.warning("Failed to load models.json (%s)", e)
                    
        self.source = "merged" if loaded_any else "builtin"

    def _load_from_json(self, path: Path) -> None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise TypeError("models.json must be a JSON array")

        # Mark first model per provider as "latest" for simple UI flag
        # (Since we are merging, we might see a provider again, but if it's the first time in this file, we can trust the file's intent or rely on what's already there)
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
                source_file=str(path),
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

    def sync_cliproxy_models(self, discovered_models: List[Any]) -> Dict[str, Any]:
        """
        Bidirectional Auto-Sync: import or update models discovered from CLIProxyAPI
        into ~/.superai/config/models.json and refresh active registry.
        """
        from pathlib import Path
        import json

        user_models_path = Path.home() / ".superai" / "config" / "models.json"
        user_models_path.parent.mkdir(parents=True, exist_ok=True)

        existing_data: List[Dict[str, Any]] = []
        if user_models_path.is_file():
            try:
                with open(user_models_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        existing_data = content
            except Exception as e:
                logger.warning("Could not parse existing user models.json: %s", e)

        existing_by_name = {m.get("name"): m for m in existing_data if isinstance(m, dict) and "name" in m}

        added_count = 0
        updated_count = 0
        synced_names: List[str] = []

        for item in discovered_models:
            if isinstance(item, str):
                mid = item.strip()
            elif isinstance(item, dict):
                mid = str(item.get("id") or item.get("name") or "").strip()
            else:
                continue

            if not mid:
                continue

            name = mid if mid.startswith("cliproxy:") else f"cliproxy:{mid}"
            synced_names.append(name)

            # Infer capabilities and context window
            lower_id = mid.lower()
            context_window = 128000
            cost_per_1k = 0.01
            strengths = "general"
            latency_tier = 2

            if "claude" in lower_id:
                context_window = 200000
                cost_per_1k = 0.015
                strengths = "coding, reasoning, analysis"
                latency_tier = 2
            elif "gpt" in lower_id or "o1" in lower_id or "o3" in lower_id or "codex" in lower_id:
                context_window = 128000
                cost_per_1k = 0.02
                strengths = "coding, reasoning, tools"
                latency_tier = 2
            elif "gemini" in lower_id:
                context_window = 1000000
                cost_per_1k = 0.005
                strengths = "multimodal, long-context"
                latency_tier = 1
            elif "deepseek" in lower_id:
                context_window = 64000
                cost_per_1k = 0.002
                strengths = "coding, math"
                latency_tier = 2
            elif "grok" in lower_id or "xai" in lower_id:
                context_window = 131072
                cost_per_1k = 0.01
                strengths = "realtime, reasoning"
                latency_tier = 2
            elif "kimi" in lower_id or "moonshot" in lower_id:
                context_window = 128000
                cost_per_1k = 0.008
                strengths = "long-context, Chinese, reasoning"
                latency_tier = 2

            if name in existing_by_name:
                row = existing_by_name[name]
                # Preserve user customizations if present
                row.setdefault("provider", "cliproxy")
                row.setdefault("model_id", mid)
                row.setdefault("context_window", context_window)
                row.setdefault("cost_per_1k_tokens", cost_per_1k)
                row.setdefault("strengths", strengths)
                row.setdefault("supports_tools", True)
                row.setdefault("latency_tier", latency_tier)
                updated_count += 1
            else:
                new_row = {
                    "name": name,
                    "provider": "cliproxy",
                    "model_id": mid,
                    "context_window": context_window,
                    "is_latest": False,
                    "supports_tools": True,
                    "strengths": strengths,
                    "cost_per_1k_tokens": cost_per_1k,
                    "latency_tier": latency_tier,
                }
                existing_data.append(new_row)
                existing_by_name[name] = new_row
                added_count += 1

        if added_count > 0 or updated_count > 0:
            try:
                from .config import atomic_write_with_backup
                backups_dir = Path.home() / ".superai" / "backups"
                atomic_write_with_backup(user_models_path, existing_data, backups_dir)
            except Exception as e:
                # Direct fallback write
                with open(user_models_path, "w", encoding="utf-8") as f:
                    json.dump(existing_data, f, indent=2)

            self.refresh()

        return {
            "ok": True,
            "added": added_count,
            "updated": updated_count,
            "synced_models": synced_names,
            "total_registered": len(self.models),
        }

