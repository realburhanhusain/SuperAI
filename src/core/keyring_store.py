"""
OS keyring / secure secret store (M10).

Uses `keyring` package when installed; falls back to restricted file under
~/.superai/secrets/ with 0600 permissions.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Optional

SERVICE = "superai"

try:
    import keyring  # type: ignore

    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False


class SecretStore:
    def __init__(self, fallback_dir: Optional[Path] = None):
        self.fallback_dir = Path(
            fallback_dir or (Path.home() / ".superai" / "secrets")
        )
        self.fallback_dir.mkdir(parents=True, exist_ok=True)
        self.file = self.fallback_dir / "store.json"

    def set(self, name: str, value: str) -> Dict[str, str]:
        if HAS_KEYRING:
            keyring.set_password(SERVICE, name, value)
            return {"backend": "keyring", "name": name}
        data = self._load_file()
        data[name] = value
        self._save_file(data)
        return {"backend": "file", "name": name, "path": str(self.file)}

    def get(self, name: str) -> Optional[str]:
        if HAS_KEYRING:
            try:
                return keyring.get_password(SERVICE, name)
            except Exception:
                pass
        return self._load_file().get(name)

    def delete(self, name: str) -> bool:
        if HAS_KEYRING:
            try:
                keyring.delete_password(SERVICE, name)
                return True
            except Exception:
                pass
        data = self._load_file()
        if name in data:
            del data[name]
            self._save_file(data)
            return True
        return False

    def list_names(self) -> Dict[str, str]:
        names = list(self._load_file().keys())
        return {
            "backend": "keyring" if HAS_KEYRING else "file",
            "names": names,
        }

    def _load_file(self) -> Dict[str, str]:
        if self.file.exists():
            try:
                return json.loads(self.file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return {}

    def _save_file(self, data: Dict[str, str]) -> None:
        self.file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            os.chmod(self.file, 0o600)
        except OSError:
            pass

    def inject_env(self, mapping: Optional[Dict[str, str]] = None) -> int:
        """
        Load secrets into process env.
        mapping: secret_name -> env var name (default same name).
        """
        mapping = mapping or {}
        n = 0
        data = self._load_file()
        keys = set(data.keys())
        if HAS_KEYRING:
            # common names
            for name in list(keys) + [
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "XAI_API_KEY",
                "GOOGLE_API_KEY",
            ]:
                val = self.get(name)
                if val:
                    env_name = mapping.get(name, name)
                    if not os.getenv(env_name):
                        os.environ[env_name] = val
                        n += 1
        else:
            for name, val in data.items():
                env_name = mapping.get(name, name)
                if val and not os.getenv(env_name):
                    os.environ[env_name] = val
                    n += 1
        return n
