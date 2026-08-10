import pytest
import os
from src.core.model_router import AliasRouter

def test_alias_router_resolve():
    path = "test_alias1.json"
    router = AliasRouter(storage_path=path)
    router.add_alias("router:fast", "gpt-3.5-turbo")
    router.add_alias("router:smart", "gpt-4")
    
    assert router.resolve("router:fast") == "gpt-3.5-turbo"
    assert router.resolve("router:smart") == "gpt-4"
    assert router.resolve("unknown:model") == "unknown:model"
    if os.path.exists(path):
        os.remove(path)

def test_alias_router_add_alias():
    path = "test_alias2.json"
    router = AliasRouter(storage_path=path)
    router.add_alias("router:cheap", "claude-3-haiku")
    
    assert router.resolve("router:cheap") == "claude-3-haiku"
    if os.path.exists(path):
        os.remove(path)

def test_alias_router_default():
    path = "test_alias3.json"
    if os.path.exists(path):
        os.remove(path)
    router = AliasRouter(storage_path=path)
    
    assert router.resolve("gemini-cli") == "gemini-cli:latest"
    assert router.resolve("pi") == "pi:latest"
    
    if os.path.exists(path):
        os.remove(path)
