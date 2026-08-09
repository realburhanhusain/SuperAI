from typing import List

class KeyPool:
    """A pool of API keys that can be rotated when rate limits (e.g. 429) are hit."""
    
    def __init__(self, keys: List[str]):
        if not keys:
            raise ValueError("At least one key must be provided")
        self.keys = list(keys)
        self.current_index = 0

    def get_key(self) -> str:
        """Get the currently active API key."""
        return self.keys[self.current_index]

    def rotate(self) -> str:
        """
        Rotate to the next key in the pool (round-robin).
        Useful when encountering HTTP 429 errors.
        Returns the new active key.
        """
        self.current_index = (self.current_index + 1) % len(self.keys)
        return self.get_key()
