"""
Constitution / system rules injection (N14).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .workspace import workspace_root


def constitution_paths() -> list[Path]:
    home = Path.home() / ".superai" / "constitution.md"
    proj = workspace_root() / ".superai" / "constitution.md"
    return [proj, home]


def load_constitution() -> str:
    for p in constitution_paths():
        if p.is_file():
            try:
                return p.read_text(encoding="utf-8")[:8000]
            except OSError:
                continue
    # Default minimal constitution
    return (
        "# SuperAI Constitution\n\n"
        "- Prefer local mock mode unless API keys are configured.\n"
        "- Never exfiltrate secrets; treat user data as private.\n"
        "- Require human approval for file-modifying external tools.\n"
        "- Stay within SUPERAI_WORKSPACE for edits.\n"
        "- Prefer clear, minimal, correct solutions.\n"
    )


def ensure_default_constitution() -> Path:
    path = Path.home() / ".superai" / "constitution.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(load_constitution(), encoding="utf-8")
    return path


def format_for_prompt(max_chars: int = 2000) -> str:
    text = load_constitution().strip()
    if len(text) > max_chars:
        text = text[: max_chars - 20] + "\n…[truncated]"
    return f"## Constitution / rules\n{text}\n"
