"""
Plugin marketplace / registry skeleton (Track J).

Local-first catalog of plugins (adapters, skills, messengers, tools).
Plugins are JSON manifests under ~/.superai/plugins/ + bundled defaults.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


BUILTIN_PLUGINS: List[Dict[str, Any]] = [
    {
        "id": "core.council",
        "name": "LLM Council",
        "version": "0.1.0",
        "category": "reasoning",
        "description": "Multi-model voting council (majority|supervisor|weighted)",
        "entry": "superai.core.council",
        "status": "installed",
        "source": "builtin",
    },
    {
        "id": "core.databao",
        "name": "Databao Adapter",
        "version": "0.1.0",
        "category": "data",
        "description": "NL → SQL analytics with Vega chart specs",
        "entry": "superai.core.databao_adapter",
        "status": "installed",
        "source": "builtin",
    },
    {
        "id": "core.messengers",
        "name": "Messenger Bus",
        "version": "0.1.0",
        "category": "messaging",
        "description": "Telegram / Slack / webhook / file channels",
        "entry": "superai.core.messengers",
        "status": "installed",
        "source": "builtin",
    },
    {
        "id": "core.memory",
        "name": "Memory Palace",
        "version": "0.1.0",
        "category": "memory",
        "description": "Semantic memory, wings, embeddings",
        "entry": "superai.core.memory_palace",
        "status": "installed",
        "source": "builtin",
    },
    {
        "id": "core.bandit",
        "name": "Bandit Router",
        "version": "0.1.0",
        "category": "routing",
        "description": "Epsilon-greedy contextual bandit for model selection",
        "entry": "superai.core.bandit_router",
        "status": "installed",
        "source": "builtin",
    },
    {
        "id": "marketplace.example",
        "name": "Example Third-Party Plugin",
        "version": "0.0.1",
        "category": "example",
        "description": "Template for external plugin manifests",
        "entry": None,
        "status": "available",
        "source": "catalog",
        "install_hint": "Copy a plugin.json into ~/.superai/plugins/<id>/",
    },
]


class PluginRegistry:
    """Local plugin catalog + install/enable/disable lifecycle."""

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root or (Path.home() / ".superai" / "plugins"))
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "registry_state.json"
        self._state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return {"enabled": {}, "installed": {}, "updated_at": None}

    def save_state(self) -> None:
        self._state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.state_path.write_text(
            json.dumps(self._state, indent=2), encoding="utf-8"
        )

    def _scan_local(self) -> List[Dict[str, Any]]:
        found: List[Dict[str, Any]] = []
        if not self.root.exists():
            return found
        for child in sorted(self.root.iterdir()):
            if not child.is_dir():
                continue
            manifest = child / "plugin.json"
            if not manifest.exists():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            data.setdefault("id", child.name)
            data.setdefault("source", "local")
            data.setdefault("status", "installed")
            data["path"] = str(child)
            found.append(data)
        return found

    def list_plugins(
        self,
        category: Optional[str] = None,
        include_available: bool = True,
    ) -> List[Dict[str, Any]]:
        by_id: Dict[str, Dict[str, Any]] = {}
        for p in BUILTIN_PLUGINS:
            by_id[p["id"]] = dict(p)
        for p in self._scan_local():
            by_id[p["id"]] = p
        # Merge enable state
        out = []
        for pid, p in by_id.items():
            enabled = self._state.get("enabled", {}).get(pid)
            if enabled is None:
                enabled = p.get("status") == "installed"
            p = dict(p)
            p["enabled"] = bool(enabled)
            if p.get("status") == "available" and not include_available:
                continue
            if category and p.get("category") != category:
                continue
            out.append(p)
        out.sort(key=lambda x: (x.get("category") or "", x.get("id") or ""))
        return out

    def get(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        for p in self.list_plugins(include_available=True):
            if p.get("id") == plugin_id:
                return p
        return None

    def enable(self, plugin_id: str) -> Dict[str, Any]:
        p = self.get(plugin_id)
        if not p:
            raise KeyError(f"Unknown plugin: {plugin_id}")
        if p.get("status") == "available" and p.get("source") == "catalog":
            raise ValueError(
                f"Plugin {plugin_id} is catalog-only; install a local manifest first"
            )
        self._state.setdefault("enabled", {})[plugin_id] = True
        self.save_state()
        return {"ok": True, "id": plugin_id, "enabled": True}

    def disable(self, plugin_id: str) -> Dict[str, Any]:
        p = self.get(plugin_id)
        if not p:
            raise KeyError(f"Unknown plugin: {plugin_id}")
        self._state.setdefault("enabled", {})[plugin_id] = False
        self.save_state()
        return {"ok": True, "id": plugin_id, "enabled": False}

    def install_manifest(
        self,
        manifest: Dict[str, Any],
        plugin_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Install (write) a plugin manifest under ~/.superai/plugins/<id>/."""
        pid = plugin_id or manifest.get("id")
        if not pid:
            raise ValueError("manifest must include id")
        dest = self.root / str(pid)
        dest.mkdir(parents=True, exist_ok=True)
        data = dict(manifest)
        data["id"] = pid
        data.setdefault("status", "installed")
        data.setdefault("source", "local")
        data.setdefault("installed_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        (dest / "plugin.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )
        self._state.setdefault("installed", {})[pid] = str(dest)
        self._state.setdefault("enabled", {})[pid] = True
        self.save_state()
        return data

    def install_from_path(self, path: Path) -> Dict[str, Any]:
        """Install from a plugin.json file or directory containing one."""
        p = Path(path)
        if p.is_dir():
            manifest_path = p / "plugin.json"
        else:
            manifest_path = p
        if not manifest_path.exists():
            raise FileNotFoundError(f"No plugin.json at {path}")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("plugin.json must be an object")
        installed = self.install_manifest(data)
        # Optionally copy sibling files
        if p.is_dir():
            dest = self.root / installed["id"]
            for item in p.iterdir():
                if item.name == "plugin.json":
                    continue
                target = dest / item.name
                if item.is_file():
                    shutil.copy2(item, target)
        return installed

    def uninstall(self, plugin_id: str) -> Dict[str, Any]:
        """Remove a local (non-builtin) plugin directory."""
        if any(b["id"] == plugin_id and b["source"] == "builtin" for b in BUILTIN_PLUGINS):
            # builtins cannot be uninstalled; only disable
            return self.disable(plugin_id)
        dest = self.root / plugin_id
        if dest.exists() and dest.is_dir():
            shutil.rmtree(dest)
        self._state.get("installed", {}).pop(plugin_id, None)
        self._state.get("enabled", {}).pop(plugin_id, None)
        self.save_state()
        return {"ok": True, "id": plugin_id, "removed": True}

    def search(self, query: str) -> List[Dict[str, Any]]:
        q = (query or "").lower().strip()
        if not q:
            return self.list_plugins()
        results = []
        for p in self.list_plugins(include_available=True):
            blob = " ".join(
                str(p.get(k) or "")
                for k in ("id", "name", "description", "category")
            ).lower()
            if q in blob:
                results.append(p)
        return results

    def marketplace_summary(self) -> Dict[str, Any]:
        plugins = self.list_plugins(include_available=True)
        by_cat: Dict[str, int] = {}
        for p in plugins:
            cat = p.get("category") or "other"
            by_cat[cat] = by_cat.get(cat, 0) + 1
        return {
            "total": len(plugins),
            "installed": sum(1 for p in plugins if p.get("status") == "installed"),
            "available": sum(1 for p in plugins if p.get("status") == "available"),
            "enabled": sum(1 for p in plugins if p.get("enabled")),
            "by_category": by_cat,
            "root": str(self.root),
        }
