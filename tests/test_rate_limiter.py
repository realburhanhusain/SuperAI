import time
import pytest
from src.core.rate_limiter import TokenBucketRateLimiter

def test_token_bucket_initial_capacity():
    limiter = TokenBucketRateLimiter(capacity=5, fill_rate=1)
    assert limiter.acquire(5) is True
    assert limiter.acquire(1) is False

def test_token_bucket_refill():
    limiter = TokenBucketRateLimiter(capacity=5, fill_rate=10) # 10 tokens/sec
    assert limiter.acquire(5) is True
    assert limiter.acquire(1) is False
    
    # Wait for 0.2 seconds, which should refill ~2 tokens
    time.sleep(0.25)
    
    # We should be able to acquire at least 2 tokens
    assert limiter.acquire(2) is True
    
def test_wait_and_acquire():
    limiter = TokenBucketRateLimiter(capacity=5, fill_rate=20)
    assert limiter.acquire(5) is True
    
    start = time.time()
    limiter.wait_and_acquire(2) # Needs 2 tokens -> 0.1s
    end = time.time()
    
    assert (end - start) >= 0.1

def test_wait_and_acquire_exceeds_capacity():
    limiter = TokenBucketRateLimiter(capacity=5, fill_rate=10)
    with pytest.raises(ValueError):
        limiter.wait_and_acquire(10)
