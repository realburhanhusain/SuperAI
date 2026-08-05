import pytest
from pathlib import Path
from core.bandit_router import EpsilonGreedyBandit
from core.ab_routing import ABRouter

def test_bandit_decay_down_ranking(tmp_path: Path):
    path = tmp_path / "bandit.json"
    b = EpsilonGreedyBandit(epsilon=0.0, path=path)
    
    # Model A starts strong
    for _ in range(10):
        b.update("A", 1.0, decay=1.0) # no decay initially for setup
    
    assert b.select(["A", "B"]) == "A"
    
    # Model A starts failing, Model B starts succeeding
    # With decay=0.5, Model A's old rewards will decay rapidly
    for _ in range(5):
        b.update("A", 0.0, decay=0.5)
        b.update("B", 1.0, decay=0.5)
        
    status = b.status()
    # B should now be ranked higher than A
    assert b.select(["A", "B"]) == "B"

def test_bandit_pinning(tmp_path: Path):
    path = tmp_path / "bandit.json"
    b = EpsilonGreedyBandit(epsilon=0.0, path=path)
    
    b.update("A", 1.0)
    b.update("B", 0.0)
    
    # A is naturally better
    assert b.select(["A", "B"]) == "A"
    
    # Pin B
    b.pin("B")
    assert b.select(["A", "B"]) == "B"
    assert b.status()["pinned"] == "B"
    
    # Unpin
    b.unpin()
    assert b.select(["A", "B"]) == "A"
    assert b.status()["pinned"] is None

def test_ab_routing_pinning(tmp_path: Path):
    path = tmp_path / "ab.json"
    ab = ABRouter(path=path)
    ab.create("test_exp", "model_a", "model_b", traffic_b_pct=50.0, task_type="general")
    
    # Pin winner
    assert ab.pin_winner("test_exp", "model_b") is True
    
    # Should always pick model_b now
    for _ in range(10):
        assert ab.pick() == "model_b"
        
    # Unpin
    assert ab.unpin("test_exp") is True

def test_routing_stats_includes_status(tmp_path: Path):
    from core.routing_stats import summarize_routing
    res = summarize_routing()
    assert "bandit_status" in res
    assert "ab_routing" in res
