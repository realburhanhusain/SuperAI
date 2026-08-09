import pytest
import os
from src.core.key_pool import KeyPool

def test_key_pool_initialization():
    path = "test_keypool1.json"
    pool = KeyPool(storage_path=path)
    pool.set_keys("OPENAI_API_KEY", ["key1", "key2"])
    assert pool.get_key("OPENAI_API_KEY") == "key1"
    if os.path.exists(path): os.remove(path)

def test_key_pool_empty_initialization():
    path = "test_keypool2.json"
    pool = KeyPool(storage_path=path)
    pool.set_keys("OPENAI_API_KEY", [])
    assert pool.get_key("OPENAI_API_KEY") is None
    if os.path.exists(path): os.remove(path)

def test_key_pool_rotation():
    path = "test_keypool3.json"
    pool = KeyPool(storage_path=path)
    pool.set_keys("OPENAI_API_KEY", ["key1", "key2", "key3"])
    assert pool.get_key("OPENAI_API_KEY") == "key1"
    
    assert pool.rotate("OPENAI_API_KEY") == "key2"
    assert pool.get_key("OPENAI_API_KEY") == "key2"
    
    assert pool.rotate("OPENAI_API_KEY") == "key3"
    assert pool.rotate("OPENAI_API_KEY") == "key1"
    if os.path.exists(path): os.remove(path)
