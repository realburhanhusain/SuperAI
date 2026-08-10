from typing import List

import json
from pathlib import Path
from typing import List, Dict, Optional
from filelock import FileLock

class KeyPool:
    """A pool of API keys that can be rotated when rate limits (e.g. 429) are hit."""
    
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.path = Path(storage_path)
        else:
            self.path = Path.home() / ".superai" / "config" / "key_pools.json"
            
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(self.path) + ".lock")
        self.pools: Dict[str, List[str]] = {}
        self.indexes: Dict[str, int] = {}
        self.exhausted_keys: Dict[str, float] = {}  # key -> timestamp when it was marked exhausted
        self.exhausted_timeout_sec = 3600  # 1 hour before re-trying an exhausted key
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
                        self.exhausted_keys = data.get("exhausted_keys", {})
            except Exception:
                pass
                
    def _save(self):
        import time
        # cleanup old exhausted keys before save
        now = time.time()
        self.exhausted_keys = {k: v for k, v in self.exhausted_keys.items() if now - v < self.exhausted_timeout_sec}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"pools": self.pools, "indexes": self.indexes, "exhausted_keys": self.exhausted_keys}, f, indent=2)

    def set_keys(self, name: str, keys: List[str]):
        """Set the pool of keys for a given name (e.g., env_name or provider)."""
        with self.lock:
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
        with self.lock:
            self._load()
            if name in self.pools and self.pools[name]:
                import time
                now = time.time()
                pool_keys = self.pools[name]
                
                # Check for an active key that isn't exhausted
                start_idx = self.indexes.get(name, 0) % len(pool_keys)
                idx = start_idx
                for _ in range(len(pool_keys)):
                    key = pool_keys[idx]
                    exhausted_time = self.exhausted_keys.get(key, 0)
                    if now - exhausted_time >= self.exhausted_timeout_sec:
                        if idx != start_idx:
                            self.indexes[name] = idx
                            self._save()
                        return key
                    idx = (idx + 1) % len(pool_keys)
                
                # If all exhausted, fallback to returning the start_idx
                return pool_keys[start_idx]
                
            if fallback_env:
                import os
                return (os.getenv(fallback_env) or "").strip()
            return None

    def mark_exhausted(self, key: str):
        """Mark a specific key as exhausted (e.g. 429 hit)."""
        import time
        with self.lock:
            self._load()
            self.exhausted_keys[key] = time.time()
            self._save()

    def rotate(self, name: str, current_key_exhausted: bool = False) -> Optional[str]:
        """
        Rotate to the next key in the pool (round-robin).
        If current_key_exhausted is True, marks the current key as exhausted.
        Returns the new active key, or None if pool is empty.
        """
        import time
        with self.lock:
            self._load()
            if name not in self.pools or not self.pools[name]:
                return self.get_key_without_lock(name, None)
                
            idx = self.indexes.get(name, 0)
            current_key = self.pools[name][idx % len(self.pools[name])]
            
            if current_key_exhausted:
                self.exhausted_keys[current_key] = time.time()
                
            self.indexes[name] = (idx + 1) % len(self.pools[name])
            self._save()
            return self.get_key_without_lock(name, None)

    def get_key_without_lock(self, name: str, fallback_env: Optional[str] = None) -> Optional[str]:
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
