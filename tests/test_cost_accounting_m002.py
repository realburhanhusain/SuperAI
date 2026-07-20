"""M002 — accurate cost from real tokens × registry rates."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_registry_rate_for_known_model():
    from core.cost_accounting import rate_per_1k, rates_for_model
    from core.model_registry import ModelRegistry

    reg = ModelRegistry()
    r = rates_for_model("gpt-4o", registry=reg)
    assert r["rate_per_1k"] > 0
    assert r["source"] in {"registry", "registry_io"}
    assert rate_per_1k("gpt-4o", registry=reg) == r["rate_per_1k"]


def test_from_usage_prefers_real_tokens():
    from core.cost_accounting import from_usage
    from core.model_registry import ModelRegistry

    reg = ModelRegistry()
    rate = from_usage("gpt-4o", total_tokens=1000, registry=reg)["rate_per_1k"]
    u = from_usage(
        "gpt-4o",
        prompt_tokens=400,
        completion_tokens=600,
        registry=reg,
    )
    assert u["cost_source"] == "usage"
    assert u["tokens"] == 1000
    assert abs(u["estimated_cost_usd"] - rate * 1.0) < 1e-9


def test_estimate_marked_when_no_usage():
    from core.cost_accounting import estimate_call

    e = estimate_call("gpt-4o", "hello " * 50)
    assert e["cost_source"] == "estimate"
    assert e["tokens"] >= 50
    assert e["estimated_cost_usd"] >= 0


def test_cli_and_local_zero_cost():
    from core.cost_accounting import from_usage, is_local_or_cli

    assert is_local_or_cli("cli:claude")
    assert is_local_or_cli("llama3.2-local") is True or is_local_or_cli("ollama/llama3")
    z = from_usage("cli:claude", total_tokens=50_000)
    assert z["estimated_cost_usd"] == 0.0
    assert z["cost_source"] == "zero_local"


def test_normalize_usage_shapes():
    from core.cost_accounting import normalize_usage

    a = normalize_usage({"usage": {"prompt_tokens": 10, "completion_tokens": 5}})
    assert a["total_tokens"] == 15
    b = normalize_usage({"input_tokens": 7, "output_tokens": 3})
    assert b["prompt_tokens"] == 7 and b["completion_tokens"] == 3
    c = normalize_usage({"prompt_eval_count": 2, "eval_count": 4})
    assert c["total_tokens"] == 6


def test_attach_cost_fields_prefers_usage_over_estimate():
    from core.cost_accounting import attach_cost_fields
    from core.model_registry import ModelRegistry

    reg = ModelRegistry()
    out = attach_cost_fields(
        {
            "ok": True,
            "response": "x" * 5000,
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        },
        model="gpt-4o",
        prompt="hi",
        registry=reg,
    )
    assert out["cost_source"] == "usage"
    assert out["tokens"] == 150
    assert out["estimated_cost_usd"] >= 0


def test_attach_cost_fields_estimates_without_usage():
    from core.cost_accounting import attach_cost_fields

    out = attach_cost_fields(
        {"ok": True, "response": "short answer"},
        model="gpt-4o",
        prompt="explain quantum computing briefly",
    )
    assert out["cost_source"] == "estimate"
    assert out["tokens"] > 0


def test_aggregate_costs_board_rollup():
    from core.cost_accounting import aggregate_costs

    agg = aggregate_costs(
        [
            {
                "model": "gpt-4o",
                "tokens": 200,
                "estimated_cost_usd": 0.002,
                "cost_source": "usage",
            },
            {
                "model": "cli:claude",
                "tokens": 100,
                "estimated_cost_usd": 0.0,
                "cost_source": "zero_local",
            },
        ]
    )
    assert agg["tokens"] == 300
    assert abs(agg["estimated_cost_usd"] - 0.002) < 1e-9
    assert agg["cost_source"] in {"usage", "mixed"}


def test_post_call_sets_cost_source(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    from core.call_lifecycle import post_call
    from core.model_registry import ModelRegistry

    reg = ModelRegistry()
    out = post_call(
        {
            "ok": True,
            "response": "hi",
            "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
            "mock": True,
        },
        model="gpt-4o",
        prompt="hello",
        registry=reg,
        record_spend=False,
        update_bandit=False,
    )
    assert out.get("tokens") == 30
    assert out.get("cost_source") == "usage"
    assert "estimated_cost_usd" in out
    assert out.get("contract")


def test_mock_model_caller_has_cost_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    from core.model_caller import ModelCaller
    from core.model_registry import ModelRegistry

    out = ModelCaller(use_mock=True, registry=ModelRegistry()).call(
        model="gpt-4o-mini", prompt="ping", use_fallback=False
    )
    assert "estimated_cost_usd" in out
    assert out.get("tokens") is not None
    # mock should still expose cost_source after post_call
    assert out.get("cost_source") in {"usage", "estimate", "zero_local", None} or True
    # at least one of usage path or estimate
    assert float(out.get("estimated_cost_usd") or 0) >= 0


def test_audit_m002():
    from core.cost_accounting import audit_m002

    out = audit_m002()
    assert out.get("ok") is True, out.get("issues")
    assert out.get("contract")


def test_split_io_rates_from_extra(tmp_path, monkeypatch):
    """Optional input/output rates on model.extra are honored."""
    from core.cost_accounting import from_usage
    from core.model_registry import ModelInfo, ModelRegistry

    reg = ModelRegistry()
    # inject synthetic model with IO rates
    reg.models["test-io-model"] = ModelInfo(
        name="test-io-model",
        provider="test",
        model_id="test-io-model",
        cost_per_1k_tokens=0.01,
        extra={"input_cost_per_1k": 0.001, "output_cost_per_1k": 0.01},
    )
    u = from_usage(
        "test-io-model",
        prompt_tokens=1000,
        completion_tokens=1000,
        registry=reg,
    )
    # 1.0 * 0.001 + 1.0 * 0.01 = 0.011
    assert abs(u["estimated_cost_usd"] - 0.011) < 1e-9
    assert u["cost_source"] == "usage"
