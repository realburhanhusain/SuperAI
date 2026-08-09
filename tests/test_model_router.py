import pytest
from src.core.model_router import AliasRouter

def test_alias_router_resolve():
    router = AliasRouter({"router:fast": "gpt-3.5-turbo", "router:smart": "gpt-4"})
    
    assert router.resolve("router:fast") == "gpt-3.5-turbo"
    assert router.resolve("router:smart") == "gpt-4"
    assert router.resolve("unknown:model") == "unknown:model"

def test_alias_router_add_alias():
    router = AliasRouter()
    router.add_alias("router:cheap", "claude-3-haiku")
    
    assert router.resolve("router:cheap") == "claude-3-haiku"
