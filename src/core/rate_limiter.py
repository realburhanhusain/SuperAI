import time
from threading import Lock

class TokenBucketRateLimiter:
    """
    A thread-safe Token Bucket Rate Limiter.
    """
    def __init__(self, capacity: int, fill_rate: float):
        """
        :param capacity: Maximum number of tokens the bucket can hold.
        :param fill_rate: Number of tokens added to the bucket per second.
        """
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if fill_rate <= 0:
            raise ValueError("fill_rate must be > 0")
            
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = Lock()

    def _add_tokens(self):
        now = time.monotonic()
        elapsed = now - self.last_update
        new_tokens = elapsed * self.fill_rate
        if new_tokens > 0:
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_update = now

    def acquire(self, amount: int = 1) -> bool:
        """
        Attempt to acquire `amount` tokens.
        Returns True if successful, False otherwise.
        """
        with self._lock:
            self._add_tokens()
            if self.tokens >= amount:
                self.tokens -= amount
                return True
            return False

    def wait_and_acquire(self, amount: int = 1):
        """
        Wait until `amount` tokens are available and consume them.
        """
        if amount > self.capacity:
            raise ValueError(f"Cannot acquire {amount} tokens, capacity is {self.capacity}")
            
        while True:
            with self._lock:
                self._add_tokens()
                if self.tokens >= amount:
                    self.tokens -= amount
                    return
                deficit = amount - self.tokens
                wait_time = deficit / self.fill_rate
            
            # Sleep outside the lock
            time.sleep(wait_time)
