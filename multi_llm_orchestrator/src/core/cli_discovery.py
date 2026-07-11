"""
SuperAI CLI & Model Discovery Module

Detects installed CLIs (Claude Code, Gemini CLI, Codex, Aider, Ollama, etc.)
and attempts to discover available models/commands for each.
"""

import shutil
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Any

class CLIDiscovery:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.discovered_file = self.config_dir / "discovered_clis.json"

    def is_command_available(self, command: str) -> bool:
        """Check if a command exists in PATH."""
        return shutil.which(command) is not None

    def discover_claude_code(self) -> Dict[str, Any]:
        """Detect Claude Code CLI and its capabilities."""
        if not self.is_command_available("claude"):
            return {"available": False}

        info = {
            "available": True,
            "command": "claude",
            "models": [],
            "features": ["file_edit", "run_command", "sub_agents", "git"]
        }

        # Try to get model list if possible
        try:
            result = subprocess.run(
                ["claude", "models", "list"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                info["models"] = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        except Exception:
            pass

        return info

    def discover_gemini_cli(self) -> Dict[str, Any]:
        if not self.is_command_available("gemini"):
            return {"available": False}

        return {
            "available": True,
            "command": "gemini",
            "models": ["gemini-2.5-pro", "gemini-2.0-flash"],
            "features": ["code_generation", "file_ops", "web_search"]
        }

    def discover_codex_or_openai(self) -> Dict[str, Any]:
        if self.is_command_available("codex"):
            return {"available": True, "command": "codex", "models": ["codex"], "features": ["code_completion"]}
        if self.is_command_available("openai"):
            return {"available": True, "command": "openai", "models": [], "features": ["chat", "completions"]}
        return {"available": False}

    def discover_ollama(self) -> Dict[str, Any]:
        if not self.is_command_available("ollama"):
            return {"available": False}

        info = {"available": True, "command": "ollama", "models": [], "features": ["local_models"]}

        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")[1:]  # Skip header
                info["models"] = [line.split()[0] for line in lines if line.strip()]
        except Exception:
            pass

        return info

    def discover_all(self) -> Dict[str, Any]:
        """Run discovery for all known AI CLIs."""
        discovered = {
            "claude_code": self.discover_claude_code(),
            "gemini_cli": self.discover_gemini_cli(),
            "codex_openai": self.discover_codex_or_openai(),
            "ollama": self.discover_ollama(),
            "github_cli": self.discover_github_cli(),
            "cursor_cli": self.discover_cursor_cli(),
            "aider": self.discover_aider(),
            "antigravity": self.discover_antigravity(),
            "junie": self.discover_junie(),
            "grok_cli": self.discover_grok_cli(),
            "nvidia_cli": self.discover_nvidia_cli(),
            "blackbox_cli": self.discover_blackbox_cli(),
            "continue": self.discover_continue(),
            "lm_studio": self.discover_lm_studio(),
            "github_copilot_cli": self.discover_github_copilot_cli(),
            "amazon_q": self.discover_amazon_q(),
            "cline": self.discover_cline(),
            "roo": self.discover_roo(),
            "warp_ai": self.discover_warp_ai(),
            "cody": self.discover_cody(),
            "tabnine": self.discover_tabnine(),
            "devgpt": self.discover_devgpt(),
            "sweep": self.discover_sweep(),
            "opendevin": self.discover_opendevin(),
        }

        # Save to config file
        with open(self.discovered_file, "w") as f:
            json.dump(discovered, f, indent=2)

        return discovered

    def get_discovered_clis(self) -> Dict[str, Any]:
        """Load previously discovered CLIs."""
        if self.discovered_file.exists():
            with open(self.discovered_file) as f:
                return json.load(f)
        return {}


def discover_and_update_config():
    """Main function to run discovery and update config."""
    discovery = CLIDiscovery()
    result = discovery.discover_all()
    print("Discovered CLIs and models:")
    print(json.dumps(result, indent=2))
    return result
