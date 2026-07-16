"""
Discover inner models for external AI CLIs.

Strategy (fast + safe):
  1. Curated known models per CLI (always available offline)
  2. Map SuperAI registry models to related CLIs (provider family)
  3. Optional live probe of CLI list commands (short timeout, cached)
  4. Never hang install/tests: probes opt-in or cached
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


# Curated fallbacks when live list is unavailable
KNOWN_CLI_MODELS: Dict[str, List[str]] = {
    "gemini": [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ],
    "claude": [
        "claude-sonnet-4",
        "claude-opus-4",
        "claude-3-5-sonnet-latest",
        "claude-3-5-haiku-latest",
        "claude-3-opus-latest",
        "sonnet",
        "opus",
        "haiku",
    ],
    "grok": [
        "grok-3",
        "grok-2",
        "grok-2-latest",
        "grok-beta",
    ],
    "codex": [
        "o3",
        "o4-mini",
        "o3-mini",
        "gpt-4.1",
        "gpt-4o",
        "codex-mini-latest",
    ],
    "aider": [
        "gpt-4o",
        "gpt-4.1",
        "claude-3-5-sonnet-20241022",
        "claude-sonnet-4",
        "gemini/gemini-2.5-pro",
        "deepseek/deepseek-chat",
    ],
    "cursor": [
        "default",
        "composer",
        "gpt-4o",
        "claude-3.5-sonnet",
    ],
    "continue": ["default"],
    "cline": ["default"],
    "roo": ["default"],
}

# Optional argv after the CLI binary for live listing
MODEL_LIST_ARGV: Dict[str, List[List[str]]] = {
    "gemini": [["--help"]],  # help-only; models often need auth
    "claude": [["--help"]],
    "grok": [["--help"]],
    "codex": [["--help"], ["models"]],
    "aider": [["--list-models"], ["--help"]],
}

# Registry name/provider hints → CLI name
REGISTRY_TO_CLI: Dict[str, Sequence[str]] = {
    "gemini": ("gemini",),
    "google": ("gemini",),
    "claude": ("claude", "aider"),
    "anthropic": ("claude", "aider"),
    "grok": ("grok",),
    "xai": ("grok",),
    "gpt": ("codex", "aider", "cursor"),
    "openai": ("codex", "aider", "cursor"),
    "o3": ("codex", "aider"),
    "o4": ("codex",),
    "deepseek": ("aider",),
    "qwen": ("aider",),
}


def _cache_path() -> Path:
    return Path.home() / ".superai" / "cache" / "cli_models.json"


def _load_cache() -> Dict[str, Any]:
    p = _cache_path()
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(data: Dict[str, Any]) -> None:
    p = _cache_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _ttl_sec() -> float:
    try:
        return float(os.getenv("SUPERAI_CLI_MODELS_TTL") or 86400)
    except ValueError:
        return 86400.0


def _registry_models_for_cli(cli_name: str) -> List[str]:
    """Pull related model ids from SuperAI ModelRegistry."""
    out: List[str] = []
    try:
        from .model_registry import ModelRegistry

        reg = ModelRegistry()
        cli = (cli_name or "").lower()
        for name in reg.list_all_models():
            if str(name).startswith("cli:"):
                continue
            info = reg.get_model(name)
            if not info:
                continue
            blob = f"{name} {info.provider} {info.model_id}".lower()
            hit = False
            for key, clis in REGISTRY_TO_CLI.items():
                if key in blob and cli in clis:
                    hit = True
                    break
            if hit or cli in blob:
                mid = info.model_id or name
                if mid and mid not in out:
                    out.append(str(mid))
                if name not in out and name != mid:
                    out.append(str(name))
    except Exception:
        pass
    return out


def _parse_models_from_text(text: str) -> List[str]:
    """Heuristic extract of model-like tokens from CLI help/list output."""
    if not text:
        return []
    found: List[str] = []
    # common patterns: model ids with digits/dots/hyphens
    patterns = [
        r"\b((?:gemini|claude|grok|gpt|o\d|codex|deepseek|qwen)[a-z0-9._/-]{0,40})\b",
        r"--model[=\s]+([a-zA-Z0-9._:/-]+)",
        r"\b([a-z][a-z0-9]+(?:-[a-z0-9.]+){1,5})\b",
    ]
    low_skip = {
        "default",
        "string",
        "boolean",
        "options",
        "command",
        "prompt",
        "model",
        "models",
        "help",
        "version",
        "true",
        "false",
    }
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.I):
            tok = m.group(1).strip().strip("\"'`")
            if len(tok) < 3 or tok.lower() in low_skip:
                continue
            if tok.count(" ") > 0:
                continue
            if tok not in found:
                found.append(tok)
    return found[:40]


def _run_list_cmd(
    resolved: str, argv: List[str], *, timeout: float = 4.0
) -> str:
    try:
        proc = subprocess.run(
            [resolved, *argv],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "CI": "1", "NO_COLOR": "1", "TERM": "dumb"},
        )
        return (proc.stdout or "") + "\n" + (proc.stderr or "")
    except Exception:
        return ""


def probe_cli_models(
    cli_name: str,
    *,
    live: bool = False,
    use_cache: bool = True,
    timeout: float = 4.0,
) -> Dict[str, Any]:
    """
    Return models for one CLI.

    live=False → curated + registry only (fast)
    live=True  → also try CLI list/help commands and merge
    """
    name = (cli_name or "").strip().lower()
    from .external_cli import ExternalCLIRegistry

    reg = ExternalCLIRegistry()
    spec = reg.get(name)
    path = None
    if spec:
        for cand in [spec.command, *(spec.detects or [])]:
            path = shutil.which(cand)
            if path:
                break
    available = path is not None

    curated = list(KNOWN_CLI_MODELS.get(name) or [])
    registry = _registry_models_for_cli(name)
    live_models: List[str] = []
    source = ["curated"]
    if registry:
        source.append("registry")

    cache = _load_cache() if use_cache else {}
    cache_key = name
    entry = cache.get(cache_key) if isinstance(cache.get(cache_key), dict) else {}
    now = time.time()
    if (
        use_cache
        and entry
        and (now - float(entry.get("ts") or 0)) < _ttl_sec()
        and entry.get("models")
    ):
        live_models = list(entry.get("models") or [])
        source.append("cache")
    elif live and available and path:
        for argv in MODEL_LIST_ARGV.get(name) or [["--help"]]:
            text = _run_list_cmd(path, argv, timeout=timeout)
            parsed = _parse_models_from_text(text)
            for p in parsed:
                if p not in live_models:
                    live_models.append(p)
            if live_models:
                source.append(f"live:{' '.join(argv)}")
                break
        if live_models and use_cache:
            cache[cache_key] = {"ts": now, "models": live_models[:40], "path": path}
            _save_cache(cache)

    # Merge unique, curated first for stable UX
    merged: List[str] = []
    for group in (curated, registry, live_models):
        for m in group:
            if m and m not in merged:
                merged.append(m)

    selectors = [f"cli:{name}"] + [f"cli:{name}@{m}" for m in merged]

    return {
        "cli": name,
        "available": available,
        "path": path,
        "model_flag": list(spec.model_flag) if spec and spec.model_flag else None,
        "models": merged,
        "selectors": selectors,
        "sources": source,
        "default_role": spec.default_role if spec else "worker",
        "description": spec.description if spec else "",
    }


def list_cli_models_catalog(
    *,
    only_available: bool = True,
    live: bool = False,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Catalog of all known CLIs with their model ids and selectors."""
    from .external_cli import ExternalCLIRegistry

    reg = ExternalCLIRegistry()
    clis: List[Dict[str, Any]] = []
    all_selectors: List[str] = []
    for d in reg.discover():
        if only_available and not d.get("available"):
            continue
        info = probe_cli_models(
            d["name"], live=live, use_cache=use_cache
        )
        clis.append(info)
        all_selectors.extend(info.get("selectors") or [])

    return {
        "ok": True,
        "live": live,
        "clis": clis,
        "selectors": all_selectors,
        "counts": {
            "clis": len(clis),
            "models": sum(len(c.get("models") or []) for c in clis),
            "selectors": len(all_selectors),
        },
    }
