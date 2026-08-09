import pytest
from src.core.key_pool import KeyPool

def test_key_pool_initialization():
    pool = KeyPool(["key1", "key2"])
    assert pool.get_key() == "key1"

def test_key_pool_empty_initialization():
    with pytest.raises(ValueError):
        KeyPool([])

def test_key_pool_rotation():
    pool = KeyPool(["key1", "key2", "key3"])
    assert pool.get_key() == "key1"
    
    assert pool.rotate() == "key2"
    assert pool.get_key() == "key2"
    
    assert pool.rotate() == "key3"
    assert pool.rotate() == "key1"
