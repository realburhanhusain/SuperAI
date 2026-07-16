"""
Discovery for first-run and ongoing detection (Phase 8 / Track I + H).

Detects external AI CLIs and environment signals for models.
"""

from __future__ import annotations

import os
import shutil
from typing import Any, Dict, List

from .external_cli import ExternalCLIRegistry
from .model_registry import ModelRegistry


def discover_environment() -> Dict[str, Any]:
    cli_reg = ExternalCLIRegistry()
    clis = cli_reg.discover()
    registry = ModelRegistry()

    api_keys = {
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
        "XAI_API_KEY": bool(os.getenv("XAI_API_KEY")),
        "GOOGLE_API_KEY": bool(os.getenv("GOOGLE_API_KEY")),
        "DEEPSEEK_API_KEY": bool(os.getenv("DEEPSEEK_API_KEY")),
        "GROQ_API_KEY": bool(os.getenv("GROQ_API_KEY")),
        "TOGETHER_API_KEY": bool(os.getenv("TOGETHER_API_KEY")),
        "DASHSCOPE_API_KEY": bool(os.getenv("DASHSCOPE_API_KEY")),
        "MISTRAL_API_KEY": bool(os.getenv("MISTRAL_API_KEY")),
        "MOONSHOT_API_KEY": bool(os.getenv("MOONSHOT_API_KEY")),
        "ZHIPU_API_KEY": bool(os.getenv("ZHIPU_API_KEY")),
        "MINIMAX_API_KEY": bool(os.getenv("MINIMAX_API_KEY")),
        "NVIDIA_API_KEY": bool(os.getenv("NVIDIA_API_KEY")),
        "OPENROUTER_API_KEY": bool(os.getenv("OPENROUTER_API_KEY")),
        "FIREWORKS_API_KEY": bool(os.getenv("FIREWORKS_API_KEY")),
        "SILICONFLOW_API_KEY": bool(os.getenv("SILICONFLOW_API_KEY")),
    }
    # Merge any remaining catalog envs
    try:
        from .provider_catalog import api_key_env_names

        for env_name in api_key_env_names():
            if env_name not in api_keys:
                api_keys[env_name] = bool(os.getenv(env_name))
    except Exception:
        pass

    ollama = shutil.which("ollama") is not None
    rclone = shutil.which("rclone") is not None

    # Soft Ollama tag count (no crash if down)
    ollama_tags = 0
    try:
        from .model_discovery import list_ollama_tags

        ollama_tags = len(list_ollama_tags())
    except Exception:
        ollama_tags = 0

    return {
        "clis": clis,
        "clis_available": [c["name"] for c in clis if c["available"]],
        "models_registered": len(registry.list_all_models()),
        "model_source": registry.source,
        "api_keys_present": api_keys,
        "ollama_on_path": ollama,
        "ollama_tags": ollama_tags,
        "rclone_on_path": rclone,
        "mock_recommended": not any(api_keys.values()) and not ollama,
    }
