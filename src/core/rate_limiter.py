import time
import json
import os
from pathlib import Path
from filelock import FileLock

class TokenBucketRateLimiter:
    """
    A process-safe Token Bucket Rate Limiter.
    """
    def __init__(self, capacity: int, fill_rate: float, name: str = "global"):
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if fill_rate <= 0:
            raise ValueError("fill_rate must be > 0")
            
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.name = name
        self.path = Path.home() / ".superai" / "config" / f"rate_limit_{name}.json"
        self.lock_path = Path.home() / ".superai" / "config" / f"rate_limit_{name}.lock"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = FileLock(str(self.lock_path))

    def _load(self) -> tuple[float, float]:
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("tokens", self.capacity), data.get("last_update", time.time())
            except Exception:
                pass
        return self.capacity, time.time()

    def _save(self, tokens: float, last_update: float):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"tokens": tokens, "last_update": last_update}, f)

    def acquire(self, amount: int = 1) -> bool:
        """Attempt to acquire `amount` tokens."""
        with self._lock:
            tokens, last_update = self._load()
            now = time.time()
            elapsed = now - last_update
            
            tokens = min(self.capacity, tokens + elapsed * self.fill_rate)
            
            if tokens >= amount:
                tokens -= amount
                self._save(tokens, now)
                return True
                
            self._save(tokens, now)
            return False

    def wait_and_acquire(self, amount: int = 1):
        """Wait until `amount` tokens are available and consume them."""
        if amount > self.capacity:
            raise ValueError(f"Cannot acquire {amount} tokens, capacity is {self.capacity}")
            
        while True:
            with self._lock:
                tokens, last_update = self._load()
                now = time.time()
                elapsed = now - last_update
                
                tokens = min(self.capacity, tokens + elapsed * self.fill_rate)
                
                if tokens >= amount:
                    tokens -= amount
                    self._save(tokens, now)
                    return
                    
                self._save(tokens, now)
                deficit = amount - tokens
                wait_time = deficit / self.fill_rate
            
            time.sleep(max(wait_time, 0.1))
