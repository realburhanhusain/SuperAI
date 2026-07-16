"""
Central catalog of LLM providers (commercial + open-weight + local).

Single source of truth for OpenAI-compatible base URLs and API key env names.
ModelCaller and discovery import from here — do not duplicate maps.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


# OpenAI-compatible chat/completions providers
# kind: cloud | local | gateway
OPENAI_COMPAT_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "env": "OPENAI_API_KEY",
        "kind": "cloud",
    },
    "xai": {
        "label": "xAI Grok",
        "base_url": "https://api.x.ai/v1",
        "env": "XAI_API_KEY",
        "kind": "cloud",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "env": "DEEPSEEK_API_KEY",
        "kind": "cloud",
        "open_weight_available": True,
    },
    "qwen": {
        "label": "Qwen / DashScope",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "env": "DASHSCOPE_API_KEY",
        "kind": "cloud",
        "open_weight_available": True,
    },
    "groq": {
        "label": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "env": "GROQ_API_KEY",
        "kind": "cloud",
        "open_weight_available": True,
    },
    "together": {
        "label": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "env": "TOGETHER_API_KEY",
        "kind": "cloud",
        "open_weight_available": True,
    },
    "mistral": {
        "label": "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "env": "MISTRAL_API_KEY",
        "kind": "cloud",
        "open_weight_available": True,
    },
    "moonshot": {
        "label": "Moonshot Kimi",
        "base_url": "https://api.moonshot.cn/v1",
        "env": "MOONSHOT_API_KEY",
        "kind": "cloud",
        "open_weight_available": True,
        "aliases": ["kimi"],
    },
    "zhipu": {
        "label": "Zhipu GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "env": "ZHIPU_API_KEY",
        "kind": "cloud",
        "open_weight_available": True,
        "aliases": ["glm"],
    },
    "minimax": {
        "label": "MiniMax",
        "base_url": "https://api.minimax.chat/v1",
        "env": "MINIMAX_API_KEY",
        "kind": "cloud",
        "open_weight_available": True,
    },
    "nvidia": {
        "label": "NVIDIA NIM / API Catalog",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "env": "NVIDIA_API_KEY",
        "kind": "cloud",
        "open_weight_available": True,
        "notes": "NVIDIA-hosted models + open-weight on NVIDIA infra",
    },
    "openrouter": {
        "label": "OpenRouter (multi-vendor gateway)",
        "base_url": "https://openrouter.ai/api/v1",
        "env": "OPENROUTER_API_KEY",
        "kind": "gateway",
        "open_weight_available": True,
        "notes": "Route to many vendors with one key",
    },
    "fireworks": {
        "label": "Fireworks AI",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "env": "FIREWORKS_API_KEY",
        "kind": "cloud",
        "open_weight_available": True,
    },
    "siliconflow": {
        "label": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "env": "SILICONFLOW_API_KEY",
        "kind": "cloud",
        "open_weight_available": True,
    },
    "lmstudio": {
        "label": "LM Studio (local)",
        "base_url": "http://localhost:1234/v1",
        "env": "LMSTUDIO_API_KEY",  # often unused; dummy ok
        "kind": "local",
        "open_weight_available": True,
        "allow_empty_key": True,
        "default_key": "lm-studio",
    },
    "vllm": {
        "label": "vLLM OpenAI server (local/remote)",
        "base_url": "http://localhost:8000/v1",
        "env": "VLLM_API_KEY",
        "kind": "local",
        "open_weight_available": True,
        "allow_empty_key": True,
        "default_key": "vllm",
    },
    "ollama_openai": {
        "label": "Ollama OpenAI-compatible (/v1)",
        "base_url": "http://localhost:11434/v1",
        "env": "OLLAMA_API_KEY",
        "kind": "local",
        "open_weight_available": True,
        "allow_empty_key": True,
        "default_key": "ollama",
    },
}

# Native (non OpenAI-compat) providers handled specially in ModelCaller
NATIVE_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "anthropic": {"label": "Anthropic Claude", "env": "ANTHROPIC_API_KEY", "kind": "cloud"},
    "google": {"label": "Google Gemini", "env": "GOOGLE_API_KEY", "kind": "cloud"},
    "ollama": {
        "label": "Ollama (native generate API)",
        "env": None,
        "kind": "local",
        "base_url": "http://localhost:11434",
        "open_weight_available": True,
    },
    "external_cli": {
        "label": "External AI CLIs",
        "env": None,
        "kind": "cli",
    },
}

# Name substring → provider for resolution
PROVIDER_HINTS: Dict[str, str] = {
    "grok": "xai",
    "claude": "anthropic",
    "gpt": "openai",
    "o3": "openai",
    "o1": "openai",
    "o4": "openai",
    "gemini": "google",
    "gemma": "ollama",  # default local; can override via registry
    "deepseek": "deepseek",
    "qwen": "qwen",
    "llama": "groq",
    "mistral": "mistral",
    "kimi": "moonshot",
    "moonshot": "moonshot",
    "glm": "zhipu",
    "zhipu": "zhipu",
    "minimax": "minimax",
    "nemotron": "nvidia",
    "nvidia": "nvidia",
    "openrouter": "openrouter",
}


def resolve_compat_provider(name: str) -> str:
    """Normalize aliases (meta→together, kimi→moonshot)."""
    n = (name or "").lower().strip()
    aliases = {
        "meta": "together",
        "kimi": "moonshot",
        "glm": "zhipu",
        "dashscope": "qwen",
    }
    n = aliases.get(n, n)
    return n


def get_openai_compat_config(provider: str) -> Optional[Dict[str, Any]]:
    p = resolve_compat_provider(provider)
    return OPENAI_COMPAT_PROVIDERS.get(p)


def list_providers(*, include_native: bool = True) -> List[Dict[str, Any]]:
    """UI/doctor listing of all known providers."""
    rows: List[Dict[str, Any]] = []
    for pid, cfg in OPENAI_COMPAT_PROVIDERS.items():
        env = cfg.get("env")
        key_set = bool(env and (os.getenv(env) or "").strip())
        if cfg.get("allow_empty_key") and cfg.get("kind") == "local":
            key_set = True  # local often needs no real key
        rows.append(
            {
                "id": pid,
                "label": cfg.get("label"),
                "kind": cfg.get("kind"),
                "base_url": cfg.get("base_url"),
                "api_key_env": env,
                "key_configured": key_set,
                "open_weight_available": bool(cfg.get("open_weight_available")),
                "protocol": "openai_compatible",
                "notes": cfg.get("notes") or "",
            }
        )
    if include_native:
        for pid, cfg in NATIVE_PROVIDERS.items():
            env = cfg.get("env")
            key_set = bool(env and (os.getenv(env) or "").strip()) if env else True
            rows.append(
                {
                    "id": pid,
                    "label": cfg.get("label"),
                    "kind": cfg.get("kind"),
                    "base_url": cfg.get("base_url"),
                    "api_key_env": env,
                    "key_configured": key_set,
                    "open_weight_available": bool(cfg.get("open_weight_available")),
                    "protocol": "native" if pid != "external_cli" else "cli",
                    "notes": cfg.get("notes") or "",
                }
            )
    return rows


def api_key_env_names() -> List[str]:
    names = []
    for cfg in OPENAI_COMPAT_PROVIDERS.values():
        e = cfg.get("env")
        if e and e not in names:
            names.append(e)
    for cfg in NATIVE_PROVIDERS.values():
        e = cfg.get("env")
        if e and e not in names:
            names.append(e)
    return names
