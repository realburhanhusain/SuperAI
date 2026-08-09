from typing import List

import json
from pathlib import Path
from typing import List, Dict, Optional

class KeyPool:
    """A pool of API keys that can be rotated when rate limits (e.g. 429) are hit."""
    
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.path = Path(storage_path)
        else:
            self.path = Path.home() / ".superai" / "config" / "key_pools.json"
            
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.pools: Dict[str, List[str]] = {}
        self.indexes: Dict[str, int] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        self.pools = data.get("pools", {})
                        self.indexes = data.get("indexes", {})
            except Exception:
                pass
                
    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"pools": self.pools, "indexes": self.indexes}, f, indent=2)

    def set_keys(self, name: str, keys: List[str]):
        """Set the pool of keys for a given name (e.g., env_name or provider)."""
        self._load()
        if not keys:
            if name in self.pools:
                del self.pools[name]
        else:
            self.pools[name] = list(keys)
            if name not in self.indexes or self.indexes[name] >= len(keys):
                self.indexes[name] = 0
        self._save()

    def get_key(self, name: str, fallback_env: Optional[str] = None) -> Optional[str]:
        """Get the currently active API key for a pool, falling back to os.getenv."""
        self._load()
        if name in self.pools and self.pools[name]:
            idx = self.indexes.get(name, 0)
            if idx >= len(self.pools[name]):
                idx = 0
                self.indexes[name] = 0
                self._save()
            return self.pools[name][idx]
            
        if fallback_env:
            import os
            return (os.getenv(fallback_env) or "").strip()
        return None

    def rotate(self, name: str) -> Optional[str]:
        """
        Rotate to the next key in the pool (round-robin).
        Useful when encountering HTTP 429 errors.
        Returns the new active key, or None if pool is empty.
        """
        self._load()
        if name not in self.pools or not self.pools[name]:
            return self.get_key(name)
            
        idx = self.indexes.get(name, 0)
        self.indexes[name] = (idx + 1) % len(self.pools[name])
        self._save()
        return self.get_key(name)
