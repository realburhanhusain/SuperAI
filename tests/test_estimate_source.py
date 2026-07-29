"""
Canonical cost provenance (Phase 3 / V1-P1-4).

Provenance used to be spread across three fields meaning different things:
``cost_source`` (where the tokens came from), ``pricing_source`` (where the
rate came from), and ``estimate_source``, which existed on exactly one public
contract and reported ``pricing_source``'s vocabulary. A consumer could not
tell a metered number from a guessed one without knowing all three.

``estimate_source`` is now one field with three values ordered by trust:
``actual`` > ``registry`` > ``fallback``.
"""

from __future__ import annotations

from core.board_preflight import estimate_board
from core.cost_accounting import (
    ESTIMATE_SOURCES,
    aggregate_costs,
    from_usage,
    resolve_estimate_source,
)
from core.spend_guard import DEFAULT_ESTIMATE_USD, budget_precheck, estimate_for_model


# ---------------------------------------------------------------------------
# The resolver
# ---------------------------------------------------------------------------


def test_metered_usage_is_actual():
    assert resolve_estimate_source("usage", "registry") == "actual"
    assert resolve_estimate_source("usage", "heuristic") == "actual"


def test_local_models_are_actual_not_estimated():
    """A local/CLI model is a genuine $0 — nothing was estimated."""
    assert resolve_estimate_source("zero_local", "zero_local") == "actual"


def test_registry_rates_without_usage_are_registry():
    assert resolve_estimate_source("estimate", "registry") == "registry"
    assert resolve_estimate_source("estimate", "registry_io") == "registry"


def test_heuristic_rates_are_fallback():
    assert resolve_estimate_source("estimate", "heuristic") == "fallback"


def test_every_result_is_a_declared_value():
    for cost in ("usage", "estimate", "zero_local", "weird"):
        for pricing in ("registry", "registry_io", "heuristic", "zero_local", "?"):
            assert resolve_estimate_source(cost, pricing) in ESTIMATE_SOURCES


# ---------------------------------------------------------------------------
# Producers emit it
# ---------------------------------------------------------------------------


def test_from_usage_labels_real_usage_actual():
    out = from_usage("gpt-4o", prompt_tokens=100, completion_tokens=100)
    assert out["estimate_source"] == "actual"
    # Legacy fields still present for callers that read them.
    assert out["cost_source"] == "usage"
    assert "pricing_source" in out


def test_from_usage_labels_unknown_model_fallback():
    out = from_usage("totally-made-up-model-xyz", total_tokens=500, cost_source="estimate")
    assert out["estimate_source"] == "fallback"


def test_aggregate_takes_the_weakest_link():
    """One guessed row makes the whole total a guess."""
    agg = aggregate_costs(
        [
            {"model": "a", "tokens": 10, "estimated_cost_usd": 0.1, "estimate_source": "actual"},
            {"model": "b", "tokens": 10, "estimated_cost_usd": 0.1, "estimate_source": "fallback"},
        ]
    )
    assert agg["estimate_source"] == "fallback"


def test_aggregate_of_actuals_stays_actual():
    agg = aggregate_costs(
        [
            {"model": "a", "tokens": 10, "estimated_cost_usd": 0.1, "estimate_source": "actual"},
            {"model": "b", "tokens": 10, "estimated_cost_usd": 0.1, "estimate_source": "actual"},
        ]
    )
    assert agg["estimate_source"] == "actual"


# ---------------------------------------------------------------------------
# Pre-flight estimates
# ---------------------------------------------------------------------------


def test_known_model_is_priced_from_the_registry():
    """Not the old flat 0.1 regardless of model."""
    out = estimate_for_model("gpt-4o", tokens=1000)
    assert out["estimate_source"] == "registry"
    assert out["rate_per_1k"] and out["rate_per_1k"] > 0
    assert out["estimated_usd"] != DEFAULT_ESTIMATE_USD


def test_local_model_estimate_is_zero_and_actual():
    out = estimate_for_model("cli:claude", tokens=1000)
    assert out["estimated_usd"] == 0.0
    assert out["estimate_source"] == "actual"


def test_unknown_model_is_flagged_fallback():
    out = estimate_for_model("totally-made-up-model-xyz", tokens=1000)
    assert out["estimate_source"] == "fallback"


def test_no_model_keeps_the_legacy_constant():
    """Callers passing nothing must behave exactly as before."""
    out = estimate_for_model(None)
    assert out["estimated_usd"] == DEFAULT_ESTIMATE_USD
    assert out["estimate_source"] == "fallback"


def test_budget_precheck_accepts_a_model():
    assert budget_precheck(model="gpt-4o", tokens=1000, enforce=False) is not None


def test_explicit_estimate_still_wins():
    """An explicit estimated_usd must not be overridden by the registry."""
    blocked = budget_precheck(
        estimated_usd=999999.0, tokens=10, command_name="probe-cmd", enforce=True
    )
    assert isinstance(blocked, dict)


# ---------------------------------------------------------------------------
# Board preflight
# ---------------------------------------------------------------------------


def test_board_reports_the_weakest_member():
    """
    Regression: this used to read per[0]["pricing_source"].

    A board with one unpriced model could advertise a registry-grade estimate
    because only the first member was consulted — and in a different
    vocabulary from the canonical field.
    """
    board = estimate_board("x", ["gpt-4o", "totally-made-up-model-xyz"])
    assert board["estimate_source"] == "fallback"


def test_board_of_known_models_is_registry():
    board = estimate_board("x", ["gpt-4o"])
    assert board["estimate_source"] == "registry"


def test_board_of_local_models_is_actual():
    board = estimate_board("x", ["cli:claude"])
    assert board["estimate_source"] == "actual"


def test_empty_board_is_unknown_not_a_guess():
    board = estimate_board("x", [])
    assert board["estimate_source"] == "unknown"
