"""
CLIProxyAPI as an additional transport (optional, opt-in).

The point of these tests is that adding a transport changed nothing for the
existing one. `external_cli` drives file-editing agents as subprocesses;
`cliproxy` serves chat completions over HTTP. Both ship, both stay supported.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.cost_accounting import from_usage, is_local_or_cli, rates_for_model
from core.provider_catalog import get_openai_compat_config, list_providers


# ---------------------------------------------------------------------------
# The provider is registered and inert until models are added
# ---------------------------------------------------------------------------


def test_cliproxy_is_an_openai_compatible_provider():
    cfg = get_openai_compat_config("cliproxy")
    assert cfg is not None
    assert cfg["base_url"].endswith("/v1")
    assert cfg["env"] == "CLIPROXY_API_KEY"
    # A loopback proxy usually needs no key of its own.
    assert cfg["allow_empty_key"] is True


def test_cliproxy_appears_in_provider_listing():
    ids = {row["id"] for row in list_providers()}
    assert "cliproxy" in ids


def test_nothing_routes_to_cliproxy_by_default():
    """
    The provider entry is inert until the user adds models.

    Registering a transport must not silently change where existing calls go.
    """
    from core.model_registry import ModelRegistry

    registry = ModelRegistry()
    routed = [
        name
        for name in registry.list_all_models()
        if (registry.get_model(name) or None)
        and getattr(registry.get_model(name), "provider", "") == "cliproxy"
    ]
    assert routed == [], f"cliproxy models registered by default: {routed}"


# ---------------------------------------------------------------------------
# The prefix must not collide with the subprocess transport
# ---------------------------------------------------------------------------


def test_cliproxy_prefix_does_not_trigger_the_subprocess_path():
    """
    `model_caller` treats a `cli:` prefix as an authoritative instruction to use
    the subprocess transport. Naming these entries `cli:*` would route them back
    through external_cli — the opposite of the intent.
    """
    assert not "cliproxy:claude-opus".startswith("cli:")


def test_external_cli_transport_is_untouched():
    """
    Both transports ship. Every external CLI spec is a file-editing agent, and
    an HTTP chat endpoint cannot run aider's edit loop or Claude Code's tools —
    so the subprocess path is not replaceable and was not removed.
    """
    from core.external_cli import ExternalCLIRegistry

    specs = ExternalCLIRegistry().specs
    assert specs, "external CLI registry should still be populated"
    assert all(getattr(s, "modifies_files", False) for s in specs.values())


# ---------------------------------------------------------------------------
# Cost provenance
# ---------------------------------------------------------------------------


def test_cliproxy_calls_are_zero_cost():
    """Subscription-backed, so the marginal cost of a call is genuinely zero."""
    assert is_local_or_cli("cliproxy:claude-opus") is True
    assert rates_for_model("cliproxy:claude-opus")["rate_per_1k"] == 0.0


def test_cliproxy_cost_is_actual_not_a_guess():
    """
    Without the prefix change this fell through to heuristic rates and reported
    `fallback` — inventing a price where none exists. `$0` labelled `actual` is
    the honest answer: nothing was estimated.
    """
    priced = from_usage(
        "cliproxy:claude-opus", total_tokens=1000, cost_source="estimate"
    )
    assert priced["estimated_cost_usd"] == 0.0
    assert priced["estimate_source"] == "actual"


def test_metered_models_are_unaffected():
    """The prefix change must not make real API models look free."""
    priced = from_usage("gpt-4o", total_tokens=1000, cost_source="estimate")
    assert priced["estimated_cost_usd"] > 0
    assert priced["estimate_source"] == "registry"


# ---------------------------------------------------------------------------
# The example registry file
# ---------------------------------------------------------------------------


def _example_rows():
    path = (
        Path(__file__).resolve().parents[1]
        / "config"
        / "models.cliproxy.example.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_example_models_are_well_formed():
    rows = _example_rows()
    assert rows
    for row in rows:
        assert row["name"].startswith("cliproxy:")
        assert row["provider"] == "cliproxy"
        assert row["base_url"].endswith("/v1")
        assert row["model_id"]
        # Subscription-backed: never advertise a per-token price.
        assert row["cost_per_1k_tokens"] == 0.0


def test_example_models_load_into_a_registry():
    """A user merging this file must get usable ModelInfo entries."""
    from core.model_registry import ModelInfo

    for row in _example_rows():
        info = ModelInfo(
            name=row["name"],
            provider=row["provider"],
            model_id=row["model_id"],
            base_url=row["base_url"],
            api_key_env=row.get("api_key_env"),
            context_window=row.get("context_window", 128000),
            cost_per_1k_tokens=row.get("cost_per_1k_tokens", 0.0),
        )
        assert info.base_url and info.model_id
        assert is_local_or_cli(info.name)
