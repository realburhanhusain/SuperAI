import time
import pytest
import os
import glob
from pathlib import Path
from src.core.rate_limiter import TokenBucketRateLimiter

def cleanup_test_files():
    config_dir = Path.home() / ".superai" / "config"
    for f in glob.glob(str(config_dir / "rate_limit_test_*.json")):
        try: os.remove(f)
        except: pass
    for f in glob.glob(str(config_dir / "rate_limit_test_*.lock")):
        try: os.remove(f)
        except: pass

@pytest.fixture(autouse=True)
def run_around_tests():
    cleanup_test_files()
    yield
    cleanup_test_files()

def test_token_bucket_initial_capacity():
    limiter = TokenBucketRateLimiter(capacity=5, fill_rate=1, name="test_init")
    assert limiter.acquire(5) is True
    assert limiter.acquire(1) is False

def test_token_bucket_refill():
    limiter = TokenBucketRateLimiter(capacity=5, fill_rate=10, name="test_refill") # 10 tokens/sec
    assert limiter.acquire(5) is True
    assert limiter.acquire(1) is False
    
    # Wait for 0.2 seconds, which should refill ~2 tokens
    time.sleep(0.3)
    
    # We should be able to acquire at least 2 tokens
    assert limiter.acquire(2) is True
    
def test_wait_and_acquire():
    limiter = TokenBucketRateLimiter(capacity=5, fill_rate=20, name="test_wait")
    assert limiter.acquire(5) is True
    
    start = time.time()
    limiter.wait_and_acquire(2) # Needs 2 tokens -> 0.1s
    end = time.time()
    
    assert (end - start) >= 0.1

def test_wait_and_acquire_exceeds_capacity():
    limiter = TokenBucketRateLimiter(capacity=5, fill_rate=10, name="test_exceeds")
    with pytest.raises(ValueError):
        limiter.wait_and_acquire(10)
