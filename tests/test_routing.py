"""Phase 2 routing / load balancer tests."""

from pathlib import Path

import pytest

from superai.core.load_balancer import (
    LoadBalancer,
    LoadBalancingStrategy,
    ProviderCandidate,
    parse_strategy,
)
from superai.core.model_registry import ModelRegistry
from superai.core.model_router import ModelRouter
from superai.core.routing_stats import compute_model_stats, summarize_routing
from superai.core.history import TaskHistory


def test_parse_strategy():
    assert parse_strategy("smart_fallback") == LoadBalancingStrategy.SMART_FALLBACK
    assert parse_strategy("LATENCY_BASED") == LoadBalancingStrategy.LATENCY_BASED
    assert parse_strategy("unknown") == LoadBalancingStrategy.SMART_FALLBACK


def test_scoring_prefers_coding_model(tmp_path: Path):
    # Use project models.json via default registry
    registry = ModelRegistry()
    router = ModelRouter(registry, LoadBalancer())
    best = router.get_best_model("Implement a FastAPI hello world endpoint")
    assert best is not None
    ranked = router.explain_selection("Implement a FastAPI hello world", top_k=5)
    assert ranked
    assert "score" in ranked[0]
    top_names = {r["model"] for r in ranked}
    # At least one strong coding model should appear in the top 5
    assert top_names & {
        "claude-4-sonnet",
        "deepseek-coder",
        "qwen2.5-coder",
        "gpt-4o",
    }
    # Top score should prefer high coding task_match over pure cheap/fast
    top_coding = max(
        (
            r
            for r in ranked
            if r["model"] in {"claude-4-sonnet", "deepseek-coder", "qwen2.5-coder"}
        ),
        key=lambda r: r["score"],
        default=None,
    )
    assert top_coding is not None
    assert top_coding["components"]["task_type_match"] >= 0.9


def test_load_balancer_fallback_and_breaker():
    lb = LoadBalancer(strategy=LoadBalancingStrategy.SMART_FALLBACK)
    attempts = []

    def call_fn(provider: str):
        attempts.append(provider)
        if provider == "bad":
            raise RuntimeError("fail")
        return {"status": "success", "response": "ok", "provider": provider}

    candidates = [
        ProviderCandidate(provider="bad", model_name="m"),
        ProviderCandidate(provider="good", model_name="m"),
    ]
    result = lb.execute_with_fallback(candidates, "m", call_fn, max_retries_per_provider=0)
    assert result["provider"] == "good"
    assert "bad" in attempts and "good" in attempts

    # Open circuit on bad
    cb = lb.get_circuit_breaker("bad")
    assert cb.failures >= 1


def test_routing_stats_from_history(tmp_path: Path):
    store = TaskHistory(history_dir=tmp_path)
    store.save(
        {
            "task_id": "a",
            "task": "x",
            "success": True,
            "model_used": "gpt-4o",
            "duration": 1.0,
            "steps": [{"model": "gpt-4o", "status": "success"}],
        }
    )
    store.save(
        {
            "task_id": "b",
            "task": "y",
            "success": False,
            "model_used": "gpt-4o",
            "duration": 2.0,
            "steps": [],
        }
    )
    stats = compute_model_stats(history=store, limit=10)
    assert "gpt-4o" in stats
    assert stats["gpt-4o"]["total"] == 2
    summary = summarize_routing(history=store, limit=10)
    assert summary["total_runs_sampled"] == 2
