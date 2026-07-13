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
    }

    ollama = shutil.which("ollama") is not None
    rclone = shutil.which("rclone") is not None

    return {
        "clis": clis,
        "clis_available": [c["name"] for c in clis if c["available"]],
        "models_registered": len(registry.list_all_models()),
        "model_source": registry.source,
        "api_keys_present": api_keys,
        "ollama_on_path": ollama,
        "rclone_on_path": rclone,
        "mock_recommended": not any(api_keys.values()) and not ollama,
    }
